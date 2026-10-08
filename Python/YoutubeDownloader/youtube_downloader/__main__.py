from __future__ import annotations

from pathlib import Path

from .helpers import download_video, load_config


PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_DIR / "config.json"


def main() -> None:
    video_url, skip_ffmpeg = load_config(CONFIG_PATH)
    output_paths = download_video(video_url, skip_ffmpeg)
    for output_path in output_paths:
        print(f"Video saved to: {output_path}")


if __name__ == "__main__":
    main()
