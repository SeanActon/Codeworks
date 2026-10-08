from __future__ import annotations

import json
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import yt_dlp


PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_DIR / "made videos"
TEMP_DIR = PROJECT_DIR / "TempVideos"


def load_config(config_path: Path) -> tuple[list[str], bool]:
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(
            f"Configuration file not found: {config_path}\n"
            "Copy config.example.json to config.json and set video_url."
        ) from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {config_path}: {error}") from error

    if not isinstance(config, dict):
        raise SystemExit(f"Expected a JSON object in {config_path}.")

    video_urls = config.get("video_url")
    if isinstance(video_urls, str):
        video_urls = [video_urls]
    if not isinstance(video_urls, list) or not video_urls:
        raise SystemExit(
            f"Set 'video_url' to a non-empty URL or array of URLs in {config_path}."
        )
    if any(not isinstance(url, str) or not url.strip() for url in video_urls):
        raise SystemExit(
            f"Every 'video_url' entry must be a non-empty string in {config_path}."
        )
    video_urls = [url.strip() for url in video_urls]

    skip_ffmpeg = config.get("skip_ffmpeg", False)
    if not isinstance(skip_ffmpeg, bool):
        raise SystemExit(
            f"'skip_ffmpeg' must be true or false in {config_path}."
        )

    return video_urls, skip_ffmpeg


def safe_filename(title: Any) -> str:
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(title)).strip(" .")
    filename = filename[:150].rstrip(" .")

    if not filename:
        filename = "video"
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", filename, re.I):
        filename = f"_{filename}"

    return filename


def run_ffmpeg_with_progress(command: list[str], duration: float | None) -> None:
    progress_queue: queue.Queue[str | None] = queue.Queue()
    started_at = time.monotonic()

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if process.stdout is None:
        raise RuntimeError("Could not read FFmpeg progress output.")

    def read_progress() -> None:
        for line in process.stdout:
            progress_queue.put(line.rstrip())
        progress_queue.put(None)

    reader = threading.Thread(target=read_progress, daemon=True)
    reader.start()

    elapsed_seconds = 0.0
    output_seconds = 0.0
    last_update_at = started_at
    stream_finished = False
    last_display_at = 0.0

    while not stream_finished:
        try:
            line = progress_queue.get(timeout=1)
        except queue.Empty:
            line = ""

        if line is None:
            stream_finished = True
        elif line.startswith("out_time_us="):
            try:
                output_seconds = int(line.partition("=")[2]) / 1_000_000
                last_update_at = time.monotonic()
            except ValueError:
                pass

        now = time.monotonic()
        elapsed_seconds = now - started_at
        if now - last_display_at >= 1:
            elapsed_label = time.strftime("%H:%M:%S", time.gmtime(elapsed_seconds))
            stalled_seconds = now - last_update_at
            if stalled_seconds >= 30:
                status = f"no progress update for {int(stalled_seconds)}s"
            else:
                status = "converting"

            if duration is not None and duration > 0:
                percentage = max(0.0, min(output_seconds / duration, 1.0))
                filled = int(percentage * 30)
                progress_bar = "#" * filled + "-" * (30 - filled)
                print(
                    f"\rFFmpeg [{progress_bar}] {percentage:5.1%} "
                    f"| {elapsed_label} elapsed | {status}",
                    end="",
                    flush=True,
                )
            else:
                output_label = time.strftime("%H:%M:%S", time.gmtime(output_seconds))
                print(
                    f"\rFFmpeg output {output_label} "
                    f"| {elapsed_label} elapsed | {status}",
                    end="",
                    flush=True,
                )
            last_display_at = now

    return_code = process.wait()
    reader.join()
    print()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def write_unreachable_report(
    report_path: Path, playlist_title: str, failures: list[str]
) -> None:
    lines = [
        f"Playlist: {playlist_title}",
        "",
    ]
    if failures:
        lines.extend(["Videos that could not be downloaded:", *failures])
    else:
        lines.append("No unreachable videos were detected.")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def download_video(video_url: str, skip_ffmpeg: bool = False) -> list[Path]:
    ffmpeg = None if skip_ffmpeg else shutil.which("ffmpeg")
    if not skip_ffmpeg and ffmpeg is None:
        raise SystemExit(
            "ffmpeg was not found on PATH. Install FFmpeg and try again."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    run_id = uuid.uuid4().hex
    run_temp_dir = TEMP_DIR / run_id
    run_temp_dir.mkdir()
    download_errors: dict[str, str] = {}
    download_errors_without_id: list[str] = []

    def record_download_error(progress: dict[str, Any]) -> None:
        if progress.get("status") != "error":
            return
        video_info = progress.get("info_dict")
        if not isinstance(video_info, dict):
            return
        error = progress.get("error") or video_info.get("error")
        reason = str(error or "Download failed.")
        video_id = video_info.get("id")
        if video_id is None:
            title = video_info.get("title") or "title unavailable"
            download_errors_without_id.append(f"{title}: {reason}")
        else:
            download_errors[str(video_id)] = reason

    try:
        ydl_options = {
            "format": (
                "best[ext=mp4]/best"
                if skip_ffmpeg
                else "bestvideo+bestaudio/best"
            ),
            "noplaylist": False,
            "outtmpl": str(run_temp_dir / "%(id)s.%(ext)s"),
            "ignoreerrors": True,
            "progress_hooks": [record_download_error],
        }
        if not skip_ffmpeg:
            ydl_options["merge_output_format"] = "mkv"

        try:
            with yt_dlp.YoutubeDL(ydl_options) as downloader:
                info = downloader.extract_info(video_url, download=True)
        except yt_dlp.DownloadError as error:
            raise SystemExit(f"Video download failed: {error}") from error

        if not isinstance(info, dict):
            raise SystemExit("yt-dlp did not return video information.")

        is_playlist = info.get("_type") == "playlist"
        playlist_title = info.get("title") or "Playlist"
        entries = info.get("entries")
        if is_playlist and entries is not None:
            entries = list(entries)
            videos = [entry for entry in entries if isinstance(entry, dict)]
        else:
            entries = []
            videos = [info]
        videos_by_id = {
            str(video["id"]): video
            for video in videos
            if video.get("id") is not None
        }

        source_files = sorted(
            path
            for path in run_temp_dir.iterdir()
            if path.is_file()
            and not path.name.endswith((".part", ".ytdl"))
        )
        if not source_files and not is_playlist:
            raise SystemExit(
                "yt-dlp completed without producing any video files."
            )

        destination_dir = OUTPUT_DIR
        if is_playlist:
            destination_dir = OUTPUT_DIR / safe_filename(playlist_title)
            destination_dir.mkdir(parents=True, exist_ok=True)
            downloaded_ids = {path.stem for path in source_files}
            failures_by_id: dict[str, str] = {}
            failures_without_id: list[str] = []

            for playlist_index, entry in enumerate(entries, start=1):
                if not isinstance(entry, dict):
                    failures_without_id.append(
                        f"Playlist item {playlist_index}: "
                        "title and video ID unavailable; yt-dlp could not "
                        "retrieve this entry."
                    )
                    continue

                video_id_value = entry.get("id")
                if video_id_value is None:
                    failures_without_id.append(
                        f"Playlist item {playlist_index}: "
                        f"{entry.get('title') or 'title unavailable'} "
                        "(video ID unavailable); yt-dlp could not retrieve "
                        "this entry."
                    )
                    continue

                video_id = str(video_id_value)
                if video_id not in downloaded_ids:
                    title = entry.get("title") or "title unavailable"
                    reason = download_errors.get(
                        video_id,
                        "yt-dlp did not produce a downloaded video file.",
                    )
                    failures_by_id[video_id] = (
                        f"{title} (ID: {video_id}): {reason}"
                    )

            for video_id, reason in download_errors.items():
                if video_id not in downloaded_ids and video_id not in failures_by_id:
                    video_info = videos_by_id.get(video_id, {})
                    title = video_info.get("title") or "title unavailable"
                    failures_by_id[video_id] = (
                        f"{title} (ID: {video_id}): {reason}"
                    )

            report_path = destination_dir / "unreachable_videos.txt"
            write_unreachable_report(
                report_path,
                str(playlist_title),
                failures_without_id
                + download_errors_without_id
                + list(failures_by_id.values()),
            )

        output_paths: list[Path] = []
        for source_path in source_files:
            video_info = videos_by_id.get(source_path.stem, {})
            title = video_info.get("title") or source_path.stem
            extension = source_path.suffix
            if skip_ffmpeg:
                output_name = f"{safe_filename(title)}{extension}"
            else:
                output_name = f"{safe_filename(title)}.mp4"
            if is_playlist:
                output_name = (
                    f"{safe_filename(title)} [{safe_filename(source_path.stem)}]"
                    f"{'.mp4' if not skip_ffmpeg else extension}"
                )

            output_path = destination_dir / output_name
            if output_path.exists():
                raise SystemExit(
                    f"Output already exists: {output_path}. "
                    "Move or rename it before downloading again."
                )

            if skip_ffmpeg:
                shutil.copy2(source_path, output_path)
            else:
                ffmpeg_command = [
                    ffmpeg or "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-stats_period",
                    "1",
                    "-progress",
                    "pipe:1",
                    "-nostats",
                    "-i",
                    str(source_path),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a?",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "23",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    "-movflags",
                    "+faststart",
                    str(output_path),
                ]

                try:
                    duration_value = video_info.get("duration")
                    duration = (
                        float(duration_value)
                        if isinstance(duration_value, (int, float))
                        and duration_value > 0
                        else None
                    )
                    run_ffmpeg_with_progress(ffmpeg_command, duration)
                except subprocess.CalledProcessError as error:
                    raise SystemExit(
                        f"ffmpeg conversion failed with exit code "
                        f"{error.returncode} for {source_path.name}."
                    ) from error

            output_paths.append(output_path)
    finally:
        shutil.rmtree(run_temp_dir)

    return output_paths
