# Human Labeling Quick Reference

## Column: human_humor_presence

Allowed values: `humor` | `non_humor` | `uncertain`

- `humor`: The post uses humor as an intentional communication device.
- `non_humor`: The post is a standard announcement, news, or informational post with no humor intent.
- `uncertain`: You cannot determine whether the post is humorous, or the post is ambiguous.

## Column: human_humor_type

Allowed values: `aggressive` | `affiliative` | `self_enhancing` | `self_defeating` | `non_humorous` | `uncertain`

- Fill this column only if `human_humor_presence = humor`.
- If `human_humor_presence = non_humor`, set this to `non_humorous`.
- If `human_humor_presence = uncertain`, set this to `uncertain`.

## Column: human_confidence

Enter a number from 1 to 3:
- `1`: Low confidence — the post is genuinely ambiguous
- `2`: Medium confidence
- `3`: High confidence

## Column: human_notes

Free text. Use to explain edge cases, flag issues, or note reasons for uncertain judgments.

## Column: reviewer_id

Your reviewer identifier (e.g., coder1, coder2, etc.)

## Column: review_status

- `pending`: not yet reviewed
- `complete`: reviewed by at least one reviewer
- `needs_second_review`: flagged for a second opinion
