# Additional database methods for new schema
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from bson import ObjectId
import logging

class DatabaseMethods:
    """Additional methods for the new database schema"""
    
    def __init__(self, db_manager):
        self.db = db_manager.db
        self.users_collection = db_manager.users_collection
        self.mailboxes_collection = db_manager.mailboxes_collection
        self.campaigns_collection = db_manager.campaigns_collection
        self.campaign_metrics_collection = db_manager.campaign_metrics_collection
        self.email_tracking_collection = db_manager.email_tracking_collection
        self.logger = db_manager.logger
    
    # ==================== USER INFORMATION METHODS ====================
    
    def create_user(self, user_name: str, login_id: str, password: str = None, 
                   email: str = None, clerk_user_id: str = None) -> Dict:
        """Create a new user in user_information_table
        IMPORTANT: Always checks for existing user first to ensure same user_id is used
        """
        try:
            # CRITICAL: Check if user already exists by clerk_user_id
            # This ensures the same user_id is always used for the same Clerk user
            if clerk_user_id:
                existing_user = self.get_user_by_clerk_id(clerk_user_id)
                if existing_user:
                    # User already exists - return existing user (preserves same user_id)
                    self.logger.info(f"User already exists (by clerk_user_id): {clerk_user_id} - User ID: {existing_user.get('user_id')}")
                    return {'success': True, 'user': existing_user}
            
            # Also check by login_id to prevent duplicates
            if login_id:
                existing_by_login = self.users_collection.find_one({
                    'login_id': login_id,
                    'is_active': True
                })
                if existing_by_login:
                    existing_by_login['user_id'] = str(existing_by_login['_id'])
                    existing_by_login.pop('_id', None)
                    existing_by_login.pop('password', None)
                    self.logger.info(f"User already exists (by login_id): {login_id} - User ID: {existing_by_login.get('user_id')}")
                    return {'success': True, 'user': existing_by_login}
            
            # User doesn't exist - create new user
            user_data = {
                'user_name': user_name,
                'login_id': login_id,
                'email': email,
                'clerk_user_id': clerk_user_id,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'is_active': True
            }
            
            if password:
                from werkzeug.security import generate_password_hash
                user_data['password'] = generate_password_hash(password)
            
            result = self.users_collection.insert_one(user_data)
            
            if result.inserted_id:
                user_data['user_id'] = str(result.inserted_id)
                user_data.pop('password', None)
                user_data.pop('_id', None)
                self.logger.info(f"User created: {user_name} ({login_id}) - User ID: {user_data['user_id']}")
                return {'success': True, 'user': user_data}
            else:
                return {'success': False, 'error': 'Failed to create user'}
                
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by user_id"""
        try:
            user = self.users_collection.find_one({'_id': ObjectId(user_id), 'is_active': True})
            if user:
                user['user_id'] = str(user['_id'])
                user.pop('_id', None)
                user.pop('password', None)
            return user
        except Exception as e:
            self.logger.error(f"Error getting user by ID: {e}")
            return None
    
    def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[Dict]:
        """Get user by Clerk user ID"""
        try:
            if self.users_collection is None:
                self.logger.error("users_collection is None - database not connected")
                return None
            user = self.users_collection.find_one({'clerk_user_id': clerk_user_id, 'is_active': True})
            if user:
                user['user_id'] = str(user['_id'])
                user.pop('_id', None)
                user.pop('password', None)
            return user
        except Exception as e:
            self.logger.error(f"Error getting user by Clerk ID: {e}")
            return None
    
    # ==================== MAILBOX METHODS ====================
    
    def create_mailbox(self, user_id: str, email: str, access_token: str, 
                      password: str = None, provider: str = 'outlook',
                      user_profile: Dict = None, is_primary: bool = False,
                      refresh_token: str = None) -> Dict:
        """Create a new mailbox in linkbox_box_table"""
        try:
            if self.mailboxes_collection is None:
                self.logger.error("mailboxes_collection is None - database not connected")
                return {'success': False, 'error': 'Database not available'}
            
            # Check if user exists
            user = self.get_user_by_id(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Check if mailbox already exists for this user (regardless of is_active status)
            # This handles re-adding previously disconnected mailboxes
            # Note: Multiple users CAN have the same email (different user_id), but same user cannot have duplicate emails
            existing = self.mailboxes_collection.find_one({
                'user_id': ObjectId(user_id),
                'email': email
            })
            
            if existing:
                self.logger.info(f"Found existing mailbox for user {user_id} and email {email}, is_active: {existing.get('is_active', 'unknown')}")
            
            if existing:
                # Check if there's already an active primary mailbox for this user
                existing_primary = self.mailboxes_collection.find_one({
                    'user_id': ObjectId(user_id),
                    'is_active': True,
                    'is_primary': True,
                    '_id': {'$ne': existing['_id']}  # Exclude the current mailbox
                })
                
                # Count active mailboxes (excluding the one we're reactivating)
                active_mailbox_count = self.mailboxes_collection.count_documents({
                    'user_id': ObjectId(user_id),
                    'is_active': True,
                    '_id': {'$ne': existing['_id']}
                })
                
                # Only set as primary if:
                # 1. There's no other active primary mailbox, AND
                # 2. Either it was explicitly requested OR there are no other active mailboxes
                should_be_primary = False
                if not existing_primary:
                    # No other primary exists, so set this as primary if:
                    # - Explicitly requested, OR
                    # - This is the only active mailbox (or will be after reactivation)
                    should_be_primary = is_primary or (active_mailbox_count == 0)
                
                # Update existing mailbox (reactivate if it was disconnected)
                mailbox_data = {
                    'access_token': access_token,
                    'password': password,
                    'user_profile': user_profile,
                    'is_active': True,  # Reactivate if it was disconnected
                    'status': 'active',
                    'is_primary': should_be_primary,  # Only set as primary if no other primary exists
                    'updated_at': datetime.now(timezone.utc),
                    'last_used': datetime.now(timezone.utc)
                }
                # Update refresh_token if provided
                if refresh_token:
                    mailbox_data['refresh_token'] = refresh_token
                # Only update provider if it's not set
                if provider and not existing.get('provider'):
                    mailbox_data['provider'] = provider
                
                # If we're setting this as primary, unset primary on all other mailboxes
                if should_be_primary:
                    self.mailboxes_collection.update_many(
                        {
                            'user_id': ObjectId(user_id),
                            'is_active': True,
                            '_id': {'$ne': existing['_id']}
                        },
                        {
                            '$set': {
                                'is_primary': False,
                                'updated_at': datetime.now(timezone.utc)
                            }
                        }
                    )
                    self.logger.info(f"Unset primary flag on other mailboxes for user {user_id}")
                
                result = self.mailboxes_collection.update_one(
                    {'_id': existing['_id']},
                    {'$set': mailbox_data}
                )
                mailbox_id = str(existing['_id'])
                if existing.get('is_active'):
                    self.logger.info(f"Updated existing active mailbox {email} for user {user_id}, is_primary: {should_be_primary}")
                else:
                    self.logger.info(f"Reactivated previously disconnected mailbox {email} for user {user_id}, is_primary: {should_be_primary}")
            else:
                # Check if this is the first mailbox (set as primary)
                mailbox_count = self.mailboxes_collection.count_documents({
                    'user_id': ObjectId(user_id),
                    'is_active': True
                })
                
                # Check if there's already a primary mailbox
                existing_primary = self.mailboxes_collection.find_one({
                    'user_id': ObjectId(user_id),
                    'is_active': True,
                    'is_primary': True
                })
                
                # Only set as primary if:
                # 1. Explicitly requested, OR
                # 2. This is the first active mailbox (no other active mailboxes exist)
                # AND there's no existing primary
                should_be_primary = False
                if not existing_primary:
                    should_be_primary = is_primary or (mailbox_count == 0)
                
                mailbox_data = {
                    'user_id': ObjectId(user_id),
                    'email': email,
                    'access_token': access_token,
                    'password': password,
                    'provider': provider,
                    'user_profile': user_profile or {},
                    'is_primary': should_be_primary,
                    'is_active': True,
                    'status': 'active',
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc),
                    'last_used': datetime.now(timezone.utc)
                }
                # Add refresh_token if provided
                if refresh_token:
                    mailbox_data['refresh_token'] = refresh_token
                
                # If we're setting this as primary, unset primary on all other mailboxes
                if should_be_primary:
                    self.mailboxes_collection.update_many(
                        {
                            'user_id': ObjectId(user_id),
                            'is_active': True
                        },
                        {
                            '$set': {
                                'is_primary': False,
                                'updated_at': datetime.now(timezone.utc)
                            }
                        }
                    )
                    self.logger.info(f"Unset primary flag on other mailboxes before creating new primary for user {user_id}")
                
                try:
                    result = self.mailboxes_collection.insert_one(mailbox_data)
                    mailbox_id = str(result.inserted_id)
                    self.logger.info(f"Created new mailbox {email} for user {user_id}, is_primary: {should_be_primary}")
                except Exception as insert_error:
                    # Handle duplicate key error - might happen if mailbox was just deleted
                    # Try to find and update it instead
                    if 'E11000' in str(insert_error) or 'duplicate key' in str(insert_error).lower():
                        self.logger.warning(f"Duplicate key error, attempting to find and update mailbox: {insert_error}")
                        existing_duplicate = self.mailboxes_collection.find_one({
                            'user_id': ObjectId(user_id),
                            'email': email
                        })
                        if existing_duplicate:
                            # Update the existing one with the same logic as above
                            update_result = self.mailboxes_collection.update_one(
                                {'_id': existing_duplicate['_id']},
                                {'$set': mailbox_data}
                            )
                            mailbox_id = str(existing_duplicate['_id'])
                            self.logger.info(f"Updated mailbox after duplicate key error: {email} for user {user_id}, is_primary: {should_be_primary}")
                        else:
                            raise insert_error
                    else:
                        raise insert_error
            
            return {'success': True, 'mailbox_id': mailbox_id}
            
        except Exception as e:
            self.logger.error(f"Error creating mailbox: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_mailboxes_by_user_id(self, user_id: str) -> List[Dict]:
        """Get all mailboxes for a user"""
        try:
            mailboxes = list(self.mailboxes_collection.find({
                'user_id': ObjectId(user_id),
                'is_active': True
            }))
            
            for mailbox in mailboxes:
                mailbox['mailbox_id'] = str(mailbox['_id'])
                mailbox.pop('_id', None)
                mailbox.pop('password', None)
                mailbox.pop('access_token', None)  # Don't expose tokens
            
            return mailboxes
        except Exception as e:
            self.logger.error(f"Error getting mailboxes: {e}")
            return []
    
    def get_mailbox_by_id(self, mailbox_id: str) -> Optional[Dict]:
        """Get mailbox by mailbox_id"""
        try:
            mailbox = self.mailboxes_collection.find_one({
                '_id': ObjectId(mailbox_id),
                'is_active': True
            })
            
            if mailbox:
                mailbox['mailbox_id'] = str(mailbox['_id'])
                mailbox.pop('_id', None)
                # Keep access_token for internal use, but don't expose password
            
            return mailbox
        except Exception as e:
            self.logger.error(f"Error getting mailbox: {e}")
            return None
    
    # ==================== CAMPAIGN CREATION METHODS ====================
    
    def create_campaign(self, user_id: str, mailbox_id: str, campaign_name: str,
                       subject: str, message: str, duration: int, start_time: datetime,
                       total_recipients: int = 0) -> Dict:
        """Create a new campaign in campaign_creation_table"""
        try:
            import uuid
            
            import uuid
            campaign_id = str(uuid.uuid4())
            end_time = start_time + timedelta(hours=duration)
            
            campaign_data = {
                'campaign_id': campaign_id,
                'user_id': ObjectId(user_id),
                'mailbox_id': ObjectId(mailbox_id),
                'campaign_name': campaign_name,
                'subject': subject,
                'message': message,
                'duration': duration,
                'start_time': start_time,
                'end_time': end_time,
                'status': 'scheduled' if start_time > datetime.now(timezone.utc) else 'active',
                'total_recipients': total_recipients,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'created_by': ObjectId(user_id)
            }
            
            result = self.campaigns_collection.insert_one(campaign_data)
            
            if result.inserted_id:
                # Create initial campaign metrics
                self.create_campaign_metrics(campaign_id, user_id, mailbox_id)
                
                self.logger.info(f"Campaign created: {campaign_name} ({campaign_id})")
                return {'success': True, 'campaign_id': campaign_id}
            else:
                return {'success': False, 'error': 'Failed to create campaign'}
                
        except Exception as e:
            self.logger.error(f"Error creating campaign: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_campaigns_by_user_id(self, user_id: str, status: str = None) -> List[Dict]:
        """Get all campaigns for a user"""
        try:
            query = {'user_id': ObjectId(user_id)}
            if status:
                query['status'] = status
            
            campaigns = list(self.campaigns_collection.find(query).sort('created_at', -1))
            
            for campaign in campaigns:
                campaign['user_id'] = str(campaign['user_id'])
                campaign['mailbox_id'] = str(campaign['mailbox_id'])
                campaign['created_by'] = str(campaign.get('created_by', ''))
                campaign.pop('_id', None)
            
            return campaigns
        except Exception as e:
            self.logger.error(f"Error getting campaigns: {e}")
            return []
    
    def get_campaign_by_id(self, campaign_id: str) -> Optional[Dict]:
        """Get campaign by campaign_id"""
        try:
            campaign = self.campaigns_collection.find_one({'campaign_id': campaign_id})
            
            if campaign:
                campaign['user_id'] = str(campaign['user_id'])
                campaign['mailbox_id'] = str(campaign['mailbox_id'])
                campaign['created_by'] = str(campaign.get('created_by', ''))
                campaign.pop('_id', None)
            
            return campaign
        except Exception as e:
            self.logger.error(f"Error getting campaign: {e}")
            return None
    
    # ==================== CAMPAIGN MATRIX METHODS ====================
    
    def create_campaign_metrics(self, campaign_id: str, user_id: str, mailbox_id: str) -> bool:
        """Create initial campaign metrics record"""
        try:
            metrics_data = {
                'campaign_id': campaign_id,
                'user_id': ObjectId(user_id),
                'mailbox_id': ObjectId(mailbox_id),
                'total_sent': 0,
                'total_delivered': 0,
                'total_opened': 0,
                'total_clicks': 0,
                'total_bounced': 0,
                'total_replied': 0,
                'total_unsubscribed': 0,
                'open_rate': 0,
                'click_rate': 0,
                'bounce_rate': 0,
                'reply_rate': 0,
                'created_at': datetime.now(timezone.utc),
                'last_updated': datetime.now(timezone.utc)
            }
            
            result = self.campaign_metrics_collection.insert_one(metrics_data)
            return bool(result.inserted_id)
            
        except Exception as e:
            self.logger.error(f"Error creating campaign metrics: {e}")
            return False
    
    def update_campaign_metrics(self, campaign_id: str, metrics: Dict) -> bool:
        """Update campaign metrics"""
        try:
            update_data = {
                **metrics,
                'last_updated': datetime.now(timezone.utc)
            }
            
            result = self.campaign_metrics_collection.update_one(
                {'campaign_id': campaign_id},
                {'$set': update_data}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            self.logger.error(f"Error updating campaign metrics: {e}")
            return False
    
    def get_campaign_metrics(self, campaign_id: str) -> Optional[Dict]:
        """Get campaign metrics by campaign_id"""
        try:
            metrics = self.campaign_metrics_collection.find_one({'campaign_id': campaign_id})
            
            if metrics:
                metrics['user_id'] = str(metrics['user_id'])
                metrics['mailbox_id'] = str(metrics['mailbox_id'])
                metrics.pop('_id', None)
            
            return metrics
        except Exception as e:
            self.logger.error(f"Error getting campaign metrics: {e}")
            return None
    
    def get_all_campaign_metrics_by_user_id(self, user_id: str) -> List[Dict]:
        """Get all campaign metrics for a user"""
        try:
            metrics_list = list(self.campaign_metrics_collection.find({
                'user_id': ObjectId(user_id)
            }))
            
            for metrics in metrics_list:
                metrics['user_id'] = str(metrics['user_id'])
                metrics['mailbox_id'] = str(metrics['mailbox_id'])
                metrics.pop('_id', None)
            
            return metrics_list
        except Exception as e:
            self.logger.error(f"Error getting campaign metrics: {e}")
            return []

