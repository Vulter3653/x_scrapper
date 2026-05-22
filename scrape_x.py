import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from twikit import Client

TARGET_USER = os.getenv('TARGET_USER', 'Wendys').lstrip('@')
OUTPUT_FILE = Path(os.getenv('OUTPUT_FILE', f'{TARGET_USER.lower()}_posts.json'))
STATE_FILE = Path(os.getenv('STATE_FILE', f'{TARGET_USER.lower()}_scrape_state.json'))
TWEET_TYPES = [
    item.strip().capitalize()
    for item in os.getenv('TWEET_TYPES', 'Tweets,Replies').split(',')
    if item.strip()
]
PAGE_SIZE = int(os.getenv('PAGE_SIZE', '100'))
MAX_PAGES_PER_TYPE = int(os.getenv('MAX_PAGES_PER_TYPE', '0'))
PAGE_DELAY_SECONDS = float(os.getenv('PAGE_DELAY_SECONDS', '0.5'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '5'))
RETRY_BASE_SECONDS = float(os.getenv('RETRY_BASE_SECONDS', '5'))
PARALLEL_TYPES = int(os.getenv('PARALLEL_TYPES', str(max(1, min(len(TWEET_TYPES), 2)))))
RESET_CURSOR = os.getenv('RESET_CURSOR', 'false').lower() in {'1', 'true', 'yes'}

AUTH_TOKEN = os.getenv('X_AUTH_TOKEN')
CT0 = os.getenv('X_CT0')
VALID_TWEET_TYPES = {'Tweets', 'Replies', 'Media', 'Likes'}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open('r', encoding='utf-8') as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write('\n')
    tmp_path.replace(path)


def tweet_to_record(tweet: Any, source_type: str) -> dict[str, Any]:
    return {
        'id': str(tweet.id),
        'created_at': getattr(tweet, 'created_at', None),
        'text': getattr(tweet, 'text', ''),
        'retweet_count': getattr(tweet, 'retweet_count', None),
        'favorite_count': getattr(tweet, 'favorite_count', None),
        'reply_count': getattr(tweet, 'reply_count', None),
        'quote_count': getattr(tweet, 'quote_count', None),
        'view_count': getattr(tweet, 'view_count', None),
        'lang': getattr(tweet, 'lang', None),
        'source_type': source_type,
    }


def merge_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = records_to_map(existing)
    for record in incoming:
        tweet_id = str(record.get('id', ''))
        if not tweet_id:
            continue
        current = by_id.get(tweet_id, {})
        merged = {**current, **record}
        if current.get('source_type') and record.get('source_type'):
            sources = set(str(current['source_type']).split(',')) | set(str(record['source_type']).split(','))
            merged['source_type'] = ','.join(sorted(sources))
        by_id[tweet_id] = merged

    return records_from_map(by_id)


def records_to_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record['id']): record for record in records if record.get('id')}


def records_from_map(records_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(records_by_id.values(), key=lambda item: int(item['id']), reverse=True)


def merge_records_into_map(
    records_by_id: dict[str, dict[str, Any]],
    incoming: list[dict[str, Any]],
) -> None:
    merged_records = merge_records(list(records_by_id.values()), incoming)
    records_by_id.clear()
    records_by_id.update(records_to_map(merged_records))


async def fetch_with_retry(client: Client, user_id: str, tweet_type: str, cursor: str | None):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if cursor:
                return await client.get_user_tweets(user_id, tweet_type, count=PAGE_SIZE, cursor=cursor)
            return await client.get_user_tweets(user_id, tweet_type, count=PAGE_SIZE)
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise
            wait_seconds = RETRY_BASE_SECONDS * attempt
            print(
                f'[{tweet_type}] 요청 실패 ({attempt}/{MAX_RETRIES}): {exc}. '
                f'{wait_seconds:.1f}초 후 재시도합니다.',
                flush=True,
            )
            await asyncio.sleep(wait_seconds)


async def scrape_timeline(
    client: Client,
    user_id: str,
    tweet_type: str,
    state: dict[str, Any],
    records_by_id: dict[str, dict[str, Any]],
    semaphore: asyncio.Semaphore,
    state_lock: asyncio.Lock,
    output_lock: asyncio.Lock,
) -> int:
    if tweet_type not in VALID_TWEET_TYPES:
        raise ValueError(f'지원하지 않는 TWEET_TYPES 값입니다: {tweet_type}')

    cursor_key = f'{tweet_type.lower()}_cursor'
    cursor = None if RESET_CURSOR else state.get(cursor_key)
    collected_count = 0
    pages = 0
    seen_page_cursors: set[str] = set()

    print(f'[{tweet_type}] 수집 시작: cursor={"resume" if cursor else "start"}', flush=True)

    while True:
        if MAX_PAGES_PER_TYPE and pages >= MAX_PAGES_PER_TYPE:
            print(f'[{tweet_type}] MAX_PAGES_PER_TYPE={MAX_PAGES_PER_TYPE}에 도달했습니다.', flush=True)
            break

        async with semaphore:
            page = await fetch_with_retry(client, user_id, tweet_type, cursor)

        if not page:
            print(f'[{tweet_type}] 더 이상 결과가 없습니다.', flush=True)
            async with state_lock:
                state[cursor_key] = None
                save_json(STATE_FILE, state)
            break

        page_records = [tweet_to_record(tweet, tweet_type) for tweet in page]
        pages += 1
        collected_count += len(page_records)

        async with output_lock:
            before_count = len(records_by_id)
            merge_records_into_map(records_by_id, page_records)
            save_json(OUTPUT_FILE, records_from_map(records_by_id))
            total_unique = len(records_by_id)

        next_cursor = getattr(page, 'next_cursor', None)
        print(
            f'[{tweet_type}] page={pages}, page_items={len(page_records)}, '
            f'new_unique={total_unique - before_count}, total_unique={total_unique}, '
            f'next_cursor={"yes" if next_cursor else "no"}',
            flush=True,
        )

        if not next_cursor or next_cursor == cursor or next_cursor in seen_page_cursors:
            async with state_lock:
                state[cursor_key] = None
                save_json(STATE_FILE, state)
            break

        seen_page_cursors.add(next_cursor)
        async with state_lock:
            state[cursor_key] = next_cursor
            save_json(STATE_FILE, state)
        cursor = next_cursor

        if PAGE_DELAY_SECONDS > 0:
            await asyncio.sleep(PAGE_DELAY_SECONDS)

    async with state_lock:
        state[f'{tweet_type.lower()}_pages_scraped'] = state.get(f'{tweet_type.lower()}_pages_scraped', 0) + pages
        state[f'{tweet_type.lower()}_last_run_at'] = int(time.time())
        save_json(STATE_FILE, state)
    return collected_count


async def main() -> None:
    if not AUTH_TOKEN or not CT0:
        print('Error: X_AUTH_TOKEN 또는 X_CT0 환경 변수가 설정되지 않았습니다.')
        sys.exit(1)

    client = Client('en-US')
    client.set_cookies({'auth_token': AUTH_TOKEN, 'ct0': CT0})

    existing_records = load_json(OUTPUT_FILE, [])
    records_by_id = records_to_map(existing_records)
    state = load_json(STATE_FILE, {})
    if RESET_CURSOR:
        state = {key: value for key, value in state.items() if not key.endswith('_cursor')}

    print(
        f'@{TARGET_USER} 수집 시작: types={TWEET_TYPES}, page_size={PAGE_SIZE}, '
        f'parallel_types={PARALLEL_TYPES}, existing={len(existing_records)}',
        flush=True,
    )

    user = await client.get_user_by_screen_name(TARGET_USER)
    semaphore = asyncio.Semaphore(max(1, PARALLEL_TYPES))
    state_lock = asyncio.Lock()
    output_lock = asyncio.Lock()
    tasks = [
        scrape_timeline(
            client,
            user.id,
            tweet_type,
            state,
            records_by_id,
            semaphore,
            state_lock,
            output_lock,
        )
        for tweet_type in TWEET_TYPES
    ]
    results = await asyncio.gather(*tasks)

    incoming_count = sum(results)
    save_json(OUTPUT_FILE, records_from_map(records_by_id))

    state['target_user'] = TARGET_USER
    state['output_file'] = str(OUTPUT_FILE)
    state['total_unique_posts'] = len(records_by_id)
    state['last_completed_at'] = int(time.time())
    save_json(STATE_FILE, state)

    print(
        f'완료: 이번 실행 {incoming_count}개 수집, '
        f'누적 고유 포스트 {len(records_by_id)}개 저장 -> {OUTPUT_FILE}',
        flush=True,
    )


if __name__ == '__main__':
    asyncio.run(main())
