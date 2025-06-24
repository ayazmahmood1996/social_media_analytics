import os
import streamlit as st
import glob
import json
import shutil
from googleapiclient.discovery import build
from google.oauth2 import service_account
from auth.youtube_auth import initiate_youtube_auth, fetch_youtube_token
from fetchers.facebook_fetch import get_facebook_oauth_url, get_facebook_page_token, get_instagram_user_id
from fetchers.instagram_fetch import fetch_instagram_data
from utils.sheet_utils import create_or_get_spreadsheet, append_youtube_data, append_channel_overview, append_facebook_data, append_instagram_data

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Social Media Analytics")
print(f"Current Working Directory: {os.getcwd()}")

# --- App Title & Reset Button ---
col_left, col_right = st.columns([6, 1])
with col_left:
    st.title("📊 Social Media Analytics App")

with col_right:
    if st.button("🔁 Reset App to Default (Safe)"):
        try:
            username = st.session_state.get("username", "")
            user_folder = os.path.join("users", username)
            deleted_files = []
            deleted_dirs = []

            if user_folder and os.path.exists(user_folder):
                # Delete temp files
                patterns = [
                    "*_last.json",
                    "channel_*_stats.json",
                    "channel_*_spreadsheet.txt",
                    "unified_spreadsheet.txt",
                    "*.pickle",
                    "*.tmp",
                    "*.cache",
                    "*.log"
                ]
                for pattern in patterns:
                    for file_path in glob.glob(os.path.join(user_folder, pattern)):
                        try:
                            os.remove(file_path)
                            deleted_files.append(os.path.basename(file_path))
                        except Exception as e:
                            st.warning(f"⚠️ Could not delete {file_path}: {e}")

                # Remove cache/temp folders
                for dir_name in ["__pycache__", ".cache", ".temp"]:
                    temp_dir = os.path.join(user_folder, dir_name)
                    if os.path.isdir(temp_dir):
                        shutil.rmtree(temp_dir)
                        deleted_dirs.append(dir_name)

                # Delete existing Google Sheet from Drive
                service_account_path = os.path.join(user_folder, "service_account.json")
                spreadsheet_id_path = os.path.join(user_folder, "unified_spreadsheet.txt")

                if os.path.exists(service_account_path) and os.path.exists(spreadsheet_id_path):
                    try:
                        with open(spreadsheet_id_path) as f:
                            spreadsheet_id = f.read().strip()
                        creds = service_account.Credentials.from_service_account_file(
                            service_account_path,
                            scopes=["https://www.googleapis.com/auth/drive"]
                        )
                        drive_service = build("drive", "v3", credentials=creds)
                        drive_service.files().delete(fileId=spreadsheet_id).execute()
                        os.remove(spreadsheet_id_path)
                        st.success("🗑️ Previous Google Sheet deleted from Drive.")
                    except Exception as e:
                        st.warning(f"⚠️ Could not delete spreadsheet: {e}")

            st.session_state.clear()
            st.success("✅ App reset completed. Cache and temp files deleted.")
            if deleted_files:
                st.info(f"🧹 Files deleted: {', '.join(deleted_files)}")
            if deleted_dirs:
                st.info(f"📁 Folders deleted: {', '.join(deleted_dirs)}")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Reset failed: {e}")

# --- Username Input ---
username = st.text_input("Enter your username")
if not username:
    st.info("Please enter a username to continue.")
    st.stop()

username = username.strip().replace(" ", "_")
user_folder = os.path.join("users", username)
os.makedirs(user_folder, exist_ok=True)
st.session_state.username = username

# Set session state placeholders
st.session_state.setdefault("youtube_data", None)
st.session_state.setdefault("facebook_data", None)
st.session_state.setdefault("instagram_data", None)
st.session_state.setdefault("youtube_stats", None)
st.session_state.setdefault("youtube_files", None)
st.session_state.setdefault("yt_connected", False)
st.session_state.setdefault("fb_connected", False)
st.session_state.setdefault("ig_connected", False)

# --- Google OAuth Authentication ---
st.header("🔐 Google API Authentication")
auth_url = None
creds = None

# Google OAuth logic
if st.button("Login with Google"):
    client_secret_path = "social_media_analytics/auth/client_secret.json"
    flow, auth_url = initiate_youtube_auth(client_secret_path)
    st.markdown(f"Click [here to authenticate with Google]({auth_url})")

# Fetch the YouTube token after redirection
if "authorization_response" in st.session_state:
    authorization_response = st.session_state["authorization_response"]
    creds = fetch_youtube_token(flow, authorization_response, os.path.join(user_folder, "youtube_token.pickle"))
    st.session_state.creds = creds
    st.success("✅ YouTube credentials authenticated.")

# --- Facebook OAuth Login ---
app_id = "<your-facebook-app-id>"
redirect_uri = "https://socialmediaanalytics-7osbmqnplvybw5xfmvhaky.streamlit.app/"
permissions = "public_profile,email,instagram_basic"

if st.button("Connect Facebook"):
    oauth_url = get_facebook_oauth_url(app_id, redirect_uri, permissions)
    st.markdown(f"Click [here to authenticate with Facebook]({oauth_url})")

# After Facebook Authentication, you will get the token and page ID
if "authorization_response" in st.session_state:
    authorization_response = st.session_state["authorization_response"]
    fb_token = authorization_response["access_token"]
    fb_page_id = authorization_response["page_id"]

    # Get Instagram user ID after Facebook login
    instagram_user_id = get_instagram_user_id(fb_page_id, fb_token)
    st.session_state.instagram_user_id = instagram_user_id
    st.session_state.facebook_token = fb_token
    st.session_state.facebook_page_id = fb_page_id
    st.success(f"✅ Facebook and Instagram connected successfully! Instagram User ID: {instagram_user_id}")

    # Fetch Instagram Data (You can replace this with your actual data processing)
    instagram_data = fetch_instagram_data(fb_token, instagram_user_id)
    st.write(instagram_data)

# --- YouTube + Social Media Platforms Setup ---
col1, col2, col3 = st.columns(3)

with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/1384/1384060.png", width=80)
    if st.button("Connect YouTube", key="connect_youtube"):
        st.session_state.yt_modal = True
    yt_status = "🟢 Connected" if st.session_state.yt_connected else "🔴 Not Connected"
    st.markdown(f"**YouTube Status:** {yt_status}")

with col2:
    st.image("https://cdn-icons-png.flaticon.com/512/124/124010.png", width=80)
    if st.button("Connect Facebook", key="connect_facebook"):
        st.session_state.fb_modal = True
    fb_status = "🟢 Connected" if st.session_state.fb_connected else "🔴 Not Connected"
    st.markdown(f"**Facebook Status:** {fb_status}")

with col3:
    st.image("https://cdn-icons-png.flaticon.com/512/174/174855.png", width=80)
    if st.button("Connect Instagram", key="connect_instagram"):
        st.session_state.ig_modal = True
    ig_status = "🟢 Connected" if st.session_state.ig_connected else "🔴 Not Connected"
    st.markdown(f"**Instagram Status:** {ig_status}")


# --- Export Data (YouTube, Facebook, Instagram) ---
if any([st.session_state.get("youtube_data"), st.session_state.get("facebook_data"), st.session_state.get("instagram_data")]):
    st.markdown("---")
    if st.button("🚀 Export All Data to Google Sheet"):
        try:
            if st.session_state.get("youtube_data"):
                yt_videos = st.session_state["youtube_data"]
                yt_stats = st.session_state["youtube_stats"]
                yt_files = st.session_state["youtube_files"]

                first_time = not os.path.exists(yt_files["last_video_file"])
                last_data = {}
                if not first_time:
                    with open(yt_files["last_video_file"]) as f:
                        last_data = json.load(f)

                new_entries = []
                for video in yt_videos:
                    vid = video["video_id"]
                    new_metrics = {
                        "views": video["views"],
                        "likes": video["likes"],
                        "comments": video["comments"]
                    }
                    old_metrics = last_data.get(vid)
                    if first_time or old_metrics != new_metrics:
                        new_entries.append(video)
                        last_data[vid] = new_metrics

                if new_entries:
                    append_youtube_data(creds, spreadsheet_id, "YouTube", new_entries)
                    append_channel_overview(creds, spreadsheet_id, "Channel Overview", yt_stats)
                    json.dump(last_data, open(yt_files["last_video_file"], "w"))
                    json.dump(yt_stats, open(yt_files["channel_stats_file"], "w"))
                    st.success(f"✅ YouTube: Exported {len(new_entries)} videos.")
                else:
                    st.info("✅ No new YouTube video data to export.")

            if st.session_state.get("facebook_data"):
                append_facebook_data(creds, spreadsheet_id, st.session_state["facebook_data"])
                st.success("✅ Facebook data exported.")

            if st.session_state.get("instagram_data"):
                append_instagram_data(creds, spreadsheet_id, st.session_state["instagram_data"])
                st.success("✅ Instagram data exported.")

        except Exception as e:
            st.error(f"❌ Export failed: {e}")
