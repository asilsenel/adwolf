"""
Ad Platform MVP - Insight Tasks

Celery tasks for AI insight generation and daily digests.
Uses campaign-level data for targeted, actionable insights.
"""

import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from app.tasks import celery_app
from app.core.config import settings
from app.core.supabase import get_supabase_service

logger = logging.getLogger(__name__)


# Enhanced system prompt for campaign-level insight generation
INSIGHT_SYSTEM_PROMPT = """
Sen deneyimli bir dijital pazarlama uzmanissin. Reklam performans verilerini kampanya bazinda analiz edip
somut, uygulanabilir insights uretiyorsun.

Gorevin:
1. Kampanya bazinda performansi analiz et (en cok harcayan, en iyi/kotu performans gosterenler)
2. Anomalileri tespit et (harcama artislari, CTR dususleri, donusum kayiplari)
3. Butce optimizasyonu onerilerinde bulun (kampanyalar arasi butce dagitimi)
4. Trend degisikliklerini yorumla (haftalik karsilastirma)
5. Somut aksiyon onerileri sun (hangi kampanya icin ne yapilmali)

Kurallar:
- HER insight belirli bir kampanyaya veya hesaba yonelik olsun (genel ifadelerden kacin)
- Somut verilere dayan (yuzde degisimler, mutlak rakamlar)
- Oncelik belirleme: spend_spike, conversion_drop => critical/high; optimization => medium; genel bilgi => low
- Turkce ve profesyonel bir dil kullan
- Maksimum 5 insight uret, en onemlilere odaklan
- Her aksiyon icin platform belirt (google_ads veya meta_ads)

Cikti formati (strict JSON):
{
    "insights": [
        {
            "insight_type": "performance|optimization|alert|opportunity|anomaly",
            "severity": "low|medium|high|critical",
            "category": "budget|targeting|creative|bidding|general",
            "platform": "google_ads|meta_ads|null",
            "entity_type": "campaign|account|org",
            "entity_id": "kampanya_id veya null",
            "title": "Kisa baslik (max 100 karakter)",
            "summary": "1-2 cumle ozet",
            "detailed_analysis": "Detayli analiz (3-5 cumle)",
            "actions": [
                {
                    "action_type": "pause_campaign|increase_budget|decrease_budget|optimize_targeting|adjust_bidding|review_creative",
                    "platform": "google_ads|meta_ads",
                    "title": "Aksiyon basligi",
                    "description": "Ne yapilmali, detayli aciklama",
                    "rationale": "Neden bu aksiyon oneriliyor",
                    "expected_impact": "Beklenen etki"
                }
            ]
        }
    ]
}
"""


@celery_app.task(name="app.tasks.insight_tasks.generate_daily_insights")
def generate_daily_insights():
    """
    Generate AI insights for all organizations.

    Scheduled to run daily at 7 AM.
    """
    import asyncio
    asyncio.run(_generate_daily_insights_async())


async def _generate_daily_insights_async():
    """Async implementation of generate_daily_insights."""
    supabase = get_supabase_service()

    # Get all active organizations
    result = supabase.client.table("organizations") \
        .select("id") \
        .eq("is_active", True) \
        .execute()

    orgs = result.data or []
    logger.info(f"Generating insights for {len(orgs)} organizations")

    for org in orgs:
        try:
            await generate_org_insights(org["id"])
        except Exception as e:
            logger.error(f"Failed to generate insights for org {org['id']}: {e}")


async def generate_org_insights(org_id: str) -> list[dict]:
    """
    Generate insights for a specific organization using campaign-level data.

    Returns list of created insight dicts.
    """
    from openai import AsyncOpenAI
    from app.services.insight_data_collector import InsightDataCollector

    supabase = get_supabase_service()
    collector = InsightDataCollector(supabase)

    # Collect rich campaign-level data
    org_data = await collector.collect_org_data(org_id)

    if not org_data.get("has_data"):
        logger.info(f"No data to analyze for org {org_id}")
        return []

    # Build context for AI
    metrics_context = json.dumps(org_data, ensure_ascii=False, default=str)

    # Check OpenAI API key
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, skipping insight generation")
        return []

    # Call OpenAI
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                {"role": "user", "content": metrics_context},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        result = json.loads(response.choices[0].message.content)
        insights = result.get("insights", [])

        created_insights = []

        # Save insights to database with CORRECT column names
        for insight_data in insights:
            try:
                insight = await supabase.create_insight({
                    "org_id": org_id,
                    "insight_type": insight_data.get("insight_type", "performance"),
                    "severity": insight_data.get("severity", "medium"),
                    "category": insight_data.get("category"),
                    "platform": insight_data.get("platform"),
                    "entity_type": insight_data.get("entity_type", "org"),
                    "entity_id": insight_data.get("entity_id"),
                    "title": insight_data.get("title", "Untitled Insight"),
                    "summary": insight_data.get("summary", ""),
                    "detailed_analysis": insight_data.get("detailed_analysis"),
                    "ai_model": settings.openai_model,
                    "ai_confidence": 0.8,
                    "metric_data": org_data.get("org_totals"),
                    "comparison_period": org_data.get("period"),
                })

                created_insights.append(insight)

                # Save recommended actions with CORRECT column names
                for action_data in insight_data.get("actions", []):
                    try:
                        supabase.client.table("recommended_actions").insert({
                            "insight_id": insight["id"],
                            "org_id": org_id,
                            "action_type": action_data.get("action_type", "review_creative"),
                            "platform": action_data.get("platform", insight_data.get("platform", "google_ads")),
                            "title": action_data.get("title", ""),
                            "description": action_data.get("description", "Detay yok"),
                            "rationale": action_data.get("rationale"),
                            "expected_impact": action_data.get("expected_impact"),
                            "is_executable": False,
                            "priority": 50,
                            "status": "pending",
                        }).execute()
                    except Exception as ae:
                        logger.error(f"Failed to save action for insight {insight['id']}: {ae}")

            except Exception as ie:
                logger.error(f"Failed to save insight: {ie}")

        logger.info(f"Generated {len(created_insights)} insights for org {org_id}")
        return created_insights

    except Exception as e:
        logger.error(f"OpenAI API error for org {org_id}: {e}")
        raise


@celery_app.task(name="app.tasks.insight_tasks.send_daily_digests")
def send_daily_digests():
    """
    Send daily digest emails/WhatsApp.

    Scheduled to run daily at 9 AM.
    """
    import asyncio
    asyncio.run(_send_daily_digests_async())


async def _send_daily_digests_async():
    """Async implementation of send_daily_digests."""
    supabase = get_supabase_service()

    # Get all organizations
    result = supabase.client.table("organizations") \
        .select("id") \
        .eq("is_active", True) \
        .execute()

    orgs = result.data or []
    logger.info(f"Generating digests for {len(orgs)} organizations")

    for org in orgs:
        try:
            await generate_daily_digest(org["id"])
        except Exception as e:
            logger.error(f"Failed to generate digest for org {org['id']}: {e}")


async def generate_daily_digest(org_id: str):
    """Generate and send daily digest for an organization."""
    from openai import AsyncOpenAI

    supabase = get_supabase_service()

    today = date.today()
    yesterday = today - timedelta(days=1)

    # Get yesterday's metrics
    metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=yesterday.isoformat(),
        date_to=yesterday.isoformat(),
    )

    # Get today's insights
    insights = await supabase.get_insights(org_id=org_id, limit=5)

    # Aggregate metrics (use correct column name: spend, not spend_micros)
    total_impressions = sum(int(m.get("impressions", 0) or 0) for m in metrics)
    total_clicks = sum(int(m.get("clicks", 0) or 0) for m in metrics)
    total_spend = sum(float(m.get("spend", 0) or 0) for m in metrics)
    total_conversions = sum(float(m.get("conversions", 0) or 0) for m in metrics)

    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, skipping digest generation")
        return

    # Generate summary with AI
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        digest_prompt = f"""
        Asagidaki verilerle kisa bir gunluk ozet yaz (maksimum 3-4 cumle):

        Tarih: {yesterday.isoformat()}
        Impressions: {total_impressions:,}
        Clicks: {total_clicks:,}
        Harcama: {total_spend:,.2f} TRY
        Donusum: {total_conversions:.1f}

        Onemli insight'lar:
        {json.dumps([i.get("title") for i in insights], ensure_ascii=False)}

        Tarz: Dostca, profesyonel, kisa.
        """

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "user", "content": digest_prompt},
            ],
            temperature=0.5,
            max_tokens=300,
        )

        summary = response.choices[0].message.content

        # Save digest
        supabase.client.table("daily_digests").insert({
            "org_id": org_id,
            "digest_date": yesterday.isoformat(),
            "title": f"Gunluk Ozet - {yesterday.strftime('%d %B %Y')}",
            "summary": summary,
            "total_spend": total_spend,
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "insight_ids": [i.get("id") for i in insights],
            "ai_model": settings.openai_model,
        }).execute()

        # TODO: Send via email/WhatsApp based on user preferences
        logger.info(f"Generated digest for org {org_id}")

    except Exception as e:
        logger.error(f"Failed to generate digest for org {org_id}: {e}")
        raise
