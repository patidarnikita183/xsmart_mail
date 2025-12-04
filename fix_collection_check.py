with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the collection check in the auto-load logic
content = content.replace(
    'if db_manager and db_manager.mailboxes_collection:',
    'if db_manager and db_manager.mailboxes_collection is not None:'
)

with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed collection boolean check")
