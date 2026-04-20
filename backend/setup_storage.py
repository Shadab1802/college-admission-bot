import os
import httpx
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

BUCKETS = ["marksheets", "admit-cards", "templates"]

def setup_storage():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_KEY not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json"
    }

    for bucket in BUCKETS:
        # 1. Create or check bucket
        create_url = f"{SUPABASE_URL}/storage/v1/bucket"
        payload = {
            "id": bucket,
            "name": bucket,
            "public": True
        }
        
        try:
            resp = httpx.post(create_url, json=payload, headers=headers)
            if resp.status_code == 200:
                print(f"Bucket '{bucket}' created successfully.")
            elif resp.status_code == 400 and "already exists" in resp.text.lower():
                print(f"Bucket '{bucket}' already exists. Updating to public...")
                # Update bucket to be public
                update_url = f"{SUPABASE_URL}/storage/v1/bucket/{bucket}"
                update_resp = httpx.put(update_url, json={"public": True}, headers=headers)
                if update_resp.status_code == 200:
                    print(f"Bucket '{bucket}' updated to public.")
                else:
                    print(f"Failed to update bucket '{bucket}': {update_resp.text}")
            else:
                print(f"Failed to create bucket '{bucket}': {resp.text}")
        except Exception as e:
            print(f"Error handling bucket '{bucket}': {e}")

if __name__ == "__main__":
    setup_storage()
