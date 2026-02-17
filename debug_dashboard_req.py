
import requests
import json
import sys

# Define base URL - assuming default localhost:8000
BASE_URL = "http://localhost:8000"

def check_dashboard():
    print(f"Checking {BASE_URL}/dashboard/summary ...")
    try:
        # 1. Get Summary
        # Note: Authentication might be needed if not mocked. 
        # settings.py says USE_MOCKS = True, but `get_current_context` depends on headers?
        # api_client.dart adds 'X-API-KEY': 'COZY_DEV_KEY'.
        headers = {'X-API-KEY': 'COZY_DEV_KEY'}
        
        response = requests.get(f"{BASE_URL}/dashboard/summary", headers=headers)
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}")
            return

        data = response.json()
        current = data.get('current', {})
        
        print("\n--- Current State Response ---")
        print(json.dumps(current, indent=2))
        
        if current.get('solar_power_kw', 0) == 0 and current.get('grid_power_kw', 0) == 0:
             print("\n[!] ALERT: All values seem to be ZERO.")
        else:
             print("\n[OK] Values detected.")

    except Exception as e:
        print(f"Failed to connect: {e}")

if __name__ == "__main__":
    check_dashboard()
