import sys
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
mongo_url = os.getenv('MONGO_URL')
if not mongo_url:
    print("ERROR: MONGO_URL not found in environment")
    sys.exit(1)

client = MongoClient(mongo_url)
db = client['xsmart_mail_send']

# Get tracking collection
tracking_collection = db['email_tracking']

# Sample a few documents
print("=" * 80)
print("TRACKING DOCUMENTS SAMPLE")
print("=" * 80)

sample_docs = list(tracking_collection.find().limit(5))
for i, doc in enumerate(sample_docs, 1):
    print(f"\nDocument {i}:")
    print(f"  Campaign ID: {doc.get('campaign_id')}")
    print(f"  Recipient: {doc.get('recipient_email')}")
    print(f"  Sent At: {doc.get('sent_at')}")
    print(f"  Sent At Type: {type(doc.get('sent_at'))}")
    if isinstance(doc.get('sent_at'), datetime):
        print(f"  Sent At Timezone: {doc.get('sent_at').tzinfo}")
    print(f"  Bounced: {doc.get('bounced')}")
    print(f"  Delivered: {doc.get('delivered')}")
    print(f"  Opens: {doc.get('opens', 0)}")
    print(f"  Clicks: {doc.get('clicks', 0)}")

# Test datetime comparisons
print("\n" + "=" * 80)
print("TESTING DATETIME COMPARISONS")
print("=" * 80)

now = datetime.now(timezone.utc)
print(f"\nNow (UTC): {now}")
print(f"Now Type: {type(now)}")
print(f"Now Timezone: {now.tzinfo}")

today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
print(f"\nToday Start: {today_start}")
print(f"Today Start Type: {type(today_start)}")
print(f"Today Start Timezone: {today_start.tzinfo}")

week_start = now - timedelta(days=7)
print(f"\nWeek Start: {week_start}")
print(f"Week Start Type: {type(week_start)}")
print(f"Week Start Timezone: {week_start.tzinfo}")

# Try to compare with a sample document
if sample_docs:
    doc = sample_docs[0]
    sent_at = doc.get('sent_at')
    print(f"\n\nTesting comparison with first document:")
    print(f"  sent_at: {sent_at}")
    print(f"  sent_at type: {type(sent_at)}")
    
    if isinstance(sent_at, datetime):
        print(f"  sent_at timezone: {sent_at.tzinfo}")
        
        # Make timezone-aware if needed
        if sent_at.tzinfo is None:
            sent_at_aware = sent_at.replace(tzinfo=timezone.utc)
            print(f"  sent_at (made aware): {sent_at_aware}")
        else:
            sent_at_aware = sent_at
        
        try:
            result = sent_at_aware >= today_start
            print(f"  ✅ Comparison successful: sent_at >= today_start = {result}")
        except Exception as e:
            print(f"  ❌ Comparison failed: {e}")

# Count total tracking documents
total_count = tracking_collection.count_documents({})
print(f"\n\nTotal tracking documents: {total_count}")

# Count by campaign
print("\nDocuments per campaign:")
pipeline = [
    {"$group": {"_id": "$campaign_id", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
]
for result in tracking_collection.aggregate(pipeline):
    print(f"  Campaign {result['_id']}: {result['count']} emails")

client.close()
print("\n" + "=" * 80)
