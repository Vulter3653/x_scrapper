#!/usr/bin/env python3
"""Discover X account candidates for Fortune firms without auto-approving them."""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse


USER_RESULT_SELECTORS = [
    '[data-testid="UserCell"]',
    '[data-testid="cellInnerDiv"] [data-testid="UserCell"]',
]
HANDLE_SELECTORS = ['a[href^="/"]', 'div[dir="ltr"] span']
DISPLAY_NAME_SELECTORS = ['a[href^="/"] div[dir="ltr"] span', 'div[dir="ltr"] span']
BIO_SELECTORS = ['[data-testid="UserDescription"]', 'div[dir="auto"]']
VERIFIED_SELECTORS = [
    'svg[aria-label*="Verified"]',
    '[data-testid="icon-verified"]',
]
PROFILE_BIO_SELECTORS = ['[data-testid="UserDescription"]']
PROFILE_URL_SELECTORS = ['[data-testid="UserUrl"] a']
PROFILE_FOLLOWERS_SELECTORS = ['a[href$="/verified_followers"]', 'a[href$="/followers"]']

CANDIDATE_FIELDS = [
    'firm_id',
    'fortune_year',
    'fortune_rank',
    'firm_name',
    'search_query',
    'candidate_rank',
    'candidate_handle',
    'candidate_display_name',
    'candidate_profile_url',
    'candidate_bio',
    'candidate_external_url',
    'candidate_followers_text',
    'candidate_verified_status',
    'candidate_role',
    'candidate_source_url',
    'candidate_source_type',
    'name_match_score',
    'handle_match_score',
    'bio_match_score',
    'external_url_score',
    'verified_score',
    'negative_penalty',
    'total_candidate_score',
    'candidate_confidence',
    'review_status',
    'review_note',
    'collected_at',
]

RECOMMENDATION_FIELDS = [
    'firm_id',
    'fortune_rank',
    'firm_name',
    'recommended_handle',
    'recommended_profile_url',
    'recommended_role',
    'recommended_score',
    'recommended_confidence',
    'recommendation_status',
    'reason',
    'needs_manual_review',
]

AUDIT_FIELDS = [
    'firm_id',
    'fortune_rank',
    'firm_name',
    'search_query',
    'search_url',
    'attempted_at',
    'status',
    'result_count',
    'error_type',
    'error_message',
    'page_title',
    'current_url',
    'login_challenge_detected',
    'rate_limited_detected',
    'selector_version',
    'notes',
]

REGIONAL_TERMS = {
    'africa', 'america', 'americas', 'asia', 'australia', 'brazil', 'canada',
    'china', 'deutschland', 'europe', 'france', 'germany', 'global uk',
    'india', 'japan', 'latam', 'mexico', 'middle east', 'singapore', 'spain',
    'uk', 'united kingdom',
}
SUPPORT_TERMS = {'support', 'help', 'care', 'customer service', 'customerservice'}
CAREER_TERMS = {'jobs', 'careers', 'career', 'hiring', 'recruiting'}
INVESTOR_TERMS = {'investor', 'investors', 'shareholder', 'shareholders', ' ir '}
NEWSROOM_TERMS = {'news', 'press', 'media', 'newsroom'}
FAN_TERMS = {'fan', 'parody', 'unofficial', 'not affiliated', 'impersonat'}
PERSON_TERMS = {'ceo', 'chief executive', 'employee', 'founder', 'president'}
CORPORATE_TERMS = {'official', 'company', 'corporate', 'global', 'headquarters'}


@dataclass
class DiscoveryConfig:
    auth_token: str
    ct0: str
    headless: bool
    max_results: int
    scrolls: int
    delay_seconds: float
    timeout_ms: int
    profile_details: bool
    backup_existing: bool


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def normalize(value: Any) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(value or '').lower())


def words(value: Any) -> set[str]:
    return set(re.findall(r'[a-z0-9]+', str(value or '').lower()))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str], backup: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + '.bak'))
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def load_firms(path: Path, limit: int) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as handle:
        firms = list(csv.DictReader(handle))
    required = {'firm_id', 'fortune_year', 'fortune_rank', 'firm_name', 'official_website'}
    missing = required - set(firms[0] if firms else [])
    if missing:
        raise ValueError(f'Missing required firm master columns: {sorted(missing)}')
    firms.sort(key=lambda row: int(row['fortune_rank']))
    return firms[:limit] if limit > 0 else firms


def query_variants(firm_name: str) -> list[str]:
    return [
        firm_name,
        f'{firm_name} official',
        f'{firm_name} corporation',
        f'{firm_name} company',
        f'{firm_name} news',
    ]


def search_url(query: str) -> str:
    return f'https://x.com/search?q={quote(query)}&f=user'


def detect_challenge(text: str, current_url: str) -> tuple[bool, bool]:
    value = f'{text} {current_url}'.lower()
    login = any(term in value for term in ('log in', 'sign in', 'login', '/i/flow/login', 'challenge'))
    limited = any(term in value for term in ('rate limit', 'try again later', 'too many requests', 'temporarily limited'))
    return login, limited


def classify_role(handle: str, display_name: str, bio: str) -> str:
    value = f' {handle} {display_name} {bio} '.lower()
    if any(term in value for term in FAN_TERMS):
        return 'fan_or_unofficial'
    if any(term in value for term in SUPPORT_TERMS):
        return 'customer_support'
    if any(term in value for term in CAREER_TERMS):
        return 'careers'
    if any(term in value for term in INVESTOR_TERMS):
        return 'investor_relations'
    if any(term in value for term in NEWSROOM_TERMS):
        return 'newsroom'
    if any(term in value for term in REGIONAL_TERMS):
        return 'regional'
    if any(term in value for term in PERSON_TERMS):
        return 'executive_or_employee'
    if any(term in value for term in CORPORATE_TERMS):
        return 'corporate'
    return 'unknown'


def name_match_score(firm_name: str, display_name: str) -> int:
    firm = normalize(firm_name)
    display = normalize(display_name)
    if firm and display and firm == display:
        return 30
    firm_words = words(firm_name)
    display_words = words(display_name)
    if firm_words and firm_words <= display_words:
        return 20
    if firm_words & display_words:
        return 10
    return 0


def handle_match_score(firm_name: str, handle: str) -> int:
    firm = normalize(firm_name)
    candidate = normalize(handle)
    if firm and candidate and (firm == candidate or firm in candidate or candidate in firm):
        return 20
    if words(firm_name) & words(handle.replace('_', ' ')):
        return 10
    return 0


def bio_match_score(firm_name: str, bio: str) -> int:
    value = bio.lower()
    if any(term in value for term in CORPORATE_TERMS):
        return 20
    if words(firm_name) & words(bio):
        return 10
    return 0


def official_domain(official_website: str) -> str:
    if not official_website:
        return ''
    url = official_website if '://' in official_website else f'https://{official_website}'
    return urlparse(url).netloc.lower().removeprefix('www.')


def external_url_score(official_website: str, external_url: str) -> tuple[int, str]:
    expected = official_domain(official_website)
    if not expected:
        return 0, 'official_website_missing'
    actual = official_domain(external_url)
    if not actual:
        return 0, 'external_url_missing'
    if actual == expected or actual.endswith(f'.{expected}'):
        return 20, 'official_domain_match'
    if expected in actual or actual in expected:
        return 10, 'related_domain_possible'
    return 0, 'external_domain_mismatch'


def negative_penalty(role: str) -> int:
    return {
        'fan_or_unofficial': -50,
        'customer_support': -30,
        'careers': -25,
        'regional': -20,
        'investor_relations': -20,
        'newsroom': -20,
        'product_brand': -20,
    }.get(role, 0)


def confidence(score: int, role: str, verified: str, penalty: int) -> str:
    if score >= 70 and role == 'corporate' and verified in {'verified', 'unknown'} and penalty == 0:
        return 'high'
    if score >= 50 and role in {'corporate', 'newsroom', 'investor_relations'} and penalty >= -20:
        return 'medium'
    if score >= 25:
        return 'low'
    return 'not_found'


def score_candidate(firm: dict[str, str], candidate: dict[str, Any]) -> dict[str, Any]:
    role = classify_role(candidate['candidate_handle'], candidate['candidate_display_name'], candidate['candidate_bio'])
    url_score, url_note = external_url_score(firm.get('official_website', ''), candidate['candidate_external_url'])
    verified_score = 10 if candidate['candidate_verified_status'] == 'verified' else 0
    scores = {
        'name_match_score': name_match_score(firm['firm_name'], candidate['candidate_display_name']),
        'handle_match_score': handle_match_score(firm['firm_name'], candidate['candidate_handle']),
        'bio_match_score': bio_match_score(firm['firm_name'], candidate['candidate_bio']),
        'external_url_score': url_score,
        'verified_score': verified_score,
        'negative_penalty': negative_penalty(role),
    }
    total = sum(scores.values())
    candidate.update(scores)
    candidate.update({
        'candidate_role': role,
        'total_candidate_score': total,
        'candidate_confidence': confidence(total, role, candidate['candidate_verified_status'], scores['negative_penalty']),
        'review_status': 'needs_manual_review',
        'review_note': ';'.join(filter(None, [candidate.get('review_note', ''), url_note])),
    })
    return candidate


async def first_text(locator, selectors: list[str]) -> str:
    for selector in selectors:
        item = locator.locator(selector).first
        if await item.count():
            try:
                return (await item.inner_text()).strip()
            except Exception:
                continue
    return ''


async def verified_status(locator) -> str:
    for selector in VERIFIED_SELECTORS:
        if await locator.locator(selector).count():
            return 'verified'
    return 'unknown'


async def parse_search_results(page, firm: dict[str, str], query: str, url: str, config: DiscoveryConfig) -> tuple[list[dict[str, Any]], str]:
    selector_used = ''
    cells = None
    for selector in USER_RESULT_SELECTORS:
        locator = page.locator(selector)
        if await locator.count():
            cells = locator
            selector_used = selector
            break
    if cells is None:
        return [], ''

    rows: list[dict[str, Any]] = []
    limit = min(await cells.count(), config.max_results)
    for index in range(limit):
        cell = cells.nth(index)
        text = (await cell.inner_text()).strip()
        handle_match = re.search(r'@[A-Za-z0-9_]{1,15}', text)
        if not handle_match:
            continue
        handle = handle_match.group(0)
        display = text.splitlines()[0].strip() if text else ''
        bio = text
        row = {
            'firm_id': firm['firm_id'],
            'fortune_year': firm['fortune_year'],
            'fortune_rank': firm['fortune_rank'],
            'firm_name': firm['firm_name'],
            'search_query': query,
            'candidate_rank': index + 1,
            'candidate_handle': handle,
            'candidate_display_name': display,
            'candidate_profile_url': f'https://x.com/{handle.lstrip("@")}',
            'candidate_bio': bio,
            'candidate_external_url': '',
            'candidate_followers_text': '',
            'candidate_verified_status': await verified_status(cell),
            'candidate_source_url': url,
            'candidate_source_type': 'x_search',
            'review_note': '',
            'collected_at': now_iso(),
        }
        rows.append(score_candidate(firm, row))
    return rows, selector_used


async def enrich_profile(page, firm: dict[str, str], candidate: dict[str, Any], audit_rows: list[dict[str, Any]], config: DiscoveryConfig) -> None:
    url = candidate['candidate_profile_url']
    attempted = now_iso()
    try:
        await page.goto(url, wait_until='domcontentloaded', timeout=config.timeout_ms)
        await page.wait_for_timeout(int(config.delay_seconds * 1000))
        text = (await page.locator('body').inner_text()).strip()
        login, limited = detect_challenge(text, page.url)
        if login or limited:
            candidate['review_note'] += ';profile_login_or_rate_limited'
            audit_rows.append(audit_row(firm, f'profile:{candidate["candidate_handle"]}', url, attempted, 'login_challenge' if login else 'rate_limited', 0, 'profile_access_failed', text[:500], await page.title(), page.url, login, limited, 'profile-v1', 'Candidate retained without profile enrichment.'))
            return
        bio = await first_text(page, PROFILE_BIO_SELECTORS)
        external = ''
        for selector in PROFILE_URL_SELECTORS:
            link = page.locator(selector).first
            if await link.count():
                external = (await link.get_attribute('href') or '').strip()
                break
        followers = await first_text(page, PROFILE_FOLLOWERS_SELECTORS)
        candidate.update({
            'candidate_bio': bio or candidate['candidate_bio'],
            'candidate_external_url': external,
            'candidate_followers_text': followers,
            'candidate_verified_status': await verified_status(page.locator('body')),
            'candidate_source_type': 'x_profile',
        })
        score_candidate(firm, candidate)
    except Exception as exc:
        candidate['review_note'] += f';profile_fetch_failed:{type(exc).__name__}'
        audit_rows.append(audit_row(firm, f'profile:{candidate["candidate_handle"]}', url, attempted, 'error', 0, type(exc).__name__, str(exc), '', page.url, False, False, 'profile-v1', 'Candidate retained without profile enrichment.'))


def audit_row(firm: dict[str, str], query: str, url: str, attempted: str, status: str, count: int, error_type: str = '', error_message: str = '', page_title: str = '', current_url: str = '', login: bool = False, limited: bool = False, selector: str = '', notes: str = '') -> dict[str, Any]:
    return {
        'firm_id': firm['firm_id'],
        'fortune_rank': firm['fortune_rank'],
        'firm_name': firm['firm_name'],
        'search_query': query,
        'search_url': url,
        'attempted_at': attempted,
        'status': status,
        'result_count': count,
        'error_type': error_type,
        'error_message': error_message,
        'page_title': page_title,
        'current_url': current_url,
        'login_challenge_detected': int(login),
        'rate_limited_detected': int(limited),
        'selector_version': selector,
        'notes': notes,
    }


def recommendation(firm: dict[str, str], candidates: list[dict[str, Any]], audits: list[dict[str, Any]]) -> dict[str, Any]:
    firm_candidates = [row for row in candidates if row['firm_id'] == firm['firm_id']]
    firm_audits = [row for row in audits if row['firm_id'] == firm['firm_id']]
    top = max(firm_candidates, key=lambda row: int(row['total_candidate_score']), default=None)
    statuses = {row['status'] for row in firm_audits}
    if {'login_challenge', 'rate_limited'} & statuses:
        status = 'login_or_rate_limited'
        reason = 'X search or profile detail was blocked by a login challenge or rate limit.'
    elif not firm_candidates and any(row['status'] in {'error', 'search_ui_failed', 'selector_not_found', 'blocked'} for row in firm_audits):
        status = 'search_failed'
        reason = 'X search did not complete successfully. Check audit rows.'
    elif not firm_candidates:
        status = 'no_candidate_found'
        reason = 'No account candidate was parsed from the X user search results.'
    else:
        plausible = [row for row in firm_candidates if row['candidate_confidence'] in {'high', 'medium'}]
        unique_high_corporate = {row['candidate_handle'].lower() for row in plausible if row['candidate_confidence'] == 'high' and row['candidate_role'] == 'corporate'}
        unique_plausible = {row['candidate_handle'].lower() for row in plausible}
        if len(unique_high_corporate) == 1 and len(unique_plausible) == 1:
            status = 'single_high_confidence_candidate'
            reason = 'One high-confidence corporate candidate was found. Manual evidence review is still required.'
        elif len(unique_plausible) > 1:
            status = 'multiple_ambiguous_candidates'
            reason = 'Multiple high or medium candidates require manual role and evidence review.'
        else:
            status = 'low_confidence_only'
            reason = 'Only low-confidence candidates were found.'
    return {
        'firm_id': firm['firm_id'],
        'fortune_rank': firm['fortune_rank'],
        'firm_name': firm['firm_name'],
        'recommended_handle': top['candidate_handle'] if top else '',
        'recommended_profile_url': top['candidate_profile_url'] if top else '',
        'recommended_role': top['candidate_role'] if top else '',
        'recommended_score': top['total_candidate_score'] if top else '',
        'recommended_confidence': top['candidate_confidence'] if top else 'not_found',
        'recommendation_status': status,
        'reason': reason,
        'needs_manual_review': 1,
    }


async def discover(firms: list[dict[str, str]], config: DiscoveryConfig) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    if not config.auth_token or not config.ct0:
        for firm in firms:
            for query in query_variants(firm['firm_name']):
                audits.append(audit_row(firm, query, search_url(query), now_iso(), 'error', 0, 'missing_credentials', 'X_AUTH_TOKEN and X_CT0 are required.', notes='No network discovery attempted.'))
        return candidates, audits

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError('playwright is required. Install requirements-scrape.txt.') from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=config.headless, args=['--disable-blink-features=AutomationControlled'])
        context = await browser.new_context(
            viewport={'width': 1440, 'height': 1600},
            locale='en-US',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36',
        )
        await context.add_cookies([
            {'name': 'auth_token', 'value': config.auth_token, 'domain': '.x.com', 'path': '/', 'httpOnly': True, 'secure': True},
            {'name': 'ct0', 'value': config.ct0, 'domain': '.x.com', 'path': '/', 'secure': True},
        ])
        page = await context.new_page()
        for firm in firms:
            seen_handles: set[str] = set()
            for query in query_variants(firm['firm_name']):
                url = search_url(query)
                attempted = now_iso()
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=config.timeout_ms)
                    await page.wait_for_timeout(int(config.delay_seconds * 1000))
                    for _ in range(config.scrolls):
                        await page.mouse.wheel(0, 1600)
                        await page.wait_for_timeout(int(config.delay_seconds * 1000))
                    body = (await page.locator('body').inner_text()).strip()
                    login, limited = detect_challenge(body, page.url)
                    if login or limited:
                        audits.append(audit_row(firm, query, url, attempted, 'login_challenge' if login else 'rate_limited', 0, 'login_or_rate_limited', body[:500], await page.title(), page.url, login, limited, 'user-search-v1'))
                        continue
                    parsed, selector = await parse_search_results(page, firm, query, url, config)
                    if not selector:
                        audits.append(audit_row(firm, query, url, attempted, 'selector_not_found', 0, 'selector_not_found', 'No configured X user-search result selector matched.', await page.title(), page.url, False, False, 'user-search-v1'))
                        continue
                    new_rows = []
                    for row in parsed:
                        key = row['candidate_handle'].lower()
                        if key in seen_handles:
                            continue
                        seen_handles.add(key)
                        new_rows.append(row)
                    candidates.extend(new_rows)
                    audits.append(audit_row(firm, query, url, attempted, 'success' if parsed else 'no_results', len(parsed), selector=selector, page_title=await page.title(), current_url=page.url))
                except Exception as exc:
                    audits.append(audit_row(firm, query, url, attempted, 'error', 0, type(exc).__name__, str(exc), '', page.url, False, False, 'user-search-v1'))

            if config.profile_details:
                firm_rows = [row for row in candidates if row['firm_id'] == firm['firm_id']][:config.max_results]
                for row in firm_rows:
                    await enrich_profile(page, firm, row, audits, config)
        await browser.close()
    return candidates, audits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Discover and score X account candidates for Fortune firms. Candidates always require manual review.')
    parser.add_argument('--input', default='config/fortune100_firm_master_sample.csv', help='Firm master CSV input.')
    parser.add_argument('--output', default='config/fortune100_account_candidates.csv', help='Candidate CSV output.')
    parser.add_argument('--recommendations', default='data/audit/x_account_discovery_recommendations.csv', help='Top-candidate recommendation CSV output.')
    parser.add_argument('--audit', default='data/audit/x_account_discovery_audit.csv', help='Search and profile discovery audit CSV output.')
    parser.add_argument('--firm-limit', type=int, default=10, help='Maximum number of input firms. Use 0 for all firms.')
    parser.add_argument('--timeout-ms', type=int, default=60000, help='Browser page timeout in milliseconds.')
    parser.add_argument('--no-profile-details', action='store_true', help='Skip candidate profile detail enrichment.')
    parser.add_argument('--backup-existing', action='store_true', help='Create .bak files before deterministic output regeneration.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    firms = load_firms(Path(args.input), args.firm_limit)
    config = DiscoveryConfig(
        auth_token=os.getenv('X_AUTH_TOKEN', ''),
        ct0=os.getenv('X_CT0', ''),
        headless=os.getenv('HEADLESS', 'true').lower() in {'1', 'true', 'yes'},
        max_results=int(os.getenv('DISCOVERY_MAX_RESULTS', '10')),
        scrolls=int(os.getenv('DISCOVERY_SCROLLS', '3')),
        delay_seconds=float(os.getenv('DISCOVERY_DELAY_SECONDS', '1.25')),
        timeout_ms=args.timeout_ms,
        profile_details=not args.no_profile_details,
        backup_existing=args.backup_existing,
    )
    candidates, audits = asyncio.run(discover(firms, config))
    recommendations = [recommendation(firm, candidates, audits) for firm in firms]
    candidates.sort(key=lambda row: (int(row['fortune_rank']), row['search_query'], int(row['candidate_rank']), row['candidate_handle'].lower()))
    audits.sort(key=lambda row: (int(row['fortune_rank']), row['search_query'], row['attempted_at']))
    write_csv(Path(args.output), candidates, CANDIDATE_FIELDS, config.backup_existing)
    write_csv(Path(args.recommendations), recommendations, RECOMMENDATION_FIELDS, config.backup_existing)
    write_csv(Path(args.audit), audits, AUDIT_FIELDS, config.backup_existing)
    print(f'firms={len(firms)} candidates={len(candidates)} recommendations={len(recommendations)} audit_rows={len(audits)}')
    if not config.auth_token or not config.ct0:
        print('warning: X_AUTH_TOKEN or X_CT0 missing; generated audited search_failed placeholders without network discovery.', file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
