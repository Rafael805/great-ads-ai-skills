#!/usr/bin/env python3
"""
Thin client for the Great Ads AI hosted Style Library API.

Creates ONE new reusable style in your Great Ads AI Style Library — a saved look
(a reusable generation prompt + optional example images) that every downstream
generator (/static-ad and the other creative skills) can then pick to render
on-brand creatives in that look. Runs entirely on the Great Ads AI API with your
one workspace key; there is NO local image generation and no AI-provider keys.

  - `create ...`  -> upload any local example images, then create the style row
                     (org-global, one-brand, or a shared public preset)

Visibility (--scope):
  - global  (default)  the style is visible to ALL brands in your workspace
  - brand              scope the style to ONE brand (requires --brand <slug>)
  - public             a shared preset visible to EVERY agency (admin key only —
                       a normal workspace key gets a 403 here, by design)

Config: reads GREAT_ADS_INTERNAL_API_KEY + GREAT_ADS_INTERNAL_BASE_URL from
~/.config/great-marketing-ai/great-marketing-ai.env (or great-ads.env), then a .env
walking up from the cwd, then the process environment. Stdlib only — no pip installs.

Exit codes: 0 success · 2 misconfiguration / bad usage · 1 network or API failure.
"""

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "great-marketing-ai"

STYLE_TYPES = ["ad", "meme", "carousel", "reel_cover", "thumbnail"]
_IMAGE_MIME = {"image/png", "image/jpeg", "image/webp", "image/gif"}

# Production app origin for the shareable Style Library link when the API base is a
# localhost dev host (never a useful link for a human).
_PROD_APP_URL = "https://www.greatads.io"
_LOCALHOST_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")


def _eprint(*a):
    print(*a, file=sys.stderr)


def _parse_env_file(path: Path) -> dict:
    out = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def load_config() -> dict:
    """Config-dir files first, then a project .env walking up, then os.environ.
    Already-set values are never overridden (matches the team env precedence)."""
    cfg: dict = {}
    candidates = [CONFIG_DIR / "great-marketing-ai.env", CONFIG_DIR / "great-ads.env"]
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / ".env").exists() or (parent / ".env.local").exists():
            candidates += [parent / ".env.local", parent / ".env"]
            break
    for f in candidates:
        for k, v in _parse_env_file(f).items():
            cfg.setdefault(k, v)
    for k, v in os.environ.items():
        cfg.setdefault(k, v)
    return cfg


def _bases(cfg: dict) -> list:
    raw = cfg.get("GREAT_ADS_INTERNAL_BASE_URL", "https://www.greatads.io")
    return [b.strip().rstrip("/") for b in raw.split(",") if b.strip()]


def _key(cfg: dict) -> str:
    key = cfg.get("GREAT_ADS_INTERNAL_API_KEY", "").strip()
    if not key:
        sys.exit(
            "Missing GREAT_ADS_INTERNAL_API_KEY. Generate one in the Great Ads AI "
            "dashboard → Settings → Integrations → Connect to Claude, then add it to "
            f"{CONFIG_DIR / 'great-marketing-ai.env'}"
        )
    return key


def _public_base(bases: list) -> str:
    """First non-localhost API base (the app origin), else the prod app URL."""
    for b in bases:
        host = urllib.parse.urlparse(b).hostname or ""
        if host and not any(host == h for h in _LOCALHOST_HOSTS):
            return b.rstrip("/")
    return _PROD_APP_URL


def _tab_for(style_type: str, ad_format: str) -> str:
    """Mirror the server's Style Library tab mapping."""
    if style_type == "ad":
        return "video" if ad_format == "video" else "static"
    if style_type == "thumbnail":
        return "thumbnails"
    return "content"


def _content_type(path: Path) -> str:
    ct = mimetypes.guess_type(str(path))[0] or ""
    return ct if ct in _IMAGE_MIME else "image/png"


def _request_json(method: str, base: str, path: str, key: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode() or "{}")


def _upload_image(base: str, key: str, path: Path, brand: str) -> str:
    """Multipart-POST one image to the style-upload endpoint, return its public URL."""
    url = f"{base}/api/internal/creative-styles/upload"
    if brand:
        url += f"?brand={urllib.parse.quote(brand)}"
    boundary = "----greatAdsStyleUploadBoundary"
    ct = _content_type(path)
    pre = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {ct}\r\n\r\n"
    ).encode()
    post = f"\r\n--{boundary}--\r\n".encode()
    payload = pre + path.read_bytes() + post
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        out = json.loads(resp.read().decode() or "{}")
    public_url = (out.get("data") or {}).get("url")
    if not public_url:
        raise RuntimeError(f"upload returned no url for {path.name}: {out}")
    return public_url


def _upload_all(bases, key, images, brand, remember):
    """Upload every image, trying each base until one succeeds for all of them.

    401/403 are authoritative (identical across bases) and raise immediately; other
    errors fall through to the next base. Each successful upload is passed to
    `remember(url)` so the caller can report partial progress on a later failure.
    """
    last = None
    for base in bases:
        urls = []
        try:
            for path in images:
                url = _upload_image(base, key, path, brand)
                urls.append(url)
                remember(url)
                print(f"  uploaded {path.name} -> {url}")
            return urls
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in (401, 403):
                raise RuntimeError(f"auth/scope error {e.code} during upload at {base}: {detail}")
            last = f"{e.code} at {base}: {detail}"
        except Exception as e:  # noqa: BLE001 — try the next base on any transport error
            last = f"{base}: {e}"
    raise RuntimeError(f"upload failed on all base URLs ({', '.join(bases)}) — {last}")


def _create_style(bases, key, body):
    """POST the create call, trying each base; return the response `data` dict.

    401/403 are authoritative and raise immediately; org-resolution / 5xx errors
    fall through to the next base (org resolution is per-server env — a 400 on one
    base may succeed on another that has GREAT_ADS_AGENCY_ORG_ID set).
    """
    last = None
    for base in bases:
        try:
            res = _request_json("POST", base, "/api/internal/creative-styles", key, body)
            return res.get("data") or {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code in (401, 403):
                raise RuntimeError(f"auth/scope error {e.code} at {base}: {detail}")
            last = f"{e.code} at {base}: {detail}"
        except Exception as e:  # noqa: BLE001 — try the next base on any transport error
            last = f"{base}: {e}"
    raise RuntimeError(f"create failed on all base URLs ({', '.join(bases)}) — {last}")


def _report_reusable(urls):
    """On failure, show how to retry without re-uploading (no orphaned storage)."""
    if not urls:
        return
    _eprint("\nThese reference images are already uploaded — retry the SAME command but")
    _eprint("replace each --image with the matching --reference-url (no new uploads):")
    for url in urls:
        _eprint(f"  --reference-url {url}")


def _library_url(data: dict, bases: list, args) -> str:
    """Prefer the server-provided brand-scoped libraryUrl; else construct one."""
    if data.get("libraryUrl"):
        return data["libraryUrl"]
    tab = data.get("tab") or _tab_for(args.style_type, args.ad_format or "")
    base = _public_base(bases)
    if args.scope == "brand" and args.brand:
        return f"{base}/{urllib.parse.quote(args.brand)}/style-library?tab={tab}"
    return f"{base}/style-library?tab={tab}"


def cmd_create(args, cfg):
    key = _key(cfg)
    bases = _bases(cfg)

    if args.scope == "brand" and not args.brand:
        sys.exit("error: --scope brand requires --brand <slug>.")
    if args.style_type == "ad" and not args.ad_format:
        _eprint("note: style-type ad without --ad-format defaults to the Static Ads tab.")

    images = []
    for img in args.image:
        path = Path(img)
        if not path.is_file():
            _eprint(f"warning: image not found, skipping: {path}")
            continue
        images.append(path)

    reference_urls = []
    for u in args.reference_url:
        u = (u or "").strip()
        if not u:
            continue
        if not (u.startswith("http://") or u.startswith("https://")):
            _eprint(f"warning: ignoring non-URL --reference-url: {u}")
            continue
        reference_urls.append(u)

    platforms = [s.strip() for s in (args.platforms or "").split(",") if s.strip()]

    # --- Phase 1: upload local example images (once), get their public URLs ----
    uploaded = []
    upload_urls = []
    if images:
        print(f"Uploading {len(images)} example image(s) ...")
        try:
            upload_urls = _upload_all(bases, key, images, args.brand or "", uploaded.append)
        except RuntimeError as e:
            _eprint(f"error: {e}")
            _report_reusable(uploaded)
            return 1

    ref_urls = upload_urls + reference_urls

    # --- Build the create body ------------------------------------------------
    body = {
        "name": args.name,
        "styleType": args.style_type,
        "category": args.category,
        "description": args.description,
        "promptTemplate": args.prompt_template,
        "referenceImages": ref_urls,
        "platforms": platforms,
    }
    if ref_urls:
        body["thumbnailUrl"] = ref_urls[0]
    if args.style_type == "ad" and args.ad_format:
        body["adFormat"] = args.ad_format
    if args.scope == "public":
        body["isPreset"] = True
    elif args.scope == "brand" and args.brand:
        body["brand"] = args.brand
    # --scope global sends no `brand`/`isPreset`: a per-org key resolves the org from
    # the key itself; the global/admin key resolves it from GREAT_ADS_AGENCY_ORG_ID.

    # --- Phase 2: create the style --------------------------------------------
    try:
        data = _create_style(bases, key, body)
    except RuntimeError as e:
        _eprint(f"error: {e}")
        _report_reusable(ref_urls)
        return 1

    style = data.get("style") or {}
    print(
        f"\nCreated style \"{style.get('name', args.name)}\" "
        f"(id {style.get('id', '?')}, type {style.get('style_type', args.style_type)})."
    )
    scope_label = {
        "public": "public preset (all agencies)",
        "brand": f"brand-scoped to {args.brand}",
        "global": "org-global (all your brands)",
    }[args.scope]
    print(f"Scope: {scope_label}. Reference images: {len(ref_urls)}.")
    tab = data.get("tab") or _tab_for(args.style_type, args.ad_format or "")
    print(f"Find it under the Style Library '{tab}' tab.")
    print(f"View: {_library_url(data, bases, args)}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Great Ads AI Style Library thin client")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Create a new style in the Style Library")
    c.add_argument("--name", required=True, help="Style name (shown on the library card)")
    c.add_argument("--style-type", required=True, choices=STYLE_TYPES,
                   help="ad | meme | carousel | reel_cover | thumbnail")
    c.add_argument("--ad-format", choices=["static", "video"],
                   help="For style-type ad only: which Ad tab (static or video)")
    c.add_argument("--category", default="custom",
                   help="Category bucket (e.g. editorial, comparison, bold)")
    c.add_argument("--description", default="", help="One-line description of the style")
    c.add_argument("--prompt-template", default="",
                   help="Reusable generation prompt (use {{headline}}/{{subheadline}}/{{cta}} "
                        "and {{subject}} placeholders; keep it ratio-agnostic)")
    c.add_argument("--platforms", default="",
                   help="Comma list for content styles, e.g. instagram,linkedin,tiktok")
    c.add_argument("--scope", choices=["global", "brand", "public"], default="global",
                   help="global (all your brands, default) | brand (one brand) | "
                        "public (shared preset, admin key only)")
    c.add_argument("--brand", help="Brand slug — required for --scope brand; also lets a "
                                   "global key resolve the org for image storage")
    c.add_argument("--image", action="append", default=[],
                   help="Local example image to upload as a reference image (repeatable)")
    c.add_argument("--reference-url", action="append", default=[],
                   help="Already-hosted image URL to use as a reference image, skipping upload "
                        "(repeatable). Use to retry a failed create without re-uploading.")
    c.set_defaults(func=cmd_create)

    args = p.parse_args()
    return args.func(args, load_config()) or 0


if __name__ == "__main__":
    sys.exit(main())
