
import asyncio
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def inspect_accounts():
    print("--- Fetching Connected Accounts (via HTTP) ---")
    
    url = f"{SUPABASE_URL}/rest/v1/connected_accounts?select=*"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return

    data = response.json()
    
    if not data:
        print("No accounts found.")
        return

    for acc in data:
        print(f"\nID: {acc['id']}")
        print(f"Name: {acc['account_name']}")
        print(f"Platform ID: {acc['platform_account_id']}")
        print(f"Platform Metadata: {json.dumps(acc.get('platform_metadata'), indent=2)}")
        
        token = acc.get('access_token_encrypted')
        if token:
            print(f"Access Token (Encrypted): {token[:20]}...")
        else:
             print("Access Token: MISSING")
             
        refresh = acc.get('refresh_token_encrypted')
        if refresh:
             print(f"Refresh Token: {refresh[:10]}...")
        else:
             print("Refresh Token: MISSING")

if __name__ == "__main__":
    inspect_accounts()
