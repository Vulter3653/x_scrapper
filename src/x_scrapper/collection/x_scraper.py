import asyncio
import json
import os
import sys
import time
import traceback
import re
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from x_scrapper.paths import DATA_ROOT

TARGET_USER = os.getenv('TARGET_USER', 'Wendys').lstrip('@')
BRAND_SLUG = re.sub(r'[^a-z0-9]+', '', TARGET_USER.lower()) or 'brand'
BRAND_DIR = Path(os.getenv('BRAND_DIR', DATA_ROOT / BRAND_SLUG))
OUTPUT_FILE = Path(os.getenv('OUTPUT_FILE', BRAND_DIR / 'posts.json'))
STATE_FILE = Path(os.getenv('STATE_FILE', BRAND_DIR / 'scrape_state.json'))
HEADLESS = os.getenv('HEADLESS', 'true').lower() in {'1', 'true', 'yes'}
MAX_SCROLLS = int(os.getenv('MAX_SCROLLS', '2500'))
MAX_POSTS = int(os.getenv('MAX_POSTS', '0'))
SCROLL_DELAY_SECONDS = float(os.getenv('SCROLL_DELAY_SECONDS', '1.25'))
IDLE_SCROLL_LIMIT = int(os.getenv('IDLE_SCROLL_LIMIT', '60'))
PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '60000'))
PROFILE_URL = f'https://x.com/{TARGET_USER}'

EXISTING_TWEET_IDS_PATH = os.getenv('EXISTING_TWEET_IDS_PATH')
STOP_ON_EXISTING = os.getenv('STOP_ON_EXISTING', '0').lower() in {'1', 'true', 'yes'}
EXISTING_STOP_THRESHOLD = int(os.getenv('EXISTING_STOP_THRESHOLD', '30'))
MIN_SCROLLS_BEFORE_STOP = int(os.getenv('MIN_SCROLLS_BEFORE_STOP', '3'))
SCRAPE_METRICS_FILE_ENV = os.getenv('SCRAPE_METRICS_FILE')
SCRAPE_METRICS_FILE = Path(SCRAPE_METRICS_FILE_ENV) if SCRAPE_METRICS_FILE_ENV else None

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


def load_existing_tweet_ids(path_value: str | None) -> set[str]:
    if not path_value:
        return set()
    path = Path(path_value)
    if not path.exists():
        return set()
    ids = set()
    with path.open('r', encoding='utf-8') as file:
        for line in file:
            tweet_id = line.strip()
            if tweet_id:
                ids.add(tweet_id)
    return ids


def records_to_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record['id']): record for record in records if record.get('id')}


def records_from_map(records_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> int:
        try:
            return int(item['id'])
        except (KeyError, TypeError, ValueError):
            return 0

    return sorted(records_by_id.values(), key=sort_key, reverse=True)


def capped_records(records_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    records = records_from_map(records_by_id)
    if MAX_POSTS > 0:
        return records[:MAX_POSTS]
    return records


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


async def assess_profile_state(page) -> dict[str, Any]:
    current_url = page.url
    title = await page.title()
    body_text = ""
    try:
        body_text = await page.locator("body").inner_text(timeout=3000)
    except Exception:
        body_text = ""
    lower_text = body_text.lower()
    lower_url = current_url.lower()

    login_wall = (
        "/i/flow/login" in lower_url
        or "sign in to x" in lower_text
        or "log in to x" in lower_text
        or "login to x" in lower_text
    )
    account_missing = (
        "this account doesn" in lower_text
        or "account doesn" in lower_text
        or "profile not found" in lower_text
    )
    error_page = account_missing or "something went wrong" in lower_text or "try again" in lower_text
    profile_loaded = bool(body_text.strip()) and not login_wall and not error_page
    return {
        "profile_loaded": profile_loaded,
        "account_exists": not account_missing,
        "login_wall": login_wall,
        "error_page": error_page,
        "profile_url_current": current_url,
        "profile_title": title,
    }


def save_metrics(state: dict[str, Any]) -> None:
    if SCRAPE_METRICS_FILE is None:
        return
    fields = [
        'target_user',
        'profile_url',
        'existing_id_count',
        'new_posts_collected',
        'known_posts_seen',
        'consecutive_existing_seen',
        'stopped_on_existing',
        'stop_reason',
        'scrolls_completed',
        'total_unique_posts',
        'posts_count',
        'profile_loaded',
        'account_exists',
        'login_wall',
        'error_page',
        'profile_url_current',
        'profile_title',
        'last_completed_at',
    ]
    metrics = {key: state.get(key, '') for key in fields}
    save_json(SCRAPE_METRICS_FILE, metrics)


async def install_response_collector(
    page,
    records_by_id: dict[str, dict[str, Any]],
    state: dict[str, Any],
    known_ids: set[str],
    runtime: dict[str, Any],
):
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
        known_count = 0
        known_observed_ids: set[str] = runtime['known_observed_ids']

        for record in records:
            tweet_id = str(record.get('id', ''))
            if STOP_ON_EXISTING and tweet_id in known_ids:
                if tweet_id not in known_observed_ids:
                    known_observed_ids.add(tweet_id)
                    known_count += 1
                continue
            if merge_record(records_by_id, record):
                new_count += 1

        runtime['new_posts_collected'] += new_count
        runtime['known_posts_seen'] += known_count
        if new_count > 0:
            runtime['consecutive_existing_seen'] = 0
        elif known_count > 0:
            runtime['consecutive_existing_seen'] += known_count

        state['target_user'] = TARGET_USER
        state['profile_url'] = PROFILE_URL
        state['existing_id_count'] = len(known_ids)
        state['new_posts_collected'] = runtime['new_posts_collected']
        state['known_posts_seen'] = runtime['known_posts_seen']
        state['consecutive_existing_seen'] = runtime['consecutive_existing_seen']
        state['stopped_on_existing'] = False
        state['total_unique_posts'] = len(capped_records(records_by_id))
        state['last_response_url'] = url.split('?')[0]
        state['last_saved_at'] = int(time.time())
        save_json(OUTPUT_FILE, capped_records(records_by_id))
        save_json(STATE_FILE, state)
        save_metrics(state)
        print(
            f'captured={len(records)}, new={new_count}, known={known_count}, '
            f'total_unique={len(records_by_id)}, known_seen={runtime["known_posts_seen"]}',
            flush=True,
        )

    def on_response(response):
        asyncio.create_task(handle_response(response))

    page.on('response', on_response)


async def scrape_profile() -> None:
    if not AUTH_TOKEN or not CT0:
        print('Error: X_AUTH_TOKEN 또는 X_CT0 환경 변수가 설정되지 않았습니다.')
        sys.exit(1)

    known_ids = load_existing_tweet_ids(EXISTING_TWEET_IDS_PATH)
    existing_records = load_json(OUTPUT_FILE, [])
    records_by_id = records_to_map(existing_records)
    state = load_json(STATE_FILE, {})
    runtime: dict[str, Any] = {
        'known_observed_ids': set(),
        'new_posts_collected': len(records_by_id),
        'known_posts_seen': 0,
        'consecutive_existing_seen': 0,
    }

    state.update({
        'target_user': TARGET_USER,
        'profile_url': PROFILE_URL,
        'existing_id_count': len(known_ids),
        'new_posts_collected': runtime['new_posts_collected'],
        'known_posts_seen': 0,
        'consecutive_existing_seen': 0,
        'stopped_on_existing': False,
        'stop_reason': '',
        'scrolls_completed': 0,
    })
    save_metrics(state)

    print(
        f'@{TARGET_USER} browser scrape start: existing={len(records_by_id)}, '
        f'existing_ids={len(known_ids)}, stop_on_existing={STOP_ON_EXISTING}, '
        f'max_scrolls={MAX_SCROLLS}, max_posts={MAX_POSTS or "unbounded"}, '
        f'idle_limit={IDLE_SCROLL_LIMIT}',
        flush=True,
    )

    stop_reason = 'max_scrolls_reached'
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ],
        )
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 900},
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/136.0.0.0 Safari/537.36'
            ),
            locale='en-US',
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )
        await context.add_cookies([
            {'name': 'auth_token', 'value': AUTH_TOKEN, 'domain': '.x.com', 'path': '/', 'httpOnly': True, 'secure': True},
            {'name': 'ct0', 'value': CT0, 'domain': '.x.com', 'path': '/', 'secure': True},
        ])

        page = await context.new_page()
        await install_response_collector(page, records_by_id, state, known_ids, runtime)

        await page.goto(PROFILE_URL, wait_until='domcontentloaded', timeout=PAGE_TIMEOUT_MS)
        state.update(await assess_profile_state(page))
        state['target_user'] = TARGET_USER
        state['profile_url'] = PROFILE_URL
        state['posts_count'] = len(capped_records(records_by_id))
        save_json(STATE_FILE, state)
        save_metrics(state)
        try:
            await page.wait_for_selector('[data-testid="tweet"]', timeout=PAGE_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            state.update(await assess_profile_state(page))
            output_records = capped_records(records_by_id)
            state['total_unique_posts'] = len(output_records)
            state['posts_count'] = len(output_records)
            state['scrolls_completed'] = 0
            state['last_completed_at'] = int(time.time())
            save_json(OUTPUT_FILE, output_records)
            if (
                state.get('profile_loaded') is True
                and state.get('account_exists') is True
                and state.get('login_wall') is False
                and state.get('error_page') is False
                and len(output_records) == 0
            ):
                state['stop_reason'] = 'profile_no_visible_posts'
                save_json(STATE_FILE, state)
                save_metrics(state)
                await context.close()
                await browser.close()
                print(f'완료: 프로필은 로드됐지만 관측 가능한 포스트가 없습니다 -> {OUTPUT_FILE}', flush=True)
                return
            current_url = page.url
            title = await page.title()
            state['stop_reason'] = 'render_failure'
            save_json(STATE_FILE, state)
            save_metrics(state)
            await context.close()
            await browser.close()
            raise RuntimeError(
                f'X profile did not render tweets. url={current_url}, title={title}. '
                '쿠키가 만료됐거나 GitHub Actions 접속이 X에서 차단됐을 수 있습니다.'
            )

        idle_scrolls = 0
        previous_total = len(records_by_id)
        scroll_index = 0
        for scroll_index in range(1, MAX_SCROLLS + 1):
            await page.mouse.wheel(0, 2200)
            await page.wait_for_timeout(int(SCROLL_DELAY_SECONDS * 1000))

            current_total = len(records_by_id)
            if current_total > previous_total:
                idle_scrolls = 0
                previous_total = current_total
            else:
                idle_scrolls += 1

            state['scrolls_completed'] = scroll_index
            save_metrics(state)

            if scroll_index % 10 == 0:
                print(
                    f'scroll={scroll_index}, total_unique={current_total}, '
                    f'idle_scrolls={idle_scrolls}, known_seen={runtime["known_posts_seen"]}, '
                    f'consecutive_existing={runtime["consecutive_existing_seen"]}',
                    flush=True,
                )

            if (
                STOP_ON_EXISTING
                and len(known_ids) > 0
                and scroll_index >= MIN_SCROLLS_BEFORE_STOP
                and runtime['consecutive_existing_seen'] >= EXISTING_STOP_THRESHOLD
            ):
                state['stopped_on_existing'] = True
                stop_reason = 'existing_threshold_reached'
                print(
                    f'Existing tweet threshold reached '
                    f'({runtime["consecutive_existing_seen"]}/{EXISTING_STOP_THRESHOLD}). Stopping.',
                    flush=True,
                )
                break

            if idle_scrolls >= IDLE_SCROLL_LIMIT:
                stop_reason = 'idle_limit_reached'
                print(f'No new posts after {idle_scrolls} scrolls. Stopping.', flush=True)
                break

            if MAX_POSTS > 0 and runtime['new_posts_collected'] >= MAX_POSTS:
                stop_reason = 'max_new_posts_reached'
                print(f'MAX_POSTS reached ({MAX_POSTS}). Stopping.', flush=True)
                break

        state['scrolls_completed'] = scroll_index
        await context.close()
        await browser.close()

    output_records = capped_records(records_by_id)
    save_json(OUTPUT_FILE, output_records)
    state['target_user'] = TARGET_USER
    state['profile_url'] = PROFILE_URL
    state['existing_id_count'] = len(known_ids)
    state['new_posts_collected'] = runtime['new_posts_collected']
    state['known_posts_seen'] = runtime['known_posts_seen']
    state['consecutive_existing_seen'] = runtime['consecutive_existing_seen']
    state['total_unique_posts'] = len(output_records)
    state['posts_count'] = len(output_records)
    state['stop_reason'] = stop_reason
    state['last_completed_at'] = int(time.time())
    save_json(STATE_FILE, state)
    save_metrics(state)
    print(
        f'완료: 신규 고유 포스트 {len(output_records)}개 저장 -> {OUTPUT_FILE} '
        f'(stop_reason={stop_reason})',
        flush=True,
    )


if __name__ == '__main__':
    try:
        asyncio.run(scrape_profile())
    except Exception as exc:
        print(f'Fatal scraper error: {type(exc).__name__}: {exc}', flush=True)
        traceback.print_exc()
        sys.exit(1)
