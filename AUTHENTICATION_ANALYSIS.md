# Authentication & Mailbox Flow Analysis

## Current State Analysis

### 1. Authentication Methods (Currently Mixed)

**Current Implementation:**
- **Clerk Authentication**: Partially integrated in `src/app/page.tsx` and `src/app/login/page.tsx`
  - Clerk is set up in `src/components/Providers.tsx` with `ClerkProvider`
  - `src/app/page.tsx` has Clerk sign-in UI but also has username/password login
  - `src/app/login/page.tsx` redirects to Microsoft OAuth (`/signin` endpoint)
  
- **Microsoft OAuth**: Primary authentication method
  - Backend handles OAuth flow in `backend_code/app.py` (`/signin`, `/callback`)
  - Session-based authentication using Flask sessions
  - Stores user profile and access tokens in session

- **Username/Password**: Also available
  - Backend has user registration/login in `backend_code/database.py`
  - Uses MongoDB `users` collection

**Issues:**
- Multiple authentication methods causing confusion
- Clerk is not the primary authentication method
- Campaigns are fetched based on `user_email` from session, not Clerk user ID
- No clear integration between Clerk user and database accounts

---

### 2. Account Information & Campaign Fetching

**Current Implementation:**
- Campaigns are fetched in `backend_code/app.py` at `/api/campaigns/user`
- Uses `user_email` from session: `user_profile.get('mail')` or `user_profile.get('userPrincipalName')`
- Campaigns stored in `email_campaigns` collection with `user_email` field
- Query: `campaigns_collection.find({'user_email': user_email})`

**Issues:**
- No Clerk user ID mapping to campaigns
- If user logs in via Clerk, there's no way to link their Clerk ID to their email campaigns
- Database doesn't have a `clerk_user_id` field in campaigns or user collections

---

### 3. Linked Mailbox Functionality

**Current Implementation:**
- Email accounts page: `src/app/(main)/email-accounts/page.tsx`
- Shows linked mailboxes from `warm_up_emails_table` collection
- Accounts are linked by `owner_email` field
- Primary account is marked with `is_primary: true`
- Clicking on a mailbox doesn't navigate to a different page - it just shows account details

**Issues:**
- No separate page for using a specific mailbox to send mail
- No navigation when clicking on a linked mailbox
- Mail sending endpoint (`/send-mail`) uses session's `user_profile`, not a selected mailbox

---

### 4. Mail Sending Logic

**Current Implementation:**
- Mail sending endpoint: `backend_code/app.py` `/send-mail`
- Uses `access_token` and `sender_email` from session:
  ```python
  access_token = session.get('access_token')
  sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
  ```
- Does NOT check for primary account or use selected mailbox
- Always uses the logged-in user's email from session

**Issues:**
- Doesn't respect primary account setting
- Doesn't allow selecting a specific mailbox to send from
- No way to send mail from a different mailbox than the logged-in account

---

## Required Changes

### 1. Make Clerk the Primary Authentication Method

**Frontend Changes:**
- `src/app/login/page.tsx`: Should use Clerk's `<SignIn />` component exclusively
- `src/app/page.tsx`: Remove username/password form, use Clerk only
- After Clerk authentication, fetch/create user record in database with Clerk user ID

**Backend Changes:**
- Create endpoint to sync Clerk user with database
- Store `clerk_user_id` in database (both `users` collection and `warm_up_emails_table`)
- Modify session/auth to use Clerk user ID instead of email-based auth

**Database Schema Changes:**
- Add `clerk_user_id` field to:
  - `users` collection
  - `warm_up_emails_table` (as `owner_clerk_id`)
  - `email_campaigns` collection (as `clerk_user_id`)

---

### 2. Fetch Campaigns Based on Clerk Account

**Backend Changes:**
- Modify `/api/campaigns/user` endpoint:
  - Accept Clerk user ID from request (via header or session)
  - Query campaigns by `clerk_user_id` instead of `user_email`
  - Fallback to `user_email` for backward compatibility

**Frontend Changes:**
- `src/api/hooks.ts`: Update `useCampaigns` hook to send Clerk user ID
- Ensure Clerk user context is available when fetching campaigns

---

### 3. Create Separate Page for Mailbox Usage

**New Page:**
- Create `src/app/(main)/mailbox/[id]/page.tsx`
- This page should:
  - Display mailbox information
  - Show campaigns sent from this mailbox
  - Allow sending new campaigns using this mailbox
  - Show mailbox-specific analytics

**Email Accounts Page Changes:**
- `src/app/(main)/email-accounts/page.tsx`:
  - Make mailbox cards clickable
  - Navigate to `/mailbox/[account_id]` when clicked
  - Add "Use this mailbox" button/link

---

### 4. Use Primary/Selected Mailbox for Sending Mail

**Backend Changes:**
- Modify `/send-mail` endpoint:
  - Accept optional `mailbox_id` parameter
  - If `mailbox_id` provided, use that mailbox's access token and email
  - If not provided, find primary mailbox for the Clerk user
  - Query: Find mailbox where `owner_clerk_id` = current user AND `is_primary` = true
  - Use that mailbox's `access_token` and `email` for sending

**Frontend Changes:**
- Campaign creation/sending:
  - Allow selecting mailbox before sending
  - Default to primary mailbox
  - Pass `mailbox_id` to send-mail endpoint

**Database Query Example:**
```python
# Find primary mailbox for Clerk user
primary_mailbox = db_manager.warmup_emails_collection.find_one({
    'owner_clerk_id': clerk_user_id,
    'is_primary': True,
    'is_active': True
})

# Use primary mailbox's access token
access_token = primary_mailbox['access_token']
sender_email = primary_mailbox['email']
```

---

## Implementation Priority

### Phase 1: Clerk Integration (High Priority)
1. Update login page to use Clerk only
2. Create Clerk user sync endpoint
3. Add `clerk_user_id` to database collections
4. Update authentication context to use Clerk

### Phase 2: Campaign Fetching (High Priority)
1. Update campaigns endpoint to use Clerk user ID
2. Migrate existing campaigns to include `clerk_user_id`
3. Update frontend hooks to send Clerk user ID

### Phase 3: Mailbox Page (Medium Priority)
1. Create mailbox detail page
2. Add navigation from email accounts page
3. Display mailbox-specific campaigns

### Phase 4: Mail Sending with Mailbox Selection (High Priority)
1. Update send-mail endpoint to use primary/selected mailbox
2. Add mailbox selection UI in campaign creation
3. Store which mailbox was used for each campaign

---

## Database Migration Required

```javascript
// Add clerk_user_id to existing documents
db.email_campaigns.updateMany(
  {},
  { $set: { clerk_user_id: null } }
);

db.warm_up_emails_table.updateMany(
  {},
  { $set: { owner_clerk_id: null } }
);

db.users.updateMany(
  {},
  { $set: { clerk_user_id: null } }
);
```

---

## Key Files to Modify

1. **Frontend:**
   - `src/app/login/page.tsx` - Use Clerk only
   - `src/app/page.tsx` - Remove username/password, use Clerk
   - `src/app/(main)/email-accounts/page.tsx` - Add navigation to mailbox page
   - `src/app/(main)/mailbox/[id]/page.tsx` - **NEW FILE** - Mailbox detail page
   - `src/contexts/AuthContext.tsx` - Integrate Clerk user ID
   - `src/api/hooks.ts` - Update to use Clerk user ID

2. **Backend:**
   - `backend_code/app.py` - Update endpoints to use Clerk user ID
   - `backend_code/database.py` - Add methods to handle Clerk user ID
   - `backend_code/auth.py` - May need updates for Clerk integration

---

## Testing Checklist

- [ ] Clerk login works and redirects to dashboard
- [ ] User profile is synced with database including Clerk ID
- [ ] Campaigns are fetched based on Clerk user ID
- [ ] Clicking on linked mailbox navigates to mailbox page
- [ ] Mailbox page shows campaigns for that mailbox
- [ ] Sending mail uses primary mailbox by default
- [ ] Sending mail can use selected mailbox
- [ ] Primary mailbox setting works correctly
- [ ] Multiple mailboxes can be linked to one Clerk account

