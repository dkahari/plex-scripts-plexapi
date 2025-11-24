#!/usr/bin/env python3
"""Plex playlist export/import using plexapi.

Usage:
  Export: python playlist_export_import.py --export --url URL --token TOKEN --outdir ./exports "My Playlist"
  Import: python playlist_export_import.py --import --url URL --token TOKEN ./exports/My_Playlist_12345.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Dict, List, Optional

try:
    from plexapi.server import PlexServer
except Exception:
    raise SystemExit("Install plexapi: python -m pip install plexapi")


DEFAULT_USER_CONFIG = os.path.expanduser("~/.plex_playlist_config.json")


def sanitize_filename(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", s)


def find_config_path(cli_path: Optional[str]) -> Optional[str]:
    if cli_path:
        return os.path.expanduser(cli_path)
    # Prefer a local, git-ignored override file if present
    local_override = os.path.join(os.path.dirname(__file__), "playlist_config.local.json")
    if os.path.isfile(local_override):
        return local_override

    # Fallback to the regular local config next to the script
    local = os.path.join(os.path.dirname(__file__), "playlist_config.json")
    if os.path.isfile(local):
        return local
    if os.path.isfile(DEFAULT_USER_CONFIG):
        return DEFAULT_USER_CONFIG
    return None


def load_config(path: Optional[str]) -> Dict[str, str]:
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def init_config(path: Optional[str], url: Optional[str], token: Optional[str], outdir: Optional[str]) -> str:
    cfg_path = path or DEFAULT_USER_CONFIG
    cfg_path = os.path.expanduser(cfg_path)
    cfg = {"url": url or "", "token": token or "", "outdir": outdir or "./"}
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)
    return cfg_path


def get_plex(url: str, token: str) -> PlexServer:
    return PlexServer(url.rstrip("/"), token)


def export_playlist(plex: PlexServer, title_or_key: str, outdir: str) -> str:
    pl = None
    for p in plex.playlists():
        if p.title == title_or_key or str(getattr(p, "ratingKey", "")) == str(title_or_key):
            pl = p
            break
    if pl is None:
        raise SystemExit("Playlist not found")

    data = {"playlist": {"title": pl.title, "ratingKey": getattr(pl, "ratingKey", None)}, "items": []}
    for it in pl.items():
        guid = None
        if getattr(it, "guid", None):
            guid = str(it.guid)
        elif getattr(it, "guids", None):
            try:
                guid = str(it.guids[0])
            except Exception:
                guid = None
        data["items"].append({
            "ratingKey": getattr(it, "ratingKey", None),
            "guid": guid,
            "type": getattr(it, "type", None),
            "title": getattr(it, "title", None),
        })

    os.makedirs(outdir, exist_ok=True)
    fname = f"{sanitize_filename(data['playlist']['title'])}_{data['playlist']['ratingKey']}.json"
    path = os.path.join(outdir, fname)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return path


def import_playlist(plex: PlexServer, json_file: str, delete_existing: bool = True) -> None:
    with open(json_file, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    title = data["playlist"].get("title")
    items = data.get("items", [])

    found = []
    missing = []
    for it in items:
        rk = it.get("ratingKey")
        g = it.get("guid")
        obj = None
        if rk:
            try:
                obj = plex.fetchItem(rk)
            except Exception:
                obj = None
        if obj is None and g:
            try:
                res = plex.search(guid=g)
                if res:
                    obj = res[0]
            except Exception:
                obj = None
        if obj:
            found.append(obj)
        else:
            missing.append(it)

    if missing:
        print(f"Warning: {len(missing)} items missing; they will be skipped")
    if not found:
        raise SystemExit("No items found on server; aborting")

    if delete_existing:
        for p in plex.playlists():
            if p.title == title:
                try:
                    p.delete()
                except Exception:
                    try:
                        plex.deletePlaylist(p)
                    except Exception:
                        pass

    plex.createPlaylist(title, items=found)
    print(f"Created playlist '{title}' with {len(found)} items (skipped {len(missing)})")


def main() -> None:
    p = argparse.ArgumentParser()
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument("--export", action="store_true")
    grp.add_argument("--import", dest="do_import", action="store_true")
    p.add_argument("--url", required=False, help="Plex base URL")
    p.add_argument("--token", required=False, help="Plex token")
    p.add_argument("--outdir", default=None, help="Output dir for exports")
    p.add_argument("--config", default=None, help="Path to JSON config file (keys: url, token, outdir)")
    p.add_argument("--init-config", action="store_true", help="Write a config file (path from --config or default) and exit")
    p.add_argument("--no-delete", dest="delete_existing", action="store_false", help="Do not delete existing playlist on import")
    p.add_argument("target", help="Playlist title (export) or json file (import)")
    args = p.parse_args()

    cfg_path = find_config_path(args.config)
    cfg = load_config(cfg_path)

    if args.init_config:
        created = init_config(args.config, args.url or cfg.get("url"), args.token or cfg.get("token"), args.outdir or cfg.get("outdir"))
        print(f"Wrote config to {created}")
        return

    final_url = args.url or cfg.get("url")
    final_token = args.token or cfg.get("token")
    final_outdir = args.outdir or cfg.get("outdir") or "./"

    if not final_url or not final_token:
        raise SystemExit("Plex URL and token must be provided via CLI or config file")

    plex = get_plex(final_url, final_token)
    if args.export:
        out = export_playlist(plex, args.target, final_outdir)
        print(f"Exported to {out}")
    else:
        import_playlist(plex, args.target, delete_existing=args.delete_existing)


if __name__ == "__main__":
    main()
