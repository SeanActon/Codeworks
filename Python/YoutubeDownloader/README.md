# YouTube Downloader

Download YouTube videos or playlists with `yt-dlp`, then optionally convert them with FFmpeg to MP4 using H.264 video and AAC audio.

## Setup

1. Install Python and [FFmpeg](https://ffmpeg.org/), and make sure `ffmpeg` is available on your `PATH`.
2. Install the Python dependency:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `config.example.json` to `config.json` and set `video_url` to a YouTube video or playlist, or an array of video and playlist URLs. `config.json` is ignored by Git.
4. Run the downloader from the project folder:

   ```powershell
   python main.py
   ```

   You can also run the package directly:

   ```powershell
   python -m youtube_downloader
   ```

## Output behavior

- Single videos are saved directly in `made videos/`.
- Playlist videos are saved in `made videos/<playlist title>/`.
- If `skip_ffmpeg` is set to `true` in `config.json`, the downloaded file is kept in its original format instead of being converted.
- If `skip_ffmpeg` is `false` (default), each video is converted to MP4 with H.264 video and AAC audio.
- Playlist downloads continue even if some entries fail, and each playlist folder includes `unreachable_videos.txt` listing unavailable videos when applicable.
- Existing output files are not overwritten.
