#!/usr/bin/env python3
"""
crawl-data-webnovel — cào dữ liệu truyện từ webnovel.vn.

Với mỗi URL truyện:
  - tải ảnh bìa (og:image) về <Downloads>/webnovel/hinh-anh-ten-truyen/<slug>.<ext>
  - lấy tên truyện (og:title) + danh mục (các thẻ a.genre)
  - ghi/merge vào <Downloads>/webnovel/truyen-data.json

Cross-platform: tự tìm thư mục Downloads của máy đang chạy (Windows / macOS / Linux).
Chạy lại nhiều lần an toàn: ảnh đã có thì bỏ qua, truyện đã có trong JSON thì cập nhật.

Usage:
    python crawl.py <url> [<url> ...]
    python crawl.py --file urls.txt
    python crawl.py --file urls.txt --out /duong/dan/khac   # đổi thư mục gốc (mặc định ~/Downloads/webnovel)
"""
import sys
import os
import re
import json
import time
import argparse
import urllib.request
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
IMG_SUBDIR = "hinh-anh-ten-truyen"
JSON_NAME = "truyen-data.json"

# Bản JSON dùng chung với skill content-webnovel (đọc để chọn đúng thể loại toplist).
# Cross-platform: ~/.claude/skills/content-webnovel/data/truyen-data.json
SKILL_JSON_DIR = Path.home() / ".claude" / "skills" / "content-webnovel" / "data"


def downloads_dir() -> Path:
    """Thư mục Downloads của user, cross-platform. Fallback về home nếu không có."""
    home = Path.home()
    d = home / "Downloads"
    return d if d.is_dir() else home


def slug_from_url(url: str) -> str:
    """Lấy path đầu tiên sau domain làm slug (bỏ query/chương con)."""
    m = re.sub(r"^https?://(www\.)?webnovel\.vn/", "", url.strip())
    m = m.split("/")[0].split("?")[0].strip()
    return m


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def extract(html: str) -> dict:
    def meta(prop):
        m = re.search(r'<meta property="%s" content="([^"]*)"' % re.escape(prop), html)
        return m.group(1).strip() if m else ""
    title = meta("og:title")
    image = meta("og:image")
    genres = re.findall(r'<a class="genre"[^>]*title="([^"]*)"', html)
    # bỏ trùng, giữ thứ tự
    seen, uniq = set(), []
    for g in genres:
        g = g.strip()
        if g and g not in seen:
            seen.add(g)
            uniq.append(g)
    # Tác giả: <p class="book-detail__author..."> ... <a ...>Tên</a>
    author = ""
    ma = re.search(r'<p class="book-detail__author[^"]*"[^>]*>(.*?)</p>', html, re.S)
    if ma:
        inner = re.search(r'<a [^>]*>([^<]*)</a>', ma.group(1))
        if inner:
            author = re.sub(r'\s+', ' ', inner.group(1)).strip()
    return {"title": title, "image": image, "genres": uniq, "author": author}


def ext_from_url(img_url: str) -> str:
    e = img_url.split("?")[0].rsplit(".", 1)
    e = e[1].lower() if len(e) == 2 else "webp"
    return e if e in ("webp", "jpg", "jpeg", "png", "gif") else "webp"


def find_local_image(img_dir: Path, slug: str):
    for f in img_dir.glob(slug + ".*"):
        return f.name
    return None


def download_image(img_url: str, dest: Path, referer: str) -> bool:
    req = urllib.request.Request(img_url, headers={"User-Agent": UA, "Referer": referer})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 1000:
        return False
    dest.write_bytes(data)
    return True


def load_json(path: Path) -> list:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def read_urls(args) -> list:
    urls = []
    if args.file:
        urls += [ln.strip() for ln in Path(args.file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    urls += [u for u in args.urls if u.strip()]
    return urls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("urls", nargs="*", help="URL truyện webnovel.vn")
    ap.add_argument("--file", help="File chứa danh sách URL (mỗi dòng 1 URL)")
    ap.add_argument("--out", help="Thư mục gốc (mặc định ~/Downloads/webnovel)")
    args = ap.parse_args()

    urls = read_urls(args)
    if not urls:
        print("Chưa có URL. Truyền URL trực tiếp hoặc --file urls.txt", file=sys.stderr)
        sys.exit(2)

    root = Path(args.out) if args.out else (downloads_dir() / "webnovel")
    img_dir = root / IMG_SUBDIR
    img_dir.mkdir(parents=True, exist_ok=True)
    json_path = root / JSON_NAME

    print("Thư mục gốc : %s" % root)
    print("Ảnh         : %s" % img_dir)
    print("JSON        : %s" % json_path)
    print("-" * 60)

    data = load_json(json_path)
    by_slug = {rec.get("slug"): rec for rec in data}

    seen = set()
    n_ok = n_new = n_upd = n_skip = n_fail = 0

    for url in urls:
        slug = slug_from_url(url)
        if not slug or slug in seen:
            continue
        seen.add(slug)
        page = "https://webnovel.vn/%s/" % slug

        try:
            html = fetch(page).decode("utf-8", "replace")
        except Exception as e:
            print("FAIL : %s (tải trang lỗi: %s)" % (slug, e))
            n_fail += 1
            continue

        info = extract(html)
        if not info["image"]:
            print("SKIP : %s (trang danh mục, không có ảnh bìa)" % slug)
            n_skip += 1
            continue

        # tải ảnh nếu chưa có
        local = find_local_image(img_dir, slug)
        if local:
            print("HAVE : %s (ảnh đã có)" % slug, end="")
        else:
            ext = ext_from_url(info["image"])
            dest = img_dir / ("%s.%s" % (slug, ext))
            try:
                if download_image(info["image"], dest, page):
                    local = dest.name
                    print("IMG  : %s" % dest.name, end="")
                else:
                    if dest.exists():
                        dest.unlink()
                    print("FAIL : %s (ảnh quá nhỏ)" % slug)
                    n_fail += 1
                    continue
            except Exception as e:
                print("FAIL : %s (tải ảnh lỗi: %s)" % (slug, e))
                n_fail += 1
                continue

        rec = {
            "tu_khoa": info["title"],
            "tac_gia": info["author"],
            "slug": slug,
            "link_truyen": page,
            "anh_local": "%s/%s" % (IMG_SUBDIR, local) if local else "",
            "anh_url": info["image"],
            "danh_muc": info["genres"],
        }

        author_tag = info["author"] or "?"
        genres_tag = " ".join(info["genres"]) if info["genres"] else "?"
        if slug in by_slug:
            by_slug[slug].update(rec)
            n_upd += 1
            print("  -> cập nhật | %s | %s" % (author_tag, genres_tag))
        else:
            by_slug[slug] = rec
            data.append(rec)
            n_new += 1
            print("  -> mới      | %s | %s" % (author_tag, genres_tag))
        n_ok += 1
        time.sleep(0.25)

    payload = json.dumps(data, ensure_ascii=False, indent=2)
    json_path.write_text(payload, encoding="utf-8")

    # Đồng bộ sang skill content-webnovel (để toplist chọn đúng thể loại)
    try:
        SKILL_JSON_DIR.mkdir(parents=True, exist_ok=True)
        skill_json = SKILL_JSON_DIR / JSON_NAME
        skill_json.write_text(payload, encoding="utf-8")
        print("Sync skill : %s" % skill_json)
    except Exception as e:
        print("WARN: không copy được sang skill content-webnovel: %s" % e)

    print("-" * 60)
    print("XONG: %d truyện trong JSON | mới %d, cập nhật %d | bỏ qua %d, lỗi %d"
          % (len(data), n_new, n_upd, n_skip, n_fail))
    print("File: %s" % json_path)


if __name__ == "__main__":
    main()
