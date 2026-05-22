# Cloudflare Pages Dashboard

This directory is a static dashboard for scraped X brand data.

Cloudflare Pages settings:

- Build command: leave empty
- Build output directory: `dashboard`
- Framework preset: None/static

The dashboard reads JSON files from `dashboard/data/`.
Run `python sync_dashboard_data.py` after scraping or analysis results change to copy root-level JSON outputs into this directory.
