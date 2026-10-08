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
from colors import to_srgb

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_SRC = os.path.join(ROOT, "site")
OUT = os.path.join(ROOT, "_site")
POD_SRC = os.path.join(ROOT, "podcast插畫")
RSS_URL = "https://feed.firstory.me/rss/user/cklabznee4z8p08728tgfauzn"
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
MAX_SIDE = 2400      # full-screen viewer
MID_SIDE = 1400      # inside the episode window


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


YT_FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=UC4ErmW38TjVICSTMydcmmJw"
_YT_TAGS = re.compile(r"Poca村長的故事時間|兒童睡前故事|兒童故事|睡前故事|小河童日記|喬弗瑞先生的冒險筆記|"
                      r"Chinese stories|新年故事|節慶故事|聖誕故事|萬聖節故事|端午節故事|^繪本$|^20\d\d$|"
                      r"^中秋節$|^端午節$|^清明節$|^中元節$|念信單元|聽眾來信|故事回顧|藍色的旅程")


def _core(text):
    text = re.sub(r"[\s　！!？?。．・·、，,：:（）()「」『』~～\-—–]", "", text)
    return text.lower()


def fill_youtube_from_channel(eps):
    """New episodes often have no YouTube link in the Firstory text. Look at the
    newest videos on the YouTube channel and link the one with the same story title."""
    try:
        req = urllib.request.Request(YT_FEED, headers={"User-Agent": "pocapoca-site-builder"})
        with urllib.request.urlopen(req, timeout=30) as r:
            root = ET.fromstring(r.read())
    except Exception as exc:
        print(f"  ! YouTube channel not read: {exc}")
        return
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    videos = []
    for en in root.findall("a:entry", ns):
        title = en.findtext("a:title", "", ns)
        vid = en.findtext("yt:videoId", "", ns)
        if re.search(r"連續聽|BGM|音樂", title):
            continue
        parts = [p.strip() for p in re.split(r"[｜|]", title) if p.strip() and not _YT_TAGS.search(p.strip())]
        if parts and vid:
            videos.append((_core(parts[0]), vid))
    for e in eps:
        if e["yt"]:
            continue
        t = re.sub(r"^EP\s*\d+\s*", "", e["title"], flags=re.I)
        t = re.sub(r"^(小河童日記|小河童|喬弗瑞先生的冒險筆記)\s*[：:]\s*", "", t)
        t = re.sub(r"[（(][^）)]*(繪本|節慶派對|系列)[^）)]*[）)]\s*$", "", t)
        c = _core(t)
        for vc, vid in videos:
            if vc and (vc == c or (len(vc) >= 3 and (vc in c or c in vc))):
                e["yt"] = vid
                break


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
    fill_youtube_from_channel(eps)
    keys = episode_keys([(e["title"], e["date"]) for e in eps])
    for e, k in zip(eps, keys):
        e["key"] = k
        e.update(overrides.get(k, {}))
    return eps


def is_blank(im):
    """True for an almost single-colour picture (an empty page background)."""
    from PIL import ImageStat
    t = im.convert("RGB")
    t.thumbnail((64, 64))
    return sum(ImageStat.Stat(t).stddev) / 3 < 8


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
    i = 0
    for f in files:
        try:
            im = Image.open(os.path.join(src, f))
            if is_blank(im):   # plain page background picked up from Wix, not an illustration
                print(f"  - skipped blank background {key}/{f}")
                continue
            i += 1
            name = f"{i:02d}.jpg"
            im = to_srgb(ImageOps.exif_transpose(im))   # CMYK etc. -> correct sRGB colours
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            im.save(os.path.join(dst, name), quality=84, optimize=True, progressive=True)
            mid = im.copy()
            mid.thumbnail((MID_SIDE, MID_SIDE), Image.LANCZOS)
            mid.save(os.path.join(dst, f"{i:02d}-m.jpg"), quality=82, optimize=True, progressive=True)
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


SITE_URL = "https://www.pocapocastoryvillage.com"
SHARE_PAGE = """<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="__DESC__">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Pocapoca 故事村">
<meta property="og:title" content="__TITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:image" content="__IMG__">
<meta property="og:url" content="__URL__">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="__URL__">
<meta http-equiv="refresh" content="0;url=../#__HASH__">
<script>location.replace("../#__HASH__");</script>
</head><body style="font-family:sans-serif;padding:40px;text-align:center">
<p><a href="../#__HASH__">__TITLE__</a></p></body></html>
"""


def write_share_page(e, gal):
    """A tiny page per episode (e.g. /ep185/) so a shared link shows that episode's
    title and picture in LINE / Facebook, then opens the episode on the site."""
    h = episode_hash(e)[1:]
    if gal:
        img = SITE_URL + "/" + gal[0].replace(".jpg", "-m.jpg")
    else:
        img = e["cover"] or SITE_URL + "/img/og.jpg"
    page = (SHARE_PAGE.replace("__TITLE__", html.escape(e["title"] + "｜Poca村長的故事時間"))
            .replace("__DESC__", html.escape(e["desc"] or "Pocapoca 故事村的 Podcast"))
            .replace("__IMG__", html.escape(img)).replace("__URL__", f"{SITE_URL}/{h}/")
            .replace("__HASH__", h))
    os.makedirs(os.path.join(OUT, h), exist_ok=True)
    with open(os.path.join(OUT, h, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)


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
        write_share_page(e, gal)
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
