# API Testing Guide

This guide explains how to test all API endpoints for the Outlook Email Application.

## Test Tools Available

### 1. Python Test Script (`test_api.py`)
A comprehensive command-line test script that tests all endpoints.

### 2. HTML Test Suite (`test_api.html`)
An interactive web-based test interface for testing endpoints in your browser.

## Prerequisites

1. **Install required Python packages:**
   ```bash
   pip install requests
   ```

2. **Start your Flask application:**
   ```bash
   python app.py
   ```
   Make sure the server is running on `http://localhost:5000` (or update the base URL in test files).

## Method 1: Python Test Script

### Usage

1. **Run all tests:**
   ```bash
   python test_api.py
   ```

2. **The script will:**
   - Test all API endpoints
   - Show colored output (green for pass, red for fail)
   - Display response data
   - Provide a summary at the end

### Example Output

```
============================================================
OUTLOOK EMAIL API TEST SUITE
============================================================

ℹ Base URL: http://localhost:5000
ℹ Test started at: 2024-01-15 10:30:00

Testing: Home Page Redirect
✓ Home Page Redirect - Status code matches expected (302)

Testing: App Page
✓ App Page - Status code matches expected (200)

...

============================================================
TEST SUMMARY
============================================================
✓ Passed: 16
✗ Failed: 0
⚠ Skipped: 0

Total Tests: 16
✓ All tests passed!
```

### Customization

Edit the script to change:
- `BASE_URL`: Default is `http://localhost:5000`
- `TEST_EMAIL`: Default is `test@example.com`

## Method 2: HTML Test Suite

### Usage

1. **Open the HTML file in your browser:**
   - Double-click `test_api.html`
   - Or open it via: `file:///path/to/test_api.html`

2. **Configure settings:**
   - Set the Base URL (default: `http://localhost:5000`)
   - Set a test email address

3. **Run tests:**
   - Click "🚀 Run All Tests" to test everything
   - Or click individual "Test" buttons for specific endpoints

4. **View results:**
   - Each test shows a result box with status and response data
   - Summary section shows total passed/failed tests

### Features

- ✅ Interactive web interface
- ✅ Test individual endpoints
- ✅ Run all tests at once
- ✅ View detailed responses
- ✅ Real-time test summary

## Endpoints Being Tested

### 1. Basic Endpoints
- `GET /` - Home page redirect
- `GET /app` - Main app page
- `GET /signin` - Signin redirect

### 2. Authentication Endpoints
- `GET /get-user-profile` - Get user profile
- `GET /get-registered-users` - Get registered users

### 3. Email Sending
- `POST /send-mail` - Send email with tracking

### 4. Email Retrieval
- `GET /get-mails/{count}` - Get recent emails

### 5. Campaign Endpoints
- `GET /api/campaign/{campaign_id}` - Get campaign details
- `GET /api/analytics/campaign/{campaign_id}` - Get campaign analytics
- `GET /get-campaign-logs` - Get campaign logs

### 6. Tracking Endpoints
- `GET /api/tracking/email/{tracking_id}` - Get email tracking
- `POST /api/tracking/resend/{tracking_id}` - Resend email
- `GET /api/track/open/{tracking_id}` - Track email open
- `GET /api/track/click/{tracking_id}` - Track link click

### 7. Warmup Endpoints
- `POST /start-warmup` - Start warmup campaign

### 8. Session Endpoints
- `GET /logout` - Logout user

## Testing with Authentication

**Note:** Many endpoints require authentication. Without a valid session, they will return `401 Unauthorized`.

To test authenticated endpoints:

1. **Via Browser:**
   - First, visit `http://localhost:5000/app`
   - Click "Sign In with Microsoft"
   - Complete OAuth flow
   - Then run tests (they'll use your session cookies)

2. **Via Python Script:**
   - You'll need to add session management to the script
   - Or use the HTML test suite which uses browser cookies

## Expected Results

### Without Authentication:
- ✅ Basic endpoints: Should work (200/302)
- ⚠️ Protected endpoints: Should return 401 (this is expected)
- ✅ Public endpoints: Should work normally

### With Authentication:
- ✅ All endpoints should work
- ✅ Email sending should create campaigns
- ✅ Tracking should work properly

## Troubleshooting

### Connection Errors
- **Error:** "Cannot connect to server"
- **Solution:** Make sure Flask app is running on the correct port

### 401 Errors
- **Error:** "401 Unauthorized" on protected endpoints
- **Solution:** This is expected if not authenticated. Sign in first via browser.

### 404 Errors
- **Error:** "404 Not Found" on campaign/tracking endpoints
- **Solution:** Use valid IDs from actual campaigns, or expect 404 for test IDs

### Import Errors
- **Error:** "ModuleNotFoundError: No module named 'requests'"
- **Solution:** Run `pip install requests`

## Advanced Testing

### Test with Real Data

1. **Send a real email:**
   - Use the HTML interface after signing in
   - Send an email to get a real `campaign_id`

2. **Test with real IDs:**
   - Update test scripts with real campaign/tracking IDs
   - Test analytics and tracking endpoints

### Automated Testing

You can integrate the Python test script into CI/CD:

```bash
python test_api.py
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed!"
    exit 1
fi
```

## Notes

- The test scripts test endpoint availability and basic functionality
- They don't test business logic or data validation in depth
- For full testing, you should also test with real authentication and data
- Some endpoints may return different status codes based on data availability (e.g., 404 for non-existent campaigns)

## Support

If you encounter issues:
1. Check that the Flask app is running
2. Verify the base URL is correct
3. Check browser console (for HTML tests) or terminal (for Python tests)
4. Review the Flask app logs for server-side errors

