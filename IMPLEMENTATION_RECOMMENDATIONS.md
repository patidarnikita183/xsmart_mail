# Implementation Recommendations for Clerk Authentication & Mailbox Flow

## Summary

Your codebase currently has **three authentication methods** (Clerk, Microsoft OAuth, Username/Password) which creates confusion. The mail sending system doesn't use the primary mailbox setting, and there's no way to navigate to a mailbox-specific page.

---

## Key Issues Found

### 1. **Authentication is Mixed**
- Clerk is partially integrated but not the primary method
- Login page redirects to Microsoft OAuth instead of using Clerk
- Campaigns are fetched by `user_email` from session, not Clerk user ID
- No link between Clerk user and database records

### 2. **Campaigns Not Linked to Clerk Users**
- Campaigns stored with `user_email` field only
- No `clerk_user_id` field in `email_campaigns` collection
- When user logs in via Clerk, their campaigns can't be found

### 3. **Mailbox Clicking Doesn't Navigate**
- Email accounts page shows mailboxes but they're not clickable
- No separate page exists for mailbox details
- No way to see campaigns sent from a specific mailbox

### 4. **Mail Sending Doesn't Use Primary Mailbox**
- `/send-mail` endpoint always uses session's `user_profile`
- Ignores `is_primary` flag in database
- Can't send from a selected mailbox

---

## Required Changes

### Phase 1: Make Clerk the Primary Authentication ✅

**File: `src/app/login/page.tsx`**
```tsx
// CURRENT: Redirects to Microsoft OAuth
// CHANGE TO: Use Clerk SignIn component
import { SignIn } from "@clerk/nextjs";

export default function LoginPage() {
    return (
        <div className="min-h-screen flex items-center justify-center">
            <SignIn />
        </div>
    );
}
```

**File: `src/app/page.tsx`**
- Remove username/password form
- Use Clerk SignIn component only
- After Clerk auth, sync user to database

**New Backend Endpoint: `/api/sync-clerk-user`**
```python
@main_bp.route('/api/sync-clerk-user', methods=['POST'])
def sync_clerk_user():
    """Sync Clerk user with database"""
    data = request.get_json()
    clerk_user_id = data.get('clerk_user_id')
    email = data.get('email')
    
    # Create or update user record
    user = db_manager.users_collection.find_one_and_update(
        {'clerk_user_id': clerk_user_id},
        {
            '$set': {
                'clerk_user_id': clerk_user_id,
                'email': email,
                'updated_at': datetime.now(timezone.utc)
            },
            '$setOnInsert': {
                'created_at': datetime.now(timezone.utc)
            }
        },
        upsert=True,
        return_document=True
    )
    
    return jsonify({'success': True, 'user_id': str(user['_id'])})
```

**Database Migration:**
```python
# Add clerk_user_id to collections
db.email_campaigns.updateMany({}, {'$set': {'clerk_user_id': None}})
db.warm_up_emails_table.updateMany({}, {'$set': {'owner_clerk_id': None}})
db.users.updateMany({}, {'$set': {'clerk_user_id': None}})
```

---

### Phase 2: Fetch Campaigns by Clerk User ID ✅

**File: `backend_code/app.py` - `/api/campaigns/user` endpoint**

**CURRENT:**
```python
user_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
campaigns = list(campaigns_collection.find({'user_email': user_email}))
```

**CHANGE TO:**
```python
# Get Clerk user ID from request header or session
clerk_user_id = request.headers.get('X-Clerk-User-Id') or session.get('clerk_user_id')

if clerk_user_id:
    # Query by Clerk user ID
    campaigns = list(campaigns_collection.find({'clerk_user_id': clerk_user_id}))
else:
    # Fallback to email for backward compatibility
    user_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
    campaigns = list(campaigns_collection.find({'user_email': user_email}))
```

**File: `src/api/hooks.ts` - `useCampaigns` hook**

**CHANGE TO:**
```typescript
export function useCampaigns(filters?: {...}) {
    const { user } = useUser(); // Clerk user
    
    return useQuery({
        queryKey: ['campaigns', filters, user?.id],
        queryFn: async () => {
            const params = new URLSearchParams();
            // ... existing params ...
            
            const { data } = await apiClient.get(`/api/campaigns/user?${params.toString()}`, {
                headers: {
                    'X-Clerk-User-Id': user?.id || ''
                }
            });
            return data;
        },
        enabled: !!user?.id, // Only fetch when Clerk user is available
    });
}
```

---

### Phase 3: Create Mailbox Detail Page ✅

**New File: `src/app/(main)/mailbox/[id]/page.tsx`**
```tsx
"use client";

import { useParams, useRouter } from "next/navigation";
import { useEmailAccount, useMailboxCampaigns } from "@/api/hooks";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Mail, ArrowLeft, Send } from "lucide-react";

export default function MailboxPage() {
    const params = useParams();
    const router = useRouter();
    const accountId = params.id as string;
    
    const { data: account, isLoading } = useEmailAccount(accountId);
    const { data: campaigns } = useMailboxCampaigns(accountId);
    
    if (isLoading) return <div>Loading...</div>;
    if (!account) return <div>Mailbox not found</div>;
    
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4">
                <Button variant="ghost" onClick={() => router.push('/email-accounts')}>
                    <ArrowLeft className="h-4 w-4 mr-2" />
                    Back to Mailboxes
                </Button>
                <div>
                    <h1 className="text-2xl font-bold">{account.email}</h1>
                    <p className="text-muted-foreground">Mailbox Details</p>
                </div>
            </div>
            
            <Card>
                <CardHeader>
                    <CardTitle>Mailbox Information</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        <p><strong>Email:</strong> {account.email}</p>
                        <p><strong>Provider:</strong> {account.provider}</p>
                        <p><strong>Status:</strong> {account.status}</p>
                        {account.is_primary && (
                            <p className="text-blue-600">✓ Primary Mailbox</p>
                        )}
                    </div>
                </CardContent>
            </Card>
            
            <Card>
                <CardHeader>
                    <CardTitle>Campaigns from this Mailbox</CardTitle>
                </CardHeader>
                <CardContent>
                    {/* Display campaigns sent from this mailbox */}
                    {campaigns?.map(campaign => (
                        <div key={campaign.campaign_id}>
                            {campaign.subject}
                        </div>
                    ))}
                </CardContent>
            </Card>
            
            <Button onClick={() => router.push(`/campaigns/new?mailbox_id=${accountId}`)}>
                <Send className="h-4 w-4 mr-2" />
                Send Campaign from this Mailbox
            </Button>
        </div>
    );
}
```

**File: `src/app/(main)/email-accounts/page.tsx`**

**ADD Navigation:**
```tsx
// In the mailbox card, make it clickable
<Card 
    key={account.id} 
    className={`cursor-pointer hover:shadow-lg transition-shadow ${account.is_primary ? 'ring-2 ring-blue-500' : ''}`}
    onClick={() => router.push(`/mailbox/${account.id}`)}
>
    {/* ... existing card content ... */}
</Card>
```

**New API Hook: `src/api/hooks.ts`**
```typescript
export function useEmailAccount(accountId: string) {
    return useQuery({
        queryKey: ['emailAccount', accountId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/email-accounts/${accountId}`);
            return data.account;
        },
    });
}

export function useMailboxCampaigns(accountId: string) {
    return useQuery({
        queryKey: ['mailboxCampaigns', accountId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/api/mailbox/${accountId}/campaigns`);
            return data.campaigns;
        },
    });
}
```

**New Backend Endpoint: `/api/mailbox/<account_id>/campaigns`**
```python
@main_bp.route('/api/mailbox/<account_id>/campaigns', methods=['GET'])
def get_mailbox_campaigns(account_id):
    """Get campaigns sent from a specific mailbox"""
    try:
        from bson import ObjectId
        
        # Get mailbox info
        mailbox = db_manager.warmup_emails_collection.find_one({'_id': ObjectId(account_id)})
        if not mailbox:
            return jsonify({'error': 'Mailbox not found'}), 404
        
        mailbox_email = mailbox['email']
        
        # Get campaigns sent from this mailbox
        campaigns = list(db_manager.db['email_campaigns'].find({
            'sender_email': mailbox_email
        }).sort('created_at', -1))
        
        return jsonify({
            'success': True,
            'campaigns': [format_campaign(c) for c in campaigns]
        })
    except Exception as error:
        return jsonify({'error': str(error)}), 500
```

---

### Phase 4: Use Primary/Selected Mailbox for Sending ✅

**File: `backend_code/app.py` - `/send-mail` endpoint**

**CURRENT:**
```python
access_token = session.get('access_token')
sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
```

**CHANGE TO:**
```python
@main_bp.route('/send-mail', methods=['POST'])
def send_mail():
    """Send email with tracking support - uses primary or selected mailbox"""
    try:
        # Get Clerk user ID
        clerk_user_id = request.headers.get('X-Clerk-User-Id') or session.get('clerk_user_id')
        
        # Get mailbox_id from request (optional)
        mailbox_id = request.json.get('mailbox_id') if request.is_json else None
        
        # Determine which mailbox to use
        mailbox = None
        
        if mailbox_id:
            # Use specified mailbox
            from bson import ObjectId
            mailbox = db_manager.warmup_emails_collection.find_one({
                '_id': ObjectId(mailbox_id),
                'owner_clerk_id': clerk_user_id,  # Ensure user owns this mailbox
                'is_active': True
            })
        elif clerk_user_id:
            # Use primary mailbox for this Clerk user
            mailbox = db_manager.warmup_emails_collection.find_one({
                'owner_clerk_id': clerk_user_id,
                'is_primary': True,
                'is_active': True
            })
        
        if not mailbox:
            # Fallback to session-based auth (for backward compatibility)
            access_token = session.get('access_token')
            user_profile = session.get('user_profile')
            if not access_token or not user_profile:
                return jsonify({'error': 'No mailbox available for sending'}), 400
            sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
        else:
            # Use mailbox credentials
            access_token = mailbox['access_token']
            sender_email = mailbox['email']
        
        # ... rest of send-mail logic using access_token and sender_email ...
        
        # Store which mailbox was used in campaign
        campaign_data = {
            'campaign_id': campaign_id,
            'clerk_user_id': clerk_user_id,  # Store Clerk user ID
            'sender_email': sender_email,
            'mailbox_id': str(mailbox['_id']) if mailbox else None,  # Store mailbox ID
            # ... rest of campaign data ...
        }
```

**File: `src/app/(main)/campaigns/new/page.tsx`**

**ADD Mailbox Selection:**
```tsx
// Add mailbox selection step
const [selectedMailboxId, setSelectedMailboxId] = useState<string | null>(null);
const { data: accounts } = useEmailAccounts();

// In ReviewStep or before sending
const campaignPayload = {
    subject: data.subject,
    message: data.body,
    recipients: recipients,
    mailbox_id: selectedMailboxId || accounts?.accounts?.find(a => a.is_primary)?.id
};
```

**File: `src/api/hooks.ts` - `useCreateCampaign`**

**UPDATE:**
```typescript
export function useCreateCampaign() {
    const queryClient = useQueryClient();
    const { user } = useUser(); // Clerk user
    
    return useMutation({
        mutationFn: async (campaignData: any) => {
            const { data } = await apiClient.post('/send-mail', campaignData, {
                headers: {
                    'X-Clerk-User-Id': user?.id || ''
                }
            });
            return data;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['campaigns'] });
        },
    });
}
```

---

## Implementation Checklist

### Frontend Changes
- [ ] Update `src/app/login/page.tsx` to use Clerk only
- [ ] Update `src/app/page.tsx` to remove username/password form
- [ ] Add Clerk user sync after authentication
- [ ] Update `src/api/hooks.ts` to send Clerk user ID in requests
- [ ] Create `src/app/(main)/mailbox/[id]/page.tsx`
- [ ] Make mailboxes clickable in `src/app/(main)/email-accounts/page.tsx`
- [ ] Add mailbox selection to campaign creation
- [ ] Update `src/contexts/AuthContext.tsx` to include Clerk user ID

### Backend Changes
- [ ] Create `/api/sync-clerk-user` endpoint
- [ ] Update `/api/campaigns/user` to use Clerk user ID
- [ ] Update `/send-mail` to use primary/selected mailbox
- [ ] Create `/api/mailbox/<id>/campaigns` endpoint
- [ ] Add `clerk_user_id` field to campaign creation
- [ ] Add `mailbox_id` field to campaign tracking
- [ ] Update `/api/email-accounts` to support Clerk user ID

### Database Changes
- [ ] Add `clerk_user_id` to `email_campaigns` collection
- [ ] Add `owner_clerk_id` to `warm_up_emails_table` collection
- [ ] Add `clerk_user_id` to `users` collection
- [ ] Migrate existing data (link emails to Clerk users)

---

## Testing Steps

1. **Clerk Login:**
   - Login via Clerk
   - Verify user is synced to database
   - Verify redirect to dashboard

2. **Campaign Fetching:**
   - Create campaign while logged in via Clerk
   - Verify campaign has `clerk_user_id`
   - Verify campaigns page shows your campaigns

3. **Mailbox Navigation:**
   - Go to email accounts page
   - Click on a mailbox
   - Verify navigation to mailbox detail page
   - Verify mailbox campaigns are shown

4. **Mail Sending:**
   - Create campaign without selecting mailbox (should use primary)
   - Create campaign with selected mailbox
   - Verify emails are sent from correct mailbox
   - Verify campaign records which mailbox was used

---

## Migration Strategy

1. **Phase 1:** Add `clerk_user_id` fields (nullable) to all collections
2. **Phase 2:** Update code to write `clerk_user_id` for new records
3. **Phase 3:** Migrate existing data (link emails to Clerk users manually or via script)
4. **Phase 4:** Make `clerk_user_id` required for new records
5. **Phase 5:** Remove email-based fallback (optional, for future)

---

## Notes

- Keep email-based fallback for backward compatibility during migration
- Primary mailbox should be automatically set when first mailbox is added
- If no primary mailbox exists, show error when trying to send
- Clerk user ID should be sent in request headers for all authenticated requests

