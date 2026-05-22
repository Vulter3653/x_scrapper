from pathlib import Path
import shutil

DATA_DIR = Path('dashboard/data')
DATA_DIR.mkdir(parents=True, exist_ok=True)

patterns = [
    '*_posts.json',
    '*_scrape_state.json',
    '*_lda_topics.json',
    '*_zero_shot_sentiment.json',
]

copied = []
for pattern in patterns:
    for source in Path('.').glob(pattern):
        if source.is_file():
            target = DATA_DIR / source.name
            shutil.copy2(source, target)
            copied.append(str(target))

print(f'Copied {len(copied)} dashboard data files')
for path in copied:
    print(path)
