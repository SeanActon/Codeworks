"""Collect episode numbers and titles from TheTVDB's public season pages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

TVDB_BASE_URL = "https://www.thetvdb.com"
SEASON_ORDER_PATHS = {
    "aired": "official",
    "dvd": "dvd",
    "absolute": "absolute",
}
REQUEST_TIMEOUT_SECONDS = 30


class EpisodeTableParser(HTMLParser):
    """Read episode numbers and titles from the season table."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.episodes: list[dict[str, int | str]] = []
        self._in_row = False
        self._in_cell = False
        self._cells: list[str] = []
        self._cell_text = ""

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "tr":
            self._in_row = True
            self._cells = []
        elif tag == "td" and self._in_row:
            self._in_cell = True
            self._cell_text = ""

    def handle_data(self, data: str) -> None:
        if self._in_row and self._in_cell:
            self._cell_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._in_cell:
            self._cells.append(" ".join(self._cell_text.split()))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            self._append_episode()
            self._in_row = False

    def _append_episode(self) -> None:
        if len(self._cells) < 2:
            return

        match = re.fullmatch(r"S\d+E(\d+)", self._cells[0])
        title = self._cells[1]
        if match and title:
            self.episodes.append(
                {"episode_number": int(match.group(1)), "title": title}
            )


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={"User-Agent": "EpisodeNamer/1.0 (episode metadata fetcher)"},
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Could not fetch {url}: {exc}") from exc


def find_season_numbers(series_html: str, slug: str, order_path: str) -> list[int]:
    path_pattern = re.escape(f"/series/{slug}/seasons/{order_path}/")
    season_pattern = re.compile(
        rf"""href=["'](?:https?://(?:www\.)?thetvdb\.com)?{path_pattern}(\d+)["']""",
        re.IGNORECASE,
    )
    return sorted({int(match.group(1)) for match in season_pattern.finditer(series_html)})


def fetch_season_episodes(
    slug: str, order_path: str, season_number: int
) -> list[dict[str, int | str]]:
    encoded_slug = quote(slug, safe="-")
    url = (
        f"{TVDB_BASE_URL}/series/{encoded_slug}/seasons/"
        f"{order_path}/{season_number}"
    )
    parser = EpisodeTableParser()
    parser.feed(fetch_text(url))
    return parser.episodes


def collect_episodes(config: dict[str, str]) -> dict[str, object]:
    show_name = config["show_name"]
    slug = config["tvdb_slug"].strip("/")
    configured_order = config["season_order"].lower()
    if configured_order not in SEASON_ORDER_PATHS:
        supported = ", ".join(SEASON_ORDER_PATHS)
        raise ValueError(
            f"Unsupported season_order {configured_order!r}; choose: {supported}"
        )

    order_path = SEASON_ORDER_PATHS[configured_order]
    series_url = f"{TVDB_BASE_URL}/series/{quote(slug, safe='-')}"
    series_html = fetch_text(series_url)
    season_numbers = find_season_numbers(series_html, slug, order_path)
    if not season_numbers:
        raise RuntimeError(
            f"No {configured_order} seasons found for TVDB series {slug!r}."
        )

    seasons: list[dict[str, object]] = []
    for season_number in season_numbers:
        episodes = fetch_season_episodes(slug, order_path, season_number)
        if episodes:
            seasons.append(
                {"season_number": season_number, "episodes": episodes}
            )

    if not seasons:
        raise RuntimeError(f"No episodes found for TVDB series {slug!r}.")

    return {
        "show_name": show_name,
        "tvdb_slug": slug,
        "season_order": configured_order,
        "source": series_url,
        "seasons": seasons,
    }


def load_config(path: Path) -> dict[str, str]:
    try:
        with path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read config file {path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError("Config file must contain a JSON object.")

    required = {"show_name", "tvdb_slug", "season_order", "output_file"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"Missing config keys: {', '.join(sorted(missing))}")
    for key in required:
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"Config value {key!r} must be a non-empty string.")
    return config


def main() -> int:
    argument_parser = argparse.ArgumentParser(
        description="Fetch episode numbers and titles from TheTVDB."
    )
    argument_parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).with_name("config.json"),
        help="JSON config file (defaults to config.json beside this script).",
    )
    args = argument_parser.parse_args()

    try:
        config = load_config(args.config)
        episode_data = collect_episodes(config)
        output_path = Path(config["output_file"])
        if not output_path.is_absolute():
            output_path = args.config.resolve().parent / output_path
        with output_path.open("w", encoding="utf-8", newline="\n") as output_file:
            json.dump(episode_data, output_file, ensure_ascii=False, indent=2)
            output_file.write("\n")
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Could not write output file: {exc}", file=sys.stderr)
        return 1

    episode_count = sum(len(season["episodes"]) for season in episode_data["seasons"])
    print(
        f"Saved {episode_count} episodes across "
        f"{len(episode_data['seasons'])} seasons to {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())