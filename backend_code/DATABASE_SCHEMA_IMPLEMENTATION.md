# Database Schema Implementation

## Overview

The database has been restructured according to the new schema requirements:

## Collections

### 1. `user_information_table`
**Purpose**: Store user account information

**Fields**:
- `_id` (ObjectId) - Primary key
- `user_id` (String) - Alias for `_id`
- `user_name` (String) - Display name
- `login_id` (String, Unique) - Email or username for login
- `password` (String, Hashed) - Optional, for password-based auth
- `email` (String, Optional) - Email address
- `clerk_user_id` (String, Unique, Optional) - Clerk authentication ID
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `is_active` (Boolean)
- `last_login` (DateTime, Optional)

### 2. `linkbox_box_table`
**Purpose**: Store linked email accounts/mailboxes

**Fields**:
- `_id` (ObjectId) - Primary key
- `mailbox_id` (String) - Alias for `_id`
- `user_id` (ObjectId, Foreign Key) - Owner user ID
- `email` (String) - Mailbox email address
- `password` (String, Encrypted) - Optional mailbox password
- `access_token` (String, Encrypted) - OAuth access token
- `provider` (String) - 'outlook', 'gmail', etc.
- `user_profile` (Object) - Provider user profile
- `is_primary` (Boolean) - Primary mailbox flag
- `is_active` (Boolean)
- `status` (String) - 'active', 'inactive', 'error'
- `last_used` (DateTime)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### 3. `campaign_creation_table`
**Purpose**: Store campaign creation and configuration

**Fields**:
- `_id` (ObjectId) - Primary key
- `campaign_id` (String, Unique) - UUID
- `user_id` (ObjectId, Foreign Key) - User who created campaign
- `mailbox_id` (ObjectId, Foreign Key) - Mailbox to use for sending
- `campaign_name` (String) - Campaign name/subject
- `subject` (String) - Email subject
- `message` (String) - Email body
- `duration` (Number) - Duration in hours
- `start_time` (DateTime) - When campaign starts
- `end_time` (DateTime) - When campaign ends (computed)
- `status` (String) - 'scheduled', 'active', 'completed', 'paused', 'cancelled'
- `total_recipients` (Number)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `created_by` (ObjectId, Foreign Key) - User who created

### 4. `campaign_matrix`
**Purpose**: Store campaign performance metrics

**Fields**:
- `_id` (ObjectId) - Primary key
- `campaign_id` (String, Unique, Foreign Key) - Links to campaign_creation_table
- `user_id` (ObjectId, Foreign Key) - User who owns campaign
- `mailbox_id` (ObjectId, Foreign Key) - Mailbox used
- `total_sent` (Number)
- `total_delivered` (Number)
- `total_opened` (Number)
- `total_clicks` (Number)
- `total_bounced` (Number)
- `total_replied` (Number)
- `total_unsubscribed` (Number)
- `open_rate` (Number) - Percentage
- `click_rate` (Number) - Percentage
- `bounce_rate` (Number) - Percentage
- `reply_rate` (Number) - Percentage
- `created_at` (DateTime)
- `last_updated` (DateTime)

### 5. `email_tracking`
**Purpose**: Track individual email sends (existing collection, kept as is)

## Migration Notes

1. **Existing Data**: The old collections (`warm_up_emails_table`, `email_campaigns`) are still accessible for backward compatibility
2. **New Data**: All new operations should use the new collections
3. **User Creation**: When a Clerk user logs in, they are automatically created in `user_information_table`
4. **Mailbox Linking**: When a mailbox is linked, it's stored in `linkbox_box_table` with the `user_id`
5. **Campaign Creation**: Campaigns are stored in `campaign_creation_table` with both `user_id` and `mailbox_id`
6. **Campaign Metrics**: Metrics are automatically created when a campaign is created

## Usage Examples

### Create User
```python
result = db_manager.create_user(
    user_name="John Doe",
    login_id="john@example.com",
    email="john@example.com",
    clerk_user_id="user_abc123"
)
```

### Create Mailbox
```python
result = db_manager.create_mailbox(
    user_id="user_id_string",
    email="mailbox@example.com",
    access_token="token_here",
    provider="outlook"
)
```

### Create Campaign
```python
result = db_manager.create_campaign(
    user_id="user_id_string",
    mailbox_id="mailbox_id_string",
    campaign_name="Q1 Outreach",
    subject="Hello",
    message="Email body",
    duration=24,
    start_time=datetime.now(timezone.utc),
    total_recipients=100
)
```

### Get Campaign Metrics
```python
metrics = db_manager.get_campaign_metrics("campaign_id_string")
```

## Indexes Created

All collections have appropriate indexes for:
- Unique constraints (login_id, email, campaign_id, etc.)
- Foreign key lookups (user_id, mailbox_id)
- Status filtering
- Time-based queries (start_time, created_at)

