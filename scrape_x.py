import asyncio
import json
import os
import sys
from twikit import Client

# 설정
TARGET_USER = os.getenv('TARGET_USER', 'Wendys')
CREDENTIALS_FILE = 'credentials.json'
COOKIES_FILE = 'cookies.json'
OUTPUT_FILE = f'{TARGET_USER.lower()}_posts.json'

async def login(client):
    # 1. 쿠키 파일 확인
    if os.path.exists(COOKIES_FILE):
        try:
            client.load_cookies(COOKIES_FILE)
            print("쿠키를 사용하여 로그인했습니다.")
            return True
        except Exception as e:
            print(f"쿠키 로드 실패: {e}, 다시 로그인을 시도합니다.")

    # 2. 환경 변수에서 정보 가져오기 (GitHub Actions용)
    username = os.getenv('X_USERNAME')
    email = os.getenv('X_EMAIL')
    password = os.getenv('X_PASSWORD')

    # 3. 환경 변수가 없으면 credentials.json 확인 (로컬용)
    if not (username and email and password):
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                creds = json.load(f)
                username = creds.get('username')
                email = creds.get('email')
                password = creds.get('password')
        
    if not (username and email and password):
        print("Error: 로그인 정보(환경 변수 또는 credentials.json)가 없습니다.")
        return False
    
    print(f"계정({username})으로 로그인을 시도합니다...")
    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password
        )
        client.save_cookies(COOKIES_FILE)
        print("로그인 성공 및 쿠키 저장 완료.")
        return True
    except Exception as e:
        print(f"로그인 중 에러 발생: {e}")
        return False

async def scrape_all_tweets(client, username):
    print(f"@{username}의 포스트를 긁어오기 시작합니다...")
    try:
        user = await client.get_user_by_screen_name(username)
        user_id = user.id
        
        all_tweets = []
        tweets = await client.get_user_tweets(user_id, 'Tweets')
        
        count = 0
        while tweets:
            for tweet in tweets:
                tweet_data = {
                    'id': tweet.id,
                    'created_at': tweet.created_at,
                    'text': tweet.text,
                    'retweet_count': tweet.retweet_count,
                    'favorite_count': tweet.favorite_count,
                    'reply_count': tweet.reply_count,
                    'lang': tweet.lang
                }
                all_tweets.append(tweet_data)
            
            count += len(tweets)
            print(f"현재 {count}개의 포스트를 가져왔습니다...")
            
            # 다음 페이지 확인
            tweets = await tweets.next()
            if not tweets:
                break
                
            await asyncio.sleep(2)
            
        return all_tweets
    except Exception as e:
        print(f"스크레이핑 중 에러 발생: {e}")
        return None # 에러 발생 시 None 반환

async def main():
    client = Client('en-US')
    
    if not await login(client):
        print("로그인 실패. 설정을 확인해 주세요.")
        sys.exit(1)

    tweets = await scrape_all_tweets(client, TARGET_USER)
    
    if tweets is not None:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=4)
        print(f"완료! 총 {len(tweets)}개의 포스트가 {OUTPUT_FILE}에 저장되었습니다.")
    else:
        print("수집 중 에러가 발생했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
