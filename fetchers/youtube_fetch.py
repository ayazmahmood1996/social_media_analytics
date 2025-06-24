from googleapiclient.discovery import build
from dateutil import parser as date_parser
import datetime

def fetch_youtube_stats(creds, last_time=None, channel_id=None):
    youtube = build("youtube", "v3", credentials=creds)
    videos = []
    next_page_token = None

    if last_time:
        last_time = last_time.astimezone(datetime.timezone.utc).replace(microsecond=0)

    while True:
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=50,
            order="date",
            pageToken=next_page_token,
            type="video"
        )
        response = request.execute()

        for item in response.get("items", []):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            published_at = snippet["publishedAt"]
            video_time = date_parser.isoparse(published_at).astimezone(datetime.timezone.utc).replace(microsecond=0)

            if last_time and video_time <= last_time:
                continue

            video_details = youtube.videos().list(
                part="statistics,contentDetails,snippet,status",
                id=video_id
            ).execute()

            if not video_details.get("items"):
                continue

            v = video_details["items"][0]
            stats = v.get("statistics", {})
            details = v.get("contentDetails", {})
            v_snippet = v.get("snippet", {})
            status = v.get("status", {})

            videos.append({
                "video_id": video_id,
                "title": v_snippet.get("title", ""),
                "published": published_at,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "duration": details.get("duration", ""),
                "description": v_snippet.get("description", "")[:200],
                "tags": v_snippet.get("tags", []),
                "category_id": v_snippet.get("categoryId", ""),
                "privacy_status": status.get("privacyStatus", ""),
                "license": status.get("license", ""),
                "video_url": f"https://www.youtube.com/watch?v={video_id}"
            })

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos
