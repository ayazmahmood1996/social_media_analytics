# auth/youtube_auth.py
# auth/youtube_auth.py

import os
import pickle
import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

REDIRECT_URI = "https://socialmediaanalytics-7osbmqnplvybw5xfmvhaky.streamlit.app/"  # Replace this with your deployed URL

def initiate_youtube_auth(client_secret_path):
    flow = Flow.from_client_secrets_file(
        client_secrets_file=client_secret_path,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    auth_url, _ = flow.authorization_url(prompt="consent", include_granted_scopes='true')
    return flow, auth_url

def fetch_youtube_token(flow, authorization_response_url, creds_path):
    try:
        flow.fetch_token(authorization_response=authorization_response_url)
        creds = flow.credentials
        with open(creds_path, "wb") as token:
            pickle.dump(creds, token)
        return creds
    except Exception as e:
        st.error(f"❌ Token fetch failed: {e}")
        return None

def load_existing_youtube_credentials(creds_path):
    if os.path.exists(creds_path):
        with open(creds_path, "rb") as token:
            creds = pickle.load(token)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return creds
    return None
