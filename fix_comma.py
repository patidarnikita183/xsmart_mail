with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the missing comma
content = content.replace(
    "            'clerk_user_id': clerk_user_id\n            'has_primary_mailbox'",
    "            'clerk_user_id': clerk_user_id,\n            'has_primary_mailbox'"
)

with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed missing comma in return statement")
