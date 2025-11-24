# Playlist Export/Import

This small script exports and imports Plex playlists to JSON files.

Features
- Export each playlist to its own JSON file. The file contains playlist metadata and an array of item entries (each item includes ratingKey and GUID when available).
- Import reads a playlist JSON file, verifies each exported track exists on the target Plex server before adding. It does NOT create new tracks.
- Existing playlists with the same title are deleted before the import so the playlist is cleared and re-created.

Requirements
- Python 3.8+
- `requests` (see `requirements.txt`)

Usage
- Export a playlist:

```powershell
python playlist_export_import.py --export --url http://127.0.0.1:32400 --token YOUR_TOKEN --outdir ./exports "My Playlist"
```

- Import a playlist (file produced by export):

```powershell
python playlist_export_import.py --import --url http://127.0.0.1:32400 --token YOUR_TOKEN ./exports/My_Playlist_12345.json
```

Config file
---------

You can avoid passing `--url` and `--token` every time by creating a config file. The script will look for a local `playlist_config.json` in the same folder as the script, then a user config at `~/.plex_playlist_config.json`. You can also specify `--config <path>` to force a specific config file.

Example (create `~/.plex_playlist_config.json` or `playlist_config.json`):

```json
{
	"url": "http://127.0.0.1:32400",
	"token": "your_plex_token_here",
	"outdir": "./exports"
}
```

To write a config file from the CLI (fills values from provided args):

```powershell
python playlist_export_import.py --init-config --url http://127.0.0.1:32400 --token YOUR_TOKEN
```


Notes
- The import operation scans all libraries to build a GUID -> ratingKey map. This can take some time on large libraries but is necessary to verify items exist on the target server.
- If the script cannot match any exported tracks to items on the server the import will abort.

If you want, I can:
- Add unit tests or a small dry-run mode that only reports which items would be imported.
- Replace the direct HTTP calls with `plexapi` objects for higher-level operations (right now the script uses the Plex HTTP API via `requests` for predictability).

Local git-ignored config (recommended)
---------

To avoid accidentally committing your Plex token to git, create a local override file named `playlist_config.local.json` in the `server_management/` folder. This file is ignored by the repository `.gitignore` and takes precedence over `playlist_config.json` and `~/.plex_playlist_config.json`.

Example `playlist_config.local.json`:

```json
{
	"url": "http://127.0.0.1:32400",
	"token": "your_plex_token_here",
	"outdir": "./exports"
}
```

Precedence when the script runs:
- CLI arguments (highest)
- `server_management/playlist_config.local.json` (if present)
- `server_management/playlist_config.json` (next to the script)
- `~/.plex_playlist_config.json` (user-wide)

There is also a `server_management/playlist_config.local.json.example` file in the repo you can copy-and-edit to create your local config.
