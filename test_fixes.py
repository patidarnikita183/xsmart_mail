import requests
import sys

BASE_URL = "http://localhost:5000"

def test_get_email_tracking():
    print("Testing /get-email-tracking endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/get-email-tracking")
        if response.status_code == 200:
            print("✅ /get-email-tracking returned 200 OK")
            data = response.json()
            if 'tracking' in data:
                print(f"✅ Response contains 'tracking' data ({len(data['tracking'])} records)")
            else:
                print("❌ Response missing 'tracking' field")
        else:
            print(f"❌ /get-email-tracking returned {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Failed to connect to {BASE_URL}: {e}")

if __name__ == "__main__":
    test_get_email_tracking()
