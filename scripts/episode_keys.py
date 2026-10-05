"""Folder names for podcast episodes, shared by build.py and migrate_wix.py.

Numbered episodes use their number:   "EP185"
Specials without a number use the air date: "20261018"
If two episodes would get the same name, the older one gets the date added,
for example "EP24-20210630".
"""
import re


def episode_keys(title_date_pairs):
    keys, used = [], set()
    for title, date in title_date_pairs:          # newest first, as in the RSS feed
        m = re.match(r"^EP\s*0*(\d+)", title.strip(), re.I)
        d = date.replace("-", "")
        key = f"EP{int(m.group(1))}" if m else d
        if key in used:
            key = f"{key}-{d}" if m else f"{key}-2"
            n = 2
            while key in used:
                n += 1
                key = f"{key.rsplit('-', 1)[0]}-{n}"
        used.add(key)
        keys.append(key)
    return keys
