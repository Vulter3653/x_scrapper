# Work Log: HSQ Humor 2x2 Matrix Dashboard

Date: 2026-05-26
Repository: `Vulter3653/x_scrapper`

## User Request

The user requested a 2x2 distribution view for humor type classification results in the dashboard.

## Classification Criteria

The dashboard maps HSQ humor labels into a 2x2 framework using two axes.

```text
Vertical axis: adaptive/positive function vs. maladaptive/negative function
Horizontal axis: other/relationship-oriented vs. self-oriented
```

## HSQ 2x2 Mapping

```text
Affiliative humor       -> adaptive/positive function + other/relationship-oriented
Self-enhancing humor    -> adaptive/positive function + self-oriented
Aggressive humor        -> maladaptive/negative function + other/relationship-oriented
Self-defeating humor    -> maladaptive/negative function + self-oriented
```

Korean labels used in the dashboard:

```text
Affiliative humor       -> 친화적 유머
Self-enhancing humor    -> 자기고양적 유머
Aggressive humor        -> 공격적 유머
Self-defeating humor    -> 자기패배적 유머
```

## Implemented Changes

- Added `dashboard/humor-matrix.js`.
- Connected `humor-matrix.js` from `dashboard/index.html`.
- Added a new dashboard section named `유머 유형 2x2 분포도`.
- Added a section navigation link named `2x2 유머 분포`.
- Added four matrix cells showing count and share for each HSQ humor type.
- Added explanatory quadrant descriptions.
- Added a brand-level table for Wendy's, Coca-Cola, and MoonPie.
- Added responsive matrix styling directly inside `humor-matrix.js`.

## Related Commits

```text
3c54330f17fac6d337bc5dd49ee56d23d7743ce4 Add HSQ humor 2x2 matrix dashboard
79008c67a9c5ffc8ccda3dc397f73573be65dd18 Load HSQ humor 2x2 matrix dashboard
```

## Verification Checklist

- Open `https://x-scrapper.pages.dev/`.
- Confirm navigation includes `2x2 유머 분포`.
- Confirm the matrix section appears near the Humor Analysis section.
- Confirm all four quadrants show counts and percentages.
- Confirm the brand-level distribution table displays Wendy's, Coca-Cola, and MoonPie rows.
- Confirm mobile layout collapses into readable vertical cards.
