#!/usr/bin/env python3
"""Build the Pocapoca Story Village website into _site/.

What it does
  1. Copies the static site (site/) into _site/.
  2. Reads the Firstory RSS feed and writes _site/data/podcast.json
     (title, date, length, cover, audio, YouTube link, illustrations).
  3. Copies each episode's illustrations from "podcast插畫/<EP folder>/"
     into _site/pod/<EP folder>/, resized for the web.
  4. Writes _site/404.html, which forwards old Wix links and short links
     such as /ep185 to the right episode.

Run locally:  python3 scripts/build.py
Needs:        Pillow (pip install pillow)
"""
import email.utils
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from episode_keys import episode_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_SRC = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "_site")
POD_SRC = os.path.join(ROOT, "podcast插畫")
RSS_URL = "https://feed.firstory.me/rss/user/cklabznee4z8p08728tgfauzn"
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
MAX_SIDE = 1500


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def fetch_rss():
    req = urllib.request.Request(RSS_URL, headers={"User-Agent": "pocapoca-site-builder"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def clean_desc(raw):
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = html.unescape(text)
    # drop sponsor blocks that end with "—— 以上為 … 廣告 ——"
    text = re.sub(r"^.*?以上為[^—]*廣告\s*——\s*", "", text, flags=re.S)
    text = re.split(r"✨|📺|☕|村莊FB|故事插畫|插畫連結|Powered by|YouTube版本|《動物村莊", text)[0]
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:160]


def parse_rss(xml_bytes, overrides):
    root = ET.fromstring(xml_bytes)
    items = root.find("channel").findall("item")
    eps = []
    for it in items:
        title = (it.findtext("title") or "").strip()
        desc_raw = it.findtext("description") or ""
        pub = email.utils.parsedate_to_datetime(it.findtext("pubDate"))
        date = pub.strftime("%Y-%m-%d")
        dur = it.findtext(ITUNES + "duration") or "0"
        try:
            if ":" in dur:
                parts = [int(p) for p in dur.split(":")]
                dur = sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
            else:
                dur = int(float(dur))
        except ValueError:
            dur = 0
        link = it.findtext("link") or ""
        story = link.rstrip("/").split("/")[-1]
        img_el = it.find(ITUNES + "image")
        cover = img_el.get("href") if img_el is not None else ""
        enc = it.find("enclosure")
        audio = enc.get("url") if enc is not None else ""
        m = re.search(r"pocapocastoryvillage\.com(/[^\s\"<'）)]+)", desc_raw)
        slug = urllib.parse.unquote(html.unescape(m.group(1))).strip() if m else ""
        m = re.search(r"(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})", desc_raw)
        yt = m.group(1) if m else ""
        eps.append({"title": title, "date": date, "dur": dur, "slug": slug, "story": story,
                    "desc": clean_desc(desc_raw), "cover": cover, "audio": audio, "yt": yt})
    # YouTube links that show up in more than one episode are usually links to
    # some other episode, so keep only the ones that are unique.
    counts = {}
    for e in eps:
        if e["yt"]:
            counts[e["yt"]] = counts.get(e["yt"], 0) + 1
    for e in eps:
        if e["yt"] and counts[e["yt"]] > 1:
            e["yt"] = ""
    keys = episode_keys([(e["title"], e["date"]) for e in eps])
    for e, k in zip(eps, keys):
        e["key"] = k
        e.update(overrides.get(k, {}))
    return eps


def copy_gallery(key):
    """Resize images in podcast插畫/<key>/ into _site/pod/<key>/ and return their paths."""
    src = os.path.join(POD_SRC, key)
    if not os.path.isdir(src):
        return []
    files = sorted(f for f in os.listdir(src) if f.lower().endswith(IMG_EXT) and not f.startswith("."))
    if not files:
        return []
    from PIL import Image, ImageOps
    dst = os.path.join(OUT, "pod", key)
    os.makedirs(dst, exist_ok=True)
    out = []
    for i, f in enumerate(files, 1):
        name = f"{i:02d}.jpg"
        try:
            im = Image.open(os.path.join(src, f))
            im = ImageOps.exif_transpose(im)
            if im.mode == "CMYK" or im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGB")
            im = im.convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            im.save(os.path.join(dst, name), quality=84, optimize=True, progressive=True)
            out.append(f"pod/{urllib.parse.quote(key)}/{name}")
        except Exception as exc:  # keep building even if one file is broken
            print(f"  ! skipped {key}/{f}: {exc}", file=sys.stderr)
    return out


REDIRECT_PAGE = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>Pocapoca 故事村</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<script>
(function(){
  var MAP = __MAP__;
  var base = location.hostname.endsWith("github.io") ? "/" + location.pathname.split("/")[1] + "/" : "/";
  var path = decodeURIComponent(location.pathname).replace(/\\u00a0/g," ");
  if (base !== "/" && path.indexOf(base) === 0) path = "/" + path.slice(base.length);
  path = path.replace(/\\/+$/,"").trim() || "/";
  var m = path.match(/^\\/ep(\\d+)$/i);
  var target = m ? "#ep" + m[1] : (MAP[path] || MAP[path.toLowerCase()] || "");
  location.replace(base + (target || ""));
})();
</script></head>
<body style="font-family:sans-serif;padding:40px;text-align:center">
<p>正在前往 Pocapoca 故事村…</p><p><a href="/">回到首頁</a></p>
</body></html>
"""


def episode_hash(e):
    m = re.match(r"^EP\s*0*(\d+)", e["title"], re.I)
    return "#ep" + m.group(1) if m else "#ep" + e["date"].replace("-", "")


def main():
    overrides = load_json(os.path.join(ROOT, "data", "overrides.json"), {})
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(SITE_SRC, OUT)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)

    eps = parse_rss(fetch_rss(), overrides)
    rows, redirects = [], {}
    for e in eps:
        gal = copy_gallery(e["key"])
        rows.append([e["title"], e["date"], e["dur"], e["slug"], e["story"], e["desc"],
                     e["cover"], e["audio"], e["yt"], gal])
        if e["slug"] and e["slug"] not in redirects:   # newest episode wins for shared links
            redirects[e["slug"]] = episode_hash(e)
            redirects[e["slug"].lower()] = episode_hash(e)
    extra = load_json(os.path.join(ROOT, "data", "old-links.json"), {})
    for k, v in extra.items():
        redirects.setdefault(k, v)

    with open(os.path.join(OUT, "data", "podcast.json"), "w", encoding="utf-8") as f:
        json.dump({"episodes": rows}, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(OUT, "404.html"), "w", encoding="utf-8") as f:
        f.write(REDIRECT_PAGE.replace("__MAP__", json.dumps(redirects, ensure_ascii=False)))
    cname = os.path.join(ROOT, "CNAME")
    if os.path.exists(cname):
        shutil.copy(cname, os.path.join(OUT, "CNAME"))
    with open(os.path.join(OUT, ".nojekyll"), "w") as f:
        f.write("")
    with_gal = sum(1 for r in rows if r[9])
    print(f"Built {len(rows)} episodes ({with_gal} with illustrations), {len({e['slug'] for e in eps if e['slug']})} old links.")


if __name__ == "__main__":
    main()
