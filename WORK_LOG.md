# Work Log: X Scraper, Wendy's Collection, LDA, and Zero-Shot Sentiment

Date: 2026-05-22
Repository: `Vulter3653/x_scrapper`
Working directory: `/home/user/marketingstrategy`

## Current Final State

- Main branch is synchronized with `origin/main`.
- Latest implementation commit: `9590fa0 Add LDA and zero-shot sentiment analysis`.
- Wendy's scrape completed successfully in GitHub Actions run `#6`.
- Wendy's collected data file: `wendys_posts.json`.
- Wendy's scrape state file: `wendys_scrape_state.json`.
- Wendy's collected unique post count: `959`.
- Wendy's oldest collected post: `2009-11-26T15:02:19+00:00`, `https://x.com/Wendys/status/6083264102`, text `Happy Thanksgiving`.
- Wendy's newest collected post: `2026-05-21T22:45:17+00:00`, `https://x.com/Wendys/status/2057593602490970314`, text `Hi @KenJennings`.
- Required fields checked for Wendy's output and had zero missing values: `tweet_url`, `created_at`, `text`, `favorite_count`, `retweet_count`, `reply_count`.

## User Requirements Captured

1. Inspect current files and work state.
2. Build a scraper to collect all Wendy's X/Twitter posts as fast as practical, using parallelism where possible.
3. Do not run daily; make it manually runnable and capable of long collection.
4. Automatically push changes/results to GitHub after work.
5. Explain how to use X cookie secrets.
6. Debug GitHub Actions failures.
7. If the current scraper is not best, evaluate alternatives under a free-only constraint.
8. Collect at minimum:
   - post text
   - date
   - likes
   - retweets
   - replies/comments count
   - post link
9. Verify GitHub results.
10. Support collecting another account, specifically `@CocaCola`.
11. Add LDA topic analysis.
12. Add zero-shot sentiment analysis.
13. Record all work, troubleshooting, debugging, and updates rigorously in a file.

## Major Implementation Timeline

### Initial Repository Inspection

Files found in the project root included:

- `scrape_x.py`
- `requirements.txt`
- `README.md`
- `README_SCRAPER.md`
- `credentials.json`
- `.github/workflows/scrape.yml`
- `.gitignore`

Initial Git state was clean on `main` tracking `origin/main`.

### Original Scraper State

The original scraper used `twikit` with cookie secrets:

- `X_AUTH_TOKEN`
- `X_CT0`

It targeted `Wendys` by default and wrote `wendys_posts.json`.

The original GitHub Actions workflow ran manually and on schedule at midnight UTC, installed Python dependencies, ran `python scrape_x.py`, committed changes, and pushed results.

### Resumable Cookie-Based `twikit` Scraper

Commit: `561c8ac Build resumable Wendy's X scraper`

Changes made:

- Reworked `scrape_x.py` to support resumable scraping.
- Added state file support: `{account}_scrape_state.json`.
- Added output file support: `{account}_posts.json`.
- Added env-driven options:
  - `TARGET_USER`
  - `OUTPUT_FILE`
  - `STATE_FILE`
  - `TWEET_TYPES`
  - `PAGE_SIZE`
  - `MAX_PAGES_PER_TYPE`
  - `PAGE_DELAY_SECONDS`
  - `MAX_RETRIES`
  - `RETRY_BASE_SECONDS`
  - `PARALLEL_TYPES`
  - `RESET_CURSOR`
- Implemented ID-based merge/deduplication.
- Collected metrics including reply count, favorite count, retweet count, quote count, view count, language.
- Changed GitHub Actions from daily schedule to manual `workflow_dispatch`.
- Added workflow inputs for target user and scrape parameters.
- Set job timeout to 360 minutes.
- Updated `README_SCRAPER.md`.
- Added `*.json.tmp` to `.gitignore`.

Validation performed:

- `venv/bin/python -m py_compile scrape_x.py`
- `git diff --check`

### Automatic Commit and Push

User requested automatic push for work progress. From this point onward, meaningful code changes were committed and pushed after validation.

Commit pushed:

- `561c8ac Build resumable Wendy's X scraper`

### GitHub Actions Failure #3

Run: `Scrape Wendy's X Posts #3`
Commit: `561c8ac`
Status: failure
Visible summary:

- `Process completed with exit code 1`
- Node.js 20 deprecation warning

Diagnosis:

- Node.js warning was not considered the failure cause.
- GitHub API showed install dependencies succeeded and scraper step failed.
- Direct log download via GitHub API failed with `403 Must have admin rights to Repository`.
- Most likely immediate causes at that point were missing secrets or runtime scraper failure.

Mitigation commit: `140f690 Validate X scraper secrets in workflow`

Changes:

- Added `Validate scraper secrets` step before running scraper.
- Explicitly checked `X_AUTH_TOKEN` and `X_CT0` for empty/missing values.
- Emitted GitHub annotation errors for missing secrets.

### GitHub Actions Failure #4

Run: `Scrape Wendy's X Posts #4`
Commit: `140f690`
Status: failure
Step status:

- `Validate scraper secrets`: success
- `Run scraper until exhausted or timeout`: failure

Diagnosis:

- Secrets were present and non-empty.
- Failure was inside `python scrape_x.py`, not missing secret configuration.

Mitigation commit: `64810f4 Surface scraper failure details`

Changes:

- Wrapped scraper entrypoint with traceback printing.
- Piped scraper output through `tee scraper.log`.
- Emitted GitHub annotation with the last error line on failure.

### GitHub Actions Failure #5 and Root Cause

Run: `Scrape Wendy's X Posts #5`
Commit: `64810f4`
Status: failure
Detailed error from logs:

```text
Fatal scraper error: Exception: Couldn't get KEY_BYTE indices
...
File "twikit/x_client_transaction/transaction.py", line 54, in get_indices
raise Exception("Couldn't get KEY_BYTE indices")
Exception: Couldn't get KEY_BYTE indices
```

Root cause:

- `twikit` failed before fetching user timeline data.
- Failure occurred during X client transaction initialization.
- This was caused by `twikit` being incompatible with current X frontend/client-transaction logic.
- This was not caused by cookie secret names or empty values.

Decision:

- Under the user's free-only constraint, abandon `twikit` as the primary scraper.
- Switch to a browser-based scraper using Playwright.
- Capture GraphQL responses emitted by the real X web app instead of using `twikit`'s broken client-transaction code.

### Free Scraper Alternative Evaluation

Options evaluated:

1. Managed paid scrapers such as Apify:
   - Most stable.
   - Rejected because the user required free operation.
2. Official X API:
   - Most legitimate and stable.
   - Likely costly and limited for complete historical collection.
   - Not selected under free constraint.
3. `twikit`, `snscrape`, `twint`, `twscrape` style libraries:
   - Considered unreliable because X changes frequently break them.
   - `twikit` specifically failed with `Couldn't get KEY_BYTE indices`.
4. Playwright browser automation:
   - Free.
   - Uses real browser and user cookies.
   - Slower than direct API access but avoids the specific `twikit` failure.
   - Selected.

### Browser-Based Playwright Scraper

Commit: `e85943e Switch to browser-based X scraper`

Changes:

- Replaced `twikit` with `playwright` in `requirements.txt`.
- Rewrote `scrape_x.py` to:
  - launch Chromium
  - inject `auth_token` and `ct0` cookies
  - open `https://x.com/{TARGET_USER}`
  - wait for tweet elements
  - scroll the profile page repeatedly
  - intercept GraphQL responses matching:
    - `UserTweets`
    - `UserTweetsAndReplies`
    - `UserMedia`
    - `TweetDetail`
  - walk response JSON recursively
  - extract tweet records for the target account only
  - save results incrementally
- Added fields:
  - `id`
  - `tweet_url`
  - `created_at`
  - `text`
  - `reply_count`
  - `favorite_count`
  - `retweet_count`
  - `quote_count`
  - `bookmark_count`
  - `view_count`
  - `lang`
  - `conversation_id`
  - `is_quote_status`
  - `source`
  - `scraped_at`
- Updated workflow inputs:
  - `target_user`
  - `max_scrolls`
  - `scroll_delay_seconds`
  - `idle_scroll_limit`
- Added `python -m playwright install --with-deps chromium` to GitHub Actions.
- Updated README for Playwright behavior.

Validation performed:

- `venv/bin/python -m py_compile scrape_x.py`
- `git diff --check`

### GitHub Actions Success #6

Run: `Scrape Wendy's X Posts #6`
Commit: `e85943e`
Status: success
Result commit generated by Actions:

- `05ee00f Update scraped X posts`

Generated files:

- `wendys_posts.json`
- `wendys_scrape_state.json`
- `scraper.log`

Result state:

```json
{
  "target_user": "Wendys",
  "profile_url": "https://x.com/Wendys",
  "total_unique_posts": 959,
  "last_response_url": "https://x.com/i/api/graphql/3AS73VJOTCg8ePuvJndFew/UserTweets",
  "last_saved_at": 1779461892,
  "last_completed_at": 1779461964
}
```

Sample output record contained:

```json
{
  "id": "2057593602490970314",
  "tweet_url": "https://x.com/Wendys/status/2057593602490970314",
  "created_at": "Thu May 21 22:45:17 +0000 2026",
  "text": "Hi @KenJennings",
  "reply_count": 3,
  "favorite_count": 94,
  "retweet_count": 0,
  "quote_count": 0,
  "bookmark_count": 3,
  "view_count": "17388",
  "lang": "und",
  "conversation_id": "2057589742649192842",
  "is_quote_status": false,
  "source": "browser_graphql",
  "scraped_at": 1779461732
}
```

### Log Cleanup

Issue found:

- `scraper.log` was accidentally committed by the successful Actions run.

Commit: `ed6154c Ignore scraper logs after successful runs`

Changes:

- Removed tracked `scraper.log`.
- Added ignored logs to `.gitignore`:
  - `scraper.log`
  - `scraper_failure.log`
  - `analysis.log`
- Updated workflow to remove scraper logs after successful scrape.

Validation performed:

- `git diff --check`
- `venv/bin/python -m py_compile scrape_x.py`

### Wendy's Dataset Verification

Local verification performed against `wendys_posts.json`:

- Count: `959`
- Oldest post:
  - Date: `2009-11-26T15:02:19+00:00`
  - URL: `https://x.com/Wendys/status/6083264102`
  - Text: `Happy Thanksgiving`
- Newest post:
  - Date: `2026-05-21T22:45:17+00:00`
  - URL: `https://x.com/Wendys/status/2057593602490970314`
  - Text: `Hi @KenJennings`

Required field missing counts:

```text
tweet_url: 0
created_at: 0
text: 0
favorite_count: 0
retweet_count: 0
reply_count: 0
```

Important limitation recorded:

- The dataset represents what X's web profile timeline made available through browser scrolling and GraphQL responses.
- It cannot prove perfect historical completeness if X withholds, deletes, rate-limits, or does not expose some posts.
- The result reaches 2009, so historical range is broad, but free scraping cannot formally guarantee 100% completeness.

### Cross-Account Collection: `@CocaCola`

User requested collection for `@CocaCola`.

Current workflow supports this without code changes by setting:

```text
target_user: CocaCola
max_scrolls: 2500
scroll_delay_seconds: 1.25
idle_scroll_limit: 60
```

Expected output files:

- `cocacola_posts.json`
- `cocacola_scrape_state.json`
- `cocacola_lda_topics.json`
- `cocacola_lda_topics.md`
- `cocacola_zero_shot_sentiment.json`
- `cocacola_zero_shot_sentiment.md`

The same existing GitHub Secrets are reused:

- `X_AUTH_TOKEN`
- `X_CT0`

### LDA and Zero-Shot Sentiment Analysis

Commit: `9590fa0 Add LDA and zero-shot sentiment analysis`

Added file:

- `analyze_posts.py`

Added dependencies:

- `scikit-learn`
- `transformers`
- `torch`

Existing dependency retained:

- `playwright`

Workflow changes:

- Added inputs:
  - `run_analysis`
  - `analysis_max_posts`
- Added analysis step after scraping.
- Analysis step runs only when `run_analysis == 'true'`.
- Analysis logs are written to `analysis.log` and removed after success.
- On analysis failure, workflow emits a GitHub annotation.

LDA implementation details:

- Uses `sklearn.decomposition.LatentDirichletAllocation`.
- Uses `CountVectorizer` with English stop words and custom stop words.
- Default topic count: `8`.
- Default words per topic: `12`.
- Default max features: `3000`.
- Produces topic terms and representative posts.

LDA output files:

- `{account}_lda_topics.json`
- `{account}_lda_topics.md`

Zero-shot sentiment implementation details:

- Uses Hugging Face `transformers.pipeline('zero-shot-classification')`.
- Default model: `typeform/distilbert-base-uncased-mnli`.
- Default labels:
  - `positive`
  - `neutral`
  - `negative`
- Default hypothesis template:
  - `This post expresses a {} sentiment.`
- Caches existing per-post sentiment results if the output JSON already exists and text/model match.

Zero-shot output files:

- `{account}_zero_shot_sentiment.json`
- `{account}_zero_shot_sentiment.md`

Recommended Actions inputs for analysis:

```text
run_analysis: true
analysis_max_posts: 0
```

Operational note:

- `analysis_max_posts=0` analyzes all available posts.
- For faster test runs, set `analysis_max_posts=300` first.
- Full zero-shot classification can take materially longer than LDA because it performs model inference per post.

Validation performed:

- `python -m py_compile analyze_posts.py scrape_x.py`
- `git diff --check`


### GitHub Actions Failure #7: CocaCola Push Rejected

Run: `Scrape Wendy's X Posts #7`
Target account: `CocaCola`
Status: failure
Observed logs:

```text
?? cocacola_posts.json
?? cocacola_scrape_state.json
[main 2c3ecb0] Update scraped X posts
2 files changed, 14732 insertions(+)
create mode 100644 cocacola_posts.json
create mode 100644 cocacola_scrape_state.json
...
! [rejected] HEAD -> main (fetch first)
error: failed to push some refs to 'https://github.com/Vulter3653/x_scrapper.git'
hint: Updates were rejected because the remote contains work that you do not have locally.
```

Diagnosis:

- The CocaCola scrape itself succeeded.
- `cocacola_posts.json` and `cocacola_scrape_state.json` were created in the Actions runner.
- The failure occurred only at the final `git push origin HEAD:main` step.
- Cause: a concurrent or newer push updated `origin/main` while the Actions runner was based on an older commit.
- This is a standard non-fast-forward push rejection, not a scraper or analysis failure.

Fix applied:

- Updated `.github/workflows/scrape.yml` commit/push step to retry pushes.
- On push failure, the workflow now:
  1. runs `git fetch origin main`
  2. runs `git rebase origin/main`
  3. retries `git push origin HEAD:main`
- Retry count: `3` attempts.

Expected result after fix:

- If another commit lands during a long scrape, Actions should rebase its generated result commit onto the latest `origin/main` and then push successfully.
- If there is a true content conflict in generated files, the workflow will still fail and require manual resolution.

## Current Important Files

Tracked project files of operational importance:

- `scrape_x.py`: Playwright browser-based X scraper.
- `analyze_posts.py`: LDA and zero-shot sentiment analysis.
- `.github/workflows/scrape.yml`: GitHub Actions workflow for scrape, optional analysis, commit, and push.
- `requirements.txt`: Python dependencies.
- `README_SCRAPER.md`: usage documentation.
- `.gitignore`: ignores environment, cache, temp, and log files.
- `wendys_posts.json`: collected Wendy's posts.
- `wendys_scrape_state.json`: Wendy's scrape state summary.
- `WORK_LOG.md`: this record.

Local untracked/ignored or sensitive files noted:

- `credentials.json`: ignored and should not be committed.
- `venv/`: ignored.
- `__pycache__/`: ignored.
- `scraper.log`: ignored.
- `analysis.log`: ignored.


### Workflow Separation for Parallel Operation

User requested that scraper, LDA, and sentiment analysis be runnable separately and in parallel.

Implementation:

- `Scrape X Posts` workflow now only scrapes posts and commits `{account}_posts.json` plus `{account}_scrape_state.json`.
- `Run LDA Analysis` workflow runs only `python analyze_posts.py --task lda`.
- `Run Zero-Shot Sentiment` workflow runs only `python analyze_posts.py --task sentiment`.
- `analyze_posts.py` supports `--task all`, `--task lda`, and `--task sentiment`.
- LDA and sentiment workflows can be started at the same time against an existing `{account}_posts.json`.
- Push retry/rebase logic is retained in each workflow to reduce non-fast-forward failures when workflows finish close together.

Operational rule:

- If a fresh scrape is required, run `Scrape X Posts` first and wait until its result files are pushed.
- After the posts JSON exists, run `Run LDA Analysis` and `Run Zero-Shot Sentiment` concurrently.
- Running analysis before the posts JSON exists will fail with `Input file not found`.

## Known Limitations and Risks

1. X may block GitHub Actions browser sessions or mark them suspicious.
2. X cookies can expire or become invalid.
3. X web timeline may not expose every historical post even if the browser scrolls deeply.
4. Metrics such as likes, replies, retweets, and views can change after collection.
5. Browser scraping is slower than direct API access.
6. Zero-shot sentiment model downloads can increase Actions runtime.
7. LDA on short social posts can produce noisy topics; results should be interpreted as exploratory, not definitive.
8. Replies/comments count is collected, but full comment text is not collected.
9. Quote count, bookmark count, and view count are collected when exposed by X response payloads.
10. Free scraping cannot provide formal completeness guarantees comparable to a paid official archive/API source.

## Commands and Checks Used

Representative validation commands used during work:

```bash
python -m py_compile analyze_posts.py scrape_x.py
venv/bin/python -m py_compile scrape_x.py
git diff --check
git status --short --branch
git log --oneline --decorate -5
curl -sS https://api.github.com/repos/Vulter3653/x_scrapper/actions/runs?per_page=5
```

Representative data verification command logic:

```python
import json
from pathlib import Path
from email.utils import parsedate_to_datetime
records = json.loads(Path('wendys_posts.json').read_text())
print(len(records))
# verified oldest, newest, and required field missing counts
```

## Git Commit Timeline Relevant to This Work

```text
561c8ac Build resumable Wendy's X scraper
140f690 Validate X scraper secrets in workflow
64810f4 Surface scraper failure details
e85943e Switch to browser-based X scraper
05ee00f Update scraped X posts
ed6154c Ignore scraper logs after successful runs
9590fa0 Add LDA and zero-shot sentiment analysis
```

Earlier repository history included multiple attempts to stabilize GitHub Actions push and scraper behavior, including explicit token push handling, safe-directory settings, API-v2 attempt, and revert to cookie-based scraping before the Playwright switch.

## Current Usage Summary

Run from GitHub Actions:

1. Open repository `Vulter3653/x_scrapper`.
2. Go to `Actions`.
3. Select `Scrape Wendy's X Posts`.
4. Click `Run workflow`.
5. Use inputs such as:

```text
target_user: Wendys
max_scrolls: 2500
scroll_delay_seconds: 1.25
idle_scroll_limit: 60
run_analysis: true
analysis_max_posts: 0
```

For CocaCola:

```text
target_user: CocaCola
max_scrolls: 2500
scroll_delay_seconds: 1.25
idle_scroll_limit: 60
run_analysis: true
analysis_max_posts: 0
```

Required GitHub Secrets:

```text
X_AUTH_TOKEN
X_CT0
```

These are copied from an authenticated browser session on `https://x.com` and must be treated like sensitive login credentials.
