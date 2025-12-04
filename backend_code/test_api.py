#!/usr/bin/env python3
"""
API Test Script for Outlook Email Application
Tests all API endpoints to ensure they work correctly
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"  # Change if your server runs on different port
TEST_EMAIL = "test@example.com"  # Change to a test email
TEST_CAMPAIGN_ID = None  # Will be set after sending email
TEST_TRACKING_ID = None  # Will be set after sending email

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def print_header(message):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def test_endpoint(name, method, url, data=None, files=None, expected_status=200, description=""):
    """Test a single endpoint"""
    print(f"\n{Colors.BOLD}Testing: {name}{Colors.RESET}")
    if description:
        print(f"Description: {description}")
    print(f"URL: {method} {url}")
    
    try:
        if method == 'GET':
            response = requests.get(url, allow_redirects=False)
        elif method == 'POST':
            if files:
                response = requests.post(url, data=data, files=files)
            else:
                response = requests.post(url, json=data)
        else:
            print_error(f"Unsupported method: {method}")
            return False
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == expected_status:
            print_success(f"✓ {name} - Status code matches expected ({expected_status})")
            
            # Try to parse JSON response
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    json_data = response.json()
                    print(f"Response: {json.dumps(json_data, indent=2)}")
                    return True, json_data
                else:
                    print_info(f"Response: {response.text[:200]}")
                    return True, response.text
            except:
                print_info(f"Response: {response.text[:200]}")
                return True, response.text
        else:
            print_error(f"✗ {name} - Expected status {expected_status}, got {response.status_code}")
            print_error(f"Response: {response.text[:500]}")
            return False, None
            
    except requests.exceptions.ConnectionError:
        print_error(f"✗ {name} - Cannot connect to server. Is the Flask app running?")
        return False, None
    except Exception as e:
        print_error(f"✗ {name} - Error: {str(e)}")
        return False, None

def main():
    """Run all API tests"""
    print_header("OUTLOOK EMAIL API TEST SUITE")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track test results
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }
    
    global TEST_CAMPAIGN_ID, TEST_TRACKING_ID
    
    # Test 1: Home page redirect
    print_header("1. BASIC ENDPOINTS")
    success, _ = test_endpoint(
        "Home Page Redirect",
        "GET",
        f"{BASE_URL}/",
        expected_status=302,  # Redirect
        description="Should redirect to /app"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 2: App page
    success, _ = test_endpoint(
        "App Page",
        "GET",
        f"{BASE_URL}/app",
        expected_status=200,
        description="Should return the main app page"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 3: Signin redirect
    success, _ = test_endpoint(
        "Signin Redirect",
        "GET",
        f"{BASE_URL}/signin",
        expected_status=302,  # Redirect to Microsoft OAuth
        description="Should redirect to Microsoft OAuth"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 4: Get User Profile (requires authentication)
    print_header("2. AUTHENTICATION ENDPOINTS")
    success, data = test_endpoint(
        "Get User Profile",
        "GET",
        f"{BASE_URL}/get-user-profile",
        expected_status=401,  # Unauthorized without auth
        description="Should return 401 if not authenticated"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: Get Registered Users (requires authentication)
    success, data = test_endpoint(
        "Get Registered Users",
        "GET",
        f"{BASE_URL}/get-registered-users",
        expected_status=401,  # Unauthorized without auth
        description="Should return 401 if not authenticated"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 6: Send Mail - JSON (requires authentication)
    print_header("3. EMAIL SENDING ENDPOINTS")
    print_warning("Note: These tests require authentication. They will return 401 without valid session.")
    
    send_mail_data = {
        "recipients": [
            {"name": "Test User", "email": TEST_EMAIL}
        ],
        "subject": "Test Email Subject",
        "message": "This is a test email message. Hi {name}!"
    }
    
    success, data = test_endpoint(
        "Send Mail (JSON)",
        "POST",
        f"{BASE_URL}/send-mail",
        data=send_mail_data,
        expected_status=401,  # Unauthorized without auth
        description="Should return 401 if not authenticated. With auth, should send email and return campaign_id"
    )
    if success:
        results['passed'] += 1
        # If we had auth, we could extract campaign_id here
        # if data and isinstance(data, dict) and 'campaign_id' in data:
        #     TEST_CAMPAIGN_ID = data['campaign_id']
        #     if data.get('tracking_data') and len(data['tracking_data']) > 0:
        #         TEST_TRACKING_ID = data['tracking_data'][0].get('tracking_id')
    else:
        results['failed'] += 1
    
    # Test 7: Get Mails (requires authentication)
    print_header("4. EMAIL RETRIEVAL ENDPOINTS")
    success, data = test_endpoint(
        "Get Recent Emails",
        "GET",
        f"{BASE_URL}/get-mails/10",
        expected_status=401,  # Unauthorized without auth
        description="Should return 401 if not authenticated. With auth, should return recent emails"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 8: Get Campaign (requires campaign_id)
    print_header("5. CAMPAIGN ENDPOINTS")
    success, data = test_endpoint(
        "Get Campaign Details",
        "GET",
        f"{BASE_URL}/api/campaign/test-campaign-id-123",
        expected_status=404,  # Not found without valid campaign
        description="Should return 404 for non-existent campaign. With valid campaign_id, should return campaign data"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 9: Get Campaign Analytics
    success, data = test_endpoint(
        "Get Campaign Analytics",
        "GET",
        f"{BASE_URL}/api/analytics/campaign/test-campaign-id-123",
        expected_status=404,  # Not found without valid campaign
        description="Should return 404 for non-existent campaign. With valid campaign_id, should return analytics"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 10: Get Campaign Logs
    success, data = test_endpoint(
        "Get Campaign Logs",
        "GET",
        f"{BASE_URL}/get-campaign-logs",
        expected_status=200,  # Should work without auth (or return empty list)
        description="Should return campaign logs"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 11: Get Email Tracking
    print_header("6. TRACKING ENDPOINTS")
    success, data = test_endpoint(
        "Get Email Tracking Details",
        "GET",
        f"{BASE_URL}/api/tracking/email/test-tracking-id-123",
        expected_status=404,  # Not found without valid tracking_id
        description="Should return 404 for non-existent tracking. With valid tracking_id, should return tracking data"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 12: Resend Email
    success, data = test_endpoint(
        "Resend Email",
        "POST",
        f"{BASE_URL}/api/tracking/resend/test-tracking-id-123",
        expected_status=401,  # Unauthorized without auth
        description="Should return 401 if not authenticated. With auth, should resend email"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 13: Track Email Open
    success, data = test_endpoint(
        "Track Email Open",
        "GET",
        f"{BASE_URL}/api/track/open/test-tracking-id-123",
        expected_status=200,  # Should return pixel image
        description="Should return 1x1 pixel image for tracking opens"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 14: Track Email Click
    success, data = test_endpoint(
        "Track Email Click",
        "GET",
        f"{BASE_URL}/api/track/click/test-tracking-id-123?url=https://example.com",
        expected_status=302,  # Redirect
        description="Should redirect to original URL after tracking click"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 15: Start Warmup (requires authentication)
    print_header("7. WARMUP ENDPOINTS")
    warmup_data = {
        "delay_between_emails": 60,
        "delete_after_minutes": 1,
        "cleanup_recipient_mailbox": True
    }
    
    success, data = test_endpoint(
        "Start Warmup Campaign",
        "POST",
        f"{BASE_URL}/start-warmup",
        data=warmup_data,
        expected_status=401,  # Unauthorized without auth
        description="Should return 401 if not authenticated. With auth, should start warmup campaign"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 16: Logout
    print_header("8. SESSION ENDPOINTS")
    success, data = test_endpoint(
        "Logout",
        "GET",
        f"{BASE_URL}/logout",
        expected_status=302,  # Redirect
        description="Should clear session and redirect"
    )
    if success:
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.RESET}")
    print(f"{Colors.YELLOW}Skipped: {results['skipped']}{Colors.RESET}")
    print(f"\nTotal Tests: {results['passed'] + results['failed'] + results['skipped']}")
    
    if results['failed'] == 0:
        print_success("\n✓ All tests passed!")
        return 0
    else:
        print_error(f"\n✗ {results['failed']} test(s) failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

