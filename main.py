import os
import pickle
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Scopes required for the application
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly", "https://www.googleapis.com/auth/spreadsheets"]

def initiate_youtube_auth(client_secret_file):
    """Initiate the OAuth flow and get the authorization URL"""
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secret_file, SCOPES)
    
    # Generate the authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')

    return flow, auth_url

def fetch_youtube_token(flow, authorization_response, token_file):
    """Fetch the OAuth token after user authentication"""
    flow.fetch_token(authorization_response=authorization_response)

    # Save the credentials for future use (token is stored as a pickle file)
    with open(token_file, 'wb') as token:
        pickle.dump(flow.credentials, token)

    return flow.credentials

def get_credentials(user_folder):
    """Get stored credentials or initiate a new authentication flow"""
    creds = None
    token_file = os.path.join(user_folder, 'token.pickle')
    
    # Check if token file exists
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If no valid credentials, prompt user to log in again
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow, auth_url = initiate_youtube_auth('auth/client_secret.json')  # Client secret only needed here
            creds = flow.run_local_server(port=0)  # User authentication flow

        # Save the new credentials for next time
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return creds
