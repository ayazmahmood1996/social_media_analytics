import requests

def fetch_instagram_data(fb_token, instagram_user_id):
    """Fetch Instagram data using Facebook OAuth token and Instagram User ID."""
    
    # Instagram media endpoint
    url = f"https://graph.facebook.com/v19.0/{instagram_user_id}/media"
    
    # Parameters for the API request
    params = {
        "access_token": fb_token,
        "fields": "id,caption,media_type,media_url,timestamp,permalink,like_count,comments_count",
        "limit": 25
    }

    # Send the request
    response = requests.get(url, params=params)
    
    # Handle errors
    response.raise_for_status()
    media = response.json().get("data", [])

    # Prepare rows of media data
    rows = []
    for post in media:
        rows.append([
            post.get("id", ""),
            post.get("timestamp", ""),
            post.get("caption", "").replace("\n", " ")[:500],  # Limit caption to 500 chars
            post.get("media_type", ""),
            post.get("media_url", ""),
            post.get("permalink", ""),
            post.get("like_count", 0),
            post.get("comments_count", 0)
        ])
    
    return rows
