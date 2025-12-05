import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
mongo_url = os.getenv('MONGO_URL')
client = MongoClient(mongo_url)
db = client['xsmart_mail_send']

# Get collections
campaigns_collection = db['email_campaigns']
tracking_collection = db['email_tracking']

# Get the Clerk user ID
clerk_user_id = "user_2pUmYOLdXWJbBFKNJbqQdxpMCQP"

print("=" * 80)
print(f"DATABASE ANALYSIS FOR USER: {clerk_user_id}")
print("=" * 80)

# Get campaigns for this user
campaigns = list(campaigns_collection.find({'clerk_user_id': clerk_user_id}))
print(f"\nTotal campaigns: {len(campaigns)}")

if campaigns:
    print("\nCampaign IDs:")
    campaign_ids = []
    for i, campaign in enumerate(campaigns[:10], 1):  # Show first 10
        campaign_id = campaign.get('campaign_id')
        campaign_ids.append(campaign_id)
        print(f"  {i}. {campaign_id}")
        print(f"     Subject: {campaign.get('subject', 'N/A')}")
        print(f"     Status: {campaign.get('status', 'N/A')}")
        print(f"     Created: {campaign.get('created_at', 'N/A')}")
    
    # Get tracking docs for these campaigns
    print(f"\n" + "=" * 80)
    print("TRACKING DOCUMENTS")
    print("=" * 80)
    
    tracking_docs = list(tracking_collection.find({'campaign_id': {'$in': campaign_ids}}))
    print(f"\nTotal tracking docs: {len(tracking_docs)}")
    
    if tracking_docs:
        # Analyze tracking docs
        bounced_count = sum(1 for doc in tracking_docs if doc.get('bounced') == True)
        app_error_count = sum(1 for doc in tracking_docs if doc.get('application_error') == True)
        delivered_count = sum(1 for doc in tracking_docs if doc.get('delivered') == True)
        
        print(f"\nTracking Stats:")
        print(f"  Bounced: {bounced_count}")
        print(f"  Application Errors: {app_error_count}")
        print(f"  Delivered: {delivered_count}")
        print(f"  Successfully sent (total - bounced - app_errors): {len(tracking_docs) - bounced_count - app_error_count}")
        
        # Sample a few tracking docs
        print(f"\nSample Tracking Documents (first 3):")
        for i, doc in enumerate(tracking_docs[:3], 1):
            print(f"\n  Document {i}:")
            print(f"    Campaign ID: {doc.get('campaign_id')}")
            print(f"    Recipient: {doc.get('recipient_email')}")
            print(f"    Sent At: {doc.get('sent_at')}")
            print(f"    Sent At Type: {type(doc.get('sent_at'))}")
            if isinstance(doc.get('sent_at'), datetime):
                sent_at = doc.get('sent_at')
                print(f"    Sent At Timezone: {sent_at.tzinfo}")
                print(f"    Sent At ISO: {sent_at.isoformat()}")
            print(f"    Bounced: {doc.get('bounced')}")
            print(f"    Application Error: {doc.get('application_error')}")
            print(f"    Delivered: {doc.get('delivered')}")
            print(f"    Opens: {doc.get('opens', 0)}")
            print(f"    Clicks: {doc.get('clicks', 0)}")
        
        # Test datetime comparison
        print(f"\n" + "=" * 80)
        print("TESTING DATETIME COMPARISONS")
        print("=" * 80)
        
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"\nNow: {now}")
        print(f"Now tzinfo: {now.tzinfo}")
        print(f"Today Start: {today_start}")
        print(f"Today Start tzinfo: {today_start.tzinfo}")
        
        # Test comparison with first tracking doc
        if tracking_docs:
            doc = tracking_docs[0]
            sent_at = doc.get('sent_at')
            print(f"\nFirst tracking doc sent_at: {sent_at}")
            print(f"Type: {type(sent_at)}")
            
            if isinstance(sent_at, datetime):
                print(f"Timezone: {sent_at.tzinfo}")
                
                # Make timezone-aware if needed
                if sent_at.tzinfo is None:
                    sent_at_aware = sent_at.replace(tzinfo=timezone.utc)
                    print(f"Made timezone-aware: {sent_at_aware}")
                else:
                    sent_at_aware = sent_at
                
                try:
                    result = sent_at_aware >= today_start
                    print(f"✅ Comparison successful: sent_at >= today_start = {result}")
                except TypeError as e:
                    print(f"❌ Comparison failed: {e}")
                    print(f"   sent_at_aware type: {type(sent_at_aware)}, tzinfo: {sent_at_aware.tzinfo}")
                    print(f"   today_start type: {type(today_start)}, tzinfo: {today_start.tzinfo}")
    else:
        print("\n⚠️  No tracking documents found for these campaigns!")
else:
    print("\n⚠️  No campaigns found for this user!")

client.close()
print("\n" + "=" * 80)
