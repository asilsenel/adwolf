#!/usr/bin/env python3
"""
Duplicate Account & Orphaned Metrics Fix Script

Bu script:
1. connected_accounts tablosunda aynı platform_account_id'ye sahip duplicate hesapları bulur
2. Her grupta en son oluşturulan/aktif olanı HEDEF, diğerlerini KAYNAK olarak işaretler
3. KAYNAK hesaplardaki daily_metrics verilerini HEDEF hesaba taşır (upsert)
4. KAYNAK hesapları deaktive eder (is_active=False, status='merged_duplicate')

Kullanım:
    cd backend
    python scripts/fix_orphaned_metrics.py [--dry-run] [--verbose]

    --dry-run: Değişiklik yapmadan ne yapılacağını gösterir
    --verbose: Detaylı log
"""

import argparse
import asyncio
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime

# Backend modüllerini import edebilmek için path'e ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.supabase import get_supabase_client


# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def find_duplicate_accounts(client, verbose: bool = False) -> dict[str, list[dict]]:
    """
    connected_accounts tablosunda aynı platform + platform_account_id'ye sahip
    hesapları grupla.

    Returns:
        Dict[str, list]: platform_account_id -> [account_records]
    """
    logger.info("Duplicate hesaplar aranıyor...")

    # Tüm hesapları çek (aktif ve inaktif)
    result = client.table("connected_accounts") \
        .select("*") \
        .execute()

    accounts = result.data or []
    logger.info(f"Toplam {len(accounts)} connected_account bulundu")

    # platform + platform_account_id'ye göre grupla
    grouped = defaultdict(list)
    for acc in accounts:
        platform = acc.get("platform", "")
        platform_account_id = acc.get("platform_account_id", "")
        key = f"{platform}:{platform_account_id}"
        grouped[key].append(acc)

    # Sadece birden fazla kayıt olanları filtrele
    duplicates = {k: v for k, v in grouped.items() if len(v) > 1}

    if verbose:
        for key, accs in duplicates.items():
            logger.info(f"  Duplicate grubu: {key}")
            for acc in accs:
                logger.info(f"    - ID: {acc['id']}, Name: {acc.get('account_name')}, "
                           f"Active: {acc.get('is_active')}, Status: {acc.get('status')}, "
                           f"Created: {acc.get('created_at')}")

    logger.info(f"{len(duplicates)} duplicate grup bulundu")
    return duplicates


def select_target_account(accounts: list[dict]) -> tuple[dict, list[dict]]:
    """
    Bir duplicate grubundan HEDEF hesabı seç.

    Seçim kriteri (öncelik sırasıyla):
    1. is_active=True olanı tercih et
    2. status='active' olanı tercih et
    3. En son oluşturulanı (created_at) tercih et

    Returns:
        (target_account, source_accounts)
    """
    # Önce aktif olanları ayır
    active_accounts = [a for a in accounts if a.get("is_active", True)]
    inactive_accounts = [a for a in accounts if not a.get("is_active", True)]

    # Aktif hesap varsa onlardan, yoksa inaktiflerden seç
    candidates = active_accounts if active_accounts else inactive_accounts

    # Status='active' olanları önceliklendir
    active_status = [a for a in candidates if a.get("status") == "active"]
    if active_status:
        candidates = active_status

    # En son oluşturulanı seç
    candidates.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    target = candidates[0]

    # Diğerleri kaynak
    sources = [a for a in accounts if a["id"] != target["id"]]

    return target, sources


def get_metrics_for_account(client, account_id: str) -> list[dict]:
    """Bir hesaba ait tüm daily_metrics kayıtlarını çek."""
    result = client.table("daily_metrics") \
        .select("*") \
        .eq("account_id", account_id) \
        .execute()
    return result.data or []


def migrate_metrics(
    client,
    source_account_id: str,
    target_account_id: str,
    dry_run: bool = False,
    verbose: bool = False
) -> tuple[int, int]:
    """
    Kaynak hesaptaki metrikleri hedef hesaba taşı.

    - Önce kaynak hesaptan verileri çek
    - account_id'yi hedef ID ile değiştir
    - id sütununu kaldır (yeni ID oluşsun)
    - Upsert ile hedef hesaba yaz
    - Başarılı olduysa kaynak verileri sil

    Returns:
        (migrated_count, deleted_count)
    """
    # Kaynak metrikleri çek
    source_metrics = get_metrics_for_account(client, source_account_id)

    if not source_metrics:
        logger.info(f"  Kaynak hesapta ({source_account_id}) metrik yok, atlanıyor")
        return 0, 0

    logger.info(f"  Kaynak hesapta {len(source_metrics)} metrik bulundu")

    if dry_run:
        logger.info(f"  [DRY-RUN] {len(source_metrics)} metrik taşınacak: {source_account_id} -> {target_account_id}")
        return len(source_metrics), 0

    # Hedefte zaten var olan date+campaign_id kombinasyonlarını bul
    # Bunları unique key olarak kullanacağız
    target_metrics = get_metrics_for_account(client, target_account_id)
    existing_keys = set()
    for m in target_metrics:
        key = f"{m.get('date')}:{m.get('campaign_id', '')}:{m.get('platform', '')}"
        existing_keys.add(key)

    # Taşınacak metrikleri hazırla
    metrics_to_insert = []
    metrics_to_update = []
    source_ids_to_delete = []

    for m in source_metrics:
        source_ids_to_delete.append(m["id"])

        # Yeni kayıt için hazırla
        new_metric = {k: v for k, v in m.items() if k != "id"}  # id'yi kaldır
        new_metric["account_id"] = target_account_id  # Hedef account ID

        # Unique key kontrolü
        key = f"{m.get('date')}:{m.get('campaign_id', '')}:{m.get('platform', '')}"

        if key in existing_keys:
            # Hedefte var, güncelleme gerekebilir (ama biz sadece eksikleri ekleyelim)
            if verbose:
                logger.info(f"    Zaten var, atlanıyor: {key}")
            continue
        else:
            metrics_to_insert.append(new_metric)

    # Yeni metrikleri ekle
    migrated_count = 0
    if metrics_to_insert:
        try:
            # Batch insert
            result = client.table("daily_metrics").insert(metrics_to_insert).execute()
            migrated_count = len(result.data) if result.data else 0
            logger.info(f"  {migrated_count} yeni metrik eklendi")
        except Exception as e:
            logger.error(f"  Metrik ekleme hatası: {e}")
            # Upsert dene
            try:
                result = client.table("daily_metrics").upsert(metrics_to_insert).execute()
                migrated_count = len(result.data) if result.data else 0
                logger.info(f"  Upsert ile {migrated_count} metrik eklendi")
            except Exception as e2:
                logger.error(f"  Upsert de başarısız: {e2}")
                return 0, 0

    # Kaynak metrikleri sil
    deleted_count = 0
    if source_ids_to_delete:
        try:
            for chunk_start in range(0, len(source_ids_to_delete), 100):  # 100'lük batch
                chunk = source_ids_to_delete[chunk_start:chunk_start + 100]
                client.table("daily_metrics") \
                    .delete() \
                    .in_("id", chunk) \
                    .execute()
                deleted_count += len(chunk)
            logger.info(f"  {deleted_count} kaynak metrik silindi")
        except Exception as e:
            logger.error(f"  Kaynak metrik silme hatası: {e}")

    return migrated_count, deleted_count


def deactivate_source_account(
    client,
    account_id: str,
    dry_run: bool = False
) -> bool:
    """Kaynak hesabı deaktive et ve merged_duplicate olarak işaretle."""
    if dry_run:
        logger.info(f"  [DRY-RUN] Hesap deaktive edilecek: {account_id}")
        return True

    try:
        client.table("connected_accounts") \
            .update({
                "is_active": False,
                "status": "merged_duplicate",
                "updated_at": datetime.utcnow().isoformat(),
            }) \
            .eq("id", account_id) \
            .execute()
        logger.info(f"  Hesap deaktive edildi: {account_id}")
        return True
    except Exception as e:
        logger.error(f"  Hesap deaktive edilemedi: {e}")
        return False


async def fix_orphaned_metrics(dry_run: bool = False, verbose: bool = False):
    """Ana fonksiyon: Duplicate hesapları bul ve metrikleri taşı."""
    logger.info("=" * 60)
    logger.info("Orphaned Metrics Fix Script Başlıyor")
    logger.info(f"Mod: {'DRY-RUN (değişiklik yapılmayacak)' if dry_run else 'LIVE'}")
    logger.info("=" * 60)

    client = get_supabase_client()

    # 1. Duplicate hesapları bul
    duplicates = find_duplicate_accounts(client, verbose)

    if not duplicates:
        logger.info("Duplicate hesap bulunamadı. İşlem tamamlandı.")
        return

    total_migrated = 0
    total_deleted = 0
    total_deactivated = 0

    # 2. Her duplicate grubu için işlem yap
    for group_key, accounts in duplicates.items():
        logger.info("-" * 40)
        logger.info(f"İşleniyor: {group_key}")

        # Hedef ve kaynak hesapları belirle
        target, sources = select_target_account(accounts)

        logger.info(f"  HEDEF: {target['id']} ({target.get('account_name')})")
        logger.info(f"  KAYNAKLAR: {len(sources)} hesap")

        # Her kaynak için metrikleri taşı
        for source in sources:
            logger.info(f"  Kaynak işleniyor: {source['id']} ({source.get('account_name')})")

            # Metrikleri taşı
            migrated, deleted = migrate_metrics(
                client,
                source["id"],
                target["id"],
                dry_run=dry_run,
                verbose=verbose
            )
            total_migrated += migrated
            total_deleted += deleted

            # Kaynak hesabı deaktive et
            if deactivate_source_account(client, source["id"], dry_run=dry_run):
                total_deactivated += 1

    # Özet
    logger.info("=" * 60)
    logger.info("İŞLEM TAMAMLANDI")
    logger.info(f"  Toplam taşınan metrik: {total_migrated}")
    logger.info(f"  Toplam silinen kaynak metrik: {total_deleted}")
    logger.info(f"  Deaktive edilen hesap: {total_deactivated}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Duplicate hesapları ve yetim metrikleri düzelt"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Değişiklik yapmadan ne yapılacağını göster"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Detaylı log"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    asyncio.run(fix_orphaned_metrics(dry_run=args.dry_run, verbose=args.verbose))


if __name__ == "__main__":
    main()
