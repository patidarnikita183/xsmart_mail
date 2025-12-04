import sys

# Read the file
with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "return jsonify({" after "user_id_str = str(user_id)"
insert_index = None
for i in range(2230, 2250):
    if i < len(lines) and 'user_id_str = str(user_id)' in lines[i]:
        # Find the next return jsonify
        for j in range(i+1, min(i+15, len(lines))):
            if 'return jsonify({' in lines[j]:
                insert_index = j
                break
        break

if insert_index is None:
    print("Could not find insertion point")
    sys.exit(1)

print(f"Found insertion point at line {insert_index + 1}")

# Code to insert
new_code = """        
        # AUTO-LOAD PRIMARY MAILBOX CREDENTIALS INTO SESSION
        # After login, if user has mailboxes, automatically load the primary one into session
        primary_mailbox = None
        if db_manager and db_manager.mailboxes_collection:
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
        
"""

# Insert the new code
lines.insert(insert_index, new_code)

# Also update the return statement to include mailbox info
# Find the closing brace of the return statement
for i in range(insert_index + 1, min(insert_index + 50, len(lines))):
    if lines[i].strip() == '})':
        # Replace with updated return
        lines[i] = """            'has_primary_mailbox': primary_mailbox is not None,
            'primary_mailbox_email': primary_mailbox.get('email') if primary_mailbox else None
        })
"""
        break

# Write back
with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Successfully inserted auto-load logic")
