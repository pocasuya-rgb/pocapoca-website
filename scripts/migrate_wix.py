#!/usr/bin/env python3
"""One-time move of podcast illustrations from the old Wix site.

For every episode whose Firstory description links to the old site, this opens
that old page, finds the illustrations in it, downloads the original files
from Wix and saves them as  podcast插畫/<EP folder>/01.jpg, 02.jpg, ...
(resized so the longest side is at most 1500px, to keep the repository small).

Usage:
  python3 scripts/migrate_wix.py --limit 3        # test with the 3 newest episodes
  python3 scripts/migrate_wix.py --only EP184,EP90
  python3 scripts/migrate_wix.py                  # everything
Episodes that already have a folder are skipped, so it is safe to run again.
A report is written to data/wix-migration-report.md.
"""
import argparse
import collections
import io
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import fetch_rss, parse_rss, load_json, ROOT, POD_SRC  # noqa: E402

OLD_SITE = "https://www.pocapocastoryvillage.com"
MEDIA = re.compile(r"7c6412_[0-9a-f]{32}(?:~mv2)?\.(?:jpg|jpeg|png|gif)", re.I)
UA = {"User-Agent": "Mozilla/5.0 (pocapoca-migration)"}
MAX_SIDE = 1500


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as exc:
            if i == tries - 1:
                raise
            time.sleep(2 + 3 * i)


def media_ids(page_html):
    seen = []
    for m in MEDIA.findall(page_html):
        if m not in seen:
            seen.append(m)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    overrides = load_json(os.path.join(ROOT, "data", "overrides.json"), {})
    all_eps = [e for e in parse_rss(fetch_rss(), overrides) if e["slug"]]
    eps = all_eps
    if args.only:
        wanted = {k.strip() for k in args.only.split(",") if k.strip()}
        eps = [e for e in all_eps if e["key"] in wanted]

    # 1. read every old page once (several episodes can share a page)
    pages = {}
    # every page is read (even in a test run) so decoration can be told apart
    for slug in sorted({e["slug"] for e in all_eps}):
        try:
            pages[slug] = media_ids(get(OLD_SITE + slug).decode("utf-8", "replace"))
        except Exception as exc:
            pages[slug] = None
            print(f"! could not open {slug}: {exc}")
        time.sleep(0.5)

    # 2. images that appear on many pages are site decoration or "recent posts",
    #    not this episode's illustrations
    freq = collections.Counter(i for ids in pages.values() if ids for i in set(ids))
    common = {i for i, n in freq.items() if n > max(3, 0.15 * len(pages))}

    report = ["# Wix 插畫搬家報告", "", "| 集數 | 舊網址 | 張數 | 狀態 |", "|---|---|---|---|"]
    done = 0
    todo = eps[: args.limit] if args.limit else eps
    for e in todo:
        key, slug = e["key"], e["slug"]
        folder = os.path.join(POD_SRC, key)
        ids = pages.get(slug)
        if ids is None:
            report.append(f"| {key} | {slug} | 0 | 打不開舊網頁 |")
            continue
        own = [i for i in ids if i not in common]
        # the first image of a blog post is its cover and belongs to it,
        # even though it also shows up in other posts' "recent posts" list
        if slug.startswith("/single-post/") and ids and ids[0] not in own:
            own.insert(0, ids[0])
        if os.path.isdir(folder) and any(not f.startswith(".") for f in os.listdir(folder)):
            report.append(f"| {key} | {slug} | – | 已經有資料夾，略過 |")
            continue
        if not own:
            report.append(f"| {key} | {slug} | 0 | 舊網頁裡沒有找到插畫 |")
            continue
        if args.dry_run:
            report.append(f"| {key} | {slug} | {len(own)} | （試算，未下載） |")
            continue
        from PIL import Image, ImageOps
        os.makedirs(folder, exist_ok=True)
        saved = 0
        for n, mid in enumerate(own, 1):
            try:
                data = get(f"https://static.wixstatic.com/media/{mid}")
                im = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
                im = im.convert("RGB")
                im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
                im.save(os.path.join(folder, f"{n:02d}.jpg"), quality=88, optimize=True, progressive=True)
                saved += 1
            except Exception as exc:
                print(f"! {key} image {mid}: {exc}")
            time.sleep(0.3)
        done += 1
        report.append(f"| {key} | {slug} | {saved} | {'完成' if saved == len(own) else f'少了 {len(own) - saved} 張'} |")
        print(f"{key}: {saved}/{len(own)} images")

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "wix-migration-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print(f"Done: {done} episodes downloaded. See data/wix-migration-report.md")


if __name__ == "__main__":
    main()
