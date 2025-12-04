# Database Schema Design

## 1. User Information Table (`users` collection)

**Purpose**: Store user account information

**Fields**:
- `user_id` (ObjectId, Primary Key)
- `user_name` (String, Required) - Display name
- `login_id` (String, Unique, Required) - Email or username for login
- `password` (String, Hashed) - Hashed password (if using password auth)
- `clerk_user_id` (String, Unique, Optional) - Clerk authentication ID
- `email` (String, Optional) - Email address
- `created_at` (DateTime, Required)
- `updated_at` (DateTime, Required)
- `is_active` (Boolean, Default: true)
- `last_login` (DateTime, Optional)

**Indexes**:
- `login_id` (unique)
- `clerk_user_id` (unique, sparse)
- `email` (unique, sparse)

---

## 2. Linkbox Box Table (`mailboxes` collection)

**Purpose**: Store linked email accounts/mailboxes

**Fields**:
- `mailbox_id` (ObjectId, Primary Key)
- `user_id` (ObjectId, Foreign Key -> users.user_id, Required) - Owner of this mailbox
- `email` (String, Required) - Mailbox email address
- `password` (String, Encrypted) - Mailbox password/access token
- `access_token` (String, Encrypted) - OAuth access token
- `refresh_token` (String, Encrypted, Optional) - OAuth refresh token
- `provider` (String, Required) - 'outlook', 'gmail', etc.
- `user_profile` (Object, Optional) - Provider user profile data
- `is_primary` (Boolean, Default: false) - Primary mailbox flag
- `is_active` (Boolean, Default: true)
- `status` (String, Default: 'active') - 'active', 'inactive', 'error'
- `last_used` (DateTime, Optional)
- `created_at` (DateTime, Required)
- `updated_at` (DateTime, Required)

**Indexes**:
- `user_id` (indexed)
- `email` (indexed)
- `user_id + email` (compound unique)
- `is_primary` (indexed)
- `is_active` (indexed)

---

## 3. Campaign Creation Table (`campaigns` collection)

**Purpose**: Store campaign creation and configuration

**Fields**:
- `campaign_id` (String, Primary Key, Unique) - UUID
- `user_id` (ObjectId, Foreign Key -> users.user_id, Required)
- `mailbox_id` (ObjectId, Foreign Key -> mailboxes.mailbox_id, Required) - Which mailbox to use
- `campaign_name` (String, Required) - Campaign name/subject
- `subject` (String, Required) - Email subject
- `message` (String, Required) - Email body/content
- `duration` (Number, Required) - Duration in hours
- `start_time` (DateTime, Required) - When campaign should start
- `end_time` (DateTime, Computed) - start_time + duration
- `status` (String, Default: 'scheduled') - 'scheduled', 'active', 'completed', 'paused', 'cancelled'
- `total_recipients` (Number, Default: 0)
- `created_at` (DateTime, Required)
- `updated_at` (DateTime, Required)
- `created_by` (ObjectId, Foreign Key -> users.user_id) - User who created

**Indexes**:
- `campaign_id` (unique)
- `user_id` (indexed)
- `mailbox_id` (indexed)
- `status` (indexed)
- `start_time` (indexed)
- `user_id + status` (compound index)

---

## 4. Campaign Matrix Table (`campaign_metrics` collection)

**Purpose**: Store campaign performance metrics and analytics

**Fields**:
- `metric_id` (ObjectId, Primary Key)
- `campaign_id` (String, Foreign Key -> campaigns.campaign_id, Required)
- `user_id` (ObjectId, Foreign Key -> users.user_id, Required)
- `mailbox_id` (ObjectId, Foreign Key -> mailboxes.mailbox_id, Required)
- `total_sent` (Number, Default: 0) - Successfully sent emails
- `total_delivered` (Number, Default: 0) - Delivered emails
- `total_opened` (Number, Default: 0) - Unique opens
- `total_clicks` (Number, Default: 0) - Unique clicks
- `total_bounced` (Number, Default: 0) - Bounced emails
- `total_replied` (Number, Default: 0) - Replies received
- `total_unsubscribed` (Number, Default: 0) - Unsubscribes
- `open_rate` (Number, Default: 0) - Percentage
- `click_rate` (Number, Default: 0) - Percentage
- `bounce_rate` (Number, Default: 0) - Percentage
- `reply_rate` (Number, Default: 0) - Percentage
- `last_updated` (DateTime, Required) - Last metrics update
- `created_at` (DateTime, Required)

**Indexes**:
- `campaign_id` (unique, indexed)
- `user_id` (indexed)
- `mailbox_id` (indexed)
- `campaign_id + user_id` (compound index)

---

## 5. Email Tracking Table (`email_tracking` collection)

**Purpose**: Track individual email sends and interactions

**Fields**:
- `tracking_id` (String, Primary Key, Unique) - UUID
- `campaign_id` (String, Foreign Key -> campaigns.campaign_id, Required)
- `user_id` (ObjectId, Foreign Key -> users.user_id, Required)
- `mailbox_id` (ObjectId, Foreign Key -> mailboxes.mailbox_id, Required)
- `sender_email` (String, Required)
- `recipient_email` (String, Required)
- `recipient_name` (String, Optional)
- `subject` (String, Required)
- `message` (String, Required)
- `sent_at` (DateTime, Required)
- `delivered_at` (DateTime, Optional)
- `opened_at` (DateTime, Optional) - First open
- `opens` (Number, Default: 0) - Total open count
- `clicked_at` (DateTime, Optional) - First click
- `clicks` (Number, Default: 0) - Total click count
- `replied_at` (DateTime, Optional)
- `replies` (Number, Default: 0)
- `bounced` (Boolean, Default: false)
- `bounce_reason` (String, Optional)
- `unsubscribed` (Boolean, Default: false)
- `unsubscribed_at` (DateTime, Optional)
- `created_at` (DateTime, Required)

**Indexes**:
- `tracking_id` (unique)
- `campaign_id` (indexed)
- `user_id` (indexed)
- `recipient_email` (indexed)
- `sent_at` (indexed)
- `campaign_id + recipient_email` (compound index)

---

## Relationships

1. **User → Mailboxes**: One-to-Many (One user can have multiple mailboxes)
2. **User → Campaigns**: One-to-Many (One user can create multiple campaigns)
3. **Mailbox → Campaigns**: One-to-Many (One mailbox can be used for multiple campaigns)
4. **Campaign → Campaign Metrics**: One-to-One (Each campaign has one metrics record)
5. **Campaign → Email Tracking**: One-to-Many (Each campaign has many email tracking records)

---

## Migration Notes

- Existing `warm_up_emails_table` → `mailboxes`
- Existing `email_campaigns` → `campaigns`
- Existing `email_tracking` → `email_tracking` (keep as is)
- New collection: `campaign_metrics` (aggregated metrics)

