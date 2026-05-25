from pathlib import Path
import re
import shutil

SOURCE_ROOT = Path('data')
DASHBOARD_DATA_DIR = Path('dashboard/data')
DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)

FILE_MAP = {
    'posts.json': '_posts.json',
    'scrape_state.json': '_scrape_state.json',
    'lda_topics.json': '_lda_topics.json',
    'zero_shot_sentiment.json': '_zero_shot_sentiment.json',
}


def slug_from_legacy(path: Path, suffix: str) -> str:
    name = path.name[:-len(suffix)]
    return re.sub(r'[^a-z0-9]+', '', name.lower()) or 'brand'


def migrate_legacy_inputs() -> list[Path]:
    migrated = []
    for filename, legacy_suffix in FILE_MAP.items():
        for source in Path('.').glob(f'*{legacy_suffix}'):
            if not source.is_file():
                continue
            brand = slug_from_legacy(source, legacy_suffix)
            target = SOURCE_ROOT / brand / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists() or source.stat().st_mtime > target.stat().st_mtime:
                shutil.copy2(source, target)
                migrated.append(target)
    return migrated


def sync_brand_folders() -> list[Path]:
    copied = []
    if not SOURCE_ROOT.exists():
        return copied
    for brand_dir in sorted(path for path in SOURCE_ROOT.iterdir() if path.is_dir()):
        dashboard_brand_dir = DASHBOARD_DATA_DIR / brand_dir.name
        dashboard_brand_dir.mkdir(parents=True, exist_ok=True)
        for filename in FILE_MAP:
            source = brand_dir / filename
            if source.is_file():
                target = dashboard_brand_dir / filename
                shutil.copy2(source, target)
                copied.append(target)
    return copied


def main() -> None:
    migrated = migrate_legacy_inputs()
    copied = sync_brand_folders()
    print(f'Migrated {len(migrated)} legacy data files into data/<brand>/')
    for path in migrated:
        print(path)
    print(f'Copied {len(copied)} dashboard data files into dashboard/data/<brand>/')
    for path in copied:
        print(path)


if __name__ == '__main__':
    main()
