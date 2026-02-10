"""
Ad Platform MVP - Chat Service

Core service for AI Chat Assistant using OpenAI Assistants API.
Handles thread management, message streaming, and tool calling.
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
            "description": "Google Ads Query Language (GAQL) sorgusu çalıştırır. Sadece SELECT sorguları kabul edilir. Gelişmiş analiz için kullanılır.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GAQL sorgusu (sadece SELECT)"
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
        """Get or create the OpenAI Assistant with tools."""
        if self.assistant_id:
            return self.assistant_id

        # Create assistant on-the-fly
        assistant = await self.openai_client.beta.assistants.create(
            name="AdWolf AI Asistan",
            instructions=SYSTEM_PROMPT,
            model=settings.openai_model,
            tools=TOOL_DEFINITIONS,
        )

        self.assistant_id = assistant.id
        logger.info(f"Created OpenAI Assistant: {assistant.id}")

        # Optionally save to settings for reuse
        # (In production, set OPENAI_ASSISTANT_ID env var)
        return assistant.id

    async def send_message_stream(
        self,
        message: str,
        org_id: str,
        user_id: str,
        thread_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response via SSE.

        Yields SSE-formatted strings: "data: {json}\n\n"
        """
        assistant_id = await self.ensure_assistant()

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

        # Save user message to DB
        await self.supabase.create_chat_message({
            "thread_id": db_thread_id,
            "role": "user",
            "content": message,
        })

        # Add message to OpenAI thread
        await self.openai_client.beta.threads.messages.create(
            thread_id=openai_thread_id,
            role="user",
            content=message,
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
                                except Exception as e:
                                    logger.error(f"Tool execution error ({fn_name}): {e}")
                                    result = json.dumps({"error": str(e)}, ensure_ascii=False)

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
        """Execute a GAQL query against Google Ads API (SELECT only)."""
        from app.connectors.google_ads import GoogleAdsConnector

        # Security: Only allow SELECT queries
        query_upper = query.strip().upper()
        if not query_upper.startswith("SELECT"):
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

        # Execute GAQL
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
                "row_count": len(rows),
                "rows": rows,
            }, ensure_ascii=False, default=str)

        except Exception as e:
            return json.dumps({"error": f"GAQL sorgu hatası: {str(e)}"})

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
