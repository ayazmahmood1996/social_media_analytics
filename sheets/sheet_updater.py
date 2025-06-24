# sheets/sheet_updater.py
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def update_google_sheet(user_folder, service_account_path, user_email, data):
    creds = service_account.Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
    sheet_service = build("sheets", "v4", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)

    sheet_name = "My Social Media Report"
    sheet_id_path = os.path.join(user_folder, "spreadsheet_id.txt")

    if os.path.exists(sheet_id_path):
        with open(sheet_id_path, "r") as f:
            spreadsheet_id = f.read().strip()
    else:
        spreadsheet = {"properties": {"title": sheet_name}}
        sheet = sheet_service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId").execute()
        spreadsheet_id = sheet["spreadsheetId"]
        with open(sheet_id_path, "w") as f:
            f.write(spreadsheet_id)
        # Share with user
        drive_service.permissions().create(
            fileId=spreadsheet_id,
            body={"type": "user", "role": "writer", "emailAddress": user_email},
            fields="id"
        ).execute()

    values = [["Title", "Video ID", "Published", "Views", "Likes", "Comments", "Duration", "Description", "Tags", "URL"]] + data

    sheet_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="YouTube!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values}
    ).execute()

    return spreadsheet_id
