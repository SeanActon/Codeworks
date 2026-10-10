# MKV Transcriber

Create plain-text and timestamped SRT transcripts from MKV videos using
faster-whisper. Audio is transcribed locally; video content is not sent to a
transcription service. The selected Whisper model is downloaded on first use.

## Setup

1. Install Python 3.9 or newer.
2. From this folder, install the dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `config.example.json` to `config.json`, set `input_paths`, and adjust
   the options. `config.json` is ignored by Git.
4. Keep the installed PyAV version below 19. PyAV 19 removed an argument used
   by the faster-whisper audio decoder; the requirements file pins a compatible
   version. If transcription reports a PyAV compatibility error, rerun the
   install command above.
5. On Windows, CUDA libraries placed in a `cuda` folder beside `main.py` are
   added to the process DLL search paths automatically. Set `device` to `cuda`
   and use a supported `compute_type` to enable GPU transcription.

## Run

With `input_paths` set in `config.json`, run:

```powershell
python main.py
```

Each episode displays its own progress bar, advancing as speech segments are
transcribed.

Alternatively, pass one or more MKV files or folders on the command line to
override `input_paths`. Folders are searched recursively:

```powershell
python main.py "D:\Videos\episode.mkv"
python main.py "D:\Videos\Season 1"
```

Use `--srt-only` to write SRT subtitles without plain-text transcripts:

```powershell
python main.py --srt-only "D:\Videos\Season 1"
```

Use `--workers` to transcribe multiple files concurrently. The default is one
worker (sequential processing); higher counts use more CPU/GPU memory:

```powershell
python main.py --workers 2 "D:\Videos\Season 1"
python main.py --workers 2 --srt-only "D:\Videos\Season 1"
```

Use another settings file with `--config path\to\config.json`.
Relative input paths and `output_dir` are resolved from the config file's folder.
The output directory is created as needed. Existing transcript files are
overwritten.

## Settings

- `input_paths`: paths to MKV files or folders to process by default; folders
  are searched recursively. An empty list requires paths to be passed on the
  command line.
- `model`: `tiny`, `base`, `small`, `medium`, or `large-v3`. `small` is the
  default; larger models generally improve accuracy but need more resources.
- `device`: `auto`, `cpu`, or `cuda`.
- `compute_type`: `auto`, `int8`, `float16`, or `float32`.
- `language`: language code such as `en`, or `null` to detect it automatically.
- `output_dir`: transcript output folder, relative to this script folder or an
  absolute path.
- `output_formats`: one or both of `txt` and `srt`.
- `workers`: number of MKV files to transcribe concurrently; must be a positive
  integer. The default is `1` (sequential processing).

Model/device combinations depend on the installed hardware and runtime. For
CPU transcription, set `device` to `cpu` and `compute_type` to `int8`. For GPU
transcription, CTranslate2 must be able to load the required CUDA and cuDNN
libraries. On Windows, begin with one worker; multiple concurrent files can
increase GPU memory use substantially.
