import pymongo
from datetime import datetime, timezone, timedelta

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_warmup"]

tracking_collection = db["email_tracking"]

# Get a sample tracking doc
sample = tracking_collection.find_one()
if sample:
    print("=== Sample Tracking Document ===")
    print(f"Campaign ID: {sample.get('campaign_id')}")
    print(f"Sent At: {sample.get('sent_at')}")
    print(f"Sent At Type: {type(sample.get('sent_at'))}")
    print(f"Bounced: {sample.get('bounced')}")
    print(f"Application Error: {sample.get('application_error')}")
    
    # Check if sent_at is a datetime
    sent_at = sample.get('sent_at')
    if sent_at:
        if isinstance(sent_at, str):
            print(f"Sent At is a string: {sent_at}")
            try:
                parsed = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                print(f"Parsed datetime: {parsed}")
            except Exception as e:
                print(f"Error parsing: {e}")
        elif isinstance(sent_at, datetime):
            print(f"Sent At is already datetime: {sent_at}")
            print(f"Timezone info: {sent_at.tzinfo}")
    else:
        print("WARNING: sent_at is None or missing!")
    
    print("\n=== All Fields ===")
    for key, value in sample.items():
        print(f"{key}: {value} (type: {type(value).__name__})")
else:
    print("No tracking documents found!")

# Count total tracking docs
total = tracking_collection.count_documents({})
print(f"\n=== Total Tracking Documents: {total} ===")

# Check how many have sent_at field
with_sent_at = tracking_collection.count_documents({'sent_at': {'$exists': True, '$ne': None}})
print(f"Documents with sent_at: {with_sent_at}")

# Get date range of sent_at
if with_sent_at > 0:
    oldest = tracking_collection.find_one(sort=[('sent_at', 1)])
    newest = tracking_collection.find_one(sort=[('sent_at', -1)])
    if oldest and newest:
        print(f"Oldest sent_at: {oldest.get('sent_at')}")
        print(f"Newest sent_at: {newest.get('sent_at')}")

client.close()
