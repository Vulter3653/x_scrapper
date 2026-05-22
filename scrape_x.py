import asyncio
import json
import os
import sys
from twikit import Client

# 설정
TARGET_USER = os.getenv('TARGET_USER', 'Wendys')
OUTPUT_FILE = f'{TARGET_USER.lower()}_posts.json'

# 필수 쿠키 (브라우저에서 추출 필요)
AUTH_TOKEN = os.getenv('X_AUTH_TOKEN')
CT0 = os.getenv('X_CT0')

async def scrape_all_tweets(client, username):
    print(f"@{username}의 포스트 수집을 시작합니다...")
    try:
        user = await client.get_user_by_screen_name(username)
        user_id = user.id
        
        all_tweets = []
        # 최신 트윗 가져오기
        tweets = await client.get_user_tweets(user_id, 'Tweets')
        
        while tweets:
            for tweet in tweets:
                all_tweets.append({
                    'id': tweet.id,
                    'created_at': tweet.created_at,
                    'text': tweet.text,
                    'retweet_count': tweet.retweet_count,
                    'favorite_count': tweet.favorite_count,
                    'reply_count': tweet.reply_count,
                    'lang': tweet.lang
                })
            
            print(f"현재 {len(all_tweets)}개의 포스트를 수집했습니다...")
            
            # 다음 페이지로 이동
            tweets = await tweets.next()
            if not tweets:
                break
                
            # X의 탐지를 피하기 위한 지연 시간
            await asyncio.sleep(3)
            
        return all_tweets
    except Exception as e:
        print(f"수집 중 에러 발생: {e}")
        return None

async def main():
    if not AUTH_TOKEN or not CT0:
        print("Error: X_AUTH_TOKEN 또는 X_CT0 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    client = Client('en-US')
    
    # 쿠키를 직접 주입 (로그인 과정 생략)
    client.set_cookies({
        'auth_token': AUTH_TOKEN,
        'ct0': CT0
    })
    
    print("쿠키를 사용하여 세션을 설정했습니다.")

    tweets = await scrape_all_tweets(client, TARGET_USER)
    
    if tweets is not None:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(tweets, f, ensure_ascii=False, indent=4)
        print(f"완료! 총 {len(tweets)}개의 포스트가 {OUTPUT_FILE}에 저장되었습니다.")
    else:
        print("수집에 실패했습니다.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
