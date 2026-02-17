import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def verify_tenancy():
    print("--- Verifying Phase 7: Multi-Tenancy Security ---")
    
    # 1. Test Unauthorized Access
    print("\n1. Testing Unauthorized Access (No Headers)...")
    try:
        r = requests.get(f"{BASE_URL}/assets/")
        if r.status_code == 401:
            print("✅ Correctly rejected with 401 Unauthorized.")
        else:
            print(f"❌ Failed: Expected 401, got {r.status_code}")
    except Exception as e:
        print(f"❌ Error connecting: {e}")

    # 2. Test Authorized Access (Dev Key)
    print("\n2. Testing Authorized Access (API Key)...")
    try:
        headers = {"X-API-KEY": "COZY_DEV_KEY"}
        r = requests.get(f"{BASE_URL}/assets/", headers=headers)
        if r.status_code == 200:
            print(f"✅ Correctly accepted with 200 OK. Found {len(r.json())} assets.")
        else:
            print(f"❌ Failed: Expected 200, got {r.status_code}")
            print(r.text)
    except Exception as e:
        print(f"❌ Error connecting: {e}")

    # 3. Test Authorized Access (Bearer Mock)
    print("\n3. Testing Authorized Access (Bearer Token)...")
    try:
        headers = {"Authorization": "Bearer mock-jwt-token-123456"}
        r = requests.get(f"{BASE_URL}/dashboard/summary", headers=headers)
        if r.status_code == 200:
            print("✅ Correctly accepted with 200 OK.")
        else:
            print(f"❌ Failed: Expected 200, got {r.status_code}")
            print(r.text)
    except Exception as e:
        print(f"❌ Error connecting: {e}")

if __name__ == "__main__":
    verify_tenancy()
