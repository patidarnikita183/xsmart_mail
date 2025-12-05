import pymongo
from datetime import datetime, timezone

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_warmup"]

# Get collections
campaigns_collection = db["email_campaigns"]
tracking_collection = db["email_tracking"]

# Check if there's any data
print("=== Database Check ===")
print(f"Total campaigns: {campaigns_collection.count_documents({})}")
print(f"Total tracking docs: {tracking_collection.count_documents({})}")

# Get a sample tracking doc
sample_tracking = tracking_collection.find_one()
if sample_tracking:
    print("\n=== Sample Tracking Document ===")
    print(f"Campaign ID: {sample_tracking.get('campaign_id')}")
    print(f"Bounced: {sample_tracking.get('bounced')}")
    print(f"Application Error: {sample_tracking.get('application_error')}")
    print(f"Sent At: {sample_tracking.get('sent_at')}")
    print(f"Opens: {sample_tracking.get('opens')}")
    print(f"Clicks: {sample_tracking.get('clicks')}")
else:
    print("\nNo tracking documents found!")

# Check campaigns
sample_campaign = campaigns_collection.find_one()
if sample_campaign:
    print("\n=== Sample Campaign Document ===")
    print(f"Campaign ID: {sample_campaign.get('campaign_id')}")
    print(f"Clerk User ID: {sample_campaign.get('clerk_user_id')}")
    print(f"Total Recipients: {sample_campaign.get('total_recipients')}")
    print(f"Status: {sample_campaign.get('status')}")
else:
    print("\nNo campaign documents found!")

# Count tracking docs by status
print("\n=== Tracking Docs Breakdown ===")
total_tracking = tracking_collection.count_documents({})
bounced_count = tracking_collection.count_documents({'bounced': True})
app_error_count = tracking_collection.count_documents({'application_error': True})
print(f"Total tracking docs: {total_tracking}")
print(f"Bounced: {bounced_count}")
print(f"Application errors: {app_error_count}")
print(f"Successfully sent (calculated): {total_tracking - bounced_count - app_error_count}")

client.close()
