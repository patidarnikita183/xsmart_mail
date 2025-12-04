# database.py
from pymongo import MongoClient
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    def __init__(self, connection_string: str, database_name: str):
        # Initialize logger FIRST (before any try/except)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize all collections as None first
        self.client = None
        self.db = None
        self.users_collection = None
        self.mailboxes_collection = None
        self.campaigns_collection = None
        self.campaign_metrics_collection = None
        self.email_tracking_collection = None
        self.warmup_emails_collection = None
        
        try:
            # Add connection options for better reliability
            connection_options = {
                'serverSelectionTimeoutMS': 10000,  # 10 second timeout
                'connectTimeoutMS': 10000,
                'socketTimeoutMS': 10000,
                'retryWrites': True,
                'retryReads': True,
                'maxPoolSize': 10,
                'minPoolSize': 1,
            }
            
            # Try to connect with options
            if not connection_string:
                raise ValueError("MongoDB connection string is not provided")
            
            self.client = MongoClient(connection_string, **connection_options)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[database_name]
            self.logger.info(f"✓ Connected to MongoDB: {database_name}")
            
            # ==================== COLLECTIONS ====================
            # 1. User Information Table
            self.users_collection = self.db['user_information_table']
            
            # 2. Linkbox Box Table (Mailboxes)
            self.mailboxes_collection = self.db['linkbox_box_table']
            
            # 3. Campaign Creation Table
            self.campaigns_collection = self.db['campaign_creation_table']
            
            # 4. Campaign Matrix Table (Metrics)
            self.campaign_metrics_collection = self.db['campaign_matrix']
            
            # 5. Email Tracking Table (for individual email tracking)
            self.email_tracking_collection = self.db['email_tracking']
            
            # Legacy collections (for backward compatibility)
            self.warmup_emails_collection = self.db['warm_up_emails_table']
            
            # ==================== CREATE INDEXES ====================
            try:
                # User Information Table indexes
                self.users_collection.create_index("login_id", unique=True, sparse=True)
                self.users_collection.create_index("email", unique=True, sparse=True)
                self.users_collection.create_index("clerk_user_id", unique=True, sparse=True)
                self.users_collection.create_index("is_active")
                
                # Mailboxes Table indexes
                self.mailboxes_collection.create_index("user_id")
                self.mailboxes_collection.create_index("email")
                self.mailboxes_collection.create_index([("user_id", 1), ("email", 1)], unique=True)
                self.mailboxes_collection.create_index("is_primary")
                self.mailboxes_collection.create_index("is_active")
                
                # Campaign Creation Table indexes
                self.campaigns_collection.create_index("campaign_id", unique=True)
                self.campaigns_collection.create_index("user_id")
                self.campaigns_collection.create_index("mailbox_id")
                self.campaigns_collection.create_index("status")
                self.campaigns_collection.create_index("start_time")
                self.campaigns_collection.create_index([("user_id", 1), ("status", 1)])
                
                # Campaign Matrix Table indexes
                self.campaign_metrics_collection.create_index("campaign_id", unique=True)
                self.campaign_metrics_collection.create_index("user_id")
                self.campaign_metrics_collection.create_index("mailbox_id")
                self.campaign_metrics_collection.create_index([("campaign_id", 1), ("user_id", 1)])
                
                # Email Tracking Table indexes
                self.email_tracking_collection.create_index("tracking_id", unique=True)
                self.email_tracking_collection.create_index("campaign_id")
                self.email_tracking_collection.create_index("user_id")
                self.email_tracking_collection.create_index("recipient_email")
                self.email_tracking_collection.create_index("sent_at")
                
                # Legacy indexes (for backward compatibility)
                self.warmup_emails_collection.create_index("email", unique=True)
                self.warmup_emails_collection.create_index("is_active")
                
                self.logger.info("✓ Database indexes created successfully")
            except Exception as e:
                self.logger.warning(f"Some indexes may not have been created: {e}")
                
        except Exception as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            self.logger.warning("Application will continue but database operations may fail")
            # Collections remain None - will be checked before use
    
    def save_user_tokens(self, email: str, access_token: str, user_profile: Dict, 
                        user_type: str = 'sender', is_new_account: bool = False, 
                        owner_email: str = None, owner_clerk_id: str = None) -> bool:
        """Save user access tokens and profile to database
        
        Args:
            email: The email of the Microsoft account being added
            access_token: OAuth access token
            user_profile: Microsoft user profile
            user_type: 'sender' or 'target'
            is_new_account: True if adding a new account, False if login
            owner_email: The email of the logged-in user who owns this account (for multiple accounts)
        """
        if self.db is None or self.warmup_emails_collection is None:
            self.logger.error("Database not available - cannot save user tokens")
            return False
            
        try:
            user_data = {
                'email': email,  # The Microsoft account email
                'access_token': access_token,
                'user_profile': user_profile,
                'user_type': user_type,  # 'sender' or 'target'
                'is_active': True,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'last_used': datetime.now(timezone.utc)
            }
            
            if is_new_account and owner_email:
                # Adding a new account - track the owner
                user_data['owner_email'] = owner_email
                # IMPORTANT: Set owner_clerk_id if provided (for Clerk users)
                if owner_clerk_id:
                    user_data['owner_clerk_id'] = owner_clerk_id
                
                # Check if this account already exists for this owner
                # Build query based on whether we have clerk_id or email
                if owner_clerk_id:
                    existing = self.warmup_emails_collection.find_one({
                        'email': email,
                        'owner_clerk_id': owner_clerk_id,
                        'is_active': True
                    })
                    query_filter = {'email': email, 'owner_clerk_id': owner_clerk_id, 'is_active': True}
                else:
                    existing = self.warmup_emails_collection.find_one({
                        'email': email,
                        'owner_email': owner_email,
                        'is_active': True
                    })
                    query_filter = {'email': email, 'owner_email': owner_email, 'is_active': True}
                
                if existing:
                    # Account already exists, update it
                    result = self.warmup_emails_collection.update_one(
                        query_filter,
                        {'$set': user_data}
                    )
                    self.logger.info(f"Updated existing account {email} for owner {owner_clerk_id or owner_email}")
                else:
                    # New account, insert it
                    # Check if this will be the first account for this owner (set as primary)
                    if owner_clerk_id:
                        account_count = self.warmup_emails_collection.count_documents({
                            'owner_clerk_id': owner_clerk_id,
                            'is_active': True
                        })
                    else:
                        account_count = self.warmup_emails_collection.count_documents({
                            'owner_email': owner_email,
                            'is_active': True
                        })
                    if account_count == 0:
                        user_data['is_primary'] = True
                    
                    result = self.warmup_emails_collection.insert_one(user_data)
                    self.logger.info(f"Added new account {email} for owner {owner_clerk_id or owner_email}")
            else:
                # Login flow - update or insert user data
                # For login, the email is both the account and owner
                user_data['owner_email'] = email
                result = self.warmup_emails_collection.update_one(
                    {'email': email},
                    {'$set': user_data},
                    upsert=True
                )
                self.logger.info(f"User data saved for {email} as {user_type}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving user tokens for {email}: {e}")
            return False
    
    def get_user_tokens(self, email: str) -> Optional[Dict]:
        """Get user access tokens from database"""
        if self.db is None or self.warmup_emails_collection is None:
            return None
        try:
            user_data = self.warmup_emails_collection.find_one(
                {'email': email, 'is_active': True}
            )
            return user_data
        except Exception as e:
            self.logger.error(f"Error retrieving user tokens for {email}: {e}")
            return None
    
    def get_all_active_users(self, user_type: str = "sender",email:str = '') -> List[Dict]:
        """Get all active users, optionally filtered by type"""
        if self.db is None or self.warmup_emails_collection is None:
            return []
        try:
            query = {'is_active': True}
            # if user_type:
            #     query['user_type'] = user_type
            if email:
                query['email'] = {'$ne': email}
            users = list(self.warmup_emails_collection.find(query))

            return users
        except Exception as e:
            self.logger.error(f"Error retrieving active users: {e}")
            return []
    
    def update_last_used(self, email: str) -> bool:
        """Update last used timestamp for user"""
        if self.db is None or self.warmup_emails_collection is None:
            return False
        try:
            result = self.warmup_emails_collection.update_one(
                {'email': email},
                {'$set': {'last_used': datetime.now(timezone.utc)}}
            )
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Error updating last used for {email}: {e}")
            return False
    
    def save_warmup_campaign_log(self, campaign_data: Dict) -> bool:
        """Save warmup campaign execution log"""
        if self.db is None:
            return False
        try:
            campaign_logs = self.db['warmup_campaign_logs']
            campaign_data['created_at'] = datetime.now(timezone.utc)
            result = campaign_logs.insert_one(campaign_data)
            return bool(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Error saving campaign log: {e}")
            return False
    
    # User authentication methods
    def register_user(self, username: str, password: str, email: str, display_name: str = None) -> Dict:
        """Register a new user with username and password"""
        if self.db is None or self.users_collection is None:
            return {'success': False, 'error': 'Database not available'}
        try:
            # Check if username already exists
            if self.users_collection.find_one({'username': username}):
                return {'success': False, 'error': 'Username already exists'}
            
            # Check if email already exists
            if self.users_collection.find_one({'email': email}):
                return {'success': False, 'error': 'Email already registered'}
            
            # Hash the password
            hashed_password = generate_password_hash(password)
            
            # Create user document
            user_data = {
                'username': username,
                'password': hashed_password,
                'email': email,
                'display_name': display_name or username,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'is_active': True
            }
            
            # Insert user
            result = self.users_collection.insert_one(user_data)
            
            if result.inserted_id:
                self.logger.info(f"User registered: {username} ({email})")
                # Return user data without password
                user_data.pop('password', None)
                user_data['id'] = str(result.inserted_id)
                return {'success': True, 'user': user_data}
            else:
                return {'success': False, 'error': 'Failed to create user'}
                
        except Exception as e:
            self.logger.error(f"Error registering user {username}: {e}")
            return {'success': False, 'error': str(e)}
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """Authenticate user with username and password"""
        if self.db is None or self.users_collection is None:
            return {'success': False, 'error': 'Database not available'}
        try:
            # Find user by username
            user = self.users_collection.find_one({'username': username, 'is_active': True})
            
            if not user:
                return {'success': False, 'error': 'Invalid username or password'}
            
            # Check password
            if not check_password_hash(user['password'], password):
                return {'success': False, 'error': 'Invalid username or password'}
            
            # Update last login
            self.users_collection.update_one(
                {'username': username},
                {'$set': {'last_login': datetime.now(timezone.utc), 'updated_at': datetime.now(timezone.utc)}}
            )
            
            # Return user data without password
            user_data = {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'display_name': user.get('display_name', user['username']),
                'created_at': user.get('created_at'),
                'userType': 'sender'  # Default user type
            }
            
            self.logger.info(f"User authenticated: {username}")
            return {'success': True, 'user': user_data}
            
        except Exception as e:
            self.logger.error(f"Error authenticating user {username}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        if self.db is None or self.users_collection is None:
            return None
        try:
            user = self.users_collection.find_one({'username': username, 'is_active': True})
            if user:
                user['id'] = str(user['_id'])
                user.pop('password', None)
                user.pop('_id', None)
            return user
        except Exception as e:
            self.logger.error(f"Error getting user {username}: {e}")
            return None
    
    # Initialize additional methods
    def _init_methods(self):
        """Initialize DatabaseMethods helper"""
        if not hasattr(self, '_methods'):
            from database_methods import DatabaseMethods
            self._methods = DatabaseMethods(self)
        return self._methods
    
    # Delegate methods to DatabaseMethods
    def create_user(self, *args, **kwargs):
        return self._init_methods().create_user(*args, **kwargs)
    
    def get_user_by_id(self, *args, **kwargs):
        return self._init_methods().get_user_by_id(*args, **kwargs)
    
    def get_user_by_clerk_id(self, *args, **kwargs):
        return self._init_methods().get_user_by_clerk_id(*args, **kwargs)
    
    def create_mailbox(self, *args, **kwargs):
        return self._init_methods().create_mailbox(*args, **kwargs)
    
    def get_mailboxes_by_user_id(self, *args, **kwargs):
        return self._init_methods().get_mailboxes_by_user_id(*args, **kwargs)
    
    def get_mailbox_by_id(self, *args, **kwargs):
        return self._init_methods().get_mailbox_by_id(*args, **kwargs)
    
    def create_campaign(self, *args, **kwargs):
        return self._init_methods().create_campaign(*args, **kwargs)
    
    def get_campaigns_by_user_id(self, *args, **kwargs):
        return self._init_methods().get_campaigns_by_user_id(*args, **kwargs)
    
    def get_campaign_by_id(self, *args, **kwargs):
        return self._init_methods().get_campaign_by_id(*args, **kwargs)
    
    def create_campaign_metrics(self, *args, **kwargs):
        return self._init_methods().create_campaign_metrics(*args, **kwargs)
    
    def update_campaign_metrics(self, *args, **kwargs):
        return self._init_methods().update_campaign_metrics(*args, **kwargs)
    
    def get_campaign_metrics(self, *args, **kwargs):
        return self._init_methods().get_campaign_metrics(*args, **kwargs)
    
    def get_all_campaign_metrics_by_user_id(self, *args, **kwargs):
        return self._init_methods().get_all_campaign_metrics_by_user_id(*args, **kwargs)
