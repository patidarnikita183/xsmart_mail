
# enhanced_email_warmup.py
import requests
import json
import time
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import uuid
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import DatabaseManager
from config import Config

class EnhancedEmailWarmupService:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.sent_message_ids = []
        self.campaign_stats = {}
    
    def get_headers(self, access_token: str) -> Dict:
        """Get request headers with access token"""
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def make_graph_request(self, endpoint: str, access_token: str, method: str = 'GET', data: Dict = None) -> Dict:
        """Make a request to Microsoft Graph API"""
        url = f"{self.base_url}{endpoint}"
        headers = self.get_headers(access_token)
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            
            response.raise_for_status()
            
            if response.content:
                try:
                    return response.json()
                except ValueError:
                    return {'success': True, 'status_code': response.status_code}
            return {'success': True, 'status_code': response.status_code}
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return {'error': str(e), 'status_code': getattr(e.response, 'status_code', 500)}
    
    def create_warmup_email(self, sender_email: str, recipient_email: str) -> Dict:
        """Create a warm-up email with natural content"""
        
        subjects = [
            "Quick check-in",
            "Following up on our conversation",
            "Hope you're doing well",
            "Brief update",
            "Touching base",
            "Quick hello",
            "Weekly sync",
            "Monthly update",
            "Project status",
            "Team coordination",
            "Quarterly review",
            "Partnership discussion",
            "Meeting follow-up",
            "Important announcement",
            "Schedule coordination"
        ]
        
        bodies = [
            """Hi there,

I hope this email finds you well. I wanted to reach out for a quick check-in and see how things are going on your end.

If you have a moment, I'd love to hear about any updates or developments you might want to share.

Best regards,
{sender_name}""",
            
            """Hello,

I hope you're having a great day! I wanted to follow up on our previous conversation and see if there's anything new to discuss.

Please let me know if you need any assistance or have any questions.

Best,
{sender_name}""",
            
            """Hi,

I hope everything is going smoothly for you. I wanted to send a quick update and check if there's anything I can help you with.

Looking forward to hearing from you soon.

Kind regards,
{sender_name}""",
            
            """Hello,

I trust you're doing well. I wanted to touch base and see how your projects are progressing.

If there's anything you'd like to discuss or if you need any support, please don't hesitate to reach out.

Best wishes,
{sender_name}""",
            
            """Hi,

I hope this message finds you in good spirits. I wanted to reach out to see if there are any updates on your end.

Please feel free to share any news or developments you think might be relevant.

Warm regards,
{sender_name}"""
        ]
        
        sender_name = sender_email.split('@')[0].replace('.', ' ').title()
        
        subject = random.choice(subjects)
        body = random.choice(bodies).format(sender_name=sender_name)
        
        return {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient_email
                        }
                    }
                ]
            }
        }
    
    def send_warmup_email(self, sender_email: str, recipient_email: str, access_token: str) -> Optional[str]:
        """Send a warm-up email and return the message ID"""
        try:
            email_data = self.create_warmup_email(sender_email, recipient_email)
            
            response = self.make_graph_request('/me/sendMail', access_token, 'POST', email_data)
            
            if 'error' in response:
                print(f"✗ Failed to send email from {sender_email} to {recipient_email}: {response['error']}")
                return None
            
            time.sleep(3)  # Wait for email to appear in sent items
            
            sent_messages = self.make_graph_request(
                f"/me/mailFolders/sentitems/messages?$top=1&$orderby=sentDateTime desc",
                access_token
            )
            
            if sent_messages.get('value'):
                message_id = sent_messages['value'][0]['id']
                print(f"✓ Email sent from {sender_email} to {recipient_email} - Message ID: {message_id}")
                return message_id
            else:
                print(f"✗ Failed to get message ID for email from {sender_email} to {recipient_email}")
                return None
                
        except Exception as e:
            print(f"✗ Error sending email from {sender_email} to {recipient_email}: {e}")
            return None
    
    def delete_email_from_mailbox(self, message_id: str, access_token: str, mailbox_type: str = 'sent') -> bool:
        """Delete an email from specified mailbox"""
        try:
            if mailbox_type == 'sent':
                # Delete from sent items
                response = self.make_graph_request(f'/me/messages/{message_id}', access_token, 'DELETE')
            else:
                # Delete from inbox
                response = self.make_graph_request(f'/me/messages/{message_id}', access_token, 'DELETE')
            
            if 'error' not in response:
                print(f"✓ Deleted email from {mailbox_type} mailbox - ID: {message_id}")
                return True
            else:
                print(f"✗ Error deleting email from {mailbox_type} mailbox {message_id}: {response['error']}")
                return False
                
        except Exception as e:
            print(f"✗ Error deleting email from {mailbox_type} mailbox {message_id}: {e}")
            return False
    
    def find_and_delete_received_emails(self, recipient_email: str, sender_email: str, subject_keywords: List[str]) -> int:
        """Find and delete received emails in target mailbox"""
        try:
            recipient_data = self.db_manager.get_user_tokens(recipient_email['email'] if isinstance(recipient_email, dict) else recipient_email)
            
            if not recipient_data:
                print(f"✗ No access token found for recipient {recipient_email}")
                print(f"✗ No access token found for recipient {recipient_email}")
                return 0
            
            access_token = recipient_data['access_token']
            print("access token",access_token)
            # Search for emails from sender
            search_query = f"from:{sender_email}"
            messages = self.make_graph_request(
                f"/me/messages?$filter=from/emailAddress/address eq '{sender_email}'&$top=50",
                access_token
            )
            
            if 'value' not in messages:
                print(f"✗ No messages found from {sender_email} to {recipient_email}")
                return 0
            
            deleted_count = 0
            for message in messages['value']:
                message_id = message['id']
                subject = message.get('subject', '')
                
                # Check if subject contains any of our warmup keywords
                if any(keyword.lower() in subject.lower() for keyword in subject_keywords):
                    if self.delete_email_from_mailbox(message_id, access_token, 'inbox'):
                        deleted_count += 1
                        time.sleep(1)  # Small delay between deletions
            
            return deleted_count
            
        except Exception as e:
            print(f"✗ Error finding and deleting emails for {recipient_email}: {e}")
            return 0
    
    def run_comprehensive_warmup_campaign(self, 
                                        sender_emails: List[str],
                                        target_emails: List[str],
                                        delay_between_emails: int = 60,
                                        delete_after_minutes: int = 5,
                                        cleanup_recipient_mailbox: bool = True) -> Dict:
        """Run a comprehensive warm-up campaign with bidirectional email management"""
        
        print(f"🚀 Starting comprehensive warm-up campaign")
        print(f"📤 Sender emails: {len(sender_emails)}")
        print(f"📥 Target emails: {len(target_emails)}")
        print(f"⏱️  Delay between emails: {delay_between_emails} seconds")
        print(f"🗑️  Delete after: {delete_after_minutes} minutes")
        print(f"🧹 Cleanup recipient mailbox: {cleanup_recipient_mailbox}")
        print("-" * 70)
        
        campaign_stats = {
            'total_sender_emails': len(sender_emails),
            'total_target_emails': len(target_emails),
            'total_combinations': len(sender_emails) * len(target_emails),
            'emails_sent': 0,
            'send_failures': 0,
            'sender_deletions': 0,
            'recipient_deletions': 0,
            'delete_failures': 0,
            'start_time': datetime.now(timezone.utc),
            'sent_messages': [],
            'subject_keywords': []
        }
        
        # Phase 1: Send emails from all senders to all targets
        print("📧 Phase 1: Sending emails...")
        
        for sender_email in sender_emails:
            sender_email = sender_email['email'] if isinstance(sender_email, dict) else sender_email
            sender_data = self.db_manager.get_user_tokens(sender_email)
            if not sender_data:
                print(f"✗ No access token found for sender {sender_email}")
                continue
            
            access_token = sender_data['access_token']
            print("access token",access_token)
            for target_email in target_emails:
                target_email = target_email['email'] if isinstance(target_email, dict) else target_email
                print(f"📤 Sending from {sender_email} to {target_email}")
                
                message_id = self.send_warmup_email(sender_email, target_email, access_token)
                
                if message_id:
                    campaign_stats['emails_sent'] += 1
                    campaign_stats['sent_messages'].append({
                        'message_id': message_id,
                        'sender': sender_email,
                        'recipient': target_email,
                        'access_token': access_token,
                        'sent_at': datetime.now(timezone.utc)
                    })
                else:
                    campaign_stats['send_failures'] += 1
                
                # Update last used timestamp
                self.db_manager.update_last_used(sender_email)
                
                # Add delay between emails
                delay = int(delay_between_emails) + random.randint(-10, 10)
                if delay > 0:
                    time.sleep(delay)
        
        print(f"\n📊 Sending phase complete:")
        print(f"✅ Successfully sent: {campaign_stats['emails_sent']}")
        print(f"❌ Failed to send: {campaign_stats['send_failures']}")
        
        # Phase 2: Wait before deletion
        if campaign_stats['sent_messages']:
            print(f"\n⏰ Waiting {delete_after_minutes} minutes before cleanup...")
            time.sleep(delete_after_minutes * 60)
            
            # Phase 3: Delete emails from sender mailboxes
            print(f"\n🗑️  Phase 3: Cleaning up sender mailboxes...")
            
            for message_data in campaign_stats['sent_messages']:
                if self.delete_email_from_mailbox(
                    message_data['message_id'], 
                    message_data['access_token'], 
                    'sent'
                ):
                    campaign_stats['sender_deletions'] += 1
                else:
                    campaign_stats['delete_failures'] += 1
                
                time.sleep(1)  # Small delay between deletions
            
            # Phase 4: Clean up recipient mailboxes (if enabled)
            if cleanup_recipient_mailbox:
                print(f"\n🧹 Phase 4: Cleaning up recipient mailboxes...")
                
                # Get common subject keywords from sent emails
                subject_keywords = [
                    "Quick check-in", "Following up", "Hope you're doing well",
                    "Brief update", "Touching base", "Quick hello", "Weekly sync",
                    "Monthly update", "Project status", "Team coordination"
                ]
                
                for target_email in target_emails:
                    target_email = target_email['email'] if isinstance(target_email, dict) else target_email
                    total_deleted = 0
                    for sender_email in sender_emails:
                        sender_email = sender_email['email'] if isinstance(sender_email, dict) else sender_email
                        deleted_count = self.find_and_delete_received_emails(
                            target_email, sender_email, subject_keywords
                        )
                        total_deleted += deleted_count
                    
                    campaign_stats['recipient_deletions'] += total_deleted
                    print(f"🧹 Cleaned {total_deleted} emails from {target_email}")
                    
                    # Update last used timestamp for target
                    self.db_manager.update_last_used(target_email)
        
        # Final statistics
        campaign_stats['end_time'] = datetime.now(timezone.utc)
        campaign_stats['total_duration'] = (campaign_stats['end_time'] - campaign_stats['start_time']).total_seconds()
        
        print(f"\n🎯 Campaign Summary:")
        print(f"📧 Total email combinations: {campaign_stats['total_combinations']}")
        print(f"✅ Emails sent: {campaign_stats['emails_sent']}")
        print(f"❌ Send failures: {campaign_stats['send_failures']}")
        print(f"🗑️  Sender deletions: {campaign_stats['sender_deletions']}")
        print(f"🧹 Recipient deletions: {campaign_stats['recipient_deletions']}")
        print(f"⚠️  Delete failures: {campaign_stats['delete_failures']}")
        print(f"⏱️  Total duration: {campaign_stats['total_duration']:.2f} seconds")
        
        # Save campaign log to database
        self.db_manager.save_warmup_campaign_log(campaign_stats)
        
        return campaign_stats
    
    def run_background_warmup_process(self):
        """Run continuous background warmup process"""
        print("🔄 Starting background warmup process...")
        
        while True:
            try:
                # Get all active senders and targets
                senders = self.db_manager.get_all_active_users('sender')
                targets = self.db_manager.get_all_active_users('target')
                
                if not senders or not targets:
                    print("⏳ No active senders or targets found, waiting...")
                    time.sleep(300)  # Wait 5 minutes
                    continue
                
                sender_emails = [user['email'] for user in senders]
                target_emails = [user['email'] for user in targets]
                
                # Run campaign
                self.run_comprehensive_warmup_campaign(
                    sender_emails=sender_emails,
                    target_emails=target_emails,
                    delay_between_emails=random.randint(120, 300),  # 2-5 minutes
                    delete_after_minutes=random.randint(5, 15),     # 5-15 minutes
                    cleanup_recipient_mailbox=True
                )
                
                # Wait before next campaign (6-12 hours)
                wait_time = random.randint(21600, 43200)  # 6-12 hours in seconds
                print(f"⏰ Next campaign in {wait_time/3600:.1f} hours...")
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"❌ Error in background process: {e}")
                time.sleep(600)  # Wait 10 minutes before retry
