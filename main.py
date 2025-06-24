# main.py
import os
import json
import datetime
import pickle
import shutil
import time

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Step 1: Ask user for basic inputs
username = input("Enter your username: ").strip().replace(" ", "_")
user_folder = os.path.join("users", username)
os.makedirs(user_folder, exist_ok=True)

client_secret_path = input("Path to your OAuth client_secret.json: ").strip()
client_secret_target = os.path.join(user_folder, "client_secret.json")
shutil.copyfile(client_secret_path, client_secret_target)

# Step 2: Authenticate with Google OAuth
creds_path = os.path.join(user_folder, "oauth_creds.pickle")
creds = None
if os.path.exists(creds_path):
    with open(creds_path, "rb") as token:
        creds = pickle.load(token)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret_target, SCOPES
        )
        creds = flow.run_local_server(port=9000, prompt='consent')
    with open(creds_path, "wb") as token:
        pickle.dump(creds, token)

# Step 3: Get all channels and let user select one
youtube = build("youtube", "v3", credentials=creds)
channels_response = youtube.channels().list(
    part="snippet,statistics",
    mine=True
).execute()

channels = channels_response.get("items", [])
print(f"🔍 Found {len(channels)} channel(s).")

if not channels:
    print("❌ No channels found for this account.")
    exit()

if len(channels) > 1:
    print("Multiple channels found. Please choose one:")
    for idx, ch in enumerate(channels):
        print(f"{idx+1}: {ch['snippet']['title']}")
    selected_index = int(input("Enter the number of the channel to select: ")) - 1
else:
    selected_index = 0

channel = channels[selected_index]
channel_id = channel["id"]
channel_title = channel["snippet"]["title"].replace("/", "-")
channel_stats = channel["statistics"]

# Step 4: Define channel-specific folder and paths
channel_folder = os.path.join(user_folder, f"channel_{channel_id}")
os.makedirs(channel_folder, exist_ok=True)

spreadsheet_id_path = os.path.join(channel_folder, "spreadsheet_id.txt")
last_run_path = os.path.join(channel_folder, "last_run.json")

# Step 5: Load last run timestamp
last_run_time = None
if os.path.exists(last_run_path):
    with open(last_run_path, "r") as f:
        last_run_time = json.load(f).get("last_run")

# Step 6: Fetch YouTube analytics data
from fetchers.youtube_fetch import fetch_youtube_stats
video_data = fetch_youtube_stats(creds, last_run_time, channel_id)

# Step 7: Create or reuse Google Sheet for this channel
sheets_service = build("sheets", "v4", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)

sheet_name = f"{channel_title} YouTube Analytics"

spreadsheet_id = None
if os.path.exists(spreadsheet_id_path):
    with open(spreadsheet_id_path) as f:
        spreadsheet_id = f.read().strip()
    try:
        # Validate the spreadsheet ID
        sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    except HttpError as e:
        if e.resp.status == 404:
            print("⚠️ Stored spreadsheet ID not found. Creating a new sheet.")
            os.remove(spreadsheet_id_path)
            spreadsheet_id = None
        else:
            raise e

if not spreadsheet_id:
    spreadsheet = {"properties": {"title": sheet_name}}
    result = sheets_service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
    spreadsheet_id = result["spreadsheetId"]
    with open(spreadsheet_id_path, "w") as f:
        f.write(spreadsheet_id)

# Step 8: Ensure "YouTube" and "Channel Overview" tabs exist
sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
sheet_titles = [s["properties"]["title"] for s in sheet_metadata.get("sheets", [])]

if "YouTube" not in sheet_titles:
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": "YouTube"}}}]}
    ).execute()
    time.sleep(2)

if "Channel Overview" not in sheet_titles:
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": "Channel Overview"}}}]}
    ).execute()
    time.sleep(2)

# Step 9: Append YouTube video data (if any)
if video_data:
    # Check if header already exists
    existing = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="YouTube!A1:A1"
    ).execute()

    has_header = "values" in existing
    values = [[
        "Channel Name", "Title", "Video ID", "Published", "Views", "Likes",
        "Comments", "Duration", "Description", "Tags", "URL"
    ]] if not has_header else []

    for row in video_data:
        values.append([channel_title] + row)

    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="YouTube!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()
    print("✅ Video data uploaded to 'YouTube' tab.")
else:
    print("ℹ️ No new video data to upload.")

# Step 10: Append Channel Overview row
timestamp = datetime.datetime.utcnow().isoformat()
overview_values = [[
    timestamp,
    channel_title,
    channel_stats.get("subscriberCount", "0"),
    channel_stats.get("viewCount", "0"),
    channel_stats.get("videoCount", "0")
]]

# Add header if first run
overview_range = "Channel Overview!A1"
existing_overview = sheets_service.spreadsheets().values().get(
    spreadsheetId=spreadsheet_id,
    range="Channel Overview!A1:A1"
).execute()

if "values" not in existing_overview:
    overview_values = [["Timestamp", "Channel", "Subscribers", "Total Views", "Video Count"]] + overview_values

sheets_service.spreadsheets().values().append(
    spreadsheetId=spreadsheet_id,
    range=overview_range,
    valueInputOption="RAW",
    insertDataOption="INSERT_ROWS",
    body={"values": overview_values}
).execute()

# Step 11: Save new run timestamp
with open(last_run_path, "w") as f:
    json.dump({"last_run": datetime.datetime.utcnow().isoformat()}, f)

print(f"\n✅ All data uploaded! View your sheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
