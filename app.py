import os
import json
import time
import glob
import shutil
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build

from auth.youtube_auth import authenticate_youtube
from fetchers.youtube_fetch import fetch_youtube_stats
from fetchers.facebook_fetch import fetch_facebook_data
from fetchers.instagram_fetch import fetch_instagram_data
from utils.sheet_utils import (
    create_or_get_spreadsheet,
    append_youtube_data,
    append_channel_overview,
    append_facebook_data,
    append_instagram_data
)

# --- Page Config ---
st.set_page_config(layout="wide", page_title="Bilytica Social Media Analytics")

# --- App Title & Reset Button ---
col_left, col_right = st.columns([6, 1])
with col_left:
    st.title("📊 Bilytica Social Media Analytics")

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

# --- Upload Google client_secret.json ---
st.header("🔐 Upload Google API Credentials")
uploaded_file = st.file_uploader("Upload your Google client_secret.json", type="json")
secret_path = os.path.join(user_folder, "client_secret.json")
creds = None

if uploaded_file:
    with open(secret_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        creds = authenticate_youtube(user_folder, secret_path)
        st.session_state.creds = creds
        st.success("✅ Google credentials authenticated.")
        sheet_id_file = os.path.join(user_folder, "unified_spreadsheet.txt")
        spreadsheet_id, _ = create_or_get_spreadsheet(creds, sheet_id_file, user_folder, username)
    except Exception as e:
        st.error(f"❌ Failed to authenticate: {e}")
        st.stop()
else:
    st.warning("⚠️ Upload your client_secret.json to proceed.")
    st.stop()

# --- Connect Platforms with Status ---
st.header("🔌 Connect Platforms")
col1, col2, col3 = st.columns(3)

with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/1384/1384060.png", width=80)
    if st.button("Connect YouTube"):
        st.session_state.yt_modal = True
    yt_status = "🟢 Connected" if st.session_state.yt_connected else "🔴 Not Connected"
    st.markdown(f"**YouTube Status:** {yt_status}")

with col2:
    st.image("https://cdn-icons-png.flaticon.com/512/124/124010.png", width=80)
    if st.button("Connect Facebook"):
        st.session_state.fb_modal = True
    fb_status = "🟢 Connected" if st.session_state.fb_connected else "🔴 Not Connected"
    st.markdown(f"**Facebook Status:** {fb_status}")

with col3:
    st.image("https://cdn-icons-png.flaticon.com/512/174/174855.png", width=80)
    if st.button("Connect Instagram"):
        st.session_state.ig_modal = True
    ig_status = "🟢 Connected" if st.session_state.ig_connected else "🔴 Not Connected"
    st.markdown(f"**Instagram Status:** {ig_status}")

# --- YouTube Modal ---
if st.session_state.get("yt_modal"):
    with st.expander("📺 YouTube Data", expanded=True):
        try:
            youtube = build("youtube", "v3", credentials=creds)
            channels = youtube.channels().list(part="snippet,statistics", mine=True).execute().get("items", [])
            if not channels:
                st.warning("No YouTube channel found.")
                st.stop()

            channel = channels[0]
            c_id = channel["id"]
            stats = channel["statistics"]
            videos = fetch_youtube_stats(creds, None, c_id)
            st.success(f"📥 Fetched {len(videos)} videos.")

            st.session_state.youtube_data = videos
            st.session_state.youtube_stats = stats
            st.session_state.youtube_files = {
                "channel_id": c_id,
                "last_video_file": os.path.join(user_folder, f"{c_id}_last.json"),
                "channel_stats_file": os.path.join(user_folder, f"channel_{c_id}_stats.json")
            }
            st.session_state.yt_connected = True

        except Exception as e:
            st.error(f"YouTube error: {e}")

# --- Facebook Modal ---
if st.session_state.get("fb_modal"):
    with st.expander("📘 Facebook Data", expanded=True):
        fb_token = st.text_input("Enter Facebook Page Access Token", type="password", key="fb_tok")
        fb_page = st.text_input("Enter Facebook Page ID", key="fb_id")
        if fb_token and fb_page:
            try:
                fb_data = fetch_facebook_data(fb_token, fb_page)
                if not fb_data:
                    st.info("📭 No new Facebook posts to export.")
                else:
                    st.success(f"📥 Fetched {len(fb_data)} Facebook posts.")
                    st.session_state.facebook_data = fb_data
                    st.session_state.fb_connected = True
            except Exception as e:
                st.error(f"Facebook error: {e}")

# --- Instagram Modal ---
if st.session_state.get("ig_modal"):
    with st.expander("📷 Instagram Data", expanded=True):
        ig_token = st.text_input("Enter Instagram Access Token", type="password", key="ig_tok")
        ig_user = st.text_input("Enter Instagram User ID", key="ig_id")
        if ig_token and ig_user:
            try:
                ig_data = fetch_instagram_data(ig_token, ig_user)
                if not ig_data:
                    st.info("📭 No new Instagram posts to export.")
                else:
                    st.success(f"📥 Fetched {len(ig_data)} Instagram posts.")
                    st.session_state.instagram_data = ig_data
                    st.session_state.ig_connected = True
            except Exception as e:
                st.error(f"Instagram error: {e}")

# --- Export All ---
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
