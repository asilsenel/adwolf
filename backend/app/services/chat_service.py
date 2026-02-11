"""
Ad Platform MVP - Chat Service

Core service for AI Chat Assistant using OpenAI Assistants API.
Handles thread management, message streaming, and tool calling.
Includes LLM pre-processing for query enrichment and DB context fallback.
"""

import json
import logging
from datetime import date, timedelta
from typing import AsyncGenerator, Optional

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.supabase import SupabaseService, get_supabase_service
from app.core.security import decrypt_token
from app.services.insight_data_collector import InsightDataCollector

logger = logging.getLogger(__name__)


# ===========================================
# QUERY ENRICHMENT PROMPT
# ===========================================

QUERY_ENRICHMENT_PROMPT = """Sen bir reklam platformu AI asistanının ön-işleyicisisin.
Kullanıcının mesajını analiz et ve asistanın doğru tool'ları çağırabilmesi için mesajı zenginleştir.

Mevcut tool'lar:
1. get_account_summary - Bağlı hesapları listeler (platform filtresi: google_ads, meta_ads)
2. get_campaign_list - Bir hesabın kampanyalarını listeler (account_id gerekir)
3. get_performance_metrics - Tarih aralığında performans metrikleri (date_from, date_to gerekir)
4. get_performance_comparison - Haftalık/aylık karşılaştırma (period: weekly/monthly)
5. get_recent_insights - AI insight'larını getirir
6. execute_gaql_query - Google Ads Query Language sorgusu (account_id ve query gerekir)

Bugünün tarihi: {today}

Kurallar:
- Kullanıcının sorusunu anla ve hangi tool'un çağrılması gerektiğini belirle
- Eğer tarih belirtilmemişse, son 7 gün veya son 30 gün gibi makul bir aralık öner
- "Performansım nasıl?" gibi genel sorularda birden fazla tool çağrısı gerekebilir
- Google Ads'e özel sorularda (anahtar kelimeler, reklam grupları, reklam metinleri, kalite puanı, açılış sayfası, hedefleme, teklif stratejisi vb.) execute_gaql_query tool'unu kullan
- Mesajı Türkçe olarak zenginleştir
- Sadece zenginleştirilmiş mesajı döndür, başka açıklama ekleme
- Eğer mesaj zaten yeterince açıksa, olduğu gibi döndür
- ÖNEMLİ: Hesap ID'lerini mutlaka mesaja ekle. Kullanıcıdan hesap seçmesini bekleme, mevcut hesapları doğrudan kullan.
- Birden fazla hesap varsa tümünü dahil et. Tek hesap varsa direkt onu kullan.

Aşağıda kullanıcının mevcut hesap bilgileri var:
{account_context}

Kullanıcının orijinal mesajı: {message}

Zenginleştirilmiş mesaj (hesap ID'lerini dahil et):"""


# ===========================================
# GAQL QUERY GENERATION PROMPT
# ===========================================

GAQL_GENERATION_PROMPT = """Sen bir Google Ads Query Language (GAQL) uzmanısın.
Kullanıcının doğal dildeki sorusuna uygun bir GAQL SELECT sorgusu oluştur.

Bugünün tarihi: {today}

Kullanılabilir GAQL kaynakları ve alanları:

1. campaign (Kampanya):
   - campaign.id, campaign.name, campaign.status, campaign.advertising_channel_type
   - campaign_budget.amount_micros
   - metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.conversions_value
   - metrics.ctr, metrics.average_cpc, metrics.average_cpm, metrics.cost_per_conversion
   - segments.date

2. ad_group (Reklam Grubu):
   - ad_group.id, ad_group.name, ad_group.status, ad_group.type
   - campaign.id, campaign.name
   - metrics.* (aynı metrikler)
   - segments.date

3. ad_group_ad (Reklam):
   - ad_group_ad.ad.id, ad_group_ad.ad.type, ad_group_ad.status
   - ad_group_ad.ad.expanded_text_ad.headline_part1, ad_group_ad.ad.expanded_text_ad.headline_part2
   - ad_group_ad.ad.responsive_search_ad.headlines, ad_group_ad.ad.responsive_search_ad.descriptions
   - ad_group_ad.ad.final_urls
   - metrics.*
   - segments.date

4. keyword_view (Anahtar Kelime):
   - ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type
   - ad_group_criterion.quality_info.quality_score
   - ad_group_criterion.status
   - ad_group.name, campaign.name
   - metrics.*
   - segments.date

5. search_term_view (Arama Terimleri):
   - search_term_view.search_term
   - campaign.name, ad_group.name
   - metrics.*
   - segments.date

6. customer (Hesap):
   - customer.id, customer.descriptive_name, customer.currency_code
   - metrics.*
   - segments.date

7. geographic_view (Coğrafi):
   - geographic_view.country_criterion_id
   - campaign.name
   - metrics.*
   - segments.date

8. gender_view, age_range_view (Demografi):
   - ad_group_criterion.gender.type, ad_group_criterion.age_range.type
   - metrics.*

9. landing_page_view (Açılış Sayfası):
   - landing_page_view.unexpanded_final_url
   - metrics.*
   - segments.date

GAQL Kuralları:
- Sadece SELECT sorguları yaz
- WHERE ile filtreleme yap (tarih aralığı, durum vb.)
- ORDER BY ile sıralama ekle (en çok harcama, en iyi CTR vb.)
- LIMIT ekle (varsayılan: 20)
- Tarih formatı: 'YYYY-MM-DD'
- Enum değerleri: ENABLED, PAUSED, REMOVED
- cost_micros 1,000,000'a bölünerek gerçek para birimine çevrilir
- Tarih belirtilmemişse son 30 günü kullan

Örnekler:
- "En çok harcama yapan kampanyalar" →
  SELECT campaign.name, metrics.cost_micros, metrics.clicks, metrics.impressions, metrics.ctr FROM campaign WHERE segments.date DURING LAST_30_DAYS AND campaign.status = 'ENABLED' ORDER BY metrics.cost_micros DESC LIMIT 10

- "Anahtar kelime performansı" →
  SELECT ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type, metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions, metrics.ctr, ad_group_criterion.quality_info.quality_score FROM keyword_view WHERE segments.date DURING LAST_30_DAYS ORDER BY metrics.cost_micros DESC LIMIT 20

- "Kalite puanı düşük anahtar kelimeler" →
  SELECT ad_group_criterion.keyword.text, ad_group_criterion.quality_info.quality_score, metrics.impressions, metrics.clicks, metrics.cost_micros, campaign.name FROM keyword_view WHERE segments.date DURING LAST_30_DAYS AND ad_group_criterion.status = 'ENABLED' ORDER BY ad_group_criterion.quality_info.quality_score ASC LIMIT 20

Kullanıcının sorusu: {question}

Sadece GAQL sorgusunu döndür, başka açıklama ekleme. Eğer soru GAQL ile cevaplanamıyorsa "NOT_APPLICABLE" döndür."""


# ===========================================
# SYSTEM PROMPT - Performance Marketing Expert
# ===========================================

SYSTEM_PROMPT = """Sen AdWolf platformunun AI asistanısın. Deneyimli bir performans pazarlama (performance marketing) uzmanısın.

## Görevlerin:
1. **Kampanya Analizi**: Google Ads ve Meta Ads kampanyalarını detaylı analiz et
2. **Metrik Yorumlama**: CTR, CPC, CPA, ROAS gibi metrikleri yorumla ve benchmark'larla karşılaştır
3. **Bütçe Optimizasyonu**: Kampanyalar arası bütçe dağılımı öner
4. **Anomali Tespiti**: Harcama artışları, dönüşüm düşüşleri gibi anomalileri tespit et
5. **Strateji Danışmanlığı**: Dijital pazarlama stratejisi konusunda danışmanlık yap

## Kurallar:
- Türkçe yanıt ver, profesyonel ama samimi bir dil kullan
- Somut verilere dayan: yüzde değişimler, mutlak rakamlar, tarih aralıkları
- Para birimi TRY (Türk Lirası) olarak göster
- Tabloları ve listeleri kullanarak bilgiyi düzenli sun
- Kullanıcının sorularını doğrudan cevapla, gereksiz bilgi verme
- Tool'ları kullanarak gerçek veriye eriş, tahmin yapma
- Eğer veri yoksa veya yetersizse, bunu açıkça belirt

## ÖNEMLİ - Hesap Seçimi:
- Kullanıcıdan hesap seçmesini İSTEME. Mevcut hesapları otomatik olarak kullan.
- Mesajda hangi hesap bilgisi verilmişse onu kullan.
- Birden fazla hesap varsa, TÜMÜ için verileri getir ve birlikte sun.
- Tek hesap varsa, doğrudan o hesabı kullan.
- Hesap bilgisi zenginleştirilmiş mesajda verilmiştir, oradan account_id'yi al.

## Metrik Bilgisi:
- **CTR** (Click-Through Rate): Tıklama oranı. İyi: >2%, Kötü: <0.5%
- **CPC** (Cost Per Click): Tıklama başı maliyet. Düşük = iyi
- **CPA** (Cost Per Acquisition): Dönüşüm başı maliyet. Düşük = iyi
- **ROAS** (Return on Ad Spend): Reklam harcaması getirisi. 1'den büyük = kârlı
- **CPM** (Cost Per Mille): 1000 gösterim başı maliyet

## Yanıt Formatı:
- Kısa ve öz cevaplar ver (gereksiz uzun metinler yazma)
- Sayıları formatla: 1,234.56 TRY şeklinde
- Karşılaştırmalarda ok işaretleri kullan: ↑ artış, ↓ düşüş
- Önemli noktaları **kalın** yaz
"""


# ===========================================
# TOOL DEFINITIONS for OpenAI Assistants API
# ===========================================

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_account_summary",
            "description": "Kullanıcının bağlı reklam hesaplarının özetini getirir. Platform, hesap adı, durum bilgileri.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "enum": ["google_ads", "meta_ads"],
                        "description": "Filtrelemek için platform (opsiyonel)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_campaign_list",
            "description": "Belirli bir hesabın kampanyalarını listeler. Kampanya adı, durumu, bütçe bilgileri.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Hesap ID'si (zorunlu)"
                    }
                },
                "required": ["account_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance_metrics",
            "description": "Belirli tarih aralığında performans metriklerini getirir. Impressions, clicks, spend, conversions, CTR, CPC, CPA, ROAS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_from": {
                        "type": "string",
                        "description": "Başlangıç tarihi (YYYY-MM-DD)"
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Bitiş tarihi (YYYY-MM-DD)"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Hesap ID filtresi (opsiyonel)"
                    },
                    "campaign_id": {
                        "type": "string",
                        "description": "Kampanya ID filtresi (opsiyonel)"
                    }
                },
                "required": ["date_from", "date_to"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_performance_comparison",
            "description": "Haftalık veya aylık performans karşılaştırması yapar. Mevcut dönem vs önceki dönem, değişim yüzdeleri ve anomaliler.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {
                        "type": "string",
                        "enum": ["weekly", "monthly"],
                        "description": "Karşılaştırma periyodu"
                    }
                },
                "required": ["period"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_insights",
            "description": "Son oluşturulan AI insight'larını getirir. Anomaliler, optimizasyon fırsatları, performans uyarıları.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Kaç insight getirilsin (varsayılan: 5)",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_gaql_query",
            "description": "Google Ads verileri için sorgu çalıştırır. Doğal dilde soru veya GAQL sorgusu kabul eder. Anahtar kelime performansı, reklam grupları, reklam metinleri, kalite puanı, arama terimleri, coğrafi veriler, demografi, açılış sayfaları gibi detaylı Google Ads verilerine erişim sağlar. Diğer tool'larla cevaplanamayan Google Ads sorularında bu tool'u kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Doğal dilde soru (örn: 'en çok harcama yapan anahtar kelimeler') veya GAQL SELECT sorgusu"
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Google Ads hesap ID'si"
                    }
                },
                "required": ["query", "account_id"]
            }
        }
    },
]


class ChatService:
    """
    AI Chat Assistant service using OpenAI Assistants API.

    Manages threads, processes messages with streaming,
    and executes tool calls against live data sources.
    """

    def __init__(self, supabase: Optional[SupabaseService] = None):
        self.supabase = supabase or get_supabase_service()
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.assistant_id = settings.openai_assistant_id

    async def ensure_assistant(self) -> str:
        """Get or create the OpenAI Assistant with tools. Updates existing assistant's config."""
        if self.assistant_id:
            # Update existing assistant with latest instructions and tools
            if not getattr(self, '_assistant_updated', False):
                try:
                    await self.openai_client.beta.assistants.update(
                        assistant_id=self.assistant_id,
                        instructions=SYSTEM_PROMPT,
                        tools=TOOL_DEFINITIONS,
                    )
                    self._assistant_updated = True
                    logger.info(f"Updated OpenAI Assistant: {self.assistant_id}")
                except Exception as e:
                    logger.warning(f"Failed to update assistant, using existing: {e}")
            return self.assistant_id

        # Create assistant on-the-fly
        assistant = await self.openai_client.beta.assistants.create(
            name="AdWolf AI Asistan",
            instructions=SYSTEM_PROMPT,
            model=settings.openai_model,
            tools=TOOL_DEFINITIONS,
        )

        self.assistant_id = assistant.id
        self._assistant_updated = True
        logger.info(f"Created OpenAI Assistant: {assistant.id}")

        # Optionally save to settings for reuse
        # (In production, set OPENAI_ASSISTANT_ID env var)
        return assistant.id

    async def _enrich_query(self, message: str, org_id: str) -> str:
        """
        Pre-process user message with LLM to enrich it for better tool calling.
        Adds account context and date hints so OpenAI assistant can call the right tools.
        """
        try:
            # Get account context for enrichment
            accounts = await self.supabase.get_connected_accounts(org_id)
            self._cached_accounts = accounts  # Cache for GAQL generation
            account_context = "Kullanıcının hesapları:\n"
            if accounts:
                for acc in accounts:
                    account_context += (
                        f"- {acc.get('account_name', 'Bilinmeyen')} "
                        f"(ID: {acc['id']}, Platform: {acc['platform']}, "
                        f"Durum: {acc.get('status', 'unknown')})\n"
                    )
            else:
                account_context += "- Henüz bağlı hesap yok\n"

            today = date.today().isoformat()

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": QUERY_ENRICHMENT_PROMPT.format(
                            today=today,
                            account_context=account_context,
                            message=message,
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )

            enriched = response.choices[0].message.content.strip()
            logger.info(f"Query enriched: '{message[:50]}' -> '{enriched[:80]}'")
            return enriched

        except Exception as e:
            logger.warning(f"Query enrichment failed, using original: {e}")
            return message

    async def _generate_gaql_query(self, question: str) -> Optional[str]:
        """
        Generate a GAQL query from a natural language question using LLM.
        Returns a valid GAQL SELECT query or None if not applicable.
        """
        try:
            today = date.today().isoformat()

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": GAQL_GENERATION_PROMPT.format(
                            today=today,
                            question=question,
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=500,
            )

            gaql = response.choices[0].message.content.strip()

            # Check if LLM determined it's not a GAQL question
            if gaql == "NOT_APPLICABLE" or not gaql.upper().startswith("SELECT"):
                logger.info(f"GAQL not applicable for: '{question[:50]}'")
                return None

            logger.info(f"Generated GAQL: {gaql[:100]}")
            return gaql

        except Exception as e:
            logger.warning(f"GAQL generation failed: {e}")
            return None

    async def _get_db_context_for_query(self, message: str, org_id: str) -> Optional[str]:
        """
        Fallback: Query database directly to provide context when tools return insufficient data.
        Fetches relevant metrics, campaigns, and account data based on the user's question.
        """
        try:
            context_parts = []
            today = date.today()
            week_ago = (today - timedelta(days=7)).isoformat()
            month_ago = (today - timedelta(days=30)).isoformat()
            today_str = today.isoformat()

            # Always fetch accounts
            accounts = await self.supabase.get_connected_accounts(org_id)
            if accounts:
                context_parts.append(f"Bağlı hesap sayısı: {len(accounts)}")
                for acc in accounts:
                    context_parts.append(
                        f"  - {acc.get('account_name', 'Bilinmeyen')} "
                        f"({acc['platform']}, ID: {acc['id']})"
                    )

            # Fetch recent metrics (last 7 days)
            metrics = await self.supabase.get_daily_metrics(
                org_id=org_id,
                date_from=week_ago,
                date_to=today_str,
            )
            if metrics:
                total_spend = sum(float(m.get("spend", 0) or 0) for m in metrics)
                total_clicks = sum(int(m.get("clicks", 0) or 0) for m in metrics)
                total_impressions = sum(int(m.get("impressions", 0) or 0) for m in metrics)
                total_conversions = sum(float(m.get("conversions", 0) or 0) for m in metrics)
                ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0
                cpc = round(total_spend / total_clicks, 2) if total_clicks > 0 else 0

                context_parts.append(f"\nSon 7 gün metrikleri ({week_ago} - {today_str}):")
                context_parts.append(f"  Toplam harcama: {total_spend:.2f} TRY")
                context_parts.append(f"  Tıklama: {total_clicks:,}")
                context_parts.append(f"  Gösterim: {total_impressions:,}")
                context_parts.append(f"  Dönüşüm: {total_conversions:.0f}")
                context_parts.append(f"  CTR: %{ctr}")
                context_parts.append(f"  CPC: {cpc:.2f} TRY")

            # Fetch last 30 days for comparison
            metrics_month = await self.supabase.get_daily_metrics(
                org_id=org_id,
                date_from=month_ago,
                date_to=today_str,
            )
            if metrics_month:
                total_spend_month = sum(float(m.get("spend", 0) or 0) for m in metrics_month)
                total_clicks_month = sum(int(m.get("clicks", 0) or 0) for m in metrics_month)
                context_parts.append(f"\nSon 30 gün: {total_spend_month:.2f} TRY harcama, {total_clicks_month:,} tıklama")

            # Fetch campaigns with per-campaign metrics
            if accounts:
                all_campaigns = []
                for acc in accounts[:5]:  # Limit to first 5 accounts
                    campaigns = await self.supabase.get_campaigns(acc["id"])
                    all_campaigns.extend(campaigns)

                if all_campaigns:
                    active = [c for c in all_campaigns if c.get("status") == "enabled"]
                    context_parts.append(f"\nToplam kampanya: {len(all_campaigns)} ({len(active)} aktif)")
                    for c in active[:10]:  # Show top 10
                        budget = c.get("budget_amount")
                        budget_str = f", Bütçe: {budget}" if budget else ""
                        context_parts.append(f"  - {c['name']} ({c.get('status', '?')}{budget_str})")

                    # Add per-campaign metrics for active campaigns
                    if metrics_month and active:
                        context_parts.append("\nKampanya bazlı son 30 gün metrikleri:")
                        campaign_metrics = {}
                        for m in metrics_month:
                            cid = m.get("campaign_id")
                            if cid:
                                if cid not in campaign_metrics:
                                    campaign_metrics[cid] = {
                                        "name": m.get("campaign_name", "?"),
                                        "spend": 0, "clicks": 0, "impressions": 0, "conversions": 0,
                                    }
                                campaign_metrics[cid]["spend"] += float(m.get("spend", 0) or 0)
                                campaign_metrics[cid]["clicks"] += int(m.get("clicks", 0) or 0)
                                campaign_metrics[cid]["impressions"] += int(m.get("impressions", 0) or 0)
                                campaign_metrics[cid]["conversions"] += float(m.get("conversions", 0) or 0)

                        sorted_campaigns = sorted(campaign_metrics.values(), key=lambda x: x["spend"], reverse=True)
                        for cm in sorted_campaigns[:15]:
                            cm_ctr = round(cm["clicks"] / cm["impressions"] * 100, 2) if cm["impressions"] > 0 else 0
                            cm_cpc = round(cm["spend"] / cm["clicks"], 2) if cm["clicks"] > 0 else 0
                            context_parts.append(
                                f"  - {cm['name']}: {cm['spend']:.2f} TRY harcama, "
                                f"{cm['clicks']:,} tıklama, CTR: %{cm_ctr}, CPC: {cm_cpc:.2f} TRY"
                            )

            if context_parts:
                return "\n".join(context_parts)
            return None

        except Exception as e:
            logger.warning(f"DB context fetch failed: {e}")
            return None

    async def _db_search_and_interpret(self, message: str, org_id: str) -> Optional[str]:
        """
        Advanced fallback: Search database for relevant data and use LLM to interpret results.
        Used when standard tools and GAQL queries don't provide sufficient answers.
        """
        try:
            db_context = await self._get_db_context_for_query(message, org_id)
            if not db_context:
                return None

            # Use LLM to interpret DB data in context of the user's question
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT + "\n\nAşağıda kullanıcının veritabanından çekilen güncel verileri var. "
                        "Bu verileri kullanarak soruyu mümkün olduğunca detaylı cevapla. "
                        "Eğer sorunun cevabı veriler arasında yoksa, hangi verilerin mevcut olduğunu ve "
                        "sorunun nasıl cevaplanabileceğini açıkla.\n\n"
                        "VERİTABANI VERİLERİ:\n" + db_context,
                    },
                    {"role": "user", "content": message},
                ],
                temperature=0.7,
                max_tokens=2000,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"DB search and interpret failed: {e}")
            return None

    async def _try_auto_gaql(self, message: str, org_id: str) -> Optional[str]:
        """
        Try to auto-generate and execute a GAQL query for the user's question.
        Returns formatted result string or None if not applicable/failed.
        """
        try:
            # Generate GAQL from natural language
            gaql = await self._generate_gaql_query(message)
            if not gaql:
                return None

            # Find first Google Ads account
            accounts = getattr(self, '_cached_accounts', None)
            if not accounts:
                accounts = await self.supabase.get_connected_accounts(org_id)

            google_accounts = [a for a in (accounts or []) if a.get("platform") == "google_ads"]
            if not google_accounts:
                return None

            # Try executing on first Google Ads account
            account_id = google_accounts[0]["id"]
            result = await self._tool_gaql_query(org_id, gaql, account_id)

            # Check if result has data
            try:
                parsed = json.loads(result)
                if parsed.get("error") or parsed.get("row_count", 0) == 0:
                    return None
                return result
            except (json.JSONDecodeError, TypeError):
                return None

        except Exception as e:
            logger.warning(f"Auto-GAQL failed: {e}")
            return None

    async def send_message_stream(
        self,
        message: str,
        org_id: str,
        user_id: str,
        thread_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response via SSE.

        Pre-processes the user message with LLM enrichment for better tool calling.
        Falls back to direct DB context when tools return insufficient data.

        Yields SSE-formatted strings: "data: {json}\n\n"
        """
        assistant_id = await self.ensure_assistant()

        # Step 1: Enrich user query with LLM pre-processing
        enriched_message = await self._enrich_query(message, org_id)

        # Get or create thread
        db_thread = None
        openai_thread_id = None

        if thread_id:
            # Load existing thread
            db_thread = await self.supabase.get_chat_thread(thread_id)
            if not db_thread or db_thread.get("org_id") != org_id:
                yield self._sse_event("error", content="Konuşma bulunamadı")
                return
            openai_thread_id = db_thread.get("openai_thread_id")

        if not openai_thread_id:
            # Create new OpenAI thread
            oai_thread = await self.openai_client.beta.threads.create()
            openai_thread_id = oai_thread.id

            # Create DB thread
            db_thread = await self.supabase.create_chat_thread({
                "org_id": org_id,
                "user_id": user_id,
                "openai_thread_id": openai_thread_id,
                "title": "Yeni Konuşma",
                "last_message_at": "now()",
            })

            yield self._sse_event("thread_created", thread_id=db_thread["id"])

        db_thread_id = db_thread["id"]

        # Save original user message to DB (not the enriched version)
        await self.supabase.create_chat_message({
            "thread_id": db_thread_id,
            "role": "user",
            "content": message,
        })

        # Add enriched message to OpenAI thread for better tool calling
        await self.openai_client.beta.threads.messages.create(
            thread_id=openai_thread_id,
            role="user",
            content=enriched_message,
        )

        # Create and stream the run
        full_response = ""
        tool_calls_log = []

        try:
            async with self.openai_client.beta.threads.runs.stream(
                thread_id=openai_thread_id,
                assistant_id=assistant_id,
            ) as stream:
                async for event in stream:
                    # Handle text deltas
                    if event.event == "thread.run.step.delta":
                        delta = event.data.delta
                        if delta and delta.step_details:
                            if delta.step_details.type == "message_creation":
                                msg_delta = delta.step_details.message_creation
                                if hasattr(msg_delta, "text") and msg_delta.text:
                                    # This path handles streaming text in step delta
                                    pass

                    elif event.event == "thread.message.delta":
                        delta = event.data.delta
                        if delta and delta.content:
                            for block in delta.content:
                                if block.type == "text" and block.text:
                                    text = block.text.value
                                    full_response += text
                                    yield self._sse_event("text_delta", content=text)

                    elif event.event == "thread.run.requires_action":
                        run = event.data
                        if run.required_action and run.required_action.type == "submit_tool_outputs":
                            tool_outputs = []
                            any_empty_result = False

                            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                                fn_name = tool_call.function.name
                                fn_args = json.loads(tool_call.function.arguments)

                                yield self._sse_event("tool_call", tool_name=fn_name, tool_args=fn_args)

                                # Execute the tool
                                try:
                                    result = await self._execute_tool(fn_name, fn_args, org_id)
                                    tool_calls_log.append({
                                        "name": fn_name,
                                        "args": fn_args,
                                        "result_preview": str(result)[:200],
                                    })

                                    # Check if result is empty/minimal
                                    try:
                                        parsed = json.loads(result) if isinstance(result, str) else result
                                        if isinstance(parsed, dict):
                                            if parsed.get("error") or parsed.get("total", 1) == 0 or parsed.get("total_accounts", 1) == 0:
                                                any_empty_result = True
                                    except (json.JSONDecodeError, TypeError):
                                        pass

                                except Exception as e:
                                    logger.error(f"Tool execution error ({fn_name}): {e}")
                                    result = json.dumps({"error": str(e)}, ensure_ascii=False)
                                    any_empty_result = True

                                # If tool returned empty, try auto-GAQL then augment with DB context
                                if any_empty_result:
                                    # Try auto-GAQL for Google Ads questions
                                    gaql_result = await self._try_auto_gaql(message, org_id)
                                    if gaql_result:
                                        if isinstance(result, str):
                                            try:
                                                result_dict = json.loads(result)
                                                result_dict["_gaql_data"] = gaql_result
                                                result = json.dumps(result_dict, ensure_ascii=False, default=str)
                                            except (json.JSONDecodeError, TypeError):
                                                result = result + f"\n\nGoogle Ads verisi:\n{gaql_result}"
                                    else:
                                        # Fall back to DB context
                                        db_context = await self._get_db_context_for_query(message, org_id)
                                        if db_context:
                                            if isinstance(result, str):
                                                try:
                                                    result_dict = json.loads(result)
                                                    result_dict["_db_context"] = db_context
                                                    result = json.dumps(result_dict, ensure_ascii=False, default=str)
                                                except (json.JSONDecodeError, TypeError):
                                                    result = result + f"\n\nEk veritabanı bağlamı:\n{db_context}"

                                tool_outputs.append({
                                    "tool_call_id": tool_call.id,
                                    "output": result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str),
                                })

                                yield self._sse_event("tool_result", tool_name=fn_name)

                            # Submit tool outputs and continue streaming
                            async with self.openai_client.beta.threads.runs.submit_tool_outputs_stream(
                                thread_id=openai_thread_id,
                                run_id=run.id,
                                tool_outputs=tool_outputs,
                            ) as tool_stream:
                                async for tool_event in tool_stream:
                                    if tool_event.event == "thread.message.delta":
                                        delta = tool_event.data.delta
                                        if delta and delta.content:
                                            for block in delta.content:
                                                if block.type == "text" and block.text:
                                                    text = block.text.value
                                                    full_response += text
                                                    yield self._sse_event("text_delta", content=text)

                    elif event.event == "thread.run.completed":
                        pass  # Run completed successfully

                    elif event.event == "thread.run.failed":
                        run = event.data
                        error_msg = "Bir hata oluştu"
                        if run.last_error:
                            error_msg = run.last_error.message
                        yield self._sse_event("error", content=error_msg)

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield self._sse_event("error", content=f"Akış hatası: {str(e)}")

        # Step 2: If no response or very short, try DB search + LLM interpretation fallback
        if not full_response or len(full_response.strip()) < 10:
            logger.info("Empty/short response from assistant, trying DB search + LLM fallback")

            fallback_text = await self._db_search_and_interpret(message, org_id)
            if fallback_text:
                full_response = fallback_text
                # Stream the fallback response
                for i in range(0, len(fallback_text), 20):
                    chunk = fallback_text[i:i + 20]
                    yield self._sse_event("text_delta", content=chunk)

        # Save assistant message to DB
        if full_response:
            await self.supabase.create_chat_message({
                "thread_id": db_thread_id,
                "role": "assistant",
                "content": full_response,
                "tool_calls": tool_calls_log if tool_calls_log else None,
            })

        # Update thread metadata
        current_count = db_thread.get("message_count", 0) + 2  # user + assistant
        await self.supabase.update_chat_thread(db_thread_id, {
            "message_count": current_count,
            "last_message_at": "now()",
        })

        # Auto-title on first message
        if current_count <= 2 and full_response:
            await self._auto_title_thread(db_thread_id, message)

        # Send done event
        yield self._sse_event("done", thread_id=db_thread_id, message_id="")

    # ===========================================
    # TOOL EXECUTION
    # ===========================================

    async def _execute_tool(self, name: str, args: dict, org_id: str) -> str:
        """Execute a tool call and return the result as a string."""

        if name == "get_account_summary":
            return await self._tool_account_summary(org_id, args.get("platform"))

        elif name == "get_campaign_list":
            return await self._tool_campaign_list(org_id, args["account_id"])

        elif name == "get_performance_metrics":
            return await self._tool_performance_metrics(
                org_id,
                args["date_from"],
                args["date_to"],
                args.get("account_id"),
                args.get("campaign_id"),
            )

        elif name == "get_performance_comparison":
            return await self._tool_performance_comparison(org_id, args["period"])

        elif name == "get_recent_insights":
            return await self._tool_recent_insights(org_id, args.get("limit", 5))

        elif name == "execute_gaql_query":
            return await self._tool_gaql_query(org_id, args["query"], args["account_id"])

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    async def _tool_account_summary(self, org_id: str, platform: Optional[str] = None) -> str:
        """Get connected accounts summary."""
        accounts = await self.supabase.get_connected_accounts(org_id, platform=platform)

        summary = []
        for acc in accounts:
            summary.append({
                "id": acc["id"],
                "platform": acc["platform"],
                "account_name": acc.get("account_name", "Unknown"),
                "platform_account_id": acc.get("platform_account_id", ""),
                "status": acc.get("status", "unknown"),
                "is_active": acc.get("is_active", False),
                "last_synced_at": acc.get("last_synced_at"),
                "currency": acc.get("currency", "TRY"),
            })

        return json.dumps({
            "total_accounts": len(summary),
            "accounts": summary,
        }, ensure_ascii=False, default=str)

    async def _tool_campaign_list(self, org_id: str, account_id: str) -> str:
        """Get campaigns for an account (with org ownership check)."""
        # Verify account belongs to org
        account = await self.supabase.get_connected_account(account_id)
        if not account or account.get("org_id") != org_id:
            return json.dumps({"error": "Bu hesaba erişim yetkiniz yok"})

        campaigns = await self.supabase.get_campaigns(account_id)

        result = []
        for c in campaigns:
            result.append({
                "id": c["id"],
                "name": c["name"],
                "status": c.get("status", "unknown"),
                "platform_campaign_id": c.get("platform_campaign_id", ""),
                "budget_amount": c.get("budget_amount"),
                "budget_type": c.get("budget_type"),
            })

        return json.dumps({
            "account_name": account.get("account_name", "Unknown"),
            "total_campaigns": len(result),
            "campaigns": result,
        }, ensure_ascii=False, default=str)

    async def _tool_performance_metrics(
        self,
        org_id: str,
        date_from: str,
        date_to: str,
        account_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> str:
        """Get performance metrics for a date range."""
        metrics = await self.supabase.get_daily_metrics(
            org_id=org_id,
            date_from=date_from,
            date_to=date_to,
            account_id=account_id,
            campaign_id=campaign_id,
        )

        # Aggregate totals
        total_impressions = sum(int(m.get("impressions", 0) or 0) for m in metrics)
        total_clicks = sum(int(m.get("clicks", 0) or 0) for m in metrics)
        total_spend = sum(float(m.get("spend", 0) or 0) for m in metrics)
        total_conversions = sum(float(m.get("conversions", 0) or 0) for m in metrics)
        total_conversion_value = sum(float(m.get("conversion_value", 0) or 0) for m in metrics)

        ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0
        cpc = round(total_spend / total_clicks, 2) if total_clicks > 0 else 0
        cpa = round(total_spend / total_conversions, 2) if total_conversions > 0 else 0
        roas = round(total_conversion_value / total_spend, 2) if total_spend > 0 else 0

        return json.dumps({
            "period": f"{date_from} ~ {date_to}",
            "total_days": len(set(m.get("date", "") for m in metrics)),
            "totals": {
                "impressions": total_impressions,
                "clicks": total_clicks,
                "spend": round(total_spend, 2),
                "conversions": round(total_conversions, 2),
                "conversion_value": round(total_conversion_value, 2),
                "ctr": ctr,
                "cpc": cpc,
                "cpa": cpa,
                "roas": roas,
            },
            "daily_records_count": len(metrics),
        }, ensure_ascii=False, default=str)

    async def _tool_performance_comparison(self, org_id: str, period: str) -> str:
        """Compare performance between periods using InsightDataCollector."""
        collector = InsightDataCollector(self.supabase)
        org_data = await collector.collect_org_data(org_id)

        if not org_data.get("has_data"):
            return json.dumps({"error": "Karşılaştırma yapacak yeterli veri yok"})

        return json.dumps({
            "period": org_data.get("period"),
            "org_totals": org_data.get("org_totals"),
            "top_campaigns": org_data.get("campaigns", [])[:10],
            "anomalies": org_data.get("anomalies", []),
            "active_campaign_count": org_data.get("active_campaign_count", 0),
        }, ensure_ascii=False, default=str)

    async def _tool_recent_insights(self, org_id: str, limit: int = 5) -> str:
        """Get recent AI-generated insights."""
        insights = await self.supabase.get_insights(org_id=org_id, limit=limit)

        result = []
        for i in insights:
            result.append({
                "id": i["id"],
                "type": i.get("insight_type"),
                "severity": i.get("severity"),
                "title": i.get("title"),
                "summary": i.get("summary"),
                "detailed_analysis": i.get("detailed_analysis"),
                "platform": i.get("platform"),
                "created_at": i.get("created_at"),
                "actions": [
                    {
                        "title": a.get("title"),
                        "description": a.get("description"),
                        "action_type": a.get("action_type"),
                    }
                    for a in (i.get("recommended_actions") or [])
                ],
            })

        return json.dumps({
            "total": len(result),
            "insights": result,
        }, ensure_ascii=False, default=str)

    async def _tool_gaql_query(self, org_id: str, query: str, account_id: str) -> str:
        """Execute a GAQL query against Google Ads API (SELECT only).
        If the query is natural language, auto-generate GAQL first."""
        from app.connectors.google_ads import GoogleAdsConnector

        original_query = query

        # If query doesn't look like GAQL, try to generate it from natural language
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
            generated_gaql = await self._generate_gaql_query(query)
            if generated_gaql:
                logger.info(f"Auto-generated GAQL from natural language: '{query[:50]}' -> '{generated_gaql[:80]}'")
                query = generated_gaql
            else:
                return json.dumps({"error": "Bu soru GAQL sorgusu ile cevaplanamıyor. Lütfen daha spesifik bir soru sorun."})

        # Security: Final check - only allow SELECT queries
        if not query.strip().upper().startswith("SELECT"):
            return json.dumps({"error": "Güvenlik: Sadece SELECT sorguları kabul edilir"})

        # Verify account ownership
        account = await self.supabase.get_connected_account(account_id)
        if not account or account.get("org_id") != org_id:
            return json.dumps({"error": "Bu hesaba erişim yetkiniz yok"})

        if account.get("platform") != "google_ads":
            return json.dumps({"error": "GAQL sorguları sadece Google Ads hesaplarında çalışır"})

        # Decrypt tokens
        try:
            access_token = decrypt_token(account["access_token_encrypted"])
            refresh_token = None
            if account.get("refresh_token_encrypted"):
                refresh_token = decrypt_token(account["refresh_token_encrypted"])
        except Exception as e:
            return json.dumps({"error": f"Token çözümleme hatası: {str(e)}"})

        # Execute GAQL (with retry on query error)
        max_attempts = 2
        last_error = None

        for attempt in range(max_attempts):
            try:
                connector = GoogleAdsConnector(
                    access_token=access_token,
                    refresh_token=refresh_token or "",
                    customer_id=account.get("platform_account_id", ""),
                    login_customer_id=account.get("login_customer_id"),
                )

                client = connector._get_client()
                ga_service = client.get_service("GoogleAdsService")

                customer_id = account.get("platform_account_id", "").replace("-", "")
                response = ga_service.search(customer_id=customer_id, query=query)

                # Convert protobuf to dict - limit results
                from google.protobuf import json_format

                rows = []
                for i, row in enumerate(response):
                    if i >= 50:  # Limit to 50 rows
                        break
                    row_dict = json_format.MessageToDict(row._pb)
                    rows.append(row_dict)

                return json.dumps({
                    "query": query,
                    "original_question": original_query if original_query != query else None,
                    "row_count": len(rows),
                    "rows": rows,
                }, ensure_ascii=False, default=str)

            except Exception as e:
                last_error = str(e)
                logger.warning(f"GAQL attempt {attempt + 1} failed: {e}")

                # On first failure with auto-generated query, try regenerating
                if attempt == 0 and original_query != query:
                    retry_query = await self._generate_gaql_query(
                        f"{original_query}\n\nÖnceki sorgu hata verdi: {query}\nHata: {last_error}\nDüzeltilmiş sorgu yaz."
                    )
                    if retry_query and retry_query.strip().upper().startswith("SELECT"):
                        query = retry_query
                        logger.info(f"Retrying with corrected GAQL: {query[:80]}")
                        continue
                break

        return json.dumps({"error": f"GAQL sorgu hatası: {last_error}"})

    # ===========================================
    # HELPERS
    # ===========================================

    async def _auto_title_thread(self, thread_id: str, first_message: str):
        """Generate a short title for the thread based on first message."""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Kullanıcının mesajına dayanarak 3-5 kelimelik kısa bir konuşma başlığı üret. Sadece başlığı yaz, başka bir şey yazma. Türkçe olsun."
                    },
                    {"role": "user", "content": first_message[:200]},
                ],
                temperature=0.5,
                max_tokens=30,
            )
            title = response.choices[0].message.content.strip().strip('"')
            await self.supabase.update_chat_thread(thread_id, {"title": title})
        except Exception as e:
            logger.warning(f"Auto-title failed: {e}")

    @staticmethod
    def _sse_event(
        event_type: str,
        content: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[dict] = None,
        thread_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> str:
        """Format an SSE event string."""
        data = {"type": event_type}
        if content is not None:
            data["content"] = content
        if tool_name is not None:
            data["tool_name"] = tool_name
        if tool_args is not None:
            data["tool_args"] = tool_args
        if thread_id is not None:
            data["thread_id"] = thread_id
        if message_id is not None:
            data["message_id"] = message_id

        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
