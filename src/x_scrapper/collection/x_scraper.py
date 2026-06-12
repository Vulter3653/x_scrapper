import asyncio
import json
import os
import sys
import time
import traceback
import re
from pathlib import Path

from x_scrapper.paths import DATA_ROOT
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

TARGET_USER = os.getenv('TARGET_USER', 'Wendys').lstrip('@')
BRAND_SLUG = re.sub(r'[^a-z0-9]+', '', TARGET_USER.lower()) or 'brand'
BRAND_DIR = Path(os.getenv('BRAND_DIR', DATA_ROOT / BRAND_SLUG))
OUTPUT_FILE = Path(os.getenv('OUTPUT_FILE', BRAND_DIR / 'posts.json'))
STATE_FILE = Path(os.getenv('STATE_FILE', BRAND_DIR / 'scrape_state.json'))
HEADLESS = os.getenv('HEADLESS', 'true').lower() in {'1', 'true', 'yes'}
MAX_SCROLLS = int(os.getenv('MAX_SCROLLS', '2500'))
SCROLL_DELAY_SECONDS = float(os.getenv('SCROLL_DELAY_SECONDS', '1.25'))
IDLE_SCROLL_LIMIT = int(os.getenv('IDLE_SCROLL_LIMIT', '60'))
PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '60000'))
PROFILE_URL = f'https://x.com/{TARGET_USER}'

AUTH_TOKEN = os.getenv('X_AUTH_TOKEN')
CT0 = os.getenv('X_CT0')


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write('\n')
    tmp_path.replace(path)


def records_to_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record['id']): record for record in records if record.get('id')}


def records_from_map(records_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> int:
        try:
            return int(item['id'])
        except (KeyError, TypeError, ValueError):
            return 0

    return sorted(records_by_id.values(), key=sort_key, reverse=True)


def merge_record(records_by_id: dict[str, dict[str, Any]], record: dict[str, Any]) -> bool:
    tweet_id = str(record.get('id', ''))
    if not tweet_id:
        return False

    existing = records_by_id.get(tweet_id)
    if existing is None:
        records_by_id[tweet_id] = record
        return True

    merged = {**existing, **record}
    records_by_id[tweet_id] = merged
    return False


def walk_json(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_json(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_json(child)


def unwrap_tweet_result(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    result = value.get('result') if 'result' in value else value
    if not isinstance(result, dict):
        return None

    while isinstance(result, dict) and result.get('__typename') == 'TweetWithVisibilityResults':
        result = result.get('tweet')

    if isinstance(result, dict) and result.get('__typename') == 'Tweet':
        return result
    return None


def extract_tweet_record(tweet: dict[str, Any]) -> dict[str, Any] | None:
    legacy = tweet.get('legacy')
    rest_id = tweet.get('rest_id')
    if not isinstance(legacy, dict) or not rest_id:
        return None

    user_result = tweet.get('core', {}).get('user_results', {}).get('result', {})
    user_legacy = user_result.get('legacy', {}) if isinstance(user_result, dict) else {}
    screen_name = user_legacy.get('screen_name')
    if screen_name and screen_name.lower() != TARGET_USER.lower():
        return None

    views = tweet.get('views') if isinstance(tweet.get('views'), dict) else {}
    note_tweet = tweet.get('note_tweet') if isinstance(tweet.get('note_tweet'), dict) else {}
    note_results = note_tweet.get('note_tweet_results') if isinstance(note_tweet.get('note_tweet_results'), dict) else {}
    note_result = note_results.get('result') if isinstance(note_results.get('result'), dict) else {}
    note_text = note_result.get('text')

    tweet_url = f'https://x.com/{TARGET_USER}/status/{rest_id}'

    return {
        'id': str(rest_id),
        'tweet_url': tweet_url,
        'created_at': legacy.get('created_at'),
        'text': note_text or legacy.get('full_text') or legacy.get('text') or '',
        'reply_count': legacy.get('reply_count'),
        'favorite_count': legacy.get('favorite_count'),
        'retweet_count': legacy.get('retweet_count'),
        'quote_count': legacy.get('quote_count'),
        'bookmark_count': legacy.get('bookmark_count'),
        'view_count': views.get('count'),
        'lang': legacy.get('lang'),
        'conversation_id': str(legacy.get('conversation_id_str') or ''),
        'is_quote_status': legacy.get('is_quote_status'),
        'source': 'browser_graphql',
        'scraped_at': int(time.time()),
    }


def extract_records_from_payload(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()

    for node in walk_json(payload):
        if 'tweet_results' in node:
            tweet = unwrap_tweet_result(node.get('tweet_results'))
        elif node.get('__typename') in {'Tweet', 'TweetWithVisibilityResults'}:
            tweet = unwrap_tweet_result(node)
        else:
            continue

        if not tweet:
            continue
        record = extract_tweet_record(tweet)
        if not record or record['id'] in seen:
            continue
        seen.add(record['id'])
        records.append(record)

    return records


async def install_response_collector(page, records_by_id: dict[str, dict[str, Any]], state: dict[str, Any]):
    async def handle_response(response):
        url = response.url
        if '/graphql/' not in url:
            return
        if not any(key in url for key in ('UserTweets', 'UserTweetsAndReplies', 'UserMedia', 'TweetDetail')):
            return

        try:
            payload = await response.json()
        except Exception:
            return

        records = extract_records_from_payload(payload)
        if not records:
            return

        new_count = 0
        for record in records:
            if merge_record(records_by_id, record):
                new_count += 1

        state['target_user'] = TARGET_USER
        state['profile_url'] = PROFILE_URL
        state['total_unique_posts'] = len(records_by_id)
        state['last_response_url'] = url.split('?')[0]
        state['last_saved_at'] = int(time.time())
        save_json(OUTPUT_FILE, records_from_map(records_by_id))
        save_json(STATE_FILE, state)
        print(
            f'captured={len(records)}, new={new_count}, total_unique={len(records_by_id)}',
            flush=True,
        )

    def on_response(response):
        asyncio.create_task(handle_response(response))

    page.on('response', on_response)


async def scrape_profile() -> None:
    if not AUTH_TOKEN or not CT0:
        print('Error: X_AUTH_TOKEN 또는 X_CT0 환경 변수가 설정되지 않았습니다.')
        sys.exit(1)

    existing_records = load_json(OUTPUT_FILE, [])
    records_by_id = records_to_map(existing_records)
    state = load_json(STATE_FILE, {})

    print(
        f'@{TARGET_USER} browser scrape start: existing={len(records_by_id)}, '
        f'max_scrolls={MAX_SCROLLS}, idle_limit={IDLE_SCROLL_LIMIT}',
        flush=True,
    )

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=HEADLESS,
            args=['--disable-blink-features=AutomationControlled'],
        )
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 1800},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/125.0.0.0 Safari/537.36'
            ),
            locale='en-US',
        )
        await context.add_cookies([
            {'name': 'auth_token', 'value': AUTH_TOKEN, 'domain': '.x.com', 'path': '/', 'httpOnly': True, 'secure': True},
            {'name': 'ct0', 'value': CT0, 'domain': '.x.com', 'path': '/', 'secure': True},
        ])

        page = await context.new_page()
        await install_response_collector(page, records_by_id, state)

        await page.goto(PROFILE_URL, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT_MS)
        try:
            await page.wait_for_selector('[data-testid="tweet"]', timeout=PAGE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            current_url = page.url
            title = await page.title()
            raise RuntimeError(
                f'X profile did not render tweets. url={current_url}, title={title}. '
                '쿠키가 만료됐거나 GitHub Actions 접속이 X에서 차단됐을 수 있습니다.'
            )

        idle_scrolls = 0
        previous_total = len(records_by_id)
        for scroll_index in range(1, MAX_SCROLLS + 1):
            await page.mouse.wheel(0, 2200)
            await page.wait_for_timeout(int(SCROLL_DELAY_SECONDS * 1000))

            current_total = len(records_by_id)
            if current_total > previous_total:
                idle_scrolls = 0
                previous_total = current_total
            else:
                idle_scrolls += 1

            if scroll_index % 10 == 0:
                print(
                    f'scroll={scroll_index}, total_unique={current_total}, idle_scrolls={idle_scrolls}',
                    flush=True,
                )

            if idle_scrolls >= IDLE_SCROLL_LIMIT:
                print(f'No new posts after {idle_scrolls} scrolls. Stopping.', flush=True)
                break

        await context.close()
        await browser.close()

    save_json(OUTPUT_FILE, records_from_map(records_by_id))
    state['target_user'] = TARGET_USER
    state['profile_url'] = PROFILE_URL
    state['total_unique_posts'] = len(records_by_id)
    state['last_completed_at'] = int(time.time())
    save_json(STATE_FILE, state)
    print(f'완료: 누적 고유 포스트 {len(records_by_id)}개 저장 -> {OUTPUT_FILE}', flush=True)


if __name__ == '__main__':
    try:
        asyncio.run(scrape_profile())
    except Exception as exc:
        print(f'Fatal scraper error: {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc()
        sys.exit(1)
