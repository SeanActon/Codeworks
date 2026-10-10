"""Create local text and SRT transcripts from MKV video files."""

from __future__ import annotations

import argparse
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from queue import Queue
import sys
from pathlib import Path
from typing import Any

from tqdm import tqdm

DEFAULT_CONFIG = Path(__file__).with_name("config.json")
CUDA_DLL_DIR = Path(__file__).with_name("cuda")
if os.name == "nt" and CUDA_DLL_DIR.is_dir():
    os.environ["PATH"] = (
        str(CUDA_DLL_DIR) + os.pathsep + os.environ.get("PATH", "")
    )
    atexit.register(os.add_dll_directory(str(CUDA_DLL_DIR)).close)
VALID_MODELS = {"tiny", "base", "small", "medium", "large-v3"}
VALID_DEVICES = {"auto", "cpu", "cuda"}
VALID_COMPUTE_TYPES = {"auto", "int8", "float16", "float32"}
MAX_SUPPORTED_AV_MAJOR = 18


def validate_pyav_version(version: str) -> None:
    try:
        major_version = int(version.split(".", maxsplit=1)[0])
    except ValueError as exc:
        raise ValueError(f"Could not determine the installed PyAV version: {version}") from exc

    if major_version > MAX_SUPPORTED_AV_MAJOR:
        raise ValueError(
            f"PyAV {version} is incompatible with the installed faster-whisper "
            "audio decoder. Install the compatible dependency versions with: "
            "python -m pip install -r requirements.txt"
        )


def load_config(config_path: Path) -> dict[str, Any]:
    try:
        with config_path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read config file {config_path}: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError("Config file must contain a JSON object.")

    defaults: dict[str, Any] = {
        "input_paths": [],
        "model": "small",
        "device": "auto",
        "compute_type": "auto",
        "language": None,
        "output_dir": "transcripts",
        "output_formats": ["txt", "srt"],
        "workers": 1,
    }
    defaults.update(config)

    input_paths = defaults["input_paths"]
    if (
        not isinstance(input_paths, list)
        or any(not isinstance(path, str) or not path.strip() for path in input_paths)
    ):
        raise ValueError("input_paths must be a list of non-empty path strings.")
    defaults["input_paths"] = input_paths

    if not isinstance(defaults["model"], str) or defaults["model"] not in VALID_MODELS:
        raise ValueError(f"model must be one of: {', '.join(sorted(VALID_MODELS))}")
    if not isinstance(defaults["device"], str) or defaults["device"] not in VALID_DEVICES:
        raise ValueError(f"device must be one of: {', '.join(sorted(VALID_DEVICES))}")
    if (
        not isinstance(defaults["compute_type"], str)
        or defaults["compute_type"] not in VALID_COMPUTE_TYPES
    ):
        raise ValueError(
            "compute_type must be one of: "
            f"{', '.join(sorted(VALID_COMPUTE_TYPES))}"
        )
    if defaults["language"] is not None and (
        not isinstance(defaults["language"], str) or not defaults["language"].strip()
    ):
        raise ValueError("language must be a language code or null.")

    formats = defaults["output_formats"]
    if (
        not isinstance(formats, list)
        or not formats
        or any(not isinstance(item, str) or item not in {"txt", "srt"} for item in formats)
    ):
        raise ValueError("output_formats must be a non-empty list of 'txt' and/or 'srt'.")
    defaults["output_formats"] = list(dict.fromkeys(formats))
    if not isinstance(defaults["output_dir"], str) or not defaults["output_dir"].strip():
        raise ValueError("output_dir must be a non-empty path string.")
    if type(defaults["workers"]) is not int or defaults["workers"] < 1:
        raise ValueError("workers must be a positive integer.")
    return defaults


def find_mkv_files(inputs: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for input_path in inputs:
        if not input_path.exists():
            raise ValueError(f"Input path does not exist: {input_path}")
        if input_path.is_file():
            if input_path.suffix.lower() != ".mkv":
                raise ValueError(f"Input file is not an MKV: {input_path}")
            files.add(input_path.resolve())
        elif input_path.is_dir():
            files.update(
                path.resolve()
                for path in input_path.rglob("*")
                if path.is_file() and path.suffix.lower() == ".mkv"
            )
        else:
            raise ValueError(f"Input path is not a file or directory: {input_path}")

    if not files:
        raise ValueError("No MKV files found in the supplied input paths.")
    return sorted(files)


def format_srt_timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    whole_seconds, milliseconds = divmod(milliseconds, 1000)
    return (
        f"{hours:02}:{minutes:02}:{whole_seconds:02},"
        f"{milliseconds:03}"
    )


def write_transcript(
    output_base: Path,
    segments: list[Any],
    output_formats: list[str],
) -> list[Path]:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []

    if "txt" in output_formats:
        text_path = output_base.with_suffix(".txt")
        text_path.write_text(
            "\n".join(segment.text.strip() for segment in segments if segment.text.strip())
            + "\n",
            encoding="utf-8",
        )
        written_paths.append(text_path)

    if "srt" in output_formats:
        srt_path = output_base.with_suffix(".srt")
        blocks = [
            (
                f"{index}\n"
                f"{format_srt_timestamp(segment.start)} --> "
                f"{format_srt_timestamp(segment.end)}\n"
                f"{segment.text.strip()}"
            )
            for index, segment in enumerate(segments, start=1)
            if segment.text.strip()
        ]
        srt_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
        written_paths.append(srt_path)

    return written_paths


def transcribe(
    video_path: Path,
    output_base: Path,
    config: dict[str, Any],
    model: Any,
    progress_position: int = 0,
    leave_progress: bool = True,
) -> list[Path]:
    segments, info = model.transcribe(
        str(video_path),
        language=config["language"],
        vad_filter=True,
    )
    transcript_segments = []
    with tqdm(
        total=info.duration,
        desc=video_path.name,
        unit="s",
        unit_scale=True,
        unit_divisor=60,
        position=progress_position,
        leave=leave_progress,
    ) as progress:
        for segment in segments:
            transcript_segments.append(segment)
            progress.update(max(0.0, segment.end - progress.n))
        progress.update(max(0.0, info.duration - progress.n))

    return write_transcript(
        output_base,
        transcript_segments,
        config["output_formats"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe MKV files locally and save TXT/SRT transcripts."
    )
    parser.add_argument(
        "input",
        nargs="*",
        type=Path,
        help=(
            "Optional MKV files or directories (searched recursively); "
            "defaults to input_paths in the config."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Settings JSON file (defaults to config.json beside this script).",
    )
    parser.add_argument(
        "--srt-only",
        action="store_true",
        help="Write only SRT subtitles, overriding output_formats in the config.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of MKV files to transcribe concurrently (defaults to config).",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        if args.srt_only:
            config["output_formats"] = ["srt"]
        if args.workers is not None:
            config["workers"] = args.workers
        if type(config["workers"]) is not int or config["workers"] < 1:
            raise ValueError("workers must be a positive integer.")
        configured_inputs = [
            Path(input_path)
            if Path(input_path).is_absolute()
            else args.config.resolve().parent / input_path
            for input_path in config["input_paths"]
        ]
        input_paths = args.input or configured_inputs
        if not input_paths:
            raise ValueError(
                "No input paths provided. Set input_paths in the config or pass "
                "one or more file/folder paths."
            )
        video_files = find_mkv_files(input_paths)
        output_dir = Path(config["output_dir"])
        if not output_dir.is_absolute():
            output_dir = args.config.resolve().parent / output_dir

        output_bases = [output_dir / f"{video_path.stem}" for video_path in video_files]
        if len(set(output_bases)) != len(output_bases):
            raise ValueError(
                "Input files have duplicate names; use separate runs or distinct "
                "output directories to avoid overwriting transcripts."
            )

        import av
        from faster_whisper import WhisperModel

        validate_pyav_version(av.__version__)
    except ImportError:
        print(
            "Missing dependency. Install it with: "
            "python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        return 1
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    try:
        model = WhisperModel(
            config["model"],
            device=config["device"],
            compute_type=config["compute_type"],
            num_workers=config["workers"],
        )
    except Exception as exc:
        print(f"Could not load the transcription model: {exc}", file=sys.stderr)
        return 1

    failures = 0

    def report_result(transcript_paths: list[Path]) -> None:
        for transcript_path in transcript_paths:
            print(f"Transcript saved: {transcript_path}")

    if config["workers"] == 1:
        for video_path, output_base in zip(video_files, output_bases):
            print(f"Transcribing: {video_path}")
            try:
                transcript_paths = transcribe(video_path, output_base, config, model)
            except Exception as exc:
                failures += 1
                print(f"Failed to transcribe {video_path}: {exc}", file=sys.stderr)
                continue
            report_result(transcript_paths)
    else:
        progress_positions: Queue[int] = Queue()
        for position in range(config["workers"]):
            progress_positions.put(position)

        def transcribe_concurrently(video_path: Path, output_base: Path) -> list[Path]:
            position = progress_positions.get()
            try:
                print(f"Transcribing: {video_path}")
                return transcribe(
                    video_path,
                    output_base,
                    config,
                    model,
                    progress_position=position,
                    leave_progress=False,
                )
            finally:
                progress_positions.put(position)

        with ThreadPoolExecutor(max_workers=config["workers"]) as executor:
            futures = {
                executor.submit(
                    transcribe_concurrently, video_path, output_base
                ): video_path
                for video_path, output_base in zip(video_files, output_bases)
            }
            for future in as_completed(futures):
                video_path = futures[future]
                try:
                    report_result(future.result())
                except Exception as exc:
                    failures += 1
                    print(f"Failed to transcribe {video_path}: {exc}", file=sys.stderr)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
