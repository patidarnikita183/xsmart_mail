from datetime import datetime, timezone

def test_parse(date_str):
    print(f"Testing string: '{date_str}'")
    try:
        # Current logic
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        print(f"✅ Success: {dt}")
    except Exception as e:
        print(f"❌ Failed: {e}")

# Test cases
test_parse("2025-12-03T12:50:00.000Z")  # Frontend format
test_parse("2025-12-03T12:50:00Z")      # No millis
test_parse("2025-12-03T12:50:00")       # No timezone
