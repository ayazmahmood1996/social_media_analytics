import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# Define the SCOPES needed for Google Sheets and Google Drive
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def get_credentials(user_folder):
    """Get the OAuth 2.0 credentials, either from a stored token or by asking the user to log in."""
    creds = None
    token_file = os.path.join(user_folder, 'token.pickle')
    
    # Check if token already exists
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are not available or invalid, let the user log in again
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Prompt user to login and obtain the credentials
            flow = InstalledAppFlow.from_client_secrets_file(
                'auth/client_secret.json', SCOPES)  # Make sure your client_secret.json is in the right location
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for future use
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return creds

def update_google_sheet(user_folder, user_email, data):
    """Update Google Sheets with user-provided data."""
    creds = get_credentials(user_folder)

    # Build the Google Sheets and Drive API services
    sheet_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    sheet_name = "My Social Media Report"
    sheet_id_path = os.path.join(user_folder, "spreadsheet_id.txt")

    # Check if the sheet ID already exists or create a new sheet
    if os.path.exists(sheet_id_path):
        with open(sheet_id_path, "r") as f:
            spreadsheet_id = f.read().strip()
    else:
        # Create a new spreadsheet
        spreadsheet = {"properties": {"title": sheet_name}}
        sheet = sheet_service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
        spreadsheet_id = sheet["spreadsheetId"]
        with open(sheet_id_path, "w") as f:
            f.write(spreadsheet_id)
        
        # Share the new spreadsheet with the user
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"type": "user", "role": "writer", "emailAddress": user_email},
            fields="id"
        ).execute()

    # Prepare the data to be added
    values = [["Title", "Video ID", "Published", "Views", "Likes", "Comments", "Duration", "Description", "Tags", "URL"]] + data

    # Append the data to the Google Sheet
    sheet_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="YouTube!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()

    return spreadsheet_id
