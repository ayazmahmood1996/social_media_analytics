def fetch_facebook_data(token, page_id):
    import requests
    base_url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    fields = "id,message,created_time,permalink_url"
    metrics = "post_reactions_by_type_total,post_comments,post_shares"

    params = {
        "access_token": token,
        "fields": fields,
        "limit": 25
    }

    response = requests.get(base_url, params=params)
    response.raise_for_status()
    data = response.json().get("data", [])

    posts = []
    for post in data:
        post_id = post["id"]
        message = post.get("message", "")
        created_time = post.get("created_time", "")
        permalink = post.get("permalink_url", "")

        # Default fallback values
        likes, comments, shares = 0, 0, 0

        try:
            insights_url = f"https://graph.facebook.com/v19.0/{post_id}/insights"
            insights_params = {
                "access_token": token,
                "metric": metrics
            }
            insights_res = requests.get(insights_url, params=insights_params)
            insights_data = insights_res.json().get("data", [])

            for metric in insights_data:
                name = metric["name"]
                value = metric["values"][0]["value"]
                if name == "post_reactions_by_type_total":
                    likes = sum(value.values())
                elif name == "post_comments":
                    comments = value
                elif name == "post_shares":
                    shares = value
        except Exception as e:
            print(f"Warning: Failed to get insights for post {post_id}: {e}")

        posts.append([post_id, message, created_time, likes, comments, shares, permalink])

    return posts
