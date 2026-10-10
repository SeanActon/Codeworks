# EpisodeNamer

Fetch episode numbers and titles from a show's public season pages on TheTVDB
and save the result as JSON. It uses only the Python standard library.

## Usage

Edit `config.json` to select a show and season order, then run:

```powershell
python main.py
```

Use another config file with `python main.py --config path\to\config.json`.
The output path is resolved relative to the config file unless it is absolute.

Configuration fields:

- `show_name`: display name included in the output.
- `tvdb_slug`: TheTVDB series URL slug, such as `life-is-worth-living`.
- `season_order`: `aired`, `dvd`, or `absolute`.
- `output_file`: JSON output path.

TheTVDB's v4 API can return episode data, but it requires an API key and an
authenticated bearer token. This script instead reads the public TVDB pages,
so it does not need credentials. `aired` maps to TheTVDB's `official` season
pages, which are labeled **Aired Order** on the site. Empty seasons, including
an empty Specials season, are omitted.
