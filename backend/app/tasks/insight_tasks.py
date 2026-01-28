"""
Ad Platform MVP - Insight Tasks

Celery tasks for AI insight generation and daily digests.
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


# System prompt for insight generation
INSIGHT_SYSTEM_PROMPT = """
Sen deneyimli bir dijital pazarlama uzmanısın. Reklam performans verilerini analiz edip
actionable insights üretiyorsun.

Görevin:
1. Verilerdeki önemli trendleri tespit et
2. Performans anomalilerini belirle
3. Optimizasyon fırsatlarını tanımla
4. Somut aksiyon önerileri sun

Kurallar:
- Somut verilere dayan (yüzde değişimler, mutlak rakamlar)
- Karşılaştırma yap (önceki dönem, hedefler)
- Net ve uygulanabilir öneriler sun
- Türkçe ve profesyonel bir dil kullan
- Her insight için priority belirle (low, medium, high, critical)

Çıktı formatı:
{
    "insights": [
        {
            "type": "performance|optimization|alert|opportunity|anomaly",
            "priority": "low|medium|high|critical",
            "title": "Kısa başlık",
            "summary": "1-2 cümle özet",
            "detailed_analysis": "Detaylı analiz",
            "actions": [
                {
                    "title": "Aksiyon başlığı",
                    "description": "Ne yapılmalı",
                    "action_type": "pause_campaign|increase_budget|decrease_budget|optimize_targeting",
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


async def generate_org_insights(org_id: str):
    """Generate insights for a specific organization."""
    from openai import AsyncOpenAI
    
    supabase = get_supabase_service()
    
    # Get metrics for last 7 days and previous 7 days
    today = date.today()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)
    
    # Get connected accounts
    accounts = await supabase.get_connected_accounts(org_id)
    if not accounts:
        logger.info(f"No active accounts for org {org_id}")
        return
    
    # Get current period metrics
    current_metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=week_ago.isoformat(),
        date_to=today.isoformat(),
    )
    
    # Get previous period metrics
    previous_metrics = await supabase.get_daily_metrics(
        org_id=org_id,
        date_from=two_weeks_ago.isoformat(),
        date_to=week_ago.isoformat(),
    )
    
    if not current_metrics:
        logger.info(f"No metrics for org {org_id}")
        return
    
    # Aggregate metrics
    def aggregate_metrics(metrics_list):
        return {
            "impressions": sum(m.get("impressions", 0) for m in metrics_list),
            "clicks": sum(m.get("clicks", 0) for m in metrics_list),
            "spend": sum(m.get("spend_micros", 0) for m in metrics_list) / 1_000_000,
            "conversions": sum(float(m.get("conversions", 0)) for m in metrics_list),
            "conversion_value": sum(m.get("conversion_value_micros", 0) for m in metrics_list) / 1_000_000,
        }
    
    current_agg = aggregate_metrics(current_metrics)
    previous_agg = aggregate_metrics(previous_metrics)
    
    # Calculate changes
    def calc_change(current, previous):
        if previous == 0:
            return None
        return round((current - previous) / previous * 100, 2)
    
    metrics_context = {
        "period": f"{week_ago.isoformat()} - {today.isoformat()}",
        "comparison_period": f"{two_weeks_ago.isoformat()} - {week_ago.isoformat()}",
        "current": current_agg,
        "previous": previous_agg,
        "changes": {
            "impressions_change": calc_change(current_agg["impressions"], previous_agg["impressions"]),
            "clicks_change": calc_change(current_agg["clicks"], previous_agg["clicks"]),
            "spend_change": calc_change(current_agg["spend"], previous_agg["spend"]),
            "conversions_change": calc_change(current_agg["conversions"], previous_agg["conversions"]),
        },
        "accounts": len(accounts),
    }
    
    # Call OpenAI
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": INSIGHT_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(metrics_context, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        
        result = json.loads(response.choices[0].message.content)
        insights = result.get("insights", [])
        
        # Save insights to database
        for insight_data in insights:
            insight = await supabase.create_insight({
                "org_id": org_id,
                "type": insight_data.get("type", "performance"),
                "priority": insight_data.get("priority", "medium"),
                "title": insight_data.get("title"),
                "summary": insight_data.get("summary"),
                "detailed_analysis": insight_data.get("detailed_analysis"),
                "ai_model": settings.openai_model,
                "ai_confidence": 0.8,
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "metrics_snapshot": metrics_context,
                "comparison_period": "last_7_days_vs_previous",
            })
            
            # Save recommended actions
            for action_data in insight_data.get("actions", []):
                supabase.client.table("recommended_actions").insert({
                    "insight_id": insight["id"],
                    "org_id": org_id,
                    "title": action_data.get("title"),
                    "description": action_data.get("description"),
                    "action_type": action_data.get("action_type"),
                    "expected_impact": action_data.get("expected_impact"),
                    "status": "pending",
                }).execute()
        
        logger.info(f"Generated {len(insights)} insights for org {org_id}")
        
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
    
    # Aggregate metrics
    total_impressions = sum(m.get("impressions", 0) for m in metrics)
    total_clicks = sum(m.get("clicks", 0) for m in metrics)
    total_spend = sum(m.get("spend_micros", 0) for m in metrics) / 1_000_000
    total_conversions = sum(float(m.get("conversions", 0)) for m in metrics)
    
    # Generate summary with AI
    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        digest_prompt = f"""
        Aşağıdaki verilerle kısa bir günlük özet yaz (maksimum 3-4 cümle):
        
        Tarih: {yesterday.isoformat()}
        Impressions: {total_impressions:,}
        Clicks: {total_clicks:,}
        Harcama: ₺{total_spend:,.2f}
        Dönüşüm: {total_conversions:.1f}
        
        Önemli insight'lar:
        {json.dumps([i.get("title") for i in insights], ensure_ascii=False)}
        
        Tarz: Dostça, profesyonel, kısa.
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
            "title": f"Günlük Özet - {yesterday.strftime('%d %B %Y')}",
            "summary": summary,
            "total_spend_micros": int(total_spend * 1_000_000),
            "total_impressions": total_impressions,
            "total_clicks": total_clicks,
            "total_conversions": total_conversions,
            "insight_ids": [i.get("id") for i in insights],
            "ai_model": settings.openai_model,
            "tokens_used": response.usage.total_tokens,
        }).execute()
        
        # TODO: Send via email/WhatsApp based on user preferences
        logger.info(f"Generated digest for org {org_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate digest for org {org_id}: {e}")
        raise
