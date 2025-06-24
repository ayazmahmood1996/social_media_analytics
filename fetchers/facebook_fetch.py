import requests
import json

# Function to get the Facebook OAuth URL (for user login)
def get_facebook_oauth_url(app_id, redirect_uri, permissions):
    oauth_url = f"https://www.facebook.com/v11.0/dialog/oauth?client_id={app_id}&redirect_uri={redirect_uri}&scope={permissions}"
    return oauth_url

# Function to get the Facebook Page Access Token using the OAuth flow
def get_facebook_page_token(fb_user_token):
    # Use the user token to get the page access token
    url = f"https://graph.facebook.com/v11.0/me/accounts?access_token={fb_user_token}"
    response = requests.get(url)
    pages_data = response.json().get("data", [])
    
    if pages_data:
        # Assuming the first page is the one we need
        page_data = pages_data[0]
        page_token = page_data["access_token"]
        page_id = page_data["id"]
        return page_token, page_id
    else:
        raise Exception("No Facebook Pages found for the user.")

# Function to get Instagram User ID linked to the Facebook Page
def get_instagram_user_id(fb_page_id, fb_token):
    url = f"https://graph.facebook.com/v11.0/{fb_page_id}?fields=instagram_business_account&access_token={fb_token}"
    response = requests.get(url)
    instagram_data = response.json()
    
    if 'instagram_business_account' in instagram_data:
        instagram_user_id = instagram_data['instagram_business_account']['id']
        return instagram_user_id
    else:
        raise Exception(f"No Instagram account linked to Facebook page {fb_page_id}.")
    
# Function to fetch Facebook Posts with insights (reactions, comments, shares)
def fetch_facebook_data(token, page_id):
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
