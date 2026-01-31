
import asyncio
import os
import sys

# Add backend directory to path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.supabase import get_supabase_service
from app.core.security import decrypt_token
from app.connectors.google_ads import GoogleAdsConnector

async def update_account_names():
    print("🚀 Starting account name update...")
    
    supabase = get_supabase_service()
    
    # 1. Fetch all connected Google Ads accounts
    result = supabase.client.table('connected_accounts') \
        .select('*') \
        .eq('platform', 'google_ads') \
        .execute()
        
    accounts = result.data
    print(f"found {len(accounts)} Google Ads accounts.")
    
    for account in accounts:
        try:
            account_id = account['platform_account_id']
            current_name = account.get('account_name', 'N/A')
            print(f"\nProcessing Account: {account_id} (Current Name: {current_name})")
            
            # Decrypt tokens
            token = decrypt_token(account['access_token_encrypted'])
            refresh = decrypt_token(account['refresh_token_encrypted']) if account.get('refresh_token_encrypted') else None
            mcc_id = account.get('platform_metadata', {}).get('mcc_id')
            
            # Initialize Connector
            connector = GoogleAdsConnector(
                customer_id=account_id,
                access_token=token,
                refresh_token=refresh,
                login_customer_id=mcc_id
            )
            
            # Fetch fresh info
            info = await connector.get_account_info()
            fresh_name = info.get('name')
            
            if fresh_name and fresh_name != current_name:
                print(f"✅ Found new name: {fresh_name}")
                
                # Update DB
                update_res = supabase.client.table('connected_accounts') \
                    .update({'account_name': fresh_name}) \
                    .eq('id', account['id']) \
                    .execute()
                    
                print(f"💾 Updated DB record.")
            else:
                print(f"ℹ️ Name is already up to date or empty.")
                
        except Exception as e:
            print(f"❌ Error updating account {account.get('platform_account_id')}: {e}")

if __name__ == "__main__":
    asyncio.run(update_account_names())
