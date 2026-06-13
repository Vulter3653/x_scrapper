#!/usr/bin/env python3
from pathlib import Path

p = Path("src/x_scrapper/collection/x_scraper.py")
s = p.read_text(encoding="utf-8")
s = s.replace("PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '60000'))", "PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '15000'))")
s = s.replace("PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '25000'))", "PAGE_TIMEOUT_MS = int(os.getenv('PAGE_TIMEOUT_MS', '15000'))")
p.write_text(s, encoding="utf-8")
print("fast retry timeout patch applied")
