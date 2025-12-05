import pymongo
from bson import ObjectId

# Connect to MongoDB
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["email_warmup"]

campaigns_collection = db["email_campaigns"]
tracking_collection = db["email_tracking"]

print("=== Database Analysis ===\n")

# Get total counts
total_campaigns = campaigns_collection.count_documents({})
total_tracking = tracking_collection.count_documents({})

print(f"Total Campaigns: {total_campaigns}")
print(f"Total Tracking Docs: {total_tracking}")

# Get a sample campaign
sample_campaign = campaigns_collection.find_one()
if sample_campaign:
    print(f"\n=== Sample Campaign ===")
    print(f"Campaign ID: {sample_campaign.get('campaign_id')}")
    print(f"Clerk User ID: {sample_campaign.get('clerk_user_id')}")
    print(f"Total Recipients: {sample_campaign.get('total_recipients')}")
    print(f"Sent Count: {sample_campaign.get('sent_count')}")
    print(f"Status: {sample_campaign.get('status')}")
    
    # Check if there are tracking docs for this campaign
    campaign_id = sample_campaign.get('campaign_id')
    tracking_for_campaign = tracking_collection.count_documents({'campaign_id': campaign_id})
    print(f"Tracking docs for this campaign: {tracking_for_campaign}")
    
    if tracking_for_campaign > 0:
        sample_tracking = tracking_collection.find_one({'campaign_id': campaign_id})
        print(f"\n=== Sample Tracking Doc ===")
        print(f"Campaign ID: {sample_tracking.get('campaign_id')}")
        print(f"Recipient: {sample_tracking.get('recipient_email')}")
        print(f"Sent At: {sample_tracking.get('sent_at')}")
        print(f"Bounced: {sample_tracking.get('bounced')}")
        print(f"Application Error: {sample_tracking.get('application_error')}")

# Check if there are ANY tracking docs
if total_tracking > 0:
    print(f"\n=== Tracking Documents Breakdown ===")
    any_tracking = tracking_collection.find_one()
    print(f"Sample tracking campaign_id: {any_tracking.get('campaign_id')}")
    
    # Get all unique campaign IDs from tracking
    tracking_campaign_ids = tracking_collection.distinct('campaign_id')
    print(f"Unique campaign IDs in tracking: {len(tracking_campaign_ids)}")
    print(f"First few: {tracking_campaign_ids[:5]}")
    
    # Get all campaign IDs from campaigns
    campaign_ids = campaigns_collection.distinct('campaign_id')
    print(f"\nUnique campaign IDs in campaigns: {len(campaign_ids)}")
    print(f"First few: {campaign_ids[:5]}")
    
    # Check for mismatches
    tracking_set = set(tracking_campaign_ids)
    campaign_set = set(campaign_ids)
    
    orphaned_tracking = tracking_set - campaign_set
    campaigns_without_tracking = campaign_set - tracking_set
    
    print(f"\nOrphaned tracking docs (no matching campaign): {len(orphaned_tracking)}")
    print(f"Campaigns without tracking: {len(campaigns_without_tracking)}")
else:
    print("\n⚠️ NO TRACKING DOCUMENTS FOUND!")
    print("This means emails were never sent or tracking wasn't created.")

client.close()
