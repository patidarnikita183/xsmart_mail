# main.py
import re
import threading
from flask import Flask, Blueprint, render_template, redirect, url_for, session, jsonify, request
from auth import get_auth_url, get_access_token, make_graph_request
from enhanced_email_warmup import EnhancedEmailWarmupService
from database import DatabaseManager
from background_service import BackgroundWarmupService
from config import Config

# Initialize Flask app
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# Initialize database and services
db_manager = DatabaseManager(Config.MONGO_URL, Config.DATABASE_NAME)
warmup_service = EnhancedEmailWarmupService(db_manager)
background_service = BackgroundWarmupService()

# Start background service
background_service.start()

main_bp = Blueprint('main', __name__)

def validate_email(email):
    """Validate email address format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@main_bp.route('/')
def index():
    return redirect('/app')

@main_bp.route('/app')
def main_app():
    """Main application page"""
    user_profile = session.get('user_profile')
    return render_template("frontend.html", user_profile=user_profile)

@main_bp.route('/signin')
def signin():
    """Redirect to OAuth signin"""
    auth_url = get_auth_url()
    return redirect(auth_url)

@main_bp.route('/signin-target')
def signin_target():
    """Redirect to OAuth signin for target users"""
    auth_url = get_auth_url()
    session['user_type'] = 'target'  # Mark this as target user signin
    return redirect(auth_url)

@main_bp.route('/callback')
def oauth_callback():
    """Handle OAuth callback and save user data to database"""
    if 'code' not in request.args:
        return redirect(url_for('main.main_app'))
    global ACCESS_TOKEN, USER_PROFILE
    auth_code = request.args.get('code')
    token_response = get_access_token(auth_code)
    
    if token_response and 'access_token' in token_response:
        access_token = token_response['access_token']
        
        # Get user profile
        user_profile = make_graph_request('/me', access_token)
        
        if 'error' not in user_profile:
            user_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
            user_type = session.get('user_type', 'sender')  # Default to sender
            
            # Save user data to database
            success = db_manager.save_user_tokens(
                email=user_email,
                access_token=access_token,
                user_profile=user_profile,
                user_type=user_type
            )
            
            if success:
                session['access_token'] = access_token
                session['user_profile'] = user_profile
                session['user_type'] = user_type
                ACCESS_TOKEN = access_token  # Store in global variable for quick access
                USER_PROFILE = user_profile  # Store in global variable for quick access
                print(f"User signed in: {user_profile.get('displayName', 'Unknown')} "
                      f"({user_email}) as {user_type}")
                
                # Clear the user_type from session after use
                session.pop('user_type', None)
                
                return redirect(url_for('main.main_app', auth='success'))
            else:
                print(f"Error saving user data for {user_email}")
                return redirect(url_for('main.main_app', auth='error'))
        else:
            print(f"Error getting user profile: {user_profile['error']}")
            return redirect(url_for('main.main_app', auth='error'))
    else:
        print(f"Token acquisition error: {token_response}")
        return redirect(url_for('main.main_app', auth='error'))

@main_bp.route('/get-user-profile')
def get_user_profile():
    """Get current user profile"""
    try:
        user_profile = session.get('user_profile')
        if not user_profile:
            return jsonify({'error': 'User not authenticated'}), 401
        
        return jsonify({
            'displayName': user_profile.get('displayName', 'Unknown'),
            'email': user_profile.get('mail') or user_profile.get('userPrincipalName', 'Unknown'),
            'id': user_profile.get('id', ''),
            'jobTitle': user_profile.get('jobTitle', ''),
            'officeLocation': user_profile.get('officeLocation', ''),
            'userType': session.get('user_type', 'sender')
        })
    except Exception as error:
        print(f"Error getting user profile: {error}")
        return jsonify({'error': 'Error fetching user profile'}), 500

@main_bp.route('/get-registered-users')
def get_registered_users():
    """Get all registered users from database"""
    try:

        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        user_profile = session.get('user_profile')
        if not user_profile:
            if USER_PROFILE:
                user_profile = USER_PROFILE
            else:
                return jsonify({'error': 'User profile not found'}), 400
        
        # sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
        # senders = db_manager.get_all_active_users('sender')
        targets = db_manager.get_all_active_users('target', user_profile.get('mail', user_profile.get('userPrincipalName', '')))
        
        sender_list = []
        
        sender_list.append({
                'email': user_profile.get('mail', user_profile.get('userPrincipalName', '')),
                'displayName': user_profile.get('displayName', 'Unknown'),
                'lastUsed': user_profile.get('last_used', '').isoformat() if user_profile.get('last_used') else '',
                'userType': 'sender'
            })
        
        target_list = []
        for target in targets:
            target_list.append({
                'email': target['email'],
                'displayName': target['user_profile'].get('displayName', 'Unknown'),
                'lastUsed': target.get('last_used', '').isoformat() if target.get('last_used') else '',
                'userType': 'target'
            })
        
        return jsonify({
            'senders': sender_list,
            'targets': target_list,
            'total_senders': len(sender_list),
            'total_targets': len(target_list)
        })
    except Exception as error:
        print(f"Error getting registered users: {error}")
        return jsonify({'error': 'Error fetching registered users'}), 500

@main_bp.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    return redirect(url_for('main.main_app'))

@main_bp.route('/start-warmup', methods=['POST'])
def start_warmup():
    """Start email warmup campaign with registered users"""
    try:
        data = request.get_json()
        
        # Get campaign parameters
        # sender_emails = data.get('sender_emails', [])
        # target_emails = data.get('target_emails', [])
        delay_between_emails = data.get('delay_between_emails', Config.MIN_DELAY_BETWEEN_EMAILS)
        delete_after_minutes = data.get('delete_after_minutes', Config.MAX_DELAY_BETWEEN_EMAILS)
        cleanup_recipient_mailbox = data.get('cleanup_recipient_mailbox', True)
        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        user_profile = session.get('user_profile')
        if not user_profile:
            if USER_PROFILE:
                user_profile = USER_PROFILE
            else:
                return jsonify({'error': 'User profile not found'}), 400
        
        # sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
        # senders = db_manager.get_all_active_users('sender')
        targets = db_manager.get_all_active_users('target', user_profile.get('mail', user_profile.get('userPrincipalName', '')))
        print(f"Targets: {targets}")
        sender_list = []
        
        sender_list.append({
                'email': user_profile.get('mail', user_profile.get('userPrincipalName', '')),
                'displayName': user_profile.get('displayName', 'Unknown'),
                'lastUsed': user_profile.get('last_used', '').isoformat() if user_profile.get('last_used') else '',
                'userType': 'sender'
            })
        print(f"Sender List: {sender_list}")
        return jsonify({'message': 'Sender list created successfully', 'senders': sender_list}), 200
        target_list = []
        for target in targets:
            target_list.append({
                'email': target['email'],
                'displayName': target['user_profile'].get('displayName', 'Unknown'),
                'lastUsed': target.get('last_used', '').isoformat() if target.get('last_used') else '',
                'userType': 'target'
            })


        valid_senders = [email for email in sender_list if validate_email(email)]
        valid_targets = [email for email in target_list if validate_email(email)]
        
        if not valid_senders:
            return jsonify({'error': 'No valid sender email addresses found'}), 400
        
        if not valid_targets:
            return jsonify({'error': 'No valid target email addresses found'}), 400
        
        # Verify all emails exist in database
        missing_senders = []
        missing_targets = []
        
        for email in valid_senders:
            if not db_manager.get_user_tokens(email):
                missing_senders.append(email)
        
        for email in valid_targets:
            if not db_manager.get_user_tokens(email):
                missing_targets.append(email)
        
        if missing_senders:
            return jsonify({
                'error': f'Sender emails not registered: {", ".join(missing_senders)}'
            }), 400
        
        if missing_targets:
            return jsonify({
                'error': f'Target emails not registered: {", ".join(missing_targets)}'
            }), 400
        
        print(f"Starting warmup campaign:")
        print(f"Senders: {valid_senders}")
        print(f"Targets: {valid_targets}")
        
        # Run comprehensive warmup campaign
        results = warmup_service.run_comprehensive_warmup_campaign(
            sender_emails=valid_senders,
            target_emails=valid_targets,
            delay_between_emails=delay_between_emails,
            delete_after_minutes=delete_after_minutes,
            cleanup_recipient_mailbox=cleanup_recipient_mailbox
        )
        
        return jsonify({
            'success': True,
            'message': 'Comprehensive warm-up campaign completed',
            'results': {
                'total_combinations': results['total_combinations'],
                'emails_sent': results['emails_sent'],
                'send_failures': results['send_failures'],
                'sender_deletions': results['sender_deletions'],
                'recipient_deletions': results['recipient_deletions'],
                'delete_failures': results['delete_failures'],
                'total_duration': f"{results['total_duration']:.2f} seconds",
                'campaign_start': results['start_time'].isoformat(),
                'campaign_end': results['end_time'].isoformat()
            }
        })
        
    except Exception as error:
        print(f"Error in warm-up campaign: {error}")
        return jsonify({'error': f'Error running warm-up campaign: {str(error)}'}), 500

@main_bp.route('/start-background-warmup', methods=['POST'])
def start_background_warmup():
    """Start or restart background warmup process"""
    try:
        # Check if there are registered users
       
        access_token = session.get('access_token')
        if not access_token:
            if ACCESS_TOKEN:
                access_token = ACCESS_TOKEN
            else:
                return jsonify({'error': 'User not authenticated'}), 401
        
        user_profile = session.get('user_profile')
        if not user_profile:
            if USER_PROFILE:
                user_profile = USER_PROFILE
            else:
                return jsonify({'error': 'User profile not found'}), 400
        
        # sender_email = user_profile.get('mail', user_profile.get('userPrincipalName', ''))
        # senders = db_manager.get_all_active_users('sender')
        targets = db_manager.get_all_active_users('target', user_profile.get('mail', user_profile.get('userPrincipalName', '')))
        
        sender_list = []
        
        sender_list.append({
                'email': user_profile.get('mail', user_profile.get('userPrincipalName', '')),
                'displayName': user_profile.get('displayName', 'Unknown'),
                'lastUsed': user_profile.get('last_used', '').isoformat() if user_profile.get('last_used') else '',
                'userType': 'sender'
            })
        
        target_list = []
        for target in targets:
            target_list.append({
                'email': target['email'],
                'displayName': target['user_profile'].get('displayName', 'Unknown'),
                'lastUsed': target.get('last_used', '').isoformat() if target.get('last_used') else '',
                'userType': 'target'
            })
        
        if not sender_list:
            return jsonify({'error': 'No registered sender emails found'}), 400
        
        if not target_list:
            return jsonify({'error': 'No registered target emails found'}), 400
        
        # Restart background service
        background_service.stop()
        background_service.start()
        
        return jsonify({
            'success': True,
            'message': 'Background warmup process started',
            'senders_count': len(sender_list),
            'targets_count': len(target_list)
        })
        
    except Exception as error:
        print(f"Error starting background warmup: {error}")
        return jsonify({'error': f'Error starting background warmup: {str(error)}'}), 500

@main_bp.route('/stop-background-warmup', methods=['POST'])
def stop_background_warmup():
    """Stop background warmup process"""
    try:
        background_service.stop()
        return jsonify({
            'success': True,
            'message': 'Background warmup process stopped'
        })
    except Exception as error:
        print(f"Error stopping background warmup: {error}")
        return jsonify({'error': f'Error stopping background warmup: {str(error)}'}), 500

@main_bp.route('/get-campaign-logs')
def get_campaign_logs():
    """Get recent campaign logs"""
    try:
        campaign_logs = db_manager.db['warmup_campaign_logs']
        logs = list(campaign_logs.find().sort('created_at', -1).limit(10))
        
        # Convert ObjectId to string for JSON serialization
        for log in logs:
            log['_id'] = str(log['_id'])
            if 'start_time' in log:
                log['start_time'] = log['start_time'].isoformat()
            if 'end_time' in log:
                log['end_time'] = log['end_time'].isoformat()
            if 'created_at' in log:
                log['created_at'] = log['created_at'].isoformat()
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as error:
        print(f"Error getting campaign logs: {error}")
        return jsonify({'error': f'Error fetching campaign logs: {str(error)}'}), 500

# Register blueprint
app.register_blueprint(main_bp)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Cleanup on shutdown
import atexit
atexit.register(lambda: background_service.stop())

if __name__ == "__main__":
    print("🚀 Starting Email Warmup Application")
    print(f"📊 Database: {Config.DATABASE_NAME}")
    print(f"🔧 Port: {Config.PORT}")
    print(f"🔄 Background service: {'Started' if background_service.running else 'Stopped'}")
    print("-" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=Config.PORT)