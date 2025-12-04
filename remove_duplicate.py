with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Remove lines 99-111 (the duplicate add_account function)
# Line numbers are 1-indexed in the editor, but 0-indexed in Python
del lines[98:111]  # This removes lines 99-111 inclusive

with open(r'c:\Users\Dell\Downloads\xsmart_mail_send_antigravity\backend_code\app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Successfully removed duplicate add_account function")
