# Humor Classification Error Analysis Notes

## 1. Current State Overview
Based on the full-chain classification results (66,823 total rows):
- **Ambiguous/Review Rate:** ~48% (32,103 rows). This is the most significant bottleneck.
- **Humor Detection:** ~14% (9,506 rows identified as humor).
- **Non-Humor:** ~38% (25,214 rows).
- **Type Distribution (within Humor):**
    - Affiliative: ~48%
    - Self-enhancing: ~50%
    - Aggressive: ~1% (Very low)
    - Self-defeating: ~0.4% (Very low)

## 2. Hypotheses for High Ambiguity
The high number of `ambiguous_or_review` cases likely stems from several factors:
- **Linguistic Nuance:** LLMs often struggle with subtle sarcasm, irony, or brand-specific inside jokes that don't use standard humor cues (like "lol" or "haha").
- **Strict Thresholding:** The classifier might be overly cautious, flagging anything that doesn't perfectly fit the "Strong Humor" or "Strong Non-Humor" rule-based cues as ambiguous.
- **Short Texts:** Very short tweets (e.g., "Same.", "Mood.", "Real.") are highly context-dependent and often get flagged as ambiguous without surrounding conversational context.
- **Promotional Humor:** Many brand tweets blend promotional copy with light humor. The boundary between "clever marketing" and "humor" is subjective and difficult for the model to navigate.

## 3. Under-representation of Aggressive/Self-Defeating Humor
- **Brand Safety Bias:** LLMs are often fine-tuned to be polite and avoid "aggressive" labels unless the hostility is overt. Brand accounts also tend to avoid truly aggressive or self-defeating humor to maintain a positive image.
- **Subtle Aggression:** Brands often use "ratio" or playful roasts that might be seen as affiliative (bonding with the audience) rather than truly aggressive, leading to misclassification or ambiguity.
- **Self-Deprecation vs. Self-Defeat:** Brands use light self-deprecation (self-enhancing/coping) but rarely use true self-defeating humor that implies genuine low self-esteem or harm.

## 4. Key Items for V2 Classifier Validation
- **Context Awareness:** Incorporate reply-to relationships or conversation history to resolve short-text ambiguity.
- **Slang/Meme Lexicon Update:** Better recognition of Gen Z slang and current meme formats (e.g., "it's giving", "caught in 4k").
- **Fine-grained Boundary Testing:** Use the `humor_type_boundary_cases.csv` fixture to test the model's ability to distinguish between closely related categories.
- **Sentiment-Humor Interaction:** Analyze if high positive sentiment is masking subtle humor or if high negative sentiment is being mislabeled as humor.

## 5. Human Review Priority Categories
Human intervention should focus on:
1.  **Ambiguous cases with Humor Cues:** Rows that contain "lol", "haha", or emojis but are still labeled ambiguous.
2.  **Short-text Ambiguity:** "Mood", "This", "Exactly" - to determine if they are indeed humorous in context.
3.  **Aggressive/Self-Defeating Candidates:** Using keyword-based filtering (from `diagnose_humor_ambiguous_cases.py`) to find "hidden" instances of these rare types.
4.  **Promotional Overlap:** Reviewing tweets that contain both product mentions and humor to refine the "Promotional vs. Humor" boundary.
