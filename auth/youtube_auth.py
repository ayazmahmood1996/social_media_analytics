# auth/youtube_auth.py
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def authenticate_youtube(user_folder, client_secret_path):
    creds_path = os.path.join(user_folder, "youtube_creds.pickle")
    
    creds = None
    if os.path.exists(creds_path):
        with open(creds_path, "rb") as token:
            creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        creds = flow.run_local_server(port=9000, prompt="consent")
        with open(creds_path, "wb") as token:
            pickle.dump(creds, token)

    return creds