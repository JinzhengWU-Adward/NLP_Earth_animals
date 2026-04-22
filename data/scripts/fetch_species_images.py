#!/usr/bin/env python3
"""
Fetch images for species listed in data/species.json.

Strategy:
- For each species_name, query Wikimedia/Wikipedia API for a representative image.
- Download the image into data/raw_data/pic with filename: "<id>_<EnglishName>.<ext>"
- Skip already-downloaded files so the script is resumable.

Notes:
- This uses public Wikimedia endpoints (no API key required).
- Some species may not have a clear page image; those will be reported and skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Any, Optional, Tuple


WIKI_API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


class RateLimitedError(RuntimeError):
    def __init__(self, message: str, retry_after_s: Optional[float] = None):
        super().__init__(message)
        self.retry_after_s = retry_after_s


@dataclass(frozen=True)
class Species:
    id: str
    species_name: str


def _slugify_filename(value: str) -> str:
    # Keep it readable and filesystem-safe.
    v = value.strip().replace(" ", "_")
    v = re.sub(r"[\\/:*?\"<>|]+", "_", v)
    v = re.sub(r"[\(\)\[\]\{\}]+", "", v)
    v = re.sub(r"_+", "_", v).strip("_")
    return v or "unknown"


def _http_get_json(url: str, timeout_s: int = 30) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NLP_Earth_animals/1.1 (image fetch script; educational use)",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            data = resp.read()
        return json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            ra = e.headers.get("Retry-After")
            retry_after_s = float(ra) if ra and ra.isdigit() else None
            raise RateLimitedError(f"HTTP 429 for {url}", retry_after_s=retry_after_s)
        raise


def _http_download(url: str, dest_path: str, timeout_s: int = 60) -> Tuple[int, str]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NLP_Earth_animals/1.1 (image fetch script; educational use)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            status = getattr(resp, "status", 200)
            content_type = resp.headers.get("Content-Type", "")
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, "wb") as f:
                f.write(resp.read())
        return status, content_type
    except urllib.error.HTTPError as e:
        if e.code == 429:
            ra = e.headers.get("Retry-After")
            retry_after_s = float(ra) if ra and ra.isdigit() else None
            raise RateLimitedError(f"HTTP 429 for {url}", retry_after_s=retry_after_s)
        raise


def _wiki_best_title(species_name: str) -> Optional[str]:
    params = {
        "action": "opensearch",
        "format": "json",
        "search": species_name,
        "limit": "1",
        "namespace": "0",
        "redirects": "resolve",
    }
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    payload = _http_get_json(url)
    # payload: [search, [titles], [descriptions], [urls]]
    if isinstance(payload, list) and len(payload) >= 2 and isinstance(payload[1], list) and payload[1]:
        t0 = payload[1][0]
        if isinstance(t0, str) and t0.strip():
            return t0.strip()
    return None


def _wiki_page_image_url(species_name: str, thumb_px: int = 900) -> Optional[str]:
    # Prefer thumbnails to reduce load and avoid 429.
    # docs: https://www.mediawiki.org/wiki/API:Page_images
    title = _wiki_best_title(species_name) or species_name
    params = {
        "action": "query",
        "format": "json",
        "prop": "pageimages",
        "piprop": "thumbnail",
        "pithumbsize": str(thumb_px),
        "redirects": "1",
        "titles": title,
    }
    url = WIKI_API + "?" + urllib.parse.urlencode(params)
    payload = _http_get_json(url)
    pages = payload.get("query", {}).get("pages", {})
    for _page_id, page in pages.items():
        thumb = page.get("thumbnail")
        if isinstance(thumb, dict) and thumb.get("source"):
            return str(thumb["source"])
    # Common title variants: strip parenthetical hints like "(Seahorse)".
    simplified = re.sub(r"\s*\(.*?\)\s*", "", species_name).strip()
    if simplified and simplified != species_name:
        params["titles"] = simplified
        url2 = WIKI_API + "?" + urllib.parse.urlencode(params)
        payload2 = _http_get_json(url2)
        pages2 = payload2.get("query", {}).get("pages", {})
        for _page_id, page in pages2.items():
            thumb2 = page.get("thumbnail")
            if isinstance(thumb2, dict) and thumb2.get("source"):
                return str(thumb2["source"])
    return None


def _commons_file_image_url(species_name: str, thumb_px: int = 900) -> Optional[str]:
    # Fallback: search Wikimedia Commons for a relevant file (namespace 6).
    # Then fetch a thumbnail URL via imageinfo.
    q = species_name
    q = re.sub(r"\s*\(.*?\)\s*", "", q).strip() or species_name
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srnamespace": "6",
        "srlimit": "5",
        "srsearch": q,
    }
    s_url = COMMONS_API + "?" + urllib.parse.urlencode(search_params)
    payload = _http_get_json(s_url)
    results = payload.get("query", {}).get("search", [])
    titles: list[str] = []
    for r in results:
        t = r.get("title")
        if isinstance(t, str) and t.startswith("File:"):
            titles.append(t)
    if not titles:
        return None

    info_params = {
        "action": "query",
        "format": "json",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": str(thumb_px),
        "titles": "|".join(titles),
    }
    i_url = COMMONS_API + "?" + urllib.parse.urlencode(info_params)
    payload2 = _http_get_json(i_url)
    pages = payload2.get("query", {}).get("pages", {})
    for _page_id, page in pages.items():
        ii = page.get("imageinfo")
        if isinstance(ii, list) and ii:
            first = ii[0]
            if isinstance(first, dict):
                # Prefer thumburl (sized) to avoid large downloads.
                if first.get("thumburl"):
                    return str(first["thumburl"])
                if first.get("url"):
                    return str(first["url"])
    return None


def _infer_extension_from_url_or_type(url: str, content_type: str) -> str:
    path = urllib.parse.urlparse(url).path
    _, ext = os.path.splitext(path)
    ext = ext.lower().strip(".")
    if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
        return "jpg" if ext == "jpeg" else ext
    ct = (content_type or "").lower()
    if "image/jpeg" in ct:
        return "jpg"
    if "image/png" in ct:
        return "png"
    if "image/gif" in ct:
        return "gif"
    if "image/webp" in ct:
        return "webp"
    return "jpg"


def _load_species(path: str) -> list[Species]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    out: list[Species] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sid = str(item.get("id", "")).strip()
        name = str(item.get("species_name", "")).strip()
        if sid and name:
            out.append(Species(id=sid, species_name=name))

    def sort_key(s: Species) -> Tuple[int, str]:
        m = re.match(r"^sp_(\d+)$", s.id)
        return (int(m.group(1)) if m else 10**9, s.id)

    out.sort(key=sort_key)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--species-json",
        default=os.path.join("data", "species.json"),
        help="Path to species.json",
    )
    parser.add_argument(
        "--out-dir",
        default=os.path.join("data", "raw_data", "pic"),
        help="Output directory for downloaded images",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="Seconds to sleep between requests (politeness)",
    )
    parser.add_argument(
        "--thumb-px",
        type=int,
        default=900,
        help="Thumbnail width in pixels (smaller reduces rate limiting)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Max retries on HTTP 429 with backoff",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of species to process (0 = no limit)",
    )
    args = parser.parse_args()

    species = _load_species(args.species_json)
    if args.limit and args.limit > 0:
        species = species[: args.limit]

    os.makedirs(args.out_dir, exist_ok=True)

    ok = 0
    skipped = 0
    failed = 0

    for idx, sp in enumerate(species, start=1):
        safe_name = _slugify_filename(sp.species_name)
        base = f"{sp.id}_{safe_name}"

        # Skip if any image file already exists for this species id+name.
        existing = [
            os.path.join(args.out_dir, base + "." + ext)
            for ext in ("jpg", "png", "gif", "webp")
        ]
        if any(os.path.exists(p) for p in existing):
            skipped += 1
            continue

        try:
            img_url = None
            source = None

            # Source 1: Wikipedia thumbnail
            try:
                img_url = _wiki_page_image_url(sp.species_name, thumb_px=args.thumb_px)
                source = "wikipedia" if img_url else None
            except RateLimitedError:
                img_url = None
                source = None

            # Source 2: Wikimedia Commons search fallback
            if not img_url:
                try:
                    img_url = _commons_file_image_url(sp.species_name, thumb_px=args.thumb_px)
                    source = "commons" if img_url else None
                except RateLimitedError:
                    img_url = None
                    source = None

            if not img_url:
                failed += 1
                print(f"[{idx:03d}/{len(species):03d}] no image: {sp.id} {sp.species_name}")
                time.sleep(args.sleep)
                continue

            tmp_path = os.path.join(args.out_dir, base + ".download")

            attempt = 0
            backoff_s = max(args.sleep, 1.0)
            while True:
                attempt += 1
                try:
                    status, content_type = _http_download(img_url, tmp_path)
                    ext = _infer_extension_from_url_or_type(img_url, content_type)
                    final_path = os.path.join(args.out_dir, base + "." + ext)
                    os.replace(tmp_path, final_path)
                    break
                except RateLimitedError as e:
                    if attempt > args.max_retries:
                        raise
                    wait_s = e.retry_after_s if e.retry_after_s is not None else backoff_s
                    wait_s = min(max(wait_s, 1.0), 60.0)
                    print(
                        f"[{idx:03d}/{len(species):03d}] 429 rate-limited ({source}); "
                        f"retry in {wait_s:.1f}s: {sp.id} {sp.species_name}"
                    )
                    time.sleep(wait_s)
                    backoff_s = min(backoff_s * 2.0, 60.0)

            ok += 1
            print(
                f"[{idx:03d}/{len(species):03d}] ok ({source}): {os.path.basename(final_path)}"
            )
        except Exception as e:
            failed += 1
            try:
                if os.path.exists(os.path.join(args.out_dir, base + ".download")):
                    os.remove(os.path.join(args.out_dir, base + ".download"))
            except Exception:
                pass
            print(f"[{idx:03d}/{len(species):03d}] fail: {sp.id} {sp.species_name} ({e})")
        finally:
            time.sleep(args.sleep)

    print(f"done. ok={ok} skipped={skipped} failed={failed} out_dir={args.out_dir}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

