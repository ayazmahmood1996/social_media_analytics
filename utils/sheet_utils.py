import os
import time
import pickle
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
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
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(
                'auth/client_secret.json', SCOPES)  # Make sure your client_secret.json is in the right location
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for future use
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return creds

def ensure_sheets_exist(service, spreadsheet_id):
    tabs = ["YouTube", "Channel Overview", "Facebook", "Instagram"]
    existing = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    current_tabs = [s["properties"]["title"] for s in existing.get("sheets", [])]

    requests = [{"addSheet": {"properties": {"title": tab}}} for tab in tabs if tab not in current_tabs]
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests}
        ).execute()
        time.sleep(2)

def create_or_get_spreadsheet(creds, id_path, folder, title):
    """Creates or gets a spreadsheet and ensures required tabs exist."""
    service = build("sheets", "v4", credentials=creds)
    spreadsheet_id = None
    is_new = False

    if os.path.exists(id_path):
        with open(id_path) as f:
            spreadsheet_id = f.read().strip()
        try:
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        except HttpError:
            os.remove(id_path)
            spreadsheet_id = None

    if not spreadsheet_id:
        body = {"properties": {"title": title}}
        spreadsheet = service.spreadsheets().create(body=body).execute()
        spreadsheet_id = spreadsheet["spreadsheetId"]
        with open(id_path, "w") as f:
            f.write(spreadsheet_id)
        is_new = True

    ensure_sheets_exist(service, spreadsheet_id)
    return spreadsheet_id, is_new

def append_youtube_data(creds, sheet_id, tab, videos):
    """Appends YouTube data to the specified tab in the Google Sheet."""
    service = build("sheets", "v4", credentials=creds)
    headers = ["video_id", "title", "published", "views", "likes", "comments", "duration", "tags", "description", "video_url"]

    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab}!A1:Z1").execute().get("values", [])
    if not existing:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", body={"values": [headers]}
        ).execute()

    rows = []
    for v in videos:
        rows.append([ 
            v.get("video_id", ""), v.get("title", ""), v.get("published", ""),
            v.get("views", 0), v.get("likes", 0), v.get("comments", 0),
            v.get("duration", ""), ", ".join(v.get("tags", [])),
            v.get("description", "")[:200], v.get("video_url", "")
        ])
    if rows:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": rows}
        ).execute()

def append_channel_overview(creds, sheet_id, tab, stats):
    """Appends channel overview data to the Google Sheet."""
    service = build("sheets", "v4", credentials=creds)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    values = [[timestamp, stats.get("subscriberCount", "0"), stats.get("viewCount", "0"), stats.get("videoCount", "0")]]

    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab}!A1").execute()
    if "values" not in existing:
        values.insert(0, ["Timestamp", "Subscribers", "Total Views", "Video Count"])

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id, range=f"{tab}!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()

def append_facebook_data(creds, sheet_id, fb_data):
    """Appends Facebook post data to the sheet."""
    service = build("sheets", "v4", credentials=creds)
    tab = "Facebook"
    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab}!A1:Z").execute().get("values", [])
    existing_ids = {row[0] for row in existing[1:]} if len(existing) > 1 else set()

    new_rows = [row for row in fb_data if row[0] not in existing_ids]
    if not existing:
        headers = ["Post ID", "Message", "Created Time", "Likes", "Comments", "Shares", "Permalink"]
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", body={"values": [headers]}
        ).execute()

    if new_rows:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": new_rows}
        ).execute()

def append_instagram_data(creds, sheet_id, ig_data):
    """Appends Instagram post data to the sheet."""
    service = build("sheets", "v4", credentials=creds)
    tab = "Instagram"
    existing = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab}!A1:Z").execute().get("values", [])
    existing_ids = {row[0] for row in existing[1:]} if len(existing) > 1 else set()

    new_rows = [row for row in ig_data if row[0] not in existing_ids]
    if not existing:
        headers = ["Post ID", "Timestamp", "Caption", "Media Type", "Media URL", "Permalink", "Like Count", "Comments Count"]
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", body={"values": [headers]}
        ).execute()

    if new_rows:
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": new_rows}
        ).execute()
