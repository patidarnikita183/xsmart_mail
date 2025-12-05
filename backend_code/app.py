# main.py
import re
import html
import requests
import threading
import uuid
import pandas as pd
from datetime import datetime, timezone
from flask import Flask, Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_cors import CORS
from auth import get_auth_url, get_access_token, make_graph_request
from enhanced_email_warmup import EnhancedEmailWarmupService
from database import DatabaseManager
from background_service import BackgroundWarmupService
from config import Config

# Helper function to refresh access token
def refresh_access_token(refresh_token_value):
    """Refresh an expired access token using refresh token"""
    try:
        token_url = f"{Config.AUTHORITY}/oauth2/v2.0/token"
        refresh_data = {
            'client_id': Config.CLIENT_ID,
            'client_secret': Config.CLIENT_SECRET,
            'refresh_token': refresh_token_value,
            'grant_type': 'refresh_token',
            'scope': ' '.join(Config.USER_SCOPES)
        }
        refresh_response = requests.post(token_url, data=refresh_data)
        
        if refresh_response.status_code == 200:
            new_token_data = refresh_response.json()
            return {
                'success': True,
                'access_token': new_token_data.get('access_token'),
                'refresh_token': new_token_data.get('refresh_token', refresh_token_value),  # Use new or keep old
                'expires_in': new_token_data.get('expires_in', 3600)
            }
        else:
            print(f"❌ Token refresh failed: HTTP {refresh_response.status_code}")
            try:
                error_data = refresh_response.json()
                print(f"   Error: {error_data}")
            except:
                print(f"   Error: {refresh_response.text}")
            return {'success': False, 'error': f'Token refresh failed: HTTP {refresh_response.status_code}'}
    except Exception as e:
        print(f"❌ Exception during token refresh: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

# ============================================================================
# BACKGROUND CAMPAIGN EXECUTION - Helper Functions
# ============================================================================

from collections import deque
from threading import Lock
import time
import signal
import sys

# Global rate limiter for email sending (30 emails per minute for Microsoft)
class RateLimiter:
    def __init__(self, max_per_minute=30):
        self.max_per_minute = max_per_minute
        self.timestamps = deque()
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait if we've hit the rate limit"""
        with self.lock:
            now = time.time()
            
            # Remove timestamps older than 1 minute
            while self.timestamps and self.timestamps[0] < now - 60:
                self.timestamps.popleft()
            
            # If we've hit the limit, wait
            if len(self.timestamps) >= self.max_per_minute:
                wait_time = 60 - (now - self.timestamps[0])
                if wait_time > 0:
                    print(f"⏸️  Rate limit reached. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                    # Clear old timestamps after waiting
                    self.timestamps.clear()
            
            # Record this send
            self.timestamps.append(now)

# Create global rate limiter
email_rate_limiter = RateLimiter(max_per_minute=30)

# Safe database update with retry logic
def safe_db_update(collection, filter_query, update_query, max_retries=3):
    """Safely update database with retry logic"""
    for attempt in range(max_retries):
        try:
            result = collection.update_one(filter_query, update_query)
            return result
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  DB update failed (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(1)  # Wait 1 second before retry
            else:
                print(f"❌ DB update failed after {max_retries} attempts: {e}")
                raise

# Check for campaign time conflicts
def check_campaign_conflicts(clerk_user_id, new_start_time, new_duration):
    """Check if new campaign overlaps with existing campaigns"""
    from datetime import timedelta
    
    if not db_manager or db_manager.db is None:
        return []
    
    campaigns_collection = db_manager.db['email_campaigns']
    now = datetime.now(timezone.utc)
    
    # Calculate new campaign time window
    new_end_time = new_start_time + timedelta(hours=new_duration)
    
    # Find all active or scheduled campaigns for this user
    user_campaigns = list(campaigns_collection.find({
        'clerk_user_id': clerk_user_id,
        'status': {'$in': ['active', 'scheduled']}
    }))
    
    conflicts = []
    for existing in user_campaigns:
        existing_start = existing.get('start_time')
        existing_duration = existing.get('duration', 24)
        
        if not existing_start:
            continue
        
        # Ensure timezone-aware
        if isinstance(existing_start, str):
            existing_start = datetime.fromisoformat(existing_start.replace('Z', '+00:00'))
        if existing_start.tzinfo is None:
            existing_start = existing_start.replace(tzinfo=timezone.utc)
        
        existing_end = existing_start + timedelta(hours=existing_duration)
        
        # Check for overlap: campaigns overlap if one starts before the other ends
        overlaps = (new_start_time < existing_end) and (new_end_time > existing_start)
        
        if overlaps:
            conflicts.append({
                'campaign_id': existing.get('campaign_id'),
                'subject': existing.get('subject'),
                'start_time': existing_start.isoformat(),
                'end_time': existing_end.isoformat()
            })
    
    return conflicts


# Background email sender function
def send_emails_in_background(campaign_id, mailbox_id, sender_email, subject, message, 
                               recipients, start_time, duration, send_interval, clerk_user_id):
    """
    Send emails in background thread respecting duration and interval.
    This function runs independently and updates campaign status in MongoDB.
    """
    from datetime import timedelta
    from bson import ObjectId
    
    print(f"📧 Background email sender started for campaign {campaign_id}")
    print(f"🐛 DEBUG: start_time={start_time}, duration={duration}, interval={send_interval}, recipients={len(recipients)}")
    print(f"🐛 DEBUG: start_time type={type(start_time)}")

    
    if not db_manager or db_manager.db is None:
        print(f"❌ Database not available for campaign {campaign_id}")
        print(f"   Campaign {campaign_id} cannot start. Please check database connection.")
        return
    
    campaigns_collection = db_manager.db['email_campaigns']
    tracking_collection = db_manager.db['email_tracking']
    
    try:
        # Wait until start_time if campaign is scheduled
        now = datetime.now(timezone.utc)
        if start_time > now:
            wait_seconds = (start_time - now).total_seconds()
            print(f"📅 Campaign {campaign_id} scheduled. Waiting {wait_seconds/60:.1f} minutes...")
            time.sleep(wait_seconds)
        
        # Update campaign status to active
        safe_db_update(
            campaigns_collection,
            {'campaign_id': campaign_id},
            {'$set': {'status': 'active', 'updated_at': datetime.now(timezone.utc)}}
        )
        
        print(f"🚀 Starting background email sending for campaign {campaign_id}")
        
        # Calculate campaign end time
        campaign_end_time = start_time + timedelta(hours=duration)
        current_send_time = start_time
        
        sent_count = 0
        failed_count = 0
        consecutive_failures = 0
        max_consecutive_failures = 5  # Stop campaign after 5 consecutive failures
        
        for idx, recipient in enumerate(recipients):
            # Check if campaign was stopped
            # We check the DB directly to ensure we catch the stop signal immediately
            current_status_doc = campaigns_collection.find_one({'campaign_id': campaign_id}, {'status': 1})
            if current_status_doc and current_status_doc.get('status') == 'stopped':
                print(f"🛑 Campaign {campaign_id} was stopped by user. Aborting remaining emails.")
                break

            # Calculate when this email should be sent
            if idx > 0:
                current_send_time = current_send_time + timedelta(minutes=float(send_interval))
            
            # Check if we're past campaign end time
            if current_send_time > campaign_end_time:
                print(f"⏰ Campaign {campaign_id} duration exceeded. Stopping.")
                break
            
            # Wait until it's time to send this email
            now = datetime.now(timezone.utc)
            if current_send_time > now:
                wait_seconds = (current_send_time - now).total_seconds()
                if wait_seconds > 0:
                    print(f"⏳ Waiting {wait_seconds:.1f}s before sending to {recipient.get('email')} (Interval: {send_interval}m)...")
                    time.sleep(wait_seconds)
            else:
                print(f"⚡ Sending immediately (Time: {current_send_time.isoformat()} <= Now: {now.isoformat()})")
            
            # Apply rate limiting
            email_rate_limiter.wait_if_needed()
            
            # Get recipient details
            recipient_email = recipient.get('email')
            if not recipient_email:
                print(f"⚠️  Recipient at index {idx} missing email, skipping")
                failed_count += 1
                continue
            
            recipient_name = recipient.get('name', recipient_email.split('@')[0])
            
            # Personalize message
            personalized_message = message
            personalized_subject = subject
            
            # Replace template variables
            template_pattern = r'\{\{?(\w+)\}?\}?'
            
            def replace_template_var(match):
                var_name = match.group(1)
                var_name_lower = var_name.lower()
                
                if var_name in recipient:
                    return str(recipient[var_name])
                elif var_name_lower in recipient:
                    return str(recipient[var_name_lower])
                elif var_name_lower in ['name', 'firstname']:
                    return recipient.get('firstName') or recipient_name.split()[0] if recipient_name else recipient_email.split('@')[0]
                elif var_name_lower == 'lastname':
                    if 'lastName' in recipient:
                        return str(recipient['lastName'])
                    name_parts = recipient_name.split()
                    return name_parts[-1] if len(name_parts) > 1 else ''
                elif var_name_lower == 'fullname':
                    return recipient_name
                elif var_name_lower == 'email':
                    return recipient_email
                else:
                    return match.group(0)
            
            personalized_message = re.sub(template_pattern, replace_template_var, personalized_message)
            personalized_subject = re.sub(template_pattern, replace_template_var, personalized_subject)
            
            # Generate tracking ID
            tracking_id = str(uuid.uuid4())
            
            # Add tracking pixel and click tracking
            tracking_url = f"{Config.BASE_URL}/api/track/open/{tracking_id}"
            click_tracking_url = f"{Config.BASE_URL}/api/track/click/{tracking_id}"
            
            # Replace links with tracking URLs
            link_pattern = r'<a\s+href=["\']([^"\']+)["\']'
            def replace_link(match):
                original_url = match.group(1)
                return f'<a href="{click_tracking_url}?url={original_url}"'
            
            email_html = re.sub(link_pattern, replace_link, personalized_message.replace('\n', '<br>'))
            tracking_pixel = f'<img src="{tracking_url}" width="1" height="1" style="display:none;" />'
            email_html += tracking_pixel
            
            # Send email with token refresh logic
            try:
                # Get fresh mailbox data (in case token was refreshed)
                mailbox = db_manager.mailboxes_collection.find_one({'_id': ObjectId(mailbox_id)})
                
                if not mailbox:
                    print(f"❌ Mailbox {mailbox_id} not found")
                    failed_count += 1
                    continue
                
                access_token = mailbox.get('access_token')
                
                # Create email payload
                email_payload = {
                    'message': {
                        'subject': personalized_subject,
                        'body': {
                            'contentType': 'HTML',
                            'content': email_html
                        },
                        'toRecipients': [{
                            'emailAddress': {
                                'address': recipient_email,
                                'name': recipient_name
                            }
                        }]
                    }
                }
                
                # Send via Microsoft Graph API
                url = f"{Config.GRAPH_ENDPOINT}/me/sendMail"
                headers = {
                    'Authorization': f'Bearer {access_token}',
                    'Content-Type': 'application/json'
                }
                
                http_response = requests.post(url, headers=headers, json=email_payload)
                http_status = http_response.status_code
                
                # Handle token expiration
                if http_status == 401:
                    print(f"⚠️  Access token expired, attempting to refresh...")
                    refresh_token_value = mailbox.get('refresh_token')
                    if refresh_token_value:
                        refresh_result = refresh_access_token(refresh_token_value)
                        if refresh_result.get('success'):
                            new_access_token = refresh_result.get('access_token')
                            new_refresh_token = refresh_result.get('refresh_token')
                            
                            # Update mailbox with new tokens
                            db_manager.mailboxes_collection.update_one(
                                {'_id': ObjectId(mailbox_id)},
                                {'$set': {
                                    'access_token': new_access_token,
                                    'refresh_token': new_refresh_token,
                                    'updated_at': datetime.now(timezone.utc)
                                }}
                            )
                            
                            # Retry with new token
                            headers['Authorization'] = f'Bearer {new_access_token}'
                            http_response = requests.post(url, headers=headers, json=email_payload)
                            http_status = http_response.status_code
                
                # Check if send was successful
                if http_status in [200, 202]:
                    sent_count += 1
                    consecutive_failures = 0  # Reset failure counter on success
                    
                    # Save tracking data
                    tracking_doc = {
                        'tracking_id': tracking_id,
                        'campaign_id': campaign_id,
                        'sender_email': sender_email,
                        'recipient_name': recipient_name,
                        'recipient_email': recipient_email,
                        'subject': personalized_subject,
                        'message': personalized_message,
                        'sent_at': datetime.now(timezone.utc),
                        'opens': 0,
                        'clicks': 0,
                        'unsubscribed': False,
                        'replies': 0,
                        'bounced': False,
                        'delivered': True,  # Successfully delivered to email server
                        'first_open': None,
                        'first_click': None,
                        'unsubscribe_date': None,
                        'reply_date': None
                    }
                    tracking_collection.insert_one(tracking_doc)
                    print(f"✅ Sent email to {recipient_email}")
                else:
                    failed_count += 1
                    consecutive_failures += 1
                    
                    # Determine if this is an actual bounce (email server rejection) or application error
                    # HTTP 4xx errors (except 401) are usually bounces from email server
                    # HTTP 5xx and other errors are application/network errors
                    is_actual_bounce = (400 <= http_status < 500 and http_status != 401)
                    is_application_error = not is_actual_bounce
                    
                    # Create tracking document - mark as not delivered for application errors
                    tracking_doc = {
                        'tracking_id': tracking_id,
                        'campaign_id': campaign_id,
                        'sender_email': sender_email,
                        'recipient_name': recipient_name,
                        'recipient_email': recipient_email,
                        'subject': personalized_subject,
                        'message': personalized_message,
                        'sent_at': datetime.now(timezone.utc),
                        'opens': 0,
                        'clicks': 0,
                        'unsubscribed': False,
                        'replies': 0,
                        'bounced': is_actual_bounce,  # Only true for actual email server bounces
                        'delivered': False,  # Not delivered
                        'application_error': is_application_error,  # Flag for application errors
                        'error_reason': f'HTTP {http_status}',
                        'bounce_reason': f'HTTP {http_status}' if is_actual_bounce else None,
                        'bounce_date': datetime.now(timezone.utc) if is_actual_bounce else None,
                        'error_date': datetime.now(timezone.utc) if is_application_error else None,
                        'first_open': None,
                        'first_click': None,
                        'unsubscribe_date': None,
                        'reply_date': None
                    }
                    tracking_collection.insert_one(tracking_doc)
                    
                    if is_application_error:
                        print(f"❌ Application error sending to {recipient_email}: HTTP {http_status} (not delivered)")
                    else:
                        print(f"❌ Failed to send to {recipient_email}: HTTP {http_status} (bounced)")
                    
                    # Stop campaign if too many consecutive failures
                    if consecutive_failures >= max_consecutive_failures:
                        print(f"🛑 Stopping campaign {campaign_id} due to {consecutive_failures} consecutive failures")
                        safe_db_update(
                            campaigns_collection,
                            {'campaign_id': campaign_id},
                            {'$set': {
                                'status': 'stopped',
                                'error': f'Campaign stopped due to {consecutive_failures} consecutive failures',
                                'updated_at': datetime.now(timezone.utc)
                            }}
                        )
                        break
                    
            except Exception as e:
                print(f"❌ Failed to send email to {recipient_email}: {e}")
                failed_count += 1
                consecutive_failures += 1
                
                # Application errors should be marked as not delivered, not bounced
                tracking_collection.insert_one({
                    'tracking_id': str(uuid.uuid4()),
                    'campaign_id': campaign_id,
                    'sender_email': sender_email,
                    'recipient_email': recipient_email,
                    'recipient_name': recipient_name,
                    'subject': personalized_subject,
                    'message': personalized_message,
                    'bounced': False,  # Not a bounce - it's an application error
                    'delivered': False,  # Not delivered
                    'application_error': True,  # Flag as application error
                    'error_reason': f'Application error: {str(e)}',
                    'bounce_reason': None,  # Not a bounce
                    'bounce_date': None,
                    'error_date': datetime.now(timezone.utc),
                    'sent_at': datetime.now(timezone.utc),
                    'opens': 0,
                    'clicks': 0,
                    'unsubscribed': False,
                    'replies': 0
                })
                
                # Stop campaign if too many consecutive failures
                if consecutive_failures >= max_consecutive_failures:
                    print(f"🛑 Stopping campaign {campaign_id} due to {consecutive_failures} consecutive failures")
                    safe_db_update(
                        campaigns_collection,
                        {'campaign_id': campaign_id},
                        {'$set': {
                            'status': 'stopped',
                            'error': f'Campaign stopped due to {consecutive_failures} consecutive failures',
                            'updated_at': datetime.now(timezone.utc)
                        }}
                    )
                    break
            
            # Update campaign progress
            safe_db_update(
                campaigns_collection,
                {'campaign_id': campaign_id},
                {'$set': {
                    'sent_count': sent_count,
                    'failed_count': failed_count,
                    'updated_at': datetime.now(timezone.utc)
                }}
            )
        
        # Mark campaign as completed
        safe_db_update(
            campaigns_collection,
            {'campaign_id': campaign_id},
            {'$set': {
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        
        print(f"✅ Campaign {campaign_id} completed. Sent: {sent_count}, Failed: {failed_count}")
        
    except Exception as e:
        print(f"❌ Critical error in background email sender for campaign {campaign_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Mark campaign as failed
        try:
            safe_db_update(
                campaigns_collection,
                {'campaign_id': campaign_id},
                {'$set': {
                    'status': 'failed',
                    'error': str(e),
                    'updated_at': datetime.now(timezone.utc)
                }}
            )
        except:
            pass



app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Configure session cookies for cross-origin requests
# For localhost development, we need to allow cross-origin cookie sharing
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Works better for localhost development
app.config['SESSION_COOKIE_PATH'] = '/'  # Available for all paths
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = None  # Don't restrict domain
app.config['SESSION_COOKIE_PATH'] = '/'  # Available for all paths

# Configure CORS to allow frontend to access backend with credentials
# Get frontend URL from environment variable
frontend_origins = []
if Config.FRONTEND_URL:
    frontend_origins.append(Config.FRONTEND_URL)
    # Also add 127.0.0.1 variant if localhost is used (for development)
    if "localhost" in Config.FRONTEND_URL:
        frontend_origins.append(Config.FRONTEND_URL.replace("localhost", "127.0.0.1"))
else:
    print("⚠️  WARNING: FRONTEND_URL not set in environment variables")
    print("   CORS will be restricted. Please set FRONTEND_URL in your .env file")

CORS(app, 
     origins=frontend_origins if frontend_origins else [],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Clerk-User-Id"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Set-Cookie"])

# Global variables for access token and user profile
ACCESS_TOKEN = None
USER_PROFILE = None

# Temporary token store for OAuth session transfer (in production, use Redis or database)
OAUTH_TOKENS = {}  # {token: {user_profile, access_token, expires_at}}

# Initialize database and services with error handling
try:
    if not Config.MONGO_URL:
        print("⚠️  WARNING: MONGO_URL not set in environment variables")
        print("   Database operations will fail. Please set MONGO_URL in your .env file")
    
    db_manager = DatabaseManager(Config.MONGO_URL, Config.DATABASE_NAME)
    warmup_service = EnhancedEmailWarmupService(db_manager) if db_manager.db is not None else None
    # background_service = BackgroundWarmupService()
    
    # Start background service
    # background_service.start()
except Exception as e:
    print(f"⚠️  ERROR: Failed to initialize database: {e}")
    print("   The application will start but database operations will fail")
    print("   Please check your MongoDB connection string and network connectivity")
    db_manager = None
    warmup_service = None

# ============================================================================
# SERVER RESTART RECOVERY
# ============================================================================

def resume_interrupted_campaigns():
    """Resume campaigns that were interrupted by server restart"""
    try:
        if not db_manager or db_manager.db is None:
            print("⚠️  Cannot resume campaigns: Database not available")
            return
        
        campaigns_collection = db_manager.db['email_campaigns']
        tracking_collection = db_manager.db['email_tracking']
        now = datetime.now(timezone.utc)
        
        # Find campaigns that should be active but might have been interrupted
        interrupted = list(campaigns_collection.find({
            'status': {'$in': ['active', 'scheduled']},
        }))
        
        resumed_count = 0
        expired_count = 0
        
        for campaign in interrupted:
            start_time = campaign.get('start_time')
            duration = campaign.get('duration', 24)
            campaign_id = campaign.get('campaign_id')
            
            if not start_time or not campaign_id:
                continue
            
            # Ensure timezone-aware
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            
            from datetime import timedelta
            end_time = start_time + timedelta(hours=duration)
            
            # Check if campaign is still within its time window
            if now >= start_time and now <= end_time:
                print(f"🔄 Resuming interrupted campaign: {campaign_id}")
                
                # Get unsent recipients
                sent_emails = set()
                tracking_docs = tracking_collection.find({'campaign_id': campaign_id})
                for doc in tracking_docs:
                    sent_emails.add(doc.get('recipient_email'))
                
                # Filter out already-sent recipients
                all_recipients = campaign.get('recipients', [])
                remaining_recipients = [r for r in all_recipients if r.get('email') not in sent_emails]
                
                if remaining_recipients:
                    # Restart background thread for remaining recipients
                    thread = threading.Thread(
                        target=send_emails_in_background,
                        args=(
                            campaign_id,
                            campaign.get('mailbox_id'),
                            campaign.get('sender_email'),
                            campaign.get('subject'),
                            campaign.get('message'),
                            remaining_recipients,
                            start_time,
                            duration,
                            campaign.get('send_interval', 5),
                            campaign.get('clerk_user_id')
                        ),
                        daemon=True
                    )
                    thread.start()
                    resumed_count += 1
                    print(f"   ✅ Resumed with {len(remaining_recipients)} remaining recipients")
                else:
                    # All emails sent, mark as completed
                    campaigns_collection.update_one(
                        {'campaign_id': campaign_id},
                        {'$set': {'status': 'completed', 'completed_at': now}}
                    )
                    print(f"   ✅ All emails already sent, marked as completed")
            elif now > end_time:
                # Campaign expired, mark as completed
                campaigns_collection.update_one(
                    {'campaign_id': campaign_id},
                    {'$set': {'status': 'completed', 'completed_at': end_time}}
                )
                expired_count += 1
                print(f"⏰ Campaign {campaign_id} expired, marked as completed")
        
        if resumed_count > 0 or expired_count > 0:
            print(f"📊 Campaign recovery complete: {resumed_count} resumed, {expired_count} expired")
    except Exception as e:
        print(f"⚠️  Error resuming interrupted campaigns: {e}")
        import traceback
        traceback.print_exc()

# Resume interrupted campaigns on startup
if db_manager and db_manager.db is not None:
    print("🔄 Checking for interrupted campaigns...")
    resume_interrupted_campaigns()

# ============================================================================
# END SERVER RESTART RECOVERY
# ============================================================================

main_bp = Blueprint('main', __name__)

def check_database():
    """Helper function to check if database is available"""
    if not db_manager or db_manager.db is None:
        return False, jsonify({'error': 'Database not available'}), 503
    return True, None, None

def validate_email(email):
    """Validate email address format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@main_bp.route('/')
def index():
    # Redirect to Next.js frontend if BASE_URL is set, otherwise to Flask app
    frontend_url = Config.BASE_URL
    if frontend_url:
        return redirect(frontend_url)
    return redirect('/app')

@main_bp.route('/app')
def main_app():
    """Main application page"""
    user_profile = session.get('user_profile')
    return render_template("frontend.html", user_profile=user_profile)

@main_bp.route('/signin')
def signin():
    """Redirect to OAuth signin"""
    # Set a flag to track OAuth flow
    session['oauth_flow'] = True
    auth_url = get_auth_url()
    return redirect(auth_url)

@main_bp.route('/signin-target')
def signin_target():
    """Redirect to OAuth signin for target users"""
    auth_url = get_auth_url()
    session['user_type'] = 'target'  # Mark this as target user signin
    return redirect(auth_url)

@main_bp.route('/api/verify-session', methods=['GET'])
def verify_session():
    """Verify and establish session after OAuth redirect"""
    try:
        # Check if session exists
        user_profile = session.get('user_profile')
        username = session.get('username')
        
        print(f"Verifying session - user_profile: {bool(user_profile)}, username: {username}")
        
        if user_profile or username:
            return jsonify({
                'success': True,
                'authenticated': True,
                'message': 'Session verified'
            }), 200
        else:
            return jsonify({
                'success': False,
                'authenticated': False,
                'message': 'No active session'
            }), 401
    except Exception as error:
        print(f"Error verifying session: {error}")
        return jsonify({'success': False, 'error': str(error)}), 500

@main_bp.route('/api/exchange-token', methods=['POST', 'OPTIONS'])
def exchange_token():
    """Exchange temporary OAuth token for session"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        response.headers.add('Access-Control-Allow-Origin', Config.FRONTEND_URL)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    print(f"=== Token Exchange Request ===")
    print(f"Method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    print(f"Data: {request.get_data(as_text=True)}")
    
    try:
        data = request.get_json()
        print(f"Parsed JSON data: {data}")
        
        if not data:
            print("ERROR: No data provided")
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        token = data.get('token')
        print(f"Token received: {token[:20] if token else 'None'}...")
        
        if not token:
            return jsonify({'success': False, 'error': 'Token is required'}), 400
        
        # Check if token exists and is not expired
        token_data = OAUTH_TOKENS.get(token)
        if not token_data:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401
        
        # Check expiration
        if token_data['expires_at'] < datetime.now(timezone.utc):
            # Remove expired token
            OAUTH_TOKENS.pop(token, None)
            return jsonify({'success': False, 'error': 'Token expired'}), 401
        
        # Create session from token data
        session['access_token'] = token_data['access_token']
        session['user_profile'] = token_data['user_profile']
        session['user_type'] = token_data['user_type']
        
        # Force session to be saved and make it permanent
        session.permanent = True
        
        # Remove used token
        OAUTH_TOKENS.pop(token, None)
        
        print(f"✓ Session established for user: {token_data['user_profile'].get('displayName', 'Unknown')}")
        print(f"Session keys after creation: {list(session.keys())}")
        print(f"Session ID: {session.get('_id', 'No ID')}")
        
        # Create response with CORS headers
        # Flask will automatically set the session cookie
        response = jsonify({
            'success': True,
            'message': 'Session established',
            'user': {
                'displayName': token_data['user_profile'].get('displayName', 'Unknown'),
                'email': token_data['user_profile'].get('mail') or token_data['user_profile'].get('userPrincipalName', ''),
                'id': token_data['user_profile'].get('id', ''),
                'userType': token_data['user_type']
            }
        })
        
        # CORS headers are handled by the global after_request handler
        # But we can also set them here explicitly
        response.headers.add('Access-Control-Allow-Origin', Config.FRONTEND_URL)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        
        return response, 200
        
        
    except Exception as error:
        print(f"Error exchanging token: {error}")
        return jsonify({'success': False, 'error': str(error)}), 500

@main_bp.route('/callback')
def oauth_callback():
    """Handle OAuth callback and save user data to database"""
    print("OAuth callback received")
    if 'code' not in request.args:
        return redirect(url_for('main.main_app'))
    print("Authorization code received")
    print("Request args:", request.args)

    global ACCESS_TOKEN, USER_PROFILE
    auth_code = request.args.get('code')
    token_response = get_access_token(auth_code)
    print("Exchanging auth code for access token",auth_code)
    print("Access token response received", token_response)
    
    # Check if this is for adding an account or login
    oauth_flow = session.get('oauth_flow', 'login')
    is_adding_account = oauth_flow == 'add_account'
    
    if token_response and 'access_token' in token_response:
        access_token = token_response['access_token']
        refresh_token = token_response.get('refresh_token')  # Get refresh token if available
        print("Access token acquired")
        print("access_token:", access_token)
        print("refresh_token:", "Present" if refresh_token else "Not provided")
        # Get user profile
        user_profile = make_graph_request('/me', access_token)
        print("User profile acquired", user_profile)
        if 'error' not in user_profile:
            user_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
            user_type = session.get('user_type', 'sender')  # Default to sender
            print(f"User email: {user_email}, User type: {user_type}")
            
            if is_adding_account:
                # Adding a new mailbox - Get Clerk user ID from session (stored during OAuth initiation)
                # This was stored in session when /add-account was called
                owner_clerk_id = session.get('clerk_user_id')
                
                if not owner_clerk_id:
                    print("⚠️  ERROR: Clerk user ID is required to add mailbox.")
                    print(f"   Session keys: {list(session.keys())}")
                    print(f"   Session clerk_user_id: {session.get('clerk_user_id')}")
                    print(f"   OAuth flow: {session.get('oauth_flow')}")
                    print(f"   Trying fallback: header or query param")
                    owner_clerk_id = request.headers.get('X-Clerk-User-Id') or request.args.get('clerk_user_id')
                    
                    if not owner_clerk_id:
                        frontend_url = Config.FRONTEND_URL
                        return redirect(f"{frontend_url}/email-accounts?account_added=error&reason=clerk_user_id_required")
                    else:
                        # Store it in session for future use
                        session['clerk_user_id'] = owner_clerk_id
                
                print(f"✅ Found Clerk user ID for adding mailbox: {owner_clerk_id}")
                print(f"   Source: {'session' if session.get('clerk_user_id') else 'header/query'}")
                
                # Get user from database using Clerk ID to get email
                user = db_manager.get_user_by_clerk_id(owner_clerk_id) if db_manager else None
                if user:
                    owner_email = user.get('email') or user.get('login_id')
                    print(f"Found user in database for Clerk ID {owner_clerk_id}: {owner_email}")
                else:
                    # Use the mailbox email as owner email if user not found
                    owner_email = user_email
                    print(f"User not found in database, using mailbox email as owner: {owner_email}")
                
                print(f"📧 Adding new mailbox {user_email} to linkbox_box_table for Clerk user: {owner_clerk_id}")
                print(f"  - Owner email: {owner_email}")
                print(f"  - Access token will be saved to linkbox_box_table: {bool(access_token)}")
                print(f"  - User profile will be saved to linkbox_box_table: {bool(user_profile)}")
                
                # Get user_id from user_information_table using Clerk ID
                user = db_manager.get_user_by_clerk_id(owner_clerk_id) if db_manager else None
                if not user:
                    print(f"⚠️  ERROR: User not found in database for Clerk ID: {owner_clerk_id}")
                    frontend_url = Config.FRONTEND_URL
                    return redirect(f"{frontend_url}/email-accounts?account_added=error&reason=user_not_found")
                
                user_id = user.get('user_id')
                print(f"  - User ID from database: {user_id}")
                
                # Save mailbox to linkbox_box_table (mailboxes_collection) with ALL information
                # CRITICAL: All mailbox data is stored in linkbox_box_table, NOT in session
                # NO session data is saved or used for mailboxes
                from bson import ObjectId
                
                print(f"  - Refresh token will be saved: {'Yes' if refresh_token else 'No'}")
                
                # Create mailbox with refresh_token included
                mailbox_result = db_manager.create_mailbox(
                    user_id=user_id,
                    email=user_email,
                    access_token=access_token,  # Saved to linkbox_box_table
                    password=None,  # OAuth doesn't need password
                    provider='outlook',
                    user_profile=user_profile,  # Saved to linkbox_box_table
                    is_primary=False,  # Will be set if this is first mailbox
                    refresh_token=refresh_token  # Save refresh token for future token refresh
                )
                
                if mailbox_result.get('success'):
                    print(f"✅ Mailbox saved to linkbox_box_table: {mailbox_result.get('mailbox_id')}")
                    print(f"  - Access token: Saved to linkbox_box_table ONLY (NOT in session)")
                    print(f"  - User profile: Saved to linkbox_box_table ONLY (NOT in session)")
                    print(f"  - User ID: {user_id}")
                    print(f"  - All mailbox data is in linkbox_box_table, will be fetched from database only")
                    
                    # Redirect back to email-accounts page
                    # Frontend will fetch mailboxes from linkbox_box_table using Clerk user ID
                    # NO session data is used for mailbox operations
                    frontend_url = Config.FRONTEND_URL
                    session.pop('oauth_flow', None)
                    return redirect(f"{frontend_url}/email-accounts?account_added=success&clerk_user_id={owner_clerk_id}")
                else:
                    print(f"❌ Failed to save mailbox to linkbox_box_table: {mailbox_result.get('error')}")
                    frontend_url = Config.FRONTEND_URL
                    return redirect(f"{frontend_url}/email-accounts?account_added=error")
            else:
                # Login flow - MUST have Clerk user ID (NO SESSION FALLBACK)
                # Get Clerk user ID from request header or query parameter
                clerk_user_id = request.headers.get('X-Clerk-User-Id') or request.args.get('clerk_user_id')
                
                if not clerk_user_id:
                    print("⚠️  ERROR: Clerk user ID is required for login flow. No session fallback.")
                    frontend_url = Config.FRONTEND_URL
                    return redirect(f"{frontend_url}/?auth=error&reason=clerk_user_id_required")
                
                # Get user_id from user_information_table using Clerk ID
                user = db_manager.get_user_by_clerk_id(clerk_user_id) if db_manager else None
                if not user:
                    print(f"⚠️  ERROR: User not found in database for Clerk ID: {clerk_user_id}")
                    frontend_url = Config.FRONTEND_URL
                    return redirect(f"{frontend_url}/?auth=error&reason=user_not_found")
                
                user_id = user.get('user_id')
                print(f"📧 Login flow - Adding mailbox to linkbox_box_table for Clerk user: {clerk_user_id}")
                print(f"  - User ID from database: {user_id}")
                print(f"  - Mailbox email: {user_email}")
                
                # Check if mailbox already exists in linkbox_box_table for this user
                from bson import ObjectId
                existing_mailbox = db_manager.mailboxes_collection.find_one({
                    'user_id': ObjectId(user_id),
                    'email': user_email,
                    'is_active': True
                })
                
                if not existing_mailbox:
                    # Add mailbox to linkbox_box_table automatically
                    mailbox_result = db_manager.create_mailbox(
                        user_id=user_id,
                        email=user_email,
                        access_token=access_token,  # Saved to linkbox_box_table
                        password=None,
                        provider='outlook',
                        user_profile=user_profile,  # Saved to linkbox_box_table
                        is_primary=False,
                        refresh_token=refresh_token  # Save refresh token for future token refresh
                    )
                    if mailbox_result.get('success'):
                        print(f"✅ Automatically added mailbox to linkbox_box_table: {mailbox_result.get('mailbox_id')}")
                    else:
                        print(f"⚠️  Failed to add mailbox to linkbox_box_table: {mailbox_result.get('error')}")
                else:
                    # Update existing mailbox with new access token and refresh token
                    update_data = {
                        'access_token': access_token,
                        'user_profile': user_profile,
                        'updated_at': datetime.now(timezone.utc),
                        'last_used': datetime.now(timezone.utc)
                    }
                    # Update refresh_token if provided
                    if refresh_token:
                        update_data['refresh_token'] = refresh_token
                    
                    db_manager.mailboxes_collection.update_one(
                        {'_id': existing_mailbox['_id']},
                        {'$set': update_data}
                    )
                    print(f"✅ Updated existing mailbox in linkbox_box_table: {existing_mailbox['_id']}")
                    if refresh_token:
                        print(f"   ✅ Refresh token also updated")
                
                success = True
                
                if success:
                    # IMPORTANT: Mailbox information is saved to database, NOT to session
                    # All mailbox data (access_token, user_profile) is in database
                    print(f"Mailbox saved to database for: {user_email} as {user_type}")
                    print("⚠️  CRITICAL: Mailbox information is stored in database ONLY, NOT in session")
                    print("   - Access token: In database ONLY")
                    print("   - User profile: In database ONLY")
                    print("   - All mailbox operations will fetch from database")
                    
                    # For login flow, we save minimal session data for OAuth compatibility
                    # But mailbox access tokens are NEVER in session - ONLY in database
                    session['user_profile'] = user_profile  # Only for display purposes, NOT for mailbox operations
                    session['user_type'] = user_type
                    # DO NOT save access_token to session - it's ONLY in database
                    # DO NOT save mailbox info to session - it's ONLY in database
                    # All mailbox fetching will use database with Clerk user ID
                    
                    print(f"User signed in: {user_profile.get('displayName', 'Unknown')} "
                          f"({user_email}) as {user_type}")
                    
                    # Generate a temporary token for frontend to exchange for session
                    temp_token = str(uuid.uuid4())
                    from datetime import timedelta
                    OAUTH_TOKENS[temp_token] = {
                        'user_profile': user_profile,
                        'access_token': access_token,  # Temporary - mailbox tokens are in DB
                        'user_type': user_type,
                        'expires_at': datetime.now(timezone.utc) + timedelta(minutes=5)
                    }
                    print(f"Generated temporary token: {temp_token[:8]}...")
                    
                    # Clear the user_type from session after use
                    session.pop('user_type', None)
                    session.pop('oauth_flow', None)
                    print("Redirecting to frontend with success")
                    # Redirect to Next.js frontend with temporary token
                    frontend_url = Config.FRONTEND_URL
                    return redirect(f"{frontend_url}/?auth=success&token={temp_token}")
                else:
                    print(f"Error saving user data for {user_email}")
                    frontend_url = Config.FRONTEND_URL
                    return redirect(f"{frontend_url}/?auth=error")
        else:
            print(f"Error getting user profile: {user_profile['error']}")
            frontend_url = Config.FRONTEND_URL
            if is_adding_account:
                return redirect(f"{frontend_url}/email-accounts?account_added=error")
            return redirect(f"{frontend_url}/?auth=error")
    else:
        print(f"Token acquisition error: {token_response}")
        frontend_url = Config.FRONTEND_URL
        if is_adding_account:
            return redirect(f"{frontend_url}/email-accounts?account_added=error")
        return redirect(f"{frontend_url}/?auth=error")

@main_bp.route('/get-user-profile')
def get_user_profile():
    """Get current user profile"""
    try:
        # Debug: Print session info
        print(f"Session keys: {list(session.keys())}")
        print(f"Session username: {session.get('username')}")
        print(f"Session user_profile: {bool(session.get('user_profile'))}")
        
        # Check for username/password auth first
        username = session.get('username')
        if username:
            user = db_manager.get_user_by_username(username)
            if user:
                return jsonify({
                    'displayName': user.get('display_name', user.get('username', 'Unknown')),
                    'email': user.get('email', 'Unknown'),
                    'id': user.get('id', ''),
                    'username': user.get('username', ''),
                    'jobTitle': user.get('jobTitle', ''),
                    'officeLocation': user.get('officeLocation', ''),
                    'userType': 'sender'
                })
        
        # Fallback to OAuth user profile
        user_profile = session.get('user_profile')
        if not user_profile:
            print("No user_profile in session, returning 401")
            return jsonify({'error': 'User not authenticated'}), 401
        
        return jsonify({
            'displayName': user_profile.get('displayName', 'Unknown'),
            'email': user_profile.get('mail') or user_profile.get('userPrincipalName', 'Unknown'),
            'id': user_profile.get('id', ''),
            'jobTitle': user_profile.get('jobTitle', ''),
            'officeLocation': user_profile.get('officeLocation', ''),
            'userType': session.get('user_type', 'sender')
        })
    except Exception as error:
        print(f"Error getting user profile: {error}")
        return jsonify({'error': 'Error fetching user profile'}), 500

@main_bp.route('/api/register', methods=['POST'])
def register():
    """Register a new user with username and password"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        display_name = data.get('display_name', '').strip()
        
        # Validation
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        if not password or len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400
        
        if not email or not validate_email(email):
            return jsonify({'success': False, 'error': 'Valid email is required'}), 400
        
        # Register user
        result = db_manager.register_user(username, password, email, display_name)
        
        if result.get('success'):
            # Set session
            user = result['user']
            session['username'] = user['username']
            session['user_id'] = user['id']
            session['user_profile'] = {
                'displayName': user.get('display_name', user['username']),
                'email': user['email'],
                'id': user['id']
            }
            
            return jsonify({
                'success': True,
                'message': 'User registered successfully',
                'user': user
            }), 201
        else:
            return jsonify(result), 400
            
    except Exception as error:
        print(f"Error registering user: {error}")
        return jsonify({'success': False, 'error': str(error)}), 500

@main_bp.route('/api/login', methods=['POST'])
def login():
    """Login user with username and password"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        # Validation
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        if not password:
            return jsonify({'success': False, 'error': 'Password is required'}), 400
        
        # Authenticate user
        result = db_manager.authenticate_user(username, password)
        
        if result.get('success'):
            # Set session
            user = result['user']
            session['username'] = user['username']
            session['user_id'] = user['id']
            session['user_profile'] = {
                'displayName': user.get('display_name', user['username']),
                'email': user['email'],
                'id': user['id']
            }
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': user
            }), 200
        else:
            return jsonify(result), 401
            
    except Exception as error:
        print(f"Error logging in user: {error}")
        return jsonify({'success': False, 'error': str(error)}), 500

@main_bp.route('/get-registered-users')
def get_registered_users():
    """Get all registered users from database"""
    try:

        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        user_profile = session.get('user_profile')
        if not user_profile:
            if USER_PROFILE:
                user_profile = USER_PROFILE
            else:
                return jsonify({'error': 'User profile not found'}), 400
        
        # sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
        # senders = db_manager.get_all_active_users('sender')
        targets = db_manager.get_all_active_users('target', user_profile.get('mail', user_profile.get('userPrincipalName', '')))
        
        sender_list = []
        
        sender_list.append({
                'email': user_profile.get('mail', user_profile.get('userPrincipalName', '')),
                'displayName': user_profile.get('displayName', 'Unknown'),
                'lastUsed': user_profile.get('last_used', '').isoformat() if user_profile.get('last_used') else '',
                'userType': 'sender'
            })
        
        target_list = []
        for target in targets:
            target_list.append({
                'email': target['email'],
                'displayName': target['user_profile'].get('displayName', 'Unknown'),
                'lastUsed': target.get('last_used', '').isoformat() if target.get('last_used') else '',
                'userType': 'target'
            })
        
        return jsonify({
            'senders': sender_list,
            'targets': target_list,
            'total_senders': len(sender_list),
            'total_targets': len(target_list)
        })
    except Exception as error:
        print(f"Error getting registered users: {error}")
        return jsonify({'error': 'Error fetching registered users'}), 500

@main_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('main.main_app'))

@main_bp.route('/start-warmup', methods=['POST'])
def start_warmup():
    """Start email warmup campaign with registered users"""
    try:
        data = request.get_json()
        
        # Get campaign parameters
        # sender_emails = data.get('sender_emails', [])
        # target_emails = data.get('target_emails', [])
        delay_between_emails = data.get('delay_between_emails', Config.MIN_DELAY_BETWEEN_EMAILS)
        delete_after_minutes = data.get('delete_after_minutes',1)
        cleanup_recipient_mailbox = data.get('cleanup_recipient_mailbox', True)
        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        user_profile = session.get('user_profile')
        if not user_profile:
            if USER_PROFILE:
                user_profile = USER_PROFILE
            else:
                return jsonify({'error': 'User profile not found'}), 400
        
        # sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
        # senders = db_manager.get_all_active_users('sender')
        targets = db_manager.get_all_active_users('target', user_profile.get('mail', user_profile.get('userPrincipalName', '')))
        print(f"Targets: {targets}")
        sender_list = []
        
        sender_list.append({
                'email': user_profile.get('mail', user_profile.get('userPrincipalName', '')),
                'displayName': user_profile.get('displayName', 'Unknown'),
                'lastUsed': user_profile.get('last_used', '').isoformat() if user_profile.get('last_used') else '',
                'userType': 'sender'
            })
        print(f"Sender List: {sender_list}")
        # return jsonify({'message': 'Sender list created successfully', 'senders': sender_list}), 200
        target_list = []
        for target in targets:
            target_list.append({
                'email': target['email'],
                'displayName': target['user_profile'].get('displayName', 'Unknown'),
                'lastUsed': target.get('last_used', '').isoformat() if target.get('last_used') else '',
                'userType': 'target'
            })
        print(f"Target List: {target_list}")
        # return jsonify({'message': 'Target list created successfully', 'targets': target_list}), 200
        # valid_senders = [email for email in sender_list if validate_email(email)]
        # valid_targets = [email for email in target_list if validate_email(email)]
        # print("1")
        # if not valid_senders:
        #     return jsonify({'error': 'No valid sender email addresses found'}), 400
        # print("2")
        # if not valid_targets:
        #     return jsonify({'error': 'No valid target email addresses found'}), 400
        
        # Verify all emails exist in database
        missing_senders = []
        missing_targets = []
        
        print("3")
        for email in sender_list:
            print(f"Checking sender email: {email}")
            if not db_manager.get_user_tokens(email['email']):
                missing_senders.append(email)
        print("4",missing_senders)
        for email in target_list:
            print(f"Checking target email: {email}")
            if not db_manager.get_user_tokens(email['email']):
                missing_targets.append(email)
        print("5",missing_targets)

        if missing_senders:
            print(f"Missing senders: {missing_senders}")
            return jsonify({
                'error': f'Sender emails not registered: {", ".join(missing_senders)}'
            }), 400
        
        print("6")
        if missing_targets:
            print(f"Missing targets: {missing_targets}")
            return jsonify({
                'error': f'Target emails not registered: {", ".join(missing_targets)}'
            }), 400
        
        print(f"Starting warmup campaign:")
        # print(f"Senders: {valid_senders}")
        # print(f"Targets: {valid_targets}")
        
        # Run comprehensive warmup campaign
        results = warmup_service.run_comprehensive_warmup_campaign(
            sender_emails=sender_list,
            target_emails=target_list,
            delay_between_emails=delay_between_emails,
            delete_after_minutes=delete_after_minutes,
            cleanup_recipient_mailbox=cleanup_recipient_mailbox
        )
        
        print(f"Warmup campaign results: {results}")
        return jsonify({
            'success': True,
            'message': 'Comprehensive warm-up campaign completed',
            'results': {
                'total_combinations': results['total_combinations'],
                'emails_sent': results['emails_sent'],
                'send_failures': results['send_failures'],
                'sender_deletions': results['sender_deletions'],
                'recipient_deletions': results['recipient_deletions'],
                'delete_failures': results['delete_failures'],
                'total_duration': f"{results['total_duration']:.2f} seconds",
                'campaign_start': results['start_time'].isoformat(),
                'campaign_end': results['end_time'].isoformat()
            }
        })
        
    except Exception as error:
        print(f"Error in warm-up campaign: {error}")
        return jsonify({'error': f'Error running warm-up campaign: {str(error)}'}), 500

# @main_bp.route('/start-background-warmup', methods=['POST'])
# def start_background_warmup():
#     """Start or restart background warmup process"""
#     try:
#         # Check if there are registered users
       
#         access_token = session.get('access_token')
#         if not access_token:
#             if ACCESS_TOKEN:
#                 access_token = ACCESS_TOKEN
#             else:
#                 return jsonify({'error': 'User not authenticated'}), 401
        
#         user_profile = session.get('user_profile')
#         if not user_profile:
#             if USER_PROFILE:
#                 user_profile = USER_PROFILE
#             else:
#                 return jsonify({'error': 'User profile not found'}), 400
        
#         # sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
#         # senders = db_manager.get_all_active_users('sender')
#         targets = db_manager.get_all_active_users('target', user_profile.get('mail', user_profile.get('userPrincipalName', '')))
        
#         sender_list = []
        
#         sender_list.append({
#                 'email': user_profile.get('mail', user_profile.get('userPrincipalName', '')),
#                 'displayName': user_profile.get('displayName', 'Unknown'),
#                 'lastUsed': user_profile.get('last_used', '').isoformat() if user_profile.get('last_used') else '',
#                 'userType': 'sender'
#             })
        
#         target_list = []
#         for target in targets:
#             target_list.append({
#                 'email': target['email'],
#                 'displayName': target['user_profile'].get('displayName', 'Unknown'),
#                 'lastUsed': target.get('last_used', '').isoformat() if target.get('last_used') else '',
#                 'userType': 'target'
#             })
        
#         if not sender_list:
#             return jsonify({'error': 'No registered sender emails found'}), 400
        
#         if not target_list:
#             return jsonify({'error': 'No registered target emails found'}), 400
        
#         # Restart background service
#         background_service.stop()
#         background_service.start()
        
#         return jsonify({
#             'success': True,
#             'message': 'Background warmup process started',
#             'senders_count': len(sender_list),
#             'targets_count': len(target_list)
#         })
        
#     except Exception as error:
#         print(f"Error starting background warmup: {error}")
#         return jsonify({'error': f'Error starting background warmup: {str(error)}'}), 500

# @main_bp.route('/stop-background-warmup', methods=['POST'])
# def stop_background_warmup():
#     """Stop background warmup process"""
#     try:
#         background_service.stop()
#         return jsonify({
#             'success': True,
#             'message': 'Background warmup process stopped'
#         })
#     except Exception as error:
#         print(f"Error stopping background warmup: {error}")
#         return jsonify({'error': f'Error stopping background warmup: {str(error)}'}), 500

@main_bp.route('/get-campaign-logs')
def get_campaign_logs():
    """Get recent campaign logs"""
    try:
        db_ok, error_response, status_code = check_database()
        if not db_ok:
            return error_response, status_code
        
        campaign_logs = db_manager.db['warmup_campaign_logs']
        logs = list(campaign_logs.find().sort('created_at', -1).limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for log in logs:
            log['_id'] = str(log['_id'])
            if 'start_time' in log:
                log['start_time'] = log['start_time'].isoformat()
            if 'end_time' in log:
                log['end_time'] = log['end_time'].isoformat()
            if 'created_at' in log:
                log['created_at'] = log['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as error:
        print(f"Error getting campaign logs: {error}")
        return jsonify({'error': f'Error fetching campaign logs: {str(error)}'}), 500

@main_bp.route('/send-mail', methods=['POST'])
def api_send_mail():
    """Send email with tracking support - uses primary or selected mailbox"""
    try:
        # Get Clerk user ID from request header
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        
        # Get mailbox_id from request (optional)
        mailbox_id = None
        if request.is_json:
            mailbox_id = request.json.get('mailbox_id')
        elif request.form:
            mailbox_id = request.form.get('mailbox_id')
        
        # Determine which mailbox to use
        mailbox = None
        access_token = None
        sender_email = None
        
        if mailbox_id:
            # Use specified mailbox
            from bson import ObjectId
            try:
                if not db_manager or db_manager.mailboxes_collection is None:
                    return jsonify({'error': 'Database not available'}), 503
                
                # Get mailbox from linkbox_box_table
                mailbox = db_manager.mailboxes_collection.find_one({
                    '_id': ObjectId(mailbox_id),
                    'is_active': True
                })
                
                # Verify ownership if Clerk user ID is provided
                if clerk_user_id and mailbox:
                    # Get user_id from user_information_table using Clerk ID
                    user = db_manager.get_user_by_clerk_id(clerk_user_id) if db_manager else None
                    if user:
                        from bson import ObjectId
                        user_id = ObjectId(user.get('user_id'))
                        # Verify mailbox belongs to this user
                        if mailbox.get('user_id') != user_id:
                            return jsonify({'error': 'Mailbox not found or access denied'}), 403
                elif not mailbox.get('owner_email'):
                    # Fallback: check by email if no clerk_id
                    pass
                    
            except Exception as e:
                print(f"Error finding mailbox by ID: {e}")
                mailbox = None
        
        # ONLY use mailboxes from database - NO SESSION FALLBACKS
        if not mailbox and clerk_user_id:
            # Use primary mailbox for this Clerk user from linkbox_box_table
            if db_manager is not None and db_manager.mailboxes_collection is not None:
                # Get user_id from user_information_table using Clerk ID
                user = db_manager.get_user_by_clerk_id(clerk_user_id) if db_manager else None
                if user:
                    from bson import ObjectId
                    user_id = ObjectId(user.get('user_id'))
                    # Get primary mailbox from linkbox_box_table
                    mailbox = db_manager.mailboxes_collection.find_one({
                        'user_id': user_id,
                        'is_primary': True,
                        'is_active': True
                    })
                    if mailbox:
                        print(f"Found primary mailbox from linkbox_box_table for Clerk user {clerk_user_id}: {mailbox['email']}")
                    else:
                        print(f"No primary mailbox found in linkbox_box_table for Clerk user {clerk_user_id}")
        
        if mailbox:
            # Use mailbox credentials from database
            access_token = mailbox.get('access_token')
            sender_email = mailbox['email']
            print(f"Using mailbox from database: {sender_email} (has access_token: {bool(access_token)})")
            
            if not access_token:
                return jsonify({'error': 'Mailbox access token not found in database. Please re-link the mailbox.'}), 400
        else:
            # NO SESSION FALLBACK - only use database
            if not clerk_user_id:
                return jsonify({'error': 'Clerk user ID is required. Please ensure X-Clerk-User-Id header is sent.'}), 400
            else:
                return jsonify({'error': 'No mailbox found in database for this user. Please link a mailbox first.'}), 404
        
        # Check if request has file (FormData) or JSON
        if request.files:
            # Handle file upload
            file = request.files.get('recipients_file')
            subject = request.form.get('subject', '')
            message = request.form.get('message', '')
            
            if not file:
                return jsonify({'error': 'No file provided'}), 400
            
            # Parse recipients from file
            recipients = []
            file_extension = file.filename.split('.')[-1].lower()
            
            try:
                if file_extension == 'txt':
                    text = file.read().decode('utf-8')
                    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
                    recipients = [{'name': email.split('@')[0], 'email': email} for email in emails]
                elif file_extension == 'csv':
                    df = pd.read_csv(file)
                    # Try to find email column
                    email_col = None
                    name_col = None
                    for col in df.columns:
                        if 'email' in col.lower():
                            email_col = col
                        if 'name' in col.lower():
                            name_col = col
                    
                    if email_col:
                        for _, row in df.iterrows():
                            email = str(row[email_col]).strip()
                            if validate_email(email):
                                name = str(row[name_col]).strip() if name_col and name_col in row else email.split('@')[0]
                                recipients.append({'name': name, 'email': email})
                elif file_extension in ['xlsx', 'xls']:
                    df = pd.read_excel(file)
                    # Try to find email column
                    email_col = None
                    name_col = None
                    for col in df.columns:
                        if 'email' in col.lower():
                            email_col = col
                        if 'name' in col.lower():
                            name_col = col
                    
                    if email_col:
                        for _, row in df.iterrows():
                            email = str(row[email_col]).strip()
                            if validate_email(email):
                                name = str(row[name_col]).strip() if name_col and name_col in row else email.split('@')[0]
                                recipients.append({'name': name, 'email': email})
                else:
                    return jsonify({'error': 'Unsupported file format'}), 400
            except Exception as e:
                return jsonify({'error': f'Error parsing file: {str(e)}'}), 400
        else:
            # Handle JSON request
            try:
                data = request.get_json()
                if not data:
                    return jsonify({'error': 'No data provided'}), 400
                
                recipients = data.get('recipients', [])
                subject = data.get('subject', '')
                message = data.get('message', '')
                start_time = data.get('start_time')  # ISO datetime string
                duration = data.get('duration', 24)  # Total duration in hours
                send_interval = data.get('send_interval', 5)  # Minutes between each email
                
                # Validate data types
                if not isinstance(recipients, list):
                    return jsonify({'error': 'Recipients must be a list'}), 400
                if not isinstance(subject, str):
                    return jsonify({'error': 'Subject must be a string'}), 400
                if not isinstance(message, str):
                    return jsonify({'error': 'Message must be a string'}), 400
                if duration and not isinstance(duration, (int, float)):
                    return jsonify({'error': 'Duration must be a number'}), 400
                if send_interval and not isinstance(send_interval, (int, float)):
                    return jsonify({'error': 'Send interval must be a number'}), 400
                    
            except Exception as parse_error:
                print(f"❌ Error parsing request data: {parse_error}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': f'Error parsing request: {str(parse_error)}'}), 400
        
        if not subject:
            return jsonify({'error': 'Subject is required'}), 400
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        if not recipients:
            return jsonify({'error': 'At least one recipient is required'}), 400
        
        # Validate recipients
        valid_recipients = []
        invalid_recipients = []
        unsubscribed_recipients = []
        
        # Check if database is available
        db_ok, error_response, status_code = check_database()
        if not db_ok:
            return error_response, status_code
        
        campaigns_collection = db_manager.db['email_campaigns']
        tracking_collection = db_manager.db['email_tracking']
        
        # Check for active campaigns for this user/mailbox (after campaigns_collection is defined)
        now = datetime.now(timezone.utc)
        active_campaigns = []
        if clerk_user_id:
            # Find active campaigns for this user
            user_campaigns = list(campaigns_collection.find({
                'clerk_user_id': clerk_user_id,
                'status': {'$in': ['active', 'scheduled']}
            }))
            
            for existing_campaign in user_campaigns:
                # Check if campaign is actually active based on start_time and duration
                existing_start = existing_campaign.get('start_time')
                existing_duration = existing_campaign.get('duration', 24)
                
                if existing_start:
                    if isinstance(existing_start, str):
                        try:
                            existing_start = datetime.fromisoformat(existing_start.replace('Z', '+00:00'))
                        except:
                            continue
                    elif not isinstance(existing_start, datetime):
                        continue
                    
                    # Ensure timezone-aware
                    if existing_start.tzinfo is None:
                        existing_start = existing_start.replace(tzinfo=timezone.utc)
                    else:
                        existing_start = existing_start.astimezone(timezone.utc)
                    
                    from datetime import timedelta
                    existing_end = existing_start + timedelta(hours=existing_duration)
                    
                    # Ensure end_time is timezone-aware
                    if existing_end.tzinfo is None:
                        existing_end = existing_end.replace(tzinfo=timezone.utc)
                    
                    # Campaign is active if current time is between start and end
                    try:
                        if now >= existing_start and now <= existing_end:
                            active_campaigns.append({
                                'campaign_id': existing_campaign.get('campaign_id'),
                                'subject': existing_campaign.get('subject', 'No Subject'),
                                'start_time': existing_start.isoformat() if isinstance(existing_start, datetime) else str(existing_start),
                                'end_time': existing_end.isoformat()
                            })
                    except TypeError as e:
                        print(f"⚠️  Warning: Could not compare datetimes for campaign {existing_campaign.get('campaign_id')}: {e}")
                        continue
        
        # Check for unsubscribed emails
        unsubscribed_emails = set()
        unsubscribed_docs = tracking_collection.find({'unsubscribed': True})
        for doc in unsubscribed_docs:
            unsubscribed_emails.add(doc.get('recipient_email', '').lower())
        
        for recipient in recipients:
            email = recipient.get('email', '').strip()
            if not validate_email(email):
                invalid_recipients.append(email)
                continue
            
            if email.lower() in unsubscribed_emails:
                unsubscribed_recipients.append(recipient)
                continue
            
            valid_recipients.append(recipient)
        
        if not valid_recipients:
            return jsonify({
                'error': 'No valid recipients',
                'invalid_recipients': invalid_recipients,
                'unsubscribed_recipients': unsubscribed_recipients
            }), 400
        
        # Create campaign with user identification
        campaign_id = str(uuid.uuid4())
        user_email = sender_email  # Use sender_email as user identifier (for backward compatibility)
        
        # Parse start_time if provided
        start_datetime = None
        if start_time:
            try:
                start_datetime = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                start_datetime = datetime.now(timezone.utc)
        else:
            start_datetime = datetime.now(timezone.utc)
        
        # Ensure start_datetime is timezone-aware (UTC)
        if start_datetime.tzinfo is None:
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        else:
            start_datetime = start_datetime.astimezone(timezone.utc)
        
        # Get current time for comparison
        now_utc = datetime.now(timezone.utc)
        
        campaign_data = {
            'campaign_id': campaign_id,
            'clerk_user_id': clerk_user_id,  # Store Clerk user ID
            'user_email': user_email,  # User identifier (backward compatibility)
            'sender_email': sender_email,
            'mailbox_id': str(mailbox['_id']) if mailbox else None,  # Store which mailbox was used
            'subject': subject,
            'message': message,
            'start_time': start_datetime,  # Campaign start time
            'duration': duration,  # Total duration in hours
            'send_interval': send_interval,  # Minutes between each email
            'total_recipients': len(valid_recipients),
            'sent_count': 0,
            'failed_count': 0,
            'bounce_count': 0,
            'status': 'scheduled' if start_datetime > now_utc else 'active',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        try:
            campaigns_collection.insert_one(campaign_data)
            print(f"✅ Campaign created: {campaign_id} for user {clerk_user_id}")
        except Exception as insert_error:
            print(f"❌ Error inserting campaign: {insert_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to create campaign: {str(insert_error)}'}), 500
        
        # Start background email sending thread
        # This allows the endpoint to return immediately while emails are sent in the background
        background_thread = threading.Thread(
            target=send_emails_in_background,
            args=(
                campaign_id,
                str(mailbox['_id']) if mailbox else None,
                sender_email,
                subject,
                message,
                valid_recipients,
                start_datetime,
                duration,
                send_interval,
                clerk_user_id
            ),
            daemon=True
        )
        background_thread.start()
        
        print(f"🚀 Campaign {campaign_id} started in background")
        
        # Prepare response
        response_data = {
            'success': True,
            'campaign_id': campaign_id,
            'total_recipients': len(valid_recipients),
            'status': 'scheduled' if start_datetime > now_utc else 'active',
            'message': f'Campaign started! Sending {len(valid_recipients)} emails in the background.',
            'invalid_recipients': invalid_recipients,
            'unsubscribed_count': len(unsubscribed_recipients),
            'unsubscribed_recipients': unsubscribed_recipients,
            'tracking_enabled': True,
            'analytics_url': f"/api/analytics/campaign/{campaign_id}"
        }
        
        # Add active campaigns warning if applicable
        if active_campaigns:
            response_data['warning'] = f'You have {len(active_campaigns)} active campaign(s) running. Multiple campaigns may cause rate limiting.'
            response_data['active_campaigns'] = active_campaigns
            print(f"⚠️  WARNING: User {clerk_user_id} started a new campaign while {len(active_campaigns)} campaign(s) are active")
        
        return jsonify(response_data)
        
    except Exception as error:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ Error sending email: {error}")
        print(f"📋 Full traceback:\n{error_traceback}")
        return jsonify({
            'error': f'Error sending email: {str(error)}',
            'details': str(error) if str(error) else 'Unknown error'
        }), 500

@main_bp.route('/get-mails/<int:count>')
def get_mails(count):
    """Get recent emails from Outlook"""
    try:
        access_token = session.get('access_token')
        
        # If no session token, try to get from database using Clerk ID
        if not access_token:
            clerk_user_id = request.headers.get('X-Clerk-User-Id')
            if clerk_user_id and db_manager:
                user = db_manager.get_user_by_clerk_id(clerk_user_id)
                if user:
                    from bson import ObjectId
                    user_id = user.get('user_id')
                    # Get primary mailbox
                    mailbox = db_manager.mailboxes_collection.find_one({
                        'user_id': ObjectId(user_id),
                        'is_primary': True,
                        'is_active': True
                    })
                    if mailbox:
                        access_token = mailbox.get('access_token')
                        # Optional: Update session to avoid future DB lookups
                        session['access_token'] = access_token
                        session['user_profile'] = mailbox.get('user_profile')
                        session['user_email'] = mailbox.get('email')
                        session['mailbox_id'] = str(mailbox['_id'])
                        print(f"Auto-resolved primary mailbox for get_mails: {mailbox.get('email')}")
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        # Fetch emails from Microsoft Graph API
        endpoint = f'/me/messages?$top={count}&$orderby=receivedDateTime desc'
        response = make_graph_request(endpoint, access_token, 'GET')
        
        if isinstance(response, dict) and 'error' in response:
            return jsonify({'error': response['error']}), 400
        
        if isinstance(response, dict) and 'value' in response:
            return jsonify(response)
        else:
            return jsonify({'value': []})
            
    except Exception as error:
        print(f"Error getting emails: {error}")
        return jsonify({'error': f'Error fetching emails: {str(error)}'}), 500

@main_bp.route('/api/campaign/<campaign_id>')
def get_campaign(campaign_id):
    """Get campaign details by ID"""
    try:
        # Check if database is available
        if not db_manager or db_manager.db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        campaigns_collection = db_manager.db['email_campaigns']
        tracking_collection = db_manager.db['email_tracking']
        
        campaign = campaigns_collection.find_one({'campaign_id': campaign_id})
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get tracking data for this campaign
        tracking_docs = list(tracking_collection.find({'campaign_id': campaign_id}))
        
        # Calculate statistics
        # Distinguish between bounces and application errors
        total_tracking = len(tracking_docs)
        bounce_count = sum(1 for doc in tracking_docs if doc.get('bounced', False) == True)
        application_error_count = sum(1 for doc in tracking_docs if doc.get('application_error', False) == True)
        
        # Successfully sent = delivered to email server
        successfully_sent_docs = [
            doc for doc in tracking_docs 
            if doc.get('delivered', False) == True or 
               (not doc.get('bounced', False) and not doc.get('application_error', False))
        ]
        total_sent = len(successfully_sent_docs)
        
        unique_opens = sum(1 for doc in successfully_sent_docs if doc.get('opens', 0) > 0)
        unique_clicks = sum(1 for doc in successfully_sent_docs if doc.get('clicks', 0) > 0)
        total_recipients = campaign.get('total_recipients', 0)
        
        # Not delivered = application errors + emails never attempted
        not_delivered_count = application_error_count + max(0, total_recipients - total_tracking)
        
        open_rate = (unique_opens / total_sent * 100) if total_sent > 0 else 0
        bounce_rate = (bounce_count / total_tracking * 100) if total_tracking > 0 else 0
        
        # Convert to JSON-serializable format
        campaign['_id'] = str(campaign['_id'])
        if 'created_at' in campaign and campaign['created_at']:
            campaign['created_at'] = campaign['created_at'].isoformat()
        if 'updated_at' in campaign and campaign['updated_at']:
            campaign['updated_at'] = campaign['updated_at'].isoformat()
        if 'start_time' in campaign and campaign['start_time']:
            if isinstance(campaign['start_time'], str):
                campaign['start_time'] = campaign['start_time']
            else:
                campaign['start_time'] = campaign['start_time'].isoformat()
        
        # Add calculated fields
        campaign['successfully_sent'] = total_sent
        campaign['bounced'] = bounce_count
        campaign['opened'] = unique_opens
        campaign['clicked'] = unique_clicks
        campaign['open_rate'] = round(open_rate, 2)
        campaign['bounce_rate'] = round(bounce_rate, 2)
        campaign['not_delivered_count'] = not_delivered_count
        campaign['application_error_count'] = application_error_count
        campaign['total_mails'] = total_tracking
        
        tracking_data = []
        for doc in tracking_docs:
            doc_copy = dict(doc)
            doc_copy['_id'] = str(doc['_id'])
            if 'sent_at' in doc and doc['sent_at']:
                doc_copy['sent_at'] = doc['sent_at'].isoformat() if hasattr(doc['sent_at'], 'isoformat') else doc['sent_at']
            if 'first_open' in doc and doc['first_open']:
                doc_copy['first_open'] = doc['first_open'].isoformat() if hasattr(doc['first_open'], 'isoformat') else doc['first_open']
            if 'first_click' in doc and doc['first_click']:
                doc_copy['first_click'] = doc['first_click'].isoformat() if hasattr(doc['first_click'], 'isoformat') else doc['first_click']
            if 'bounce_date' in doc and doc['bounce_date']:
                doc_copy['bounce_date'] = doc['bounce_date'].isoformat() if hasattr(doc['bounce_date'], 'isoformat') else doc['bounce_date']
            tracking_data.append(doc_copy)
        
        campaign['tracking_data'] = tracking_data
        
        return jsonify(campaign)
        
    except Exception as error:
        print(f"Error getting campaign: {error}")
        return jsonify({'error': f'Error fetching campaign: {str(error)}'}), 500

@main_bp.route('/api/campaigns/user')
def get_user_campaigns():
    """Get all campaigns for the current user"""
    try:
        campaigns_collection = db_manager.db['email_campaigns']
        tracking_collection = db_manager.db['email_tracking']
        
        # Check for Clerk user ID first (new method)
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        
        if clerk_user_id:
            print(f"Fetching campaigns for Clerk user: {clerk_user_id}")
            # Get all campaigns for this Clerk user
            campaigns = list(campaigns_collection.find({'clerk_user_id': clerk_user_id}).sort('created_at', -1))
        else:
            # NO SESSION FALLBACK - Clerk user ID is required
            print("⚠️  ERROR: Clerk user ID is required. No session fallback.")
            return jsonify({
                'error': 'Clerk user ID is required. Please ensure X-Clerk-User-Id header is sent. This endpoint uses database only, not session.',
                'campaigns': []
            }), 400
        
        # Get analytics for each campaign
        campaign_list = []
        for campaign in campaigns:
            campaign_id = campaign.get('campaign_id')
            
            # Get tracking data for this campaign
            tracking_docs = list(tracking_collection.find({'campaign_id': campaign_id}))
            
            # Calculate quick stats
            total_tracking = len(tracking_docs)
            bounce_count = sum(1 for doc in tracking_docs if doc.get('bounced', False))
            total_sent = total_tracking - bounce_count
            unique_opens = sum(1 for doc in tracking_docs if not doc.get('bounced', False) and doc.get('opens', 0) > 0)
            unique_clicks = sum(1 for doc in tracking_docs if not doc.get('bounced', False) and doc.get('clicks', 0) > 0)
            
            open_rate = (unique_opens / total_sent * 100) if total_sent > 0 else 0
            bounce_rate = (bounce_count / total_tracking * 100) if total_tracking > 0 else 0
            
            # Determine campaign status
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            start_time = campaign.get('start_time')
            duration = campaign.get('duration', 24)
            campaign_status = campaign.get('status', 'unknown')
            
            # Calculate if campaign is actually active based on time
            # IMPORTANT: Stopped campaigns should NEVER be active
            is_active = False
            if campaign_status != 'stopped':  # Only check time if not stopped
                if start_time:
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    end_time = start_time + timedelta(hours=duration)
                    is_active = now >= start_time and now <= end_time
            
            # Update status based on time and current status
            # Don't mark as completed if campaign just started or is scheduled for future
            if campaign_status == 'stopped':
                # Keep stopped status, never change it
                campaign_status = 'stopped'
            elif campaign_status == 'scheduled':
                if now < start_time:
                    # Still scheduled, keep as scheduled
                    campaign_status = 'scheduled'
                elif is_active:
                    # Should be active now
                    campaign_status = 'active'
                else:
                    # Past end time, mark as completed
                    campaign_status = 'completed'
            elif campaign_status == 'active':
                if is_active:
                    # Still active, keep as active
                    campaign_status = 'active'
                else:
                    # Past end time, mark as completed
                    campaign_status = 'completed'
            # For other statuses (failed, completed), keep as is
            
            campaign_info = {
                'campaign_id': campaign_id,
                'subject': campaign.get('subject', 'No Subject'),
                'status': campaign_status,
                'created_at': campaign.get('created_at').isoformat() if campaign.get('created_at') else None,
                'updated_at': campaign.get('updated_at').isoformat() if campaign.get('updated_at') else None,
                'start_time': start_time.isoformat() if start_time else None,
                'duration': duration,
                'send_interval': campaign.get('send_interval', 5),
                'total_recipients': campaign.get('total_recipients', 0),
                'total_mails': total_tracking,
                'successfully_sent': total_sent,
                'bounced': bounce_count,
                'opened': unique_opens,
                'clicked': unique_clicks,
                'open_rate': round(open_rate, 2),
                'bounce_rate': round(bounce_rate, 2),
                'is_active': is_active
            }
            campaign_list.append(campaign_info)
        
        return jsonify({
            'success': True,
            'clerk_user_id': clerk_user_id if clerk_user_id else None,
            'total_campaigns': len(campaign_list),
            'campaigns': campaign_list
        })
        
    except Exception as error:
        print(f"Error getting user campaigns: {error}")
        return jsonify({'error': f'Error fetching campaigns: {str(error)}'}), 500

@main_bp.route('/api/analytics/campaign/<campaign_id>')
def get_campaign_analytics(campaign_id):
    """Get campaign analytics and tracking data"""
    try:
        campaigns_collection = db_manager.db['email_campaigns']
        tracking_collection = db_manager.db['email_tracking']
        
        campaign = campaigns_collection.find_one({'campaign_id': campaign_id})
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get all tracking data for this campaign
        tracking_docs = list(tracking_collection.find({'campaign_id': campaign_id}))
        
        # Calculate statistics
        # Distinguish between:
        # 1. Actual bounces (email server rejected) - bounced = True
        # 2. Application errors (app-side errors) - application_error = True, delivered = False
        # 3. Successfully sent - delivered = True (or not set but no error)
        total_tracking = len(tracking_docs)
        bounce_count = sum(1 for doc in tracking_docs if doc.get('bounced', False) == True)
        application_error_count = sum(1 for doc in tracking_docs if doc.get('application_error', False) == True)
        
        # Successfully sent = delivered to email server (may still bounce later, but reached server)
        # Count emails that were delivered (delivered=True) or successfully sent (no error flags)
        successfully_sent_docs = [
            doc for doc in tracking_docs 
            if doc.get('delivered', False) == True or 
               (not doc.get('bounced', False) and not doc.get('application_error', False))
        ]
        total_sent = len(successfully_sent_docs)
        
        # Calculate engagement metrics only for successfully sent emails
        unique_opens = sum(1 for doc in successfully_sent_docs if doc.get('opens', 0) > 0)
        unique_clicks = sum(1 for doc in successfully_sent_docs if doc.get('clicks', 0) > 0)
        unsubscribe_count = sum(1 for doc in successfully_sent_docs if doc.get('unsubscribed', False))
        reply_count = sum(1 for doc in successfully_sent_docs if doc.get('replies', 0) > 0)
        
        # Calculate rates based on successfully sent emails (not bounced)
        open_rate = (unique_opens / total_sent * 100) if total_sent > 0 else 0
        unsubscribe_rate = (unsubscribe_count / total_sent * 100) if total_sent > 0 else 0
        reply_rate = (reply_count / total_sent * 100) if total_sent > 0 else 0
        bounce_rate = (bounce_count / total_tracking * 100) if total_tracking > 0 else 0
        
        # Calculate not delivered count
        # Includes: application errors + emails never attempted
        total_recipients = campaign.get('total_recipients', 0)
        not_delivered_count = application_error_count + max(0, total_recipients - total_tracking)
        
        print(f"Analytics for campaign {campaign_id}: Total={total_tracking}, Sent={total_sent}, Bounced={bounce_count}, AppErrors={application_error_count}, NotDelivered={not_delivered_count}")
        
        # Format recipients data and collect bounced emails
        recipients = []
        bounced_recipients = []
        for doc in tracking_docs:
            # Ensure bounced is a boolean, not None
            bounced_status = doc.get('bounced', False)
            if bounced_status is None:
                bounced_status = False
            elif isinstance(bounced_status, str):
                bounced_status = bounced_status.lower() in ('true', '1', 'yes')
            
            application_error = doc.get('application_error', False)
            delivered = doc.get('delivered', False)
            
            recipient_data = {
                'tracking_id': doc.get('tracking_id', ''),
                'name': doc.get('recipient_name', ''),
                'email': doc.get('recipient_email', ''),
                'opens': doc.get('opens', 0),
                'clicks': doc.get('clicks', 0),
                'unsubscribed': doc.get('unsubscribed', False),
                'replies': doc.get('replies', 0),
                'bounced': bool(bounced_status),  # Ensure it's a boolean
                'application_error': bool(application_error),  # Application-side error
                'delivered': bool(delivered) if delivered is not None else (not bool(bounced_status) and not bool(application_error)),
                'bounce_reason': doc.get('bounce_reason'),
                'error_reason': doc.get('error_reason'),
                'first_open': doc.get('first_open').isoformat() if doc.get('first_open') else None,
                'first_click': doc.get('first_click').isoformat() if doc.get('first_click') else None,
                'unsubscribe_date': doc.get('unsubscribe_date').isoformat() if doc.get('unsubscribe_date') else None,
                'reply_date': doc.get('reply_date').isoformat() if doc.get('reply_date') else None,
                'bounce_date': doc.get('bounce_date').isoformat() if doc.get('bounce_date') else None,
                'error_date': doc.get('error_date').isoformat() if doc.get('error_date') else None,
                'sent_at': doc.get('sent_at').isoformat() if doc.get('sent_at') else None
            }
            
            # Debug: Log bounced status for each recipient
            if recipient_data['bounced']:
                print(f"DEBUG: Recipient {recipient_data['email']} is marked as bounced: {recipient_data['bounced']}, reason: {recipient_data['bounce_reason']}")
            recipients.append(recipient_data)
            
            # Collect bounced emails
            if doc.get('bounced', False):
                bounced_recipients.append({
                    'email': doc.get('recipient_email', ''),
                    'name': doc.get('recipient_name', ''),
                    'bounce_reason': doc.get('bounce_reason', 'Unknown reason'),
                    'bounce_date': doc.get('bounce_date').isoformat() if doc.get('bounce_date') else None
                })
        
        # Calculate timing information
        from datetime import timedelta
        start_time = campaign.get('start_time')
        duration = campaign.get('duration', 24)  # hours
        send_interval = campaign.get('send_interval', 5)  # minutes
        
        # Calculate end time
        end_time = None
        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            end_time = start_time + timedelta(hours=duration)
        
        # Calculate estimated time per email (send_interval in minutes)
        time_per_email_minutes = send_interval
        
        # Determine if campaign is still active
        now = datetime.now(timezone.utc)
        is_active = False
        if start_time and end_time:
            is_active = now >= start_time and now <= end_time
        
        return jsonify({
            'campaign_id': campaign_id,
            'subject': campaign.get('subject', ''),
            'status': campaign.get('status', 'unknown'),
            'total_mails': total_tracking,  # Total emails attempted (including bounced)
            'total_sent': total_sent,  # Successfully sent (non-bounced)
            'successfully_sent': total_sent,  # Alias for clarity
            'unique_opens': unique_opens,
            'unique_clicks': unique_clicks,
            'open_rate': round(open_rate, 2),
            'unsubscribe_count': unsubscribe_count,
            'unsubscribe_rate': round(unsubscribe_rate, 2),
            'reply_count': reply_count,
            'reply_rate': round(reply_rate, 2),
            'bounce_count': bounce_count,
            'total_bounced': bounce_count,  # Alias for clarity
            'bounce_rate': round(bounce_rate, 2),
            'bounced_recipients': bounced_recipients,
            'recipients': recipients,
            # Timing information
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None,
            'duration': duration,  # Total duration in hours
            'send_interval': send_interval,  # Minutes between each email
            'time_per_email_minutes': time_per_email_minutes,
            'is_active': is_active,
            'total_recipients': campaign.get('total_recipients', 0),
            'not_delivered_count': not_delivered_count,
            'application_error_count': application_error_count
        })
        
    except Exception as error:
        print(f"Error getting campaign analytics: {error}")
        return jsonify({'error': f'Error fetching analytics: {str(error)}'}), 500

@main_bp.route('/api/campaign/<campaign_id>/email/<tracking_id>')
def get_email_analytics(campaign_id, tracking_id):
    """Get detailed analytics for a specific email"""
    try:
        if not db_manager or db_manager.db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        tracking_collection = db_manager.db['email_tracking']
        
        # Get tracking data for this specific email
        tracking_doc = tracking_collection.find_one({
            'campaign_id': campaign_id,
            'tracking_id': tracking_id
        })
        
        if not tracking_doc:
            return jsonify({'error': 'Email tracking not found'}), 404
        
        # Format the response
        email_analytics = {
            'tracking_id': tracking_doc.get('tracking_id', ''),
            'campaign_id': campaign_id,
            'recipient_email': tracking_doc.get('recipient_email', ''),
            'recipient_name': tracking_doc.get('recipient_name', ''),
            'subject': tracking_doc.get('subject', ''),
            'sent_at': tracking_doc.get('sent_at').isoformat() if tracking_doc.get('sent_at') else None,
            'status': 'bounced' if tracking_doc.get('bounced', False) else 'delivered',
            'bounced': tracking_doc.get('bounced', False),
            'bounce_reason': tracking_doc.get('bounce_reason'),
            'bounce_date': tracking_doc.get('bounce_date').isoformat() if tracking_doc.get('bounce_date') else None,
            'opens': tracking_doc.get('opens', 0),
            'clicks': tracking_doc.get('clicks', 0),
            'replies': tracking_doc.get('replies', 0),
            'unsubscribed': tracking_doc.get('unsubscribed', False),
            'first_open': tracking_doc.get('first_open').isoformat() if tracking_doc.get('first_open') else None,
            'first_click': tracking_doc.get('first_click').isoformat() if tracking_doc.get('first_click') else None,
            'reply_date': tracking_doc.get('reply_date').isoformat() if tracking_doc.get('reply_date') else None,
            'unsubscribe_date': tracking_doc.get('unsubscribe_date').isoformat() if tracking_doc.get('unsubscribe_date') else None,
        }
        
        return jsonify(email_analytics)
        
    except Exception as error:
        print(f"Error getting email analytics: {error}")
        return jsonify({'error': f'Error fetching email analytics: {str(error)}'}), 500

@main_bp.route('/api/tracking/email/<tracking_id>')
def get_email_tracking(tracking_id):
    """Get email tracking details by tracking ID"""
    try:
        tracking_collection = db_manager.db['email_tracking']
        
        tracking_doc = tracking_collection.find_one({'tracking_id': tracking_id})
        if not tracking_doc:
            return jsonify({'error': 'Tracking data not found'}), 404
        
        # Convert to JSON-serializable format
        tracking_doc['_id'] = str(tracking_doc['_id'])
        if 'sent_at' in tracking_doc:
            tracking_doc['sent_at'] = tracking_doc['sent_at'].isoformat()
        if 'first_open' in tracking_doc and tracking_doc['first_open']:
            tracking_doc['opened_at'] = tracking_doc['first_open'].isoformat()
        if 'first_click' in tracking_doc and tracking_doc['first_click']:
            tracking_doc['clicked_at'] = tracking_doc['first_click'].isoformat()
        
        # Add boolean flags for easier frontend use
        tracking_doc['opened'] = tracking_doc.get('opens', 0) > 0
        tracking_doc['clicked'] = tracking_doc.get('clicks', 0) > 0
        tracking_doc['bounced'] = tracking_doc.get('bounced', False)
        
        # Format bounce date if exists
        if 'bounce_date' in tracking_doc and tracking_doc['bounce_date']:
            tracking_doc['bounce_date'] = tracking_doc['bounce_date'].isoformat()
        
        return jsonify(tracking_doc)
        
    except Exception as error:
        print(f"Error getting email tracking: {error}")
        return jsonify({'error': f'Error fetching tracking data: {str(error)}'}), 500

@main_bp.route('/api/tracking/resend/<tracking_id>', methods=['POST'])
def resend_email(tracking_id):
    """Resend email by tracking ID"""
    try:
        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        tracking_collection = db_manager.db['email_tracking']
        
        tracking_doc = tracking_collection.find_one({'tracking_id': tracking_id})
        if not tracking_doc:
            return jsonify({'error': 'Tracking data not found'}), 404
        
        # Check if email is bounced - don't allow resending bounced emails
        if tracking_doc.get('bounced', False):
            return jsonify({'error': 'Cannot resend bounced email. Please use a different email address.'}), 400
        
        recipient_email = tracking_doc.get('recipient_email')
        recipient_name = tracking_doc.get('recipient_name', recipient_email.split('@')[0])
        subject = tracking_doc.get('subject', '')
        message = tracking_doc.get('message', '')
        
        # Create email payload
        email_payload = {
            'message': {
                'subject': subject,
                'body': {
                    'contentType': 'HTML',
                    'content': message.replace('\n', '<br>')
                },
                'toRecipients': [{
                    'emailAddress': {
                        'address': recipient_email,
                        'name': recipient_name
                    }
                }]
            }
        }
        
        # Send email via Microsoft Graph API
        response = make_graph_request('/me/sendMail', access_token, 'POST', email_payload)
        
        if response and 'error' not in str(response):
            # Update tracking document with new sent time and clear bounce status
            tracking_collection.update_one(
                {'tracking_id': tracking_id},
                {'$set': {
                    'sent_at': datetime.now(timezone.utc),
                    'bounced': False,
                    'bounce_reason': None,
                    'bounce_date': None
                }}
            )
            
            return jsonify({
                'success': True,
                'message': 'Email resent successfully',
                'tracking_id': tracking_id
            })
        else:
            return jsonify({'error': 'Failed to resend email'}), 500
        
    except Exception as error:
        print(f"Error resending email: {error}")
        return jsonify({'error': f'Error resending email: {str(error)}'}), 500

@main_bp.route('/api/tracking/mark-bounced/<tracking_id>', methods=['POST'])
def mark_email_bounced(tracking_id):
    """Manually mark an email as bounced"""
    try:
        tracking_collection = db_manager.db['email_tracking']
        
        data = request.get_json() or {}
        bounce_reason = data.get('bounce_reason', 'Manually marked as bounced')
        
        result = tracking_collection.update_one(
            {'tracking_id': tracking_id},
            {'$set': {
                'bounced': True,
                'bounce_reason': bounce_reason,
                'bounce_date': datetime.now(timezone.utc)
            }}
        )
        
        if result.matched_count > 0:
            return jsonify({
                'success': True,
                'message': 'Email marked as bounced',
                'tracking_id': tracking_id
            })
        else:
            return jsonify({'error': 'Tracking data not found'}), 404
        
    except Exception as error:
        print(f"Error marking email as bounced: {error}")
        return jsonify({'error': f'Error marking email as bounced: {str(error)}'}), 500

@main_bp.route('/api/track/open/<tracking_id>')
def track_email_open(tracking_id):
    """Track email open event"""
    try:
        tracking_collection = db_manager.db['email_tracking']
        
        tracking_doc = tracking_collection.find_one({'tracking_id': tracking_id})
        if tracking_doc:
            # Update opens count
            current_opens = tracking_doc.get('opens', 0)
            update_data = {
                'opens': current_opens + 1
            }
            
            # Set first_open if not already set
            if not tracking_doc.get('first_open'):
                update_data['first_open'] = datetime.now(timezone.utc)
            
            tracking_collection.update_one(
                {'tracking_id': tracking_id},
                {'$set': update_data}
            )
        
        # Return 1x1 transparent pixel
        from flask import Response
        pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
        return Response(pixel, mimetype='image/gif')
        
    except Exception as error:
        print(f"Error tracking email open: {error}")
        # Still return pixel even on error
        from flask import Response
        pixel = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
        return Response(pixel, mimetype='image/gif')

@main_bp.route('/api/track/click/<tracking_id>')
def track_email_click(tracking_id):
    """Track email link click event"""
    try:
        import urllib.parse
        
        url = request.args.get('url', '')
        if not url:
            return redirect('/')
        
        tracking_collection = db_manager.db['email_tracking']
        
        tracking_doc = tracking_collection.find_one({'tracking_id': tracking_id})
        if tracking_doc:
            # Update clicks count
            current_clicks = tracking_doc.get('clicks', 0)
            update_data = {
                'clicks': current_clicks + 1
            }
            
            # Set first_click if not already set
            if not tracking_doc.get('first_click'):
                update_data['first_click'] = datetime.now(timezone.utc)
            
            tracking_collection.update_one(
                {'tracking_id': tracking_id},
                {'$set': update_data}
            )
        
        # Redirect to original URL
        return redirect(url)
        
    except Exception as error:
        print(f"Error tracking email click: {error}")
        url = request.args.get('url', '/')
        return redirect(url)

@main_bp.route('/api/check-bounces/<campaign_id>')
def check_bounces(campaign_id):
    """Check for bounced emails by examining NDR (Non-Delivery Reports) from Microsoft Graph"""
    try:
        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        tracking_collection = db_manager.db['email_tracking']
        campaigns_collection = db_manager.db['email_campaigns']
        
        campaign = campaigns_collection.find_one({'campaign_id': campaign_id})
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Get all tracking docs for this campaign (including already bounced to re-check)
        all_tracking_docs = list(tracking_collection.find({'campaign_id': campaign_id}))
        tracking_docs = [doc for doc in all_tracking_docs if not doc.get('bounced', False)]
        
        # Get all recipient emails from campaign for matching
        campaign_recipients = {doc.get('recipient_email', '').lower(): doc.get('recipient_email', '') 
                              for doc in all_tracking_docs if doc.get('recipient_email')}
        
        print(f"Checking bounces for campaign {campaign_id}, {len(tracking_docs)} non-bounced emails to check")
        
        # General bounce detection - works with any bounce message format
        # Use a more general approach to identify bounce messages
        bounce_indicators = [
            # Delivery failures
            'delivery', 'delivered', 'undeliverable', 'undelivered', 'failed', 'failure',
            # Not found errors
            'not found', 'notfound', 'wasn\'t found', "wasn't found", 'was not found',
            # Rejection errors
            'rejected', 'reject', 'bounce', 'bounced', 'returned',
            # Status notifications
            'status notification', 'delivery status', 'mail delivery',
            # Common phrases
            'couldn\'t be', "couldn't be", 'could not be', 'unable to',
            # System messages
            'mailer-daemon', 'postmaster', 'mail delivery subsystem',
            # Action required
            'action required', 'action needed'
        ]
        
        bounced_emails = []
        updated_count = 0
        
        # Search for bounce messages in the last 14 days
        from datetime import timedelta
        fourteen_days_ago = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        
        # Get messages from inbox - check for bounce notifications
        messages_endpoint = f"/me/messages?$filter=receivedDateTime ge {fourteen_days_ago}&$top=200&$orderby=receivedDateTime desc&$select=id,subject,bodyPreview,receivedDateTime,from"
        messages = make_graph_request(messages_endpoint, access_token, 'GET')
        
        print(f"Found {len(messages.get('value', [])) if isinstance(messages, dict) else 0} messages to check")
        
        if isinstance(messages, dict) and 'value' in messages:
            for message in messages['value']:
                subject = message.get('subject', '')
                body_preview = message.get('bodyPreview', '')
                message_id = message.get('id', '')
                
                # Combine text for initial check (case-insensitive)
                search_text = (subject + ' ' + body_preview).lower()
                
                # General bounce detection: check if message contains bounce indicators
                # Count how many indicators are present (more = more likely to be a bounce)
                indicator_count = sum(1 for indicator in bounce_indicators if indicator in search_text)
                
                # Also check if sender is a system/mailer address
                sender = message.get('from', {})
                sender_email = sender.get('emailAddress', {}).get('address', '').lower() if isinstance(sender, dict) else ''
                is_system_sender = any(term in sender_email for term in ['mailer', 'postmaster', 'mail', 'noreply', 'no-reply', 'daemon'])
                
                # Consider it a bounce message if:
                # 1. Has multiple bounce indicators, OR
                # 2. Has at least one indicator and is from a system sender, OR
                # 3. Subject contains common bounce keywords
                is_ndr = (indicator_count >= 2) or (indicator_count >= 1 and is_system_sender) or any(
                    term in subject.lower() for term in ['delivery', 'undeliverable', 'bounce', 'failure', 'rejected']
                )
                
                if is_ndr:
                    print(f"Found potential bounce message: {subject} (indicators: {indicator_count}, system sender: {is_system_sender})")
                    
                    # Get full message body for comprehensive email extraction
                    full_message = make_graph_request(f"/me/messages/{message_id}", access_token, 'GET')
                    body_text = ''
                    if isinstance(full_message, dict):
                        body_content = full_message.get('body', {})
                        if isinstance(body_content, dict):
                            body_text = body_content.get('content', '')
                        elif isinstance(body_content, str):
                            body_text = body_content
                    
                    # Combine all text sources for searching (normalize HTML entities and whitespace)
                    body_text_clean = html.unescape(body_text) if body_text else ''
                    # Remove HTML tags for better text extraction
                    body_text_clean = re.sub(r'<[^>]+>', ' ', body_text_clean)
                    # Normalize whitespace
                    body_text_clean = ' '.join(body_text_clean.split())
                    
                    all_text = (subject + ' ' + body_preview + ' ' + body_text_clean)
                    all_text_lower = all_text.lower()
                    
                    # GENERAL EMAIL EXTRACTION: Extract ALL email addresses from the message
                    # Use a comprehensive email regex pattern
                    email_regex = r'\b([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Z|a-z]{2,})\b'
                    
                    # Extract all emails from the text (case-insensitive)
                    all_found_emails = []
                    matches = re.finditer(email_regex, all_text, re.IGNORECASE)
                    for match in matches:
                        email = match.group(1).strip().lower()
                        # Filter out common system emails that shouldn't be matched
                        if email and not any(system_term in email for system_term in [
                            'mailer-daemon', 'postmaster', 'mail delivery', 'noreply', 
                            'no-reply', 'donotreply', 'daemon', 'mailer'
                        ]):
                            if email not in all_found_emails:
                                all_found_emails.append(email)
                    
                    print(f"DEBUG: Extracted {len(all_found_emails)} email(s) from bounce message: {all_found_emails}")
                    print(f"DEBUG: Campaign recipients to match: {list(campaign_recipients.keys())}")
                    
                    # DYNAMIC MATCHING: Try multiple matching strategies
                    recipient_email = None
                    
                    # Strategy 1: Exact match (case-insensitive)
                    for found_email in all_found_emails:
                        if found_email in campaign_recipients:
                            recipient_email = campaign_recipients[found_email]
                            print(f"✓ Matched bounce email (exact): {recipient_email}")
                            break
                    
                    # Strategy 2: Partial match by username (if exact match failed)
                    if not recipient_email and all_found_emails:
                        for found_email in all_found_emails:
                            if '@' in found_email:
                                bounce_username = found_email.split('@')[0].lower()
                                bounce_domain = found_email.split('@')[1].lower()
                                
                                for camp_email_lower, camp_email in campaign_recipients.items():
                                    if '@' in camp_email_lower:
                                        camp_username = camp_email_lower.split('@')[0].lower()
                                        camp_domain = camp_email_lower.split('@')[1].lower()
                                        
                                        # Match if username matches and domain matches
                                        if bounce_username == camp_username and bounce_domain == camp_domain:
                                            recipient_email = camp_email
                                            print(f"✓ Matched bounce email (username+domain): {recipient_email}")
                                            break
                                        # Or match if username is similar (handles variations)
                                        elif bounce_username == camp_username:
                                            recipient_email = camp_email
                                            print(f"✓ Matched bounce email (username only): {recipient_email} (bounce domain: {bounce_domain}, campaign domain: {camp_domain})")
                                            break
                                    
                                    if recipient_email:
                                        break
                            
                            if recipient_email:
                                break
                    
                    # Strategy 3: Fuzzy match - check if any part of the email appears in campaign recipients
                    if not recipient_email and all_found_emails:
                        for found_email in all_found_emails:
                            for camp_email_lower, camp_email in campaign_recipients.items():
                                # Check if the found email is contained in campaign email or vice versa
                                if found_email in camp_email_lower or camp_email_lower in found_email:
                                    recipient_email = camp_email
                                    print(f"✓ Matched bounce email (fuzzy): {recipient_email}")
                                    break
                            if recipient_email:
                                break
                    
                    # DYNAMIC BOUNCE REASON EXTRACTION: Extract reason from message content
                    bounce_reason = subject if subject else "Delivery failed"
                    
                    # Try to extract a more specific reason from the message
                    reason_patterns = [
                        (r"wasn['']t\s+found", "Recipient wasn't found"),
                        (r"couldn['']t\s+be\s+delivered", "Message couldn't be delivered"),
                        (r"could\s+not\s+be\s+delivered", "Message could not be delivered"),
                        (r"mailbox\s+full", "Mailbox full"),
                        (r"mailbox\s+quota", "Mailbox quota exceeded"),
                        (r"invalid\s+(?:email\s+)?address", "Invalid email address"),
                        (r"address\s+rejected", "Address rejected"),
                        (r"domain\s+not\s+found", "Domain not found"),
                        (r"user\s+unknown", "User unknown"),
                        (r"recipient\s+rejected", "Recipient rejected"),
                        (r"permanent\s+failure", "Permanent delivery failure"),
                        (r"temporary\s+failure", "Temporary delivery failure"),
                        (r"spam", "Message rejected as spam"),
                        (r"blocked", "Message blocked"),
                    ]
                    
                    for pattern, reason in reason_patterns:
                        if re.search(pattern, all_text_lower, re.IGNORECASE):
                            bounce_reason = reason
                            break
                    
                    # If no specific reason found, use a generic one based on common phrases
                    if bounce_reason == subject:
                        if any(term in all_text_lower for term in ['not found', 'notfound']):
                            bounce_reason = "Recipient not found"
                        elif any(term in all_text_lower for term in ['couldn\'t', "couldn't", 'could not']):
                            bounce_reason = "Message could not be delivered"
                        elif any(term in all_text_lower for term in ['rejected', 'reject']):
                            bounce_reason = "Message rejected"
                        else:
                            bounce_reason = "Delivery failed"
                    
                    # Update tracking document if we found a match
                    if recipient_email:
                        # Check if email was previously marked as sent (not bounced)
                        existing_doc = tracking_collection.find_one({
                            'campaign_id': campaign_id, 
                            'recipient_email': recipient_email
                        })
                        
                        was_previously_sent = existing_doc and not existing_doc.get('bounced', False)
                        
                        # Update tracking document - mark as bounced
                        result = tracking_collection.update_one(
                            {'campaign_id': campaign_id, 'recipient_email': recipient_email},
                            {'$set': {
                                'bounced': True,
                                'bounce_reason': bounce_reason,
                                'bounce_date': datetime.now(timezone.utc)
                            }},
                            upsert=False
                        )
                        
                        # Check if document was found and updated
                        if result.matched_count > 0:
                            if result.modified_count > 0:
                                updated_count += 1
                                bounced_emails.append({
                                    'email': recipient_email,
                                    'bounce_reason': bounce_reason,
                                    'bounce_date': datetime.now(timezone.utc).isoformat()
                                })
                                print(f"✓ Marked {recipient_email} as bounced: {bounce_reason}")
                                
                                # If this email was previously counted as "sent", we need to update campaign stats
                                # The analytics endpoint will recalculate, but we can also update the campaign
                                if was_previously_sent:
                                    # Decrement sent_count in campaign (if it exists)
                                    campaign_doc = campaigns_collection.find_one({'campaign_id': campaign_id})
                                    if campaign_doc:
                                        current_sent_count = campaign_doc.get('sent_count', 0)
                                        if current_sent_count > 0:
                                            return jsonify({'error': 'Internal server error'}), 500
                            else:
                                print(f"✗ {recipient_email} was not previously marked as sent")
                
    except Exception as e:
        print(f"Error updating campaign stats: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== CLERK AUTHENTICATION ENDPOINTS ====================
@main_bp.route('/api/sync-clerk-user', methods=['POST', 'OPTIONS'])
def sync_clerk_user():
    """Sync Clerk user with database"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # Check if database is available
        if not db_manager or db_manager.db is None or db_manager.users_collection is None:
            return jsonify({'success': False, 'error': 'Database not available'}), 503
        
        data = request.get_json()
        clerk_user_id = data.get('clerk_user_id')
        email = data.get('email', '')
        display_name = data.get('display_name', '')
        
        if not clerk_user_id:
            return jsonify({'success': False, 'error': 'clerk_user_id is required'}), 400
        
        # Create or update user record using new schema (user_information_table)
        # Check if user exists by clerk_user_id
        existing_user = db_manager.get_user_by_clerk_id(clerk_user_id)
        
        if existing_user:
            # Update existing user
            db_manager.users_collection.update_one(
                {'clerk_user_id': clerk_user_id},
                {
                    '$set': {
                        'user_name': display_name or existing_user.get('user_name', ''),
                        'login_id': email,  # Update login_id to email
                        'email': email,
                        'updated_at': datetime.now(timezone.utc)
                    }
                }
            )
            user_id = str(existing_user.get('user_id'))  # Convert ObjectId to string
            print(f"✓ Updated Clerk user: {clerk_user_id} ({email})")
        else:
            # Create new user in user_information_table
            result = db_manager.create_user(
                user_name=display_name or email.split('@')[0],
                login_id=email,  # login_id is the email
                email=email,
                clerk_user_id=clerk_user_id
            )
            
            if result['success']:
                user_id = str(result['user']['user_id'])  # Convert ObjectId to string
                print(f"✓ Created new Clerk user: {clerk_user_id} ({email})")
            else:
                return jsonify({'success': False, 'error': result.get('error', 'Failed to create user')}), 500
        
        # After syncing user, update any existing mailboxes in linkbox_box_table to link them to this Clerk user
        # This handles the case where mailboxes were added before Clerk integration
        if db_manager is not None and db_manager.mailboxes_collection is not None:
            try:
                # Get user_id from user_information_table (already have user_id as string from above)
                # We need ObjectId for database query, but user_id variable is already a string
                from bson import ObjectId
                user_id_obj = ObjectId(user_id)  # Convert string user_id to ObjectId for database query
                    
                # Update mailboxes in linkbox_box_table that belong to this user
                # Mailboxes are linked by user_id in linkbox_box_table
                update_result = db_manager.mailboxes_collection.update_many(
                    {
                        'user_id': user_id_obj,
                        'is_active': True
                    },
                    {
                        '$set': {
                            'owner_clerk_id': clerk_user_id,  # Also store clerk_id for easy lookup
                            'updated_at': datetime.now(timezone.utc)
                        }
                    }
                )
                if update_result.modified_count > 0:
                    print(f"✓ Updated {update_result.modified_count} existing mailboxes in linkbox_box_table with Clerk user ID")
            except Exception as e:
                print(f"Warning: Could not update existing mailboxes: {e}")
        
        # Ensure user_id is a string (not ObjectId) for JSON serialization
        user_id_str = str(user_id) if user_id else None
        
        
        # AUTO-LOAD PRIMARY MAILBOX CREDENTIALS INTO SESSION
        # After login, if user has mailboxes, automatically load the primary one into session
        primary_mailbox = None
        if db_manager and db_manager.mailboxes_collection is not None:
            try:
                from bson import ObjectId
                user_id_obj = ObjectId(user_id)
                
                # Find primary mailbox for this user
                primary_mailbox = db_manager.mailboxes_collection.find_one({
                    'user_id': user_id_obj,
                    'is_primary': True,
                    'is_active': True
                })
                
                # If no primary mailbox, get any active mailbox and set it as primary
                if not primary_mailbox:
                    primary_mailbox = db_manager.mailboxes_collection.find_one({
                        'user_id': user_id_obj,
                        'is_active': True
                    })
                    
                    if primary_mailbox:
                        # Set this mailbox as primary
                        db_manager.mailboxes_collection.update_one(
                            {'_id': primary_mailbox['_id']},
                            {'$set': {'is_primary': True, 'updated_at': datetime.now(timezone.utc)}}
                        )
                        print(f"Auto-set first mailbox as primary: {primary_mailbox.get('email')}")
                
                # Load primary mailbox credentials into session
                if primary_mailbox:
                    session['access_token'] = primary_mailbox.get('access_token')
                    session['user_profile'] = primary_mailbox.get('user_profile')
                    session['user_email'] = primary_mailbox.get('email')
                    session['mailbox_id'] = str(primary_mailbox['_id'])
                    print(f"✓ Auto-loaded primary mailbox into session: {primary_mailbox.get('email')}")
                else:
                    print(f"ℹ No mailboxes found for user {clerk_user_id}")
                    
            except Exception as e:
                print(f"Warning: Could not auto-load primary mailbox: {e}")
        
        return jsonify({
            'success': True,
            'user_id': user_id_str,
            'clerk_user_id': clerk_user_id,
            'has_primary_mailbox': primary_mailbox is not None,
            'primary_mailbox_email': primary_mailbox.get('email') if primary_mailbox else None
        })
        
    except Exception as error:
        print(f"Error syncing Clerk user: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(error)}), 500

# ==================== EMAIL ACCOUNTS ENDPOINTS ====================
@main_bp.route('/api/email-accounts', methods=['GET', 'OPTIONS'])
def get_email_accounts():
    """Get all linked email accounts for the current user"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-Clerk-User-Id')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # Check if database is available
        if not db_manager or db_manager.db is None or db_manager.mailboxes_collection is None:
            return jsonify({'error': 'Database not available', 'accounts': []}), 503
        
        # ONLY use Clerk user ID from request header - NO SESSION FALLBACKS
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        
        if not clerk_user_id:
            print("❌ ERROR: X-Clerk-User-Id header is REQUIRED")
            print("   🚫 NO SESSION FALLBACK - Database is the ONLY source")
            print("   ⚠️  This endpoint ONLY uses database, NOT session")
            return jsonify({
                'error': 'Clerk user ID is required. Please ensure X-Clerk-User-Id header is sent. This endpoint uses database only, not session.',
                'accounts': []
            }), 400
        
        print(f"🔍 Fetching mailboxes from DATABASE ONLY for Clerk user: {clerk_user_id}")
        print(f"   ⚠️  NO SESSION DATA USED - All data from database")
        
        # CRITICAL: Get mailboxes from linkbox_box_table (mailboxes_collection) using user_id
        # All mailbox information (access tokens, user profiles, etc.) is stored in linkbox_box_table
        # NO SESSION FALLBACK - Database is the ONLY source of truth
        
        # First, get user_id from user_information_table using Clerk ID
        user = db_manager.get_user_by_clerk_id(clerk_user_id) if db_manager else None
        if not user:
            print(f"⚠️  User not found in database for Clerk ID: {clerk_user_id}")
            return jsonify({'accounts': []})
        
        user_id = user.get('user_id')
        print(f"  - User ID from database: {user_id}")
        
        # Get mailboxes from linkbox_box_table using user_id
        from bson import ObjectId
        accounts = list(db_manager.mailboxes_collection.find({
            'user_id': ObjectId(user_id),  # Link mailboxes by user_id from user_information_table
            'is_active': True
        }))
        
        print(f"✅ Found {len(accounts)} mailboxes in linkbox_box_table for Clerk user: {clerk_user_id}")
        print(f"   📊 Source: Database (linkbox_box_table / mailboxes_collection)")
        print(f"   🚫 Session: NOT USED")
        
        # Debug: Print account details to verify
        for acc in accounts:
            print(f"  - Mailbox: {acc.get('email')}, user_id: {acc.get('user_id')}, has_access_token: {bool(acc.get('access_token'))}")
        
        # Safeguard: Ensure only one primary account exists
        primary_accounts = [acc for acc in accounts if acc.get('is_primary')]
        if len(primary_accounts) > 1:
            print(f"⚠️  WARNING: Found {len(primary_accounts)} primary accounts for user {clerk_user_id}, fixing...")
            # Keep the first one as primary, unset others
            for idx, acc in enumerate(primary_accounts):
                if idx > 0:  # Unset primary on all except the first
                    db_manager.mailboxes_collection.update_one(
                        {'_id': acc['_id']},
                        {'$set': {'is_primary': False, 'updated_at': datetime.now(timezone.utc)}}
                    )
                    acc['is_primary'] = False
            print(f"✅ Fixed: Set only first primary account as primary")
        elif len(primary_accounts) == 0 and len(accounts) > 0:
            # No primary account exists, set the first one as primary
            print(f"⚠️  WARNING: No primary account found for user {clerk_user_id}, setting first account as primary")
            first_account = accounts[0]
            db_manager.mailboxes_collection.update_one(
                {'_id': first_account['_id']},
                {'$set': {'is_primary': True, 'updated_at': datetime.now(timezone.utc)}}
            )
            first_account['is_primary'] = True
            print(f"✅ Set first account as primary: {first_account.get('email')}")
        
        # Transform to frontend format
        formatted_accounts = []
        for idx, account in enumerate(accounts):
            formatted_accounts.append({
                'id': str(account['_id']),
                'email': account['email'],
                'provider': account.get('provider', 'outlook'),
                'status': 'active' if account.get('is_active') else 'inactive',
                'is_primary': account.get('is_primary', False),  # Use actual value from database
                'last_used': account.get('last_used', account.get('created_at')).isoformat() if account.get('last_used') or account.get('created_at') else datetime.now(timezone.utc).isoformat(),
                'created_at': account.get('created_at').isoformat() if account.get('created_at') else datetime.now(timezone.utc).isoformat()
            })
        
        return jsonify({'accounts': formatted_accounts})
        
    except Exception as error:
        print(f"Error getting email accounts: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(error), 'accounts': []}), 500

@main_bp.route('/api/email-accounts/<account_id>', methods=['GET'])
def get_email_account(account_id):
    """Get a single email account by ID"""
    try:
        from bson import ObjectId
        
        # Get mailbox from linkbox_box_table
        account = db_manager.mailboxes_collection.find_one({
            '_id': ObjectId(account_id),
            'is_active': True
        })
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        formatted_account = {
            'id': str(account['_id']),
            'email': account['email'],
            'provider': account.get('provider', 'outlook'),
            'status': 'active' if account.get('is_active') else 'inactive',
            'is_primary': account.get('is_primary', False),
            'last_used': account.get('last_used', account.get('created_at')).isoformat() if account.get('last_used') or account.get('created_at') else datetime.now(timezone.utc).isoformat(),
            'created_at': account.get('created_at').isoformat() if account.get('created_at') else datetime.now(timezone.utc).isoformat()
        }
        
        return jsonify({'account': formatted_account})
        
    except Exception as error:
        print(f"Error getting email account: {error}")
        return jsonify({'error': str(error)}), 500

@main_bp.route('/api/email-accounts/<account_id>', methods=['DELETE', 'OPTIONS'])
def disconnect_email_account(account_id):
    """Disconnect an email account"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-Clerk-User-Id')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # ONLY use Clerk user ID from database - NO SESSION
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        print(f"🔍 [disconnect] Received request for account_id: {account_id}")
        print(f"   📋 Headers: {dict(request.headers)}")
        print(f"   👤 Clerk User ID from header: {clerk_user_id}")
        
        if not clerk_user_id or clerk_user_id.strip() == '':
            print("❌ ERROR: X-Clerk-User-Id header is missing or empty")
            return jsonify({'error': 'Clerk user ID is required. Please ensure X-Clerk-User-Id header is sent.'}), 400
        
        # Get user_id from user_information_table
        user = db_manager.get_user_by_clerk_id(clerk_user_id) if db_manager else None
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        from bson import ObjectId
        user_id = ObjectId(user.get('user_id'))
        
        # Verify mailbox belongs to this user before deleting
        mailbox = db_manager.mailboxes_collection.find_one({
            '_id': ObjectId(account_id),
            'user_id': user_id
        })
        
        if not mailbox:
            return jsonify({'error': 'Mailbox not found or access denied'}), 404
        
        # Hard delete the mailbox from linkbox_box_table (completely remove from database)
        result = db_manager.mailboxes_collection.delete_one({
            '_id': ObjectId(account_id),
            'user_id': user_id  # Ensure we only delete if it belongs to this user
        })
        
        if result.deleted_count > 0:
            print(f"✅ Successfully deleted mailbox {account_id} for user {clerk_user_id}")
            return jsonify({'success': True, 'message': 'Account disconnected and removed from database'})
        else:
            print(f"⚠️  Mailbox {account_id} not found or already deleted")
            return jsonify({'error': 'Account not found'}), 404
            
    except Exception as error:
        print(f"Error disconnecting account: {error}")
        return jsonify({'error': str(error)}), 500

@main_bp.route('/api/email-accounts/<account_id>/set-primary', methods=['POST', 'OPTIONS'])
def set_primary_account(account_id):
    """Set an email account as primary"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-Clerk-User-Id')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # Check if database is available
        if not db_manager or db_manager.db is None or db_manager.mailboxes_collection is None:
            return jsonify({'error': 'Database not available'}), 503
        
        from bson import ObjectId
        
        # ONLY use Clerk user ID from database - NO SESSION
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        print(f"🔍 [set-primary] Received request for account_id: {account_id}")
        print(f"   📋 Headers: {dict(request.headers)}")
        print(f"   👤 Clerk User ID from header: {clerk_user_id}")
        
        if not clerk_user_id or clerk_user_id.strip() == '':
            print("❌ ERROR: X-Clerk-User-Id header is missing or empty")
            return jsonify({'error': 'Clerk user ID is required. Please ensure X-Clerk-User-Id header is sent.'}), 400
        
        # Get user_id from user_information_table
        user = db_manager.get_user_by_clerk_id(clerk_user_id) if db_manager else None
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_id = ObjectId(user.get('user_id'))
        
        # Verify mailbox belongs to this user
        account = db_manager.mailboxes_collection.find_one({
            '_id': ObjectId(account_id),
            'user_id': user_id,
            'is_active': True
        })
        
        if not account:
            return jsonify({'error': 'Mailbox not found or access denied'}), 404
        
        # Unset all primary flags for this user in linkbox_box_table
        db_manager.mailboxes_collection.update_many(
            {'user_id': user_id, 'is_active': True},
            {'$set': {'is_primary': False, 'updated_at': datetime.now(timezone.utc)}}
        )
        
        # Set this mailbox as primary in linkbox_box_table
        result = db_manager.mailboxes_collection.update_one(
            {'_id': ObjectId(account_id)},
            {'$set': {'is_primary': True, 'updated_at': datetime.now(timezone.utc)}}
        )
        
        # Save credentials to session as requested
        # This ensures the session has the primary account's credentials
        session['access_token'] = account.get('access_token')
        session['user_profile'] = account.get('user_profile')
        session['user_email'] = account.get('email')
        session['mailbox_id'] = str(account['_id'])
        print(f"Updated session with primary account credentials: {account.get('email')}")

        if result.modified_count > 0 or result.matched_count > 0:
            return jsonify({'success': True, 'message': 'Primary account updated'})
        else:
            return jsonify({'error': 'Account not found'}), 404
            
    except Exception as error:
        print(f"Error setting primary account: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(error)}), 500

@main_bp.route('/api/mailbox/<account_id>/campaigns', methods=['GET'])
def get_mailbox_campaigns(account_id):
    """Get campaigns sent from a specific mailbox"""
    try:
        from bson import ObjectId
        
        # Get mailbox info
        # Get mailbox from linkbox_box_table
        mailbox = db_manager.mailboxes_collection.find_one({
            '_id': ObjectId(account_id),
            'is_active': True
        })
        
        if not mailbox:
            return jsonify({'error': 'Mailbox not found'}), 404
        
        mailbox_email = mailbox['email']
        
        # Get campaigns sent from this mailbox
        campaigns = list(db_manager.db['email_campaigns'].find({
            'sender_email': mailbox_email
        }).sort('created_at', -1))
        
        # Format campaigns
        formatted_campaigns = []
        for campaign in campaigns:
            formatted_campaigns.append({
                'campaign_id': campaign.get('campaign_id', str(campaign['_id'])),
                'subject': campaign.get('subject', 'No Subject'),
                'created_at': campaign.get('created_at').isoformat() if campaign.get('created_at') else datetime.now(timezone.utc).isoformat(),
                'total_recipients': campaign.get('total_recipients', 0),
                'successfully_sent': campaign.get('successfully_sent', 0),
                'bounced': campaign.get('bounced', 0),
                'opened': campaign.get('opened', 0),
                'clicked': campaign.get('clicked', 0),
                'open_rate': campaign.get('open_rate', 0),
                'bounce_rate': campaign.get('bounce_rate', 0)
            })
        
        return jsonify({
            'success': True,
            'campaigns': formatted_campaigns
        })
        
    except Exception as error:
        print(f"Error getting mailbox campaigns: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(error)}), 500

# Route for adding a new email account (separate from login)
@main_bp.route('/add-account')
def add_account():
    """Redirect to OAuth signin for adding a new account"""
    # Get Clerk user ID from query parameter or header
    clerk_user_id = request.args.get('clerk_user_id') or request.headers.get('X-Clerk-User-Id')
    
    if not clerk_user_id:
        # Try to get from session as fallback (for backward compatibility)
        clerk_user_id = session.get('clerk_user_id')
        if not clerk_user_id:
            print("⚠️  ERROR: Clerk user ID is required to add mailbox")
            print(f"   Query params: {request.args}")
            print(f"   Headers: X-Clerk-User-Id = {request.headers.get('X-Clerk-User-Id')}")
            print(f"   Session keys: {list(session.keys())}")
            frontend_url = Config.FRONTEND_URL
            return redirect(f"{frontend_url}/email-accounts?account_added=error&reason=clerk_user_id_required")
    
    # Store Clerk user ID in session for OAuth callback
    session['oauth_flow'] = 'add_account'
    session['clerk_user_id'] = clerk_user_id
    session.permanent = True  # Make session persistent
    print(f"📧 Initiating OAuth flow to add mailbox for Clerk user: {clerk_user_id}")
    print(f"   ✅ Stored in session: clerk_user_id = {clerk_user_id}")
    
    auth_url = get_auth_url()
    return redirect(auth_url)

# ==================== END EMAIL ACCOUNTS ENDPOINTS ====================

# ==================== DASHBOARD ANALYTICS ENDPOINT ====================
@main_bp.route('/api/analytics/dashboard', methods=['GET', 'OPTIONS'])
def get_dashboard_analytics():
    """Get aggregated analytics for dashboard"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-Clerk-User-Id')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        # Check if database is available
        if not db_manager or db_manager.db is None:
            return jsonify({
                'error': 'Database not available',
                'total_sent': 0,
                'total_opened': 0,
                'total_clicked': 0,
                'total_bounced': 0,
                'open_rate': 0,
                'click_rate': 0,
                'bounce_rate': 0,
                'reply_rate': 0,
                'total_campaigns': 0,
                'active_campaigns': 0,
                'recent_campaigns': []
            }), 503
        
        # Check for Clerk user ID first
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        
        if clerk_user_id:
            print(f"Fetching dashboard analytics for Clerk user: {clerk_user_id}")
            # Get all campaigns for this Clerk user
            campaigns = list(db_manager.db['email_campaigns'].find({'clerk_user_id': clerk_user_id}))
        else:
            # Fallback to email-based lookup
            user_profile = session.get('user_profile')
            if not user_profile:
                return jsonify({'error': 'Not authenticated'}), 401
            
            user_email = user_profile.get('mail') or user_profile.get('userPrincipalName')
            print(f"Fetching dashboard analytics for email: {user_email}")
            # Get all campaigns for this user
            campaigns = list(db_manager.db['email_campaigns'].find({'user_email': user_email}))
        
        # Calculate aggregated stats from tracking collection for accuracy
        tracking_collection = db_manager.db['email_tracking']
        campaign_ids = [c.get('campaign_id') for c in campaigns if c.get('campaign_id')]
        
        # Get all tracking docs for user's campaigns
        tracking_docs = list(tracking_collection.find({'campaign_id': {'$in': campaign_ids}}))
        
        print(f"📊 Dashboard Analytics Debug:")
        print(f"   Total campaigns: {len(campaigns)}")
        print(f"   Campaign IDs: {campaign_ids[:5]}..." if len(campaign_ids) > 5 else f"   Campaign IDs: {campaign_ids}")
        print(f"   Total tracking docs: {len(tracking_docs)}")
        
        # Calculate stats from tracking data
        # Count all tracking docs as total attempts
        total_tracking_attempts = len(tracking_docs)
        
        if total_tracking_attempts > 0:
            # Use tracking collection data (more accurate)
            # Count bounced and errors (treat None/missing as False)
            total_bounced = sum(1 for doc in tracking_docs if doc.get('bounced') == True)
            total_app_errors = sum(1 for doc in tracking_docs if doc.get('application_error') == True)
            
            # Successfully sent = total attempts - bounced - app errors
            total_sent = total_tracking_attempts - total_bounced - total_app_errors
            
            print(f"   Total attempts: {total_tracking_attempts}")
            print(f"   Total bounced: {total_bounced}")
            print(f"   Total app errors: {total_app_errors}")
            print(f"   Total sent (calculated): {total_sent}")
            # Count engagement metrics
            total_opened = sum(1 for doc in tracking_docs if doc.get('opens', 0) > 0)
            total_clicked = sum(1 for doc in tracking_docs if doc.get('clicks', 0) > 0)
            total_replied = sum(1 for doc in tracking_docs if doc.get('replies', 0) > 0)
        else:
            # Fallback to campaign document values when no tracking data
            print(f"⚠️ No tracking documents found, using campaign document values")
            total_sent = sum(c.get('sent_count', 0) for c in campaigns)
            total_opened = sum(c.get('opened', 0) for c in campaigns)
            total_clicked = sum(c.get('clicked', 0) for c in campaigns)
            total_bounced = sum(c.get('bounce_count', 0) for c in campaigns)
            total_replied = 0  # Not stored in campaign docs
        
        # Calculate rates
        open_rate = (total_opened / total_sent * 100) if total_sent > 0 else 0
        click_rate = (total_clicked / total_sent * 100) if total_sent > 0 else 0
        bounce_rate = (total_bounced / (total_sent + total_bounced) * 100) if (total_sent + total_bounced) > 0 else 0
        reply_rate = (total_replied / total_sent * 100) if total_sent > 0 else 0
        
        # Calculate active campaigns based on start_time and duration
        # IMPORTANT: Exclude stopped campaigns from active count
        now = datetime.now(timezone.utc)
        active_campaigns_count = 0
        for campaign in campaigns:
            # Skip stopped campaigns - they should never be counted as active
            if campaign.get('status') == 'stopped':
                continue
                
            if campaign.get('start_time') and campaign.get('duration'):
                start_time = campaign.get('start_time')
                if isinstance(start_time, str):
                    try:
                        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    except:
                        continue
                elif not isinstance(start_time, datetime):
                    continue
                
                # Ensure start_time is timezone-aware (UTC)
                # Handle both timezone-naive and timezone-aware datetimes
                try:
                    if start_time.tzinfo is None:
                        # If timezone-naive, assume it's UTC
                        start_time = start_time.replace(tzinfo=timezone.utc)
                    else:
                        # If timezone-aware, convert to UTC
                        start_time = start_time.astimezone(timezone.utc)
                except AttributeError:
                    # If start_time doesn't have tzinfo attribute, make it UTC
                    if not hasattr(start_time, 'tzinfo') or start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=timezone.utc)
                
                # Calculate end time (duration in hours)
                from datetime import timedelta
                end_time = start_time + timedelta(hours=campaign.get('duration', 24))
                
                # Ensure end_time is also timezone-aware (should be, but double-check)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=timezone.utc)
                
                # Now safe to compare - wrap in try-except for safety
                try:
                    if now >= start_time and now <= end_time:
                        active_campaigns_count += 1
                except TypeError as e:
                    # If there's still a comparison error, log it and skip this campaign
                    print(f"⚠️  Warning: Could not compare datetimes for campaign {campaign.get('campaign_id')}: {e}")
                    print(f"   start_time type: {type(start_time)}, tzinfo: {start_time.tzinfo if hasattr(start_time, 'tzinfo') else 'N/A'}")
                    print(f"   end_time type: {type(end_time)}, tzinfo: {end_time.tzinfo if hasattr(end_time, 'tzinfo') else 'N/A'}")
                    print(f"   now type: {type(now)}, tzinfo: {now.tzinfo if hasattr(now, 'tzinfo') else 'N/A'}")
                    continue
            elif campaign.get('status') == 'active':
                active_campaigns_count += 1
        
        # Get recent campaigns (last 5)
        # Use timezone-aware datetime.min to avoid comparison errors
        recent_campaigns = sorted(campaigns, key=lambda x: x.get('created_at', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)[:5]
        
        formatted_recent = []
        for campaign in recent_campaigns:
            formatted_recent.append({
                'campaign_id': campaign.get('campaign_id', str(campaign['_id'])),
                'subject': campaign.get('subject', ''),
                'created_at': campaign.get('created_at').isoformat() if campaign.get('created_at') else datetime.now(timezone.utc).isoformat(),
                'successfully_sent': campaign.get('successfully_sent', 0),
                'opened': campaign.get('opened', 0),
                'open_rate': campaign.get('open_rate', 0)
            })
        
        # Calculate time-based analytics
        from datetime import timedelta
        
        # Define time ranges
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        print(f"   Time ranges:")
        print(f"     now: {now} (tzinfo: {now.tzinfo})")
        print(f"     today_start: {today_start} (tzinfo: {today_start.tzinfo})")
        print(f"     week_start: {week_start} (tzinfo: {week_start.tzinfo})")
        print(f"     month_start: {month_start} (tzinfo: {month_start.tzinfo})")
        
        # Helper function to filter tracking docs by date
        def filter_by_date(docs, start_date):
            filtered = []
            for doc in docs:
                sent_at = doc.get('sent_at')
                if not sent_at:
                    continue
                    
                # Convert string to datetime if needed
                if isinstance(sent_at, str):
                    try:
                        sent_at = datetime.fromisoformat(sent_at.replace('Z', '+00:00'))
                    except Exception as e:
                        print(f"     ⚠️  Failed to parse sent_at string: {sent_at}, error: {e}")
                        continue
                
                # Ensure it's a datetime object
                if not isinstance(sent_at, datetime):
                    print(f"     ⚠️  sent_at is not a datetime: {type(sent_at)}")
                    continue
                
                # Ensure timezone-aware
                if sent_at.tzinfo is None:
                    sent_at = sent_at.replace(tzinfo=timezone.utc)
                
                # Compare dates with error handling
                try:
                    if sent_at >= start_date:
                        filtered.append(doc)
                except TypeError as e:
                    print(f"     ❌ Comparison error: {e}")
                    print(f"        sent_at: {sent_at} (type: {type(sent_at)}, tzinfo: {sent_at.tzinfo if hasattr(sent_at, 'tzinfo') else 'N/A'})")
                    print(f"        start_date: {start_date} (type: {type(start_date)}, tzinfo: {start_date.tzinfo if hasattr(start_date, 'tzinfo') else 'N/A'})")
                    continue
            return filtered
        
        # Calculate today's metrics
        today_docs = filter_by_date(tracking_docs, today_start)
        today_bounced = sum(1 for doc in today_docs if doc.get('bounced') == True)
        today_app_errors = sum(1 for doc in today_docs if doc.get('application_error') == True)
        today_sent = len(today_docs) - today_bounced - today_app_errors
        today_opened = sum(1 for doc in today_docs if doc.get('opens', 0) > 0)
        today_clicked = sum(1 for doc in today_docs if doc.get('clicks', 0) > 0)
        
        # Calculate last week's metrics
        week_docs = filter_by_date(tracking_docs, week_start)
        week_bounced = sum(1 for doc in week_docs if doc.get('bounced') == True)
        week_app_errors = sum(1 for doc in week_docs if doc.get('application_error') == True)
        week_sent = len(week_docs) - week_bounced - week_app_errors
        week_opened = sum(1 for doc in week_docs if doc.get('opens', 0) > 0)
        week_clicked = sum(1 for doc in week_docs if doc.get('clicks', 0) > 0)
        
        # Calculate last month's metrics
        month_docs = filter_by_date(tracking_docs, month_start)
        month_bounced = sum(1 for doc in month_docs if doc.get('bounced') == True)
        month_app_errors = sum(1 for doc in month_docs if doc.get('application_error') == True)
        month_sent = len(month_docs) - month_bounced - month_app_errors
        month_opened = sum(1 for doc in month_docs if doc.get('opens', 0) > 0)
        month_clicked = sum(1 for doc in month_docs if doc.get('clicks', 0) > 0)
        
        # Calculate daily breakdown for last 30 days
        daily_stats = []
        for i in range(30, -1, -1):  # Last 30 days including today
            day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            # Filter documents for this day, ensuring timezone-aware comparison
            day_docs = []
            for doc in tracking_docs:
                sent_at = doc.get('sent_at')
                if not sent_at or not isinstance(sent_at, datetime):
                    continue
                
                # Ensure timezone-aware
                if sent_at.tzinfo is None:
                    sent_at = sent_at.replace(tzinfo=timezone.utc)
                
                # Check if within day range
                if day_start <= sent_at < day_end:
                    day_docs.append(doc)
            
            day_bounced = sum(1 for doc in day_docs if doc.get('bounced') == True)
            day_app_errors = sum(1 for doc in day_docs if doc.get('application_error') == True)
            day_sent = len(day_docs) - day_bounced - day_app_errors
            day_opened = sum(1 for doc in day_docs if doc.get('opens', 0) > 0)
            day_clicked = sum(1 for doc in day_docs if doc.get('clicks', 0) > 0)
            
            daily_stats.append({
                'date': day_start.strftime('%Y-%m-%d'),
                'sent': day_sent,
                'opened': day_opened,
                'clicked': day_clicked,
                'bounced': day_bounced
            })
        
        
        return jsonify({
            # Overall totals
            'total_sent': total_sent,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'total_bounced': total_bounced,
            'total_replied': total_replied,
            'open_rate': round(open_rate, 2),
            'click_rate': round(click_rate, 2),
            'bounce_rate': round(bounce_rate, 2),
            'reply_rate': round(reply_rate, 2),
            'total_campaigns': len(campaigns),
            'active_campaigns': active_campaigns_count,
            'recent_campaigns': formatted_recent,
            
            # Time-based analytics
            'today': {
                'sent': today_sent,
                'opened': today_opened,
                'clicked': today_clicked,
                'bounced': today_bounced,
                'date': today_start.strftime('%Y-%m-%d')
            },
            'last_week': {
                'sent': week_sent,
                'opened': week_opened,
                'clicked': week_clicked,
                'bounced': week_bounced,
                'start_date': week_start.strftime('%Y-%m-%d'),
                'end_date': now.strftime('%Y-%m-%d')
            },
            'last_month': {
                'sent': month_sent,
                'opened': month_opened,
                'clicked': month_clicked,
                'bounced': month_bounced,
                'start_date': month_start.strftime('%Y-%m-%d'),
                'end_date': now.strftime('%Y-%m-%d')
            },
            
            # Daily breakdown for charts
            'daily_stats': daily_stats
        })
        
    except Exception as error:
        print(f"Error getting dashboard analytics: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(error)}), 500

# ==================== END DASHBOARD ANALYTICS ENDPOINT ====================

@main_bp.route('/get-email-tracking')
def get_all_email_tracking():
    """Get all email tracking data, optionally filtered by campaign_id"""
    try:
        campaign_id = request.args.get('campaign_id')
        tracking_collection = db_manager.db['email_tracking']
        
        query = {}
        if campaign_id:
            query['campaign_id'] = campaign_id
            
        tracking_docs = list(tracking_collection.find(query).sort('sent_at', -1))
        
        # Convert to JSON-serializable format
        for doc in tracking_docs:
            doc['_id'] = str(doc['_id'])
            if 'sent_at' in doc and doc['sent_at']:
                doc['sent_at'] = doc['sent_at'].isoformat()
            if 'first_open' in doc and doc['first_open']:
                doc['first_open'] = doc['first_open'].isoformat()
            if 'first_click' in doc and doc['first_click']:
                doc['first_click'] = doc['first_click'].isoformat()
            if 'reply_date' in doc and doc['reply_date']:
                doc['reply_date'] = doc['reply_date'].isoformat()
            if 'bounce_date' in doc and doc['bounce_date']:
                doc['bounce_date'] = doc['bounce_date'].isoformat()
            if 'unsubscribe_date' in doc and doc['unsubscribe_date']:
                doc['unsubscribe_date'] = doc['unsubscribe_date'].isoformat()
            if 'error_date' in doc and doc['error_date']:
                doc['error_date'] = doc['error_date'].isoformat()
                
            # Ensure boolean fields
            doc['bounced'] = doc.get('bounced', False)
            doc['application_error'] = doc.get('application_error', False)
            
        return jsonify({'success': True, 'tracking': tracking_docs})
        
    except Exception as error:
        print(f"Error getting all email tracking: {error}")
        return jsonify({'error': f'Error fetching tracking data: {str(error)}'}), 500

# ==================== CAMPAIGN CREATION ENDPOINT ====================

@main_bp.route('/send-mail', methods=['POST'])
def send_mail():
    """Create and launch email campaign with background execution"""
    try:
        # Get Clerk user ID
        clerk_user_id = request.headers.get('X-Clerk-User-Id')
        if not clerk_user_id:
            return jsonify({'error': 'Clerk user ID is required'}), 400
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        recipients = data.get('recipients', [])
        subject = data.get('subject', '')
        message = data.get('message', '')
        mailbox_id = data.get('mailbox_id')
        start_time_str = data.get('start_time')  # ISO datetime string
        duration = data.get('duration', 24)  # Total duration in hours
        duration = data.get('duration', 24)  # Total duration in hours
        # send_interval will be calculated later if not provided, defaulting to 5 initially
        send_interval = data.get('send_interval', 5)
        
        # Validate required fields
        if not subject:
            return jsonify({'error': 'Subject is required'}), 400
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        if not recipients or not isinstance(recipients, list):
            return jsonify({'error': 'At least one recipient is required'}), 400
        if not mailbox_id:
            return jsonify({'error': 'Mailbox ID is required'}), 400
        
        # Check database availability
        if not db_manager or db_manager.db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        campaigns_collection = db_manager.db['email_campaigns']
        tracking_collection = db_manager.db['email_tracking']
        
        # Get mailbox
        from bson import ObjectId
        try:
            mailbox = db_manager.mailboxes_collection.find_one({'_id': ObjectId(mailbox_id)})
        except:
            return jsonify({'error': 'Invalid mailbox ID'}), 400
        
        if not mailbox:
            return jsonify({'error': 'Mailbox not found'}), 404
        
        sender_email = mailbox.get('email')
        
        # Parse start_time
        from datetime import timedelta
        if start_time_str:
            try:
                # Handle potential 'Z' or other formats
                if start_time_str.endswith('Z'):
                    start_time_str = start_time_str.replace('Z', '+00:00')
                start_datetime = datetime.fromisoformat(start_time_str)
                print(f"📅 Parsed start_time: {start_time_str} -> {start_datetime}")
            except Exception as parse_error:
                print(f"⚠️  Failed to parse start_time '{start_time_str}': {parse_error}")
                return jsonify({'error': f"Invalid start_time format: {start_time_str}"}), 400
        else:
            start_datetime = datetime.now(timezone.utc)
        
        # Ensure start_datetime is timezone-aware
        if start_datetime.tzinfo is None:
            # If no timezone info, assume it's UTC
            print(f"⚠️  start_time has no timezone, assuming UTC")
            start_datetime = start_datetime.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC for consistent handling
            start_datetime = start_datetime.astimezone(timezone.utc)
        
        # Debug: Show current time vs start time
        now_utc = datetime.now(timezone.utc)
        print(f"🕐 Current UTC time: {now_utc.isoformat()}")
        print(f"🕐 Campaign start UTC: {start_datetime.isoformat()}")
        if start_datetime > now_utc:
            wait_minutes = (start_datetime - now_utc).total_seconds() / 60
            print(f"⏰ Campaign will start in {wait_minutes:.1f} minutes")
        else:
            print(f"⚡ Start time is in the past. Resetting start_time to NOW to respect duration.")
            start_datetime = now_utc

        
        # Check for campaign time conflicts
        conflicts = check_campaign_conflicts(clerk_user_id, start_datetime, duration)
        if conflicts:
            return jsonify({
                'error': 'Campaign time conflict detected',
                'conflicts': conflicts,
                'message': f'This campaign would overlap with {len(conflicts)} existing campaign(s). Please choose a different start time or duration.',
                'suggestion': f'Try scheduling after {conflicts[0]["end_time"]}'
            }), 409  # 409 Conflict
        
        # Validate recipients
        valid_recipients = []
        invalid_recipients = []
        unsubscribed_recipients = []
        
        # Check for unsubscribed emails
        unsubscribed_emails = set()
        unsubscribed_docs = tracking_collection.find({'unsubscribed': True})
        for doc in unsubscribed_docs:
            unsubscribed_emails.add(doc.get('recipient_email', '').lower())
        
        for recipient in recipients:
            email = recipient.get('email', '').strip()
            if not validate_email(email):
                invalid_recipients.append(email)
                continue
            
            if email.lower() in unsubscribed_emails:
                unsubscribed_recipients.append(recipient)
                continue
            
            valid_recipients.append(recipient)
        
        
        if not valid_recipients:
            return jsonify({
                'error': 'No valid recipients',
                'invalid_recipients': invalid_recipients,
                'unsubscribed_recipients': unsubscribed_recipients
            }), 400

        # Calculate optimal interval based on duration
        try:
            # Ensure numbers
            duration_val = float(duration)
            send_interval_val = float(send_interval)
            
            if len(valid_recipients) > 1:
                total_minutes = duration_val * 60
                # Use 95% of duration to be safe
                effective_minutes = total_minutes * 0.95
                calculated_interval = effective_minutes / len(valid_recipients)
                
                # If the calculated interval is significantly larger than the provided interval,
                # it means the user likely wants to spread the emails over the duration.
                # We'll use the larger of the two to ensure we fill the duration.
                if calculated_interval > send_interval_val:
                    print(f"⚖️  Adjusting interval: User={send_interval_val}m, Calculated={calculated_interval:.2f}m. Using Calculated.")
                    send_interval = calculated_interval
                else:
                    print(f"⚖️  Using user interval: {send_interval_val}m (Calculated was {calculated_interval:.2f}m)")
                    
                # Ensure minimum interval
                min_interval = 1.0
                if hasattr(Config, 'MIN_DELAY_BETWEEN_EMAILS'):
                    min_interval = float(Config.MIN_DELAY_BETWEEN_EMAILS)
                
                send_interval = max(send_interval, min_interval)
            
        except Exception as e:
            print(f"⚠️ Error calculating optimal interval: {e}")

        
        # Create campaign
        campaign_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc)
        
        campaign_data = {
            'campaign_id': campaign_id,
            'clerk_user_id': clerk_user_id,
            'user_email': sender_email,
            'sender_email': sender_email,
            'mailbox_id': str(mailbox['_id']),
            'subject': subject,
            'message': message,
            'start_time': start_datetime,
            'duration': duration,
            'send_interval': send_interval,
            'total_recipients': len(valid_recipients),
            'sent_count': 0,
            'failed_count': 0,
            'bounce_count': 0,
            'status': 'scheduled' if start_datetime > now_utc else 'active',
            'created_at': now_utc,
            'updated_at': now_utc,
            'recipients': valid_recipients  # Store recipients for server restart recovery
        }
        
        try:
            campaigns_collection.insert_one(campaign_data)
            print(f"✅ Campaign created: {campaign_id} for user {clerk_user_id}")
        except Exception as insert_error:
            print(f"❌ Error inserting campaign: {insert_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Failed to create campaign: {str(insert_error)}'}), 500
        
        # Start background thread for email sending
        thread = threading.Thread(
            target=send_emails_in_background,
            args=(
                campaign_id,
                str(mailbox['_id']),
                sender_email,
                subject,
                message,
                valid_recipients,
                start_datetime,
                duration,
                send_interval,
                clerk_user_id
            ),
            daemon=True  # Thread dies when main program exits
        )
        thread.start()
        
        print(f"🚀 Background thread started for campaign {campaign_id}")
        
        # Return immediately (don't wait for emails to send)
        return jsonify({
            'success': True,
            'campaign_id': campaign_id,
            'message': f'Campaign created successfully. Emails will be sent in background.',
            'status': 'scheduled' if start_datetime > now_utc else 'active',
            'total_recipients': len(valid_recipients),
            'start_time': start_datetime.isoformat(),
            'duration': duration,
            'send_interval': send_interval,
            'invalid_recipients': invalid_recipients,
            'unsubscribed_count': len(unsubscribed_recipients)
        })
        
    except Exception as error:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ Error in send_mail endpoint: {error}")
        print(f"📋 Full traceback:\n{error_traceback}")
        return jsonify({
            'error': f'Error creating campaign: {str(error)}',
            'details': str(error) if str(error) else 'Unknown error'
        }), 500

# ==================== END CAMPAIGN CREATION ENDPOINT ====================

# ==================== CAMPAIGN STATUS ENDPOINT ====================

@main_bp.route('/api/campaigns/<campaign_id>/status', methods=['GET'])
def get_campaign_status(campaign_id):
    """Get real-time campaign status"""
    try:
        if not db_manager or db_manager.db is None:
            return jsonify({'error': 'Database not available'}), 503
        
        campaigns_collection = db_manager.db['email_campaigns']
        campaign = campaigns_collection.find_one({'campaign_id': campaign_id})
        
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Calculate if campaign is active
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        start_time = campaign.get('start_time')
        duration = campaign.get('duration', 24)
        
        is_active = False
        if start_time:
            # Ensure timezone-aware
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            
            end_time = start_time + timedelta(hours=duration)
            is_active = now >= start_time and now <= end_time
        
        total_recipients = campaign.get('total_recipients', 0)
        sent_count = campaign.get('sent_count', 0)
        progress = (sent_count / total_recipients * 100) if total_recipients > 0 else 0
        
        return jsonify({
            'campaign_id': campaign_id,
            'status': campaign.get('status'),
            'is_active': is_active,
            'sent_count': sent_count,
            'failed_count': campaign.get('failed_count', 0),
            'total_recipients': total_recipients,
            'progress': round(progress, 2),
            'start_time': start_time.isoformat() if start_time else None,
            'duration': duration,
            'send_interval': campaign.get('send_interval', 5)
        })
        
    except Exception as error:
        print(f"Error getting campaign status: {error}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(error)}), 500

# ==================== END CAMPAIGN STATUS ENDPOINT ====================


@main_bp.route('/api/campaigns/<campaign_id>/stop', methods=['POST', 'OPTIONS'])
def stop_campaign(campaign_id):
    """Stop a running campaign"""
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = jsonify({})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Requested-With,X-Clerk-User-Id')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
    
    try:
        if not db_manager or db_manager.db is None:
            return jsonify({'error': 'Database not available'}), 503

        campaigns_collection = db_manager.db['email_campaigns']
        
        # Update status to stopped
        result = campaigns_collection.update_one(
            {'campaign_id': campaign_id},
            {'$set': {
                'status': 'stopped',
                'updated_at': datetime.now(timezone.utc)
            }}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Campaign not found'}), 404
            
        print(f"🛑 Campaign {campaign_id} stopped via API")
        return jsonify({'success': True, 'message': 'Campaign stopped'})
        
    except Exception as e:
        print(f"❌ Error stopping campaign: {e}")
        return jsonify({'error': str(e)}), 500

print("✅ Stop campaign endpoint registered at /api/campaigns/<campaign_id>/stop")

# Register blueprint
app.register_blueprint(main_bp)

# Cleanup on shutdown
# import atexit
# atexit.register(lambda: background_service.stop())

if __name__ == "__main__":
    print("🚀 Starting Email Warmup Application (Version: Fix-Scheduling-v2)")
    print(f"📊 Database: {Config.DATABASE_NAME}")
    print(f"🔧 Port: {Config.PORT}")
    if db_manager and db_manager.db is not None:
        print("✓ Database connection: Active")
    else:
        print("⚠️  Database connection: Not available")
    # print(f"🔄 Background service: {'Started' if background_service.running else 'Stopped'}")
    print("-" * 50)
    
    # Disable reloader on Windows to avoid socket errors
    import sys
    use_reloader = sys.platform != 'win32'
    
    app.run(debug=True, host='0.0.0.0', port=Config.PORT, use_reloader=use_reloader)