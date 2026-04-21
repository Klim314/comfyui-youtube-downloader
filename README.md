# ComfyUI Video Downloader

A ComfyUI custom node that downloads videos or audio tracks via [yt-dlp](https://github.com/yt-dlp/yt-dlp). Supports cookie-based authentication so you can use Premium accounts for higher-quality streams.

## Features

- Download video (merged to mp4) or audio only (mp3/m4a/opus/wav/flac/aac/vorbis)
- Optional `cookies.txt` for Premium / age-gated / members-only content
- Outputs a file path string — pipe into [VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) `LoadVideo` for frame extraction
- Works with any site yt-dlp supports (YouTube, Vimeo, Twitter/X, etc.)

## Install

### Manual

```bash
cd ComfyUI/custom_nodes
git clone <this-repo> comfyui_video_downloader
cd comfyui_video_downloader
pip install -r requirements.txt
```

### With UV (for development)

```bash
uv sync
```

### External dependency

`audio_only` mode requires **ffmpeg** on your PATH. Video merging to mp4 also uses ffmpeg. Install via your package manager (`winget install Gyan.FFmpeg`, `brew install ffmpeg`, `apt install ffmpeg`, etc.).

## Usage

Add the **Video Downloader (yt-dlp)** node (category: `video/download`).

### Inputs

| Input | Type | Notes |
|---|---|---|
| `url` | STRING | The video URL |
| `mode` | `video` \| `audio_only` | Pick output kind |
| `output_dir` | STRING | Defaults to `ComfyUI/output/downloads` |
| `filename_template` | STRING | yt-dlp template, default `%(title)s.%(ext)s` |
| `audio_format` | dropdown | Only used when `mode=audio_only` |
| `format_override` | STRING | Raw yt-dlp `-f` string; overrides mode default when set |
| `cookies_file` | STRING | Path to a `cookies.txt` (Netscape format) |

### Outputs

- `file_path` (STRING) — absolute path to the downloaded file
- `title` (STRING)
- `duration` (FLOAT) — seconds

## Using Premium / authenticated downloads

Export your browser cookies to a Netscape-format `cookies.txt`:

1. Install a cookie exporter extension (e.g. "Get cookies.txt LOCALLY" for Chrome/Firefox).
2. While logged in to the target site, export cookies for that domain.
3. Save the file somewhere ComfyUI can read (e.g. `ComfyUI/user/cookies.txt`).
4. Set the node's `cookies_file` input to that absolute path.

**Security note**: the cookie file grants session access to your account. Keep it out of shared folders and out of version control.

## Caching behavior

ComfyUI caches node outputs by input hash. Same URL + same options = no re-download on repeated queue runs. Change the URL or delete the file manually to force a fresh download.
