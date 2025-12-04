import urllib.parse
import requests
from flask import session, redirect, url_for
from config import Config

def get_auth_url():
    """Generate the authorization URL for Microsoft Graph"""
    params = {
        'client_id': Config.CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': Config.REDIRECT_URI,
        'scope': ' '.join(Config.USER_SCOPES),
        'response_mode': 'query',
        'prompt': 'select_account'
    }
    return f"{Config.AUTHORITY}/oauth2/v2.0/authorize?" + urllib.parse.urlencode(params)

def get_access_token(auth_code):
    """Exchange authorization code for access token"""
    token_url = f"{Config.AUTHORITY}/oauth2/v2.0/token"
    print("Exchanging auth code for access token",auth_code)
    data = {
        'client_id': Config.CLIENT_ID,
        'client_secret': Config.CLIENT_SECRET,
        'code': auth_code,
        'redirect_uri': Config.REDIRECT_URI,
        'grant_type': 'authorization_code',
        'scope': ' '.join(Config.USER_SCOPES)
    }
    print("Token request data:", data)
    response = requests.post(token_url, data=data)
    print("Token response status:", response.status_code)
    return response.json() if response.status_code == 200 else None

def make_graph_request(endpoint, access_token, method='GET', data=None):
    """Make a request to Microsoft Graph API"""
    url = f"{Config.GRAPH_ENDPOINT}{endpoint}"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        
        if response.status_code in [200, 202]:
            if response.text.strip():
                try:
                    return response.json()
                except ValueError:
                    return {'success': True, 'status_code': response.status_code, 'text': response.text}
            return {'success': True, 'status_code': response.status_code}
        else:
            # Error response - try to parse JSON error, otherwise return error dict
            try:
                error_data = response.json()
                return {'error': error_data, 'status_code': response.status_code, 'error_text': response.text}
            except ValueError:
                return {'error': {'message': response.text, 'code': f'HTTP_{response.status_code}'}, 'status_code': response.status_code, 'error_text': response.text}
    except Exception as e:
        return {'error': {'message': str(e), 'code': 'EXCEPTION'}, 'status_code': 500, 'error_text': str(e)}