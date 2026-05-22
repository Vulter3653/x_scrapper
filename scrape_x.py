import os
import json
import requests

TARGET_USER = os.getenv("TARGET_USER", "Wendys")
BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
OUTPUT_FILE = f"{TARGET_USER.lower()}_posts.json"

if not BEARER_TOKEN:
    raise RuntimeError("X_BEARER_TOKEN secret is missing.")

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}"
}

print(f"@{TARGET_USER}의 정보를 가져오는 중...")

# 1. username -> user id
user_url = f"https://api.x.com/2/users/by/username/{TARGET_USER}"
user_resp = requests.get(user_url, headers=headers, timeout=30)
user_resp.raise_for_status()

user_data = user_resp.json().get("data")
if not user_data:
    raise RuntimeError(f"User @{TARGET_USER}를 찾을 수 없습니다.")

user_id = user_data["id"]

# 2. user id -> tweets
tweets_url = f"https://api.x.com/2/users/{user_id}/tweets"
params = {
    "max_results": 100,
    "tweet.fields": "created_at,lang,public_metrics"
}

all_tweets = []
pagination_token = None

print("포스트 수집 시작...")

while True:
    if pagination_token:
        params["pagination_token"] = pagination_token

    resp = requests.get(tweets_url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    tweets = data.get("data", [])
    all_tweets.extend(tweets)
    
    print(f"현재 {len(all_tweets)}개의 포스트를 수집했습니다...")

    pagination_token = data.get("meta", {}).get("next_token")
    if not pagination_token or not tweets:
        break

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_tweets, f, ensure_ascii=False, indent=4)

print(f"완료! 총 {len(all_tweets)}개의 포스트가 {OUTPUT_FILE}에 저장되었습니다.")
