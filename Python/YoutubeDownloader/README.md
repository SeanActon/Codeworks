# YouTube Downloader

Download YouTube videos or playlists with `yt-dlp`, then optionally convert
them with FFmpeg to MP4 using H.264 video and AAC audio.

## Setup

1. Install Python and [FFmpeg](https://ffmpeg.org/), and make sure `ffmpeg` is
   available on your `PATH`.
2. Install the Python dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `config.example.json` to `config.json` and set `video_url` to a
   YouTube video or playlist. `config.json` is ignored by Git.
4. Run the downloader:

   ```powershell
   python YoutubeDownloader.py
   ```

Videos from a playlist are saved under `made videos/<playlist title>/`.
Individual videos are saved directly in `made videos`. Set `skip_ffmpeg` to
`true` in `config.json` to keep the downloaded format without conversion;
when enabled, yt-dlp prefers a single-file MP4 and falls back to its best
single-file format. The default `false` converts videos to MP4 with H.264/AAC.
Playlist downloads continue when individual entries are unavailable. Each
playlist folder contains `unreachable_videos.txt` with failed video titles and
IDs when available, or a note that no unreachable videos were detected.

Downloads are temporarily stored in `TempVideos` and removed after processing.
The output and temporary directories are ignored by Git. FFmpeg conversion
displays progress when the video duration is available and warns if it has not
reported progress for 30 seconds. Existing output files are not overwritten.
