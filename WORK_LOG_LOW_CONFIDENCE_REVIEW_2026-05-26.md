# Work Log: Low-confidence Review

Date: 2026-05-26
Repository: `Vulter3653/x_scrapper`
Scope: dashboard analysis reliability enhancement, steps 1-3.

## User Request

The user requested proceeding sequentially through the first three recommended next steps:

1. Check Dashboard Check status.
2. Keep additions within a React-compatible dashboard structure.
3. Add a Low-confidence Review section.

## Step 1. Dashboard Check Status Review

The repository already contained the dashboard validation workflow:

```text
.github/workflows/dashboard-check.yml
```

The latest stabilization commits were inspected. GitHub status/run APIs did not yet show a completed workflow run attached to the latest stabilization commit at the time of review. Therefore, the next dashboard-related commits were used to trigger the workflow again.

## Step 2. React-compatible Implementation Approach

The previous instability was caused by DOM overlay scripts using `MutationObserver`. To avoid repeating that failure pattern, the Low-confidence Review addition was implemented as a separate React component mounted into a dedicated root:

```html
<div id="confidence-root"></div>
```

This approach avoids mutating the main React root and does not manipulate `.tabs`, `.content`, or `#root` after the main dashboard is mounted.

The new component reads the current active tab label and reloads scope when the user changes tabs. It does not insert or remove sections inside the main dashboard component tree.

## Step 3. Low-confidence Review Section

A new dashboard file was added:

```text
dashboard/low-confidence-review.js
```

The component loads each brand's existing output files:

```text
dashboard/data/<account>/posts.json
dashboard/data/<account>/zero_shot_sentiment.json
dashboard/data/<account>/hsq_humor_classification.json
```

It joins records by post id and calculates low-confidence review candidates.

### Low-confidence Threshold

Current threshold:

```text
score < 0.50
```

The section reports:

- Humor low-confidence post count
- Sentiment low-confidence post count
- Posts where both humor and sentiment confidence are low
- Average humor score
- Average sentiment score
- Review-needed share
- Humor label confidence table
- Sentiment label confidence table
- Manual review priority post table

### Manual Review Table

The table includes:

- Date
- Brand
- Text
- Sentiment score
- Humor score
- Sentiment / humor label
- Link to original post

## Dashboard Check Update

The validation workflow was updated to include the new file and mount point:

```bash
test -f dashboard/low-confidence-review.js
node --check dashboard/low-confidence-review.js
grep -q 'confidence-root' dashboard/index.html
grep -q 'low-confidence-review.js' dashboard/index.html
grep -q 'Low-confidence Review' dashboard/low-confidence-review.js
```

## Files Changed

- `dashboard/low-confidence-review.js`
- `dashboard/index.html`
- `.github/workflows/dashboard-check.yml`
- `WORK_LOG_LOW_CONFIDENCE_REVIEW_2026-05-26.md`

## Commits

```text
b0ba785b790894407362ee32fbd83bcd76d5783f Add low-confidence review dashboard component
f9098d0f1aa8d92652f50530f4ef5bc4d85453f9 Load low-confidence review component
96cfdcd5eb0cc35e3e192e47db6e80f71b3c6e93 Validate low-confidence review dashboard component
```

## Verification Checklist

After Cloudflare Pages and GitHub Actions complete:

- Open `https://x-scrapper.pages.dev/`.
- Confirm the main dashboard loads normally.
- Confirm the `Low-confidence Review` section appears.
- Switch between `전체 브랜드`, `Wendy's`, `Coca-Cola`, and `MoonPie`.
- Confirm the Low-confidence Review metrics change according to the selected tab.
- Confirm no tab oscillation occurs.
- Confirm GitHub Actions `Dashboard Check` passes.

## Next Recommended Step

The next analytical enhancement should be step 4:

```text
유머 × 감성 × 참여도 요약표 추가
```

This should summarize each humor type by sentiment composition and engagement outcomes.
