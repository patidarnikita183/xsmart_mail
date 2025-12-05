import requests
import json

# Test the dashboard analytics endpoint
url = "http://localhost:5000/api/analytics/dashboard"

# You'll need to provide a valid Clerk user ID
# Replace with an actual user ID from your database
headers = {
    "X-Clerk-User-Id": "user_2pUmYOLdXWJbBFKNJbqQdxpMCQP"  # Replace with actual user ID
}

print("Testing Dashboard Analytics Endpoint")
print("=" * 80)
print(f"URL: {url}")
print(f"Headers: {headers}")
print()

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print("Response Data:")
        print(json.dumps(data, indent=2))
    else:
        print("Error Response:")
        print(response.text)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
