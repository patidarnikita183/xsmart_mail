"""
Script to add new endpoints to app.py
Run this script to automatically integrate the new endpoints
"""

import os

# Read the new endpoints
with open('new_endpoints.py', 'r', encoding='utf-8') as f:
    new_endpoints_content = f.read()

# Remove the comment header (first 3 lines)
new_endpoints_lines = new_endpoints_content.split('\n')[3:]  # Skip first 3 comment lines
new_endpoints_to_add = '\n'.join(new_endpoints_lines)

# Read the current app.py
with open('app.py', 'r', encoding='utf-8') as f:
    app_content = f.read()

# Find the insertion point - before @app.after_request
insertion_marker = '@app.after_request\ndef after_request(response):'

if insertion_marker in app_content:
    # Split at the insertion point
    parts = app_content.split(insertion_marker)
    
    # Insert new endpoints
    new_content = parts[0] + '\n' + new_endpoints_to_add + '\n\n# Register blueprint\napp.register_blueprint(main_bp)\n\n@app.after_request\ndef after_request(response):' + parts[1]
    
    # Write back to app.py
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Successfully added new endpoints to app.py!")
    print("📝 Added 5 new endpoints:")
    print("   - GET /api/email-accounts")
    print("   - DELETE /api/email-accounts/<id>")
    print("   - POST /api/email-accounts/<id>/set-primary")
    print("   - GET /api/campaigns/user")
    print("   - GET /api/analytics/dashboard")
    print("\n🔄 Please restart the backend server:")
    print("   python app.py")
else:
    print("❌ Could not find insertion point in app.py")
    print("Please manually add the endpoints from new_endpoints.py")
