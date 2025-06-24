import requests

def fetch_instagram_data(token, user_id):
    url = f"https://graph.facebook.com/v19.0/{user_id}/media"
    params = {
        "access_token": token,
        "fields": "id,caption,media_type,media_url,timestamp,permalink,like_count,comments_count",
        "limit": 25
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    media = response.json().get("data", [])

    rows = []
    for post in media:
        rows.append([
            post.get("id", ""),
            post.get("timestamp", ""),
            post.get("caption", "").replace("\n", " ")[:500],
            post.get("media_type", ""),
            post.get("media_url", ""),
            post.get("permalink", ""),
            post.get("like_count", 0),
            post.get("comments_count", 0)
        ])
    return rows
