from __future__ import annotations

import os
from pathlib import Path

import yt_dlp

try:
    import folder_paths  # provided by ComfyUI at runtime
    _DEFAULT_OUTPUT_DIR = os.path.join(folder_paths.get_output_directory(), "downloads")
except Exception:
    _DEFAULT_OUTPUT_DIR = os.path.abspath(os.path.join("output", "downloads"))


AUDIO_FORMATS = ["mp3", "m4a", "opus", "wav", "flac", "aac", "vorbis"]
MODES = ["video", "audio_only"]


class VideoDownloader:
    """Download a video or audio track via yt-dlp and return its file path."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "url": ("STRING", {"default": "", "multiline": False}),
                "mode": (MODES, {"default": "video"}),
            },
            "optional": {
                "output_dir": ("STRING", {"default": _DEFAULT_OUTPUT_DIR, "multiline": False}),
                "filename_template": ("STRING", {"default": "%(title)s.%(ext)s", "multiline": False}),
                "audio_format": (AUDIO_FORMATS, {"default": "mp3"}),
                "format_override": ("STRING", {"default": "", "multiline": False}),
                "cookies_file": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "FLOAT")
    RETURN_NAMES = ("file_path", "title", "duration")
    FUNCTION = "download"
    CATEGORY = "video/download"
    OUTPUT_NODE = False

    def download(
        self,
        url: str,
        mode: str,
        output_dir: str = _DEFAULT_OUTPUT_DIR,
        filename_template: str = "%(title)s.%(ext)s",
        audio_format: str = "mp3",
        format_override: str = "",
        cookies_file: str = "",
    ):
        if not url.strip():
            raise ValueError("VideoDownloader: url is empty")

        out_dir = Path(output_dir).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts: dict = {
            "outtmpl": str(out_dir / filename_template),
            "noprogress": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": False,
            "ignoreerrors": False,
            "overwrites": False,
        }

        if mode == "audio_only":
            ydl_opts["format"] = format_override or "bestaudio/best"
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": "0",
                }
            ]
        else:
            ydl_opts["format"] = format_override or "bestvideo*+bestaudio/best"
            ydl_opts["merge_output_format"] = "mp4"

        cookies_file = cookies_file.strip()
        if cookies_file:
            cookie_path = Path(cookies_file).expanduser()
            if not cookie_path.is_file():
                raise FileNotFoundError(f"VideoDownloader: cookies_file not found: {cookie_path}")
            ydl_opts["cookiefile"] = str(cookie_path)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        file_path = self._resolve_path(info, mode, audio_format)
        title = info.get("title", "") or ""
        duration = float(info.get("duration") or 0.0)

        return (file_path, title, duration)

    @staticmethod
    def _resolve_path(info: dict, mode: str, audio_format: str) -> str:
        requested = info.get("requested_downloads") or []
        if requested:
            path = requested[-1].get("filepath")
            if path and os.path.isfile(path):
                return os.path.abspath(path)

        # Fallback: reconstruct from _filename, adjusting extension if a postprocessor changed it.
        filename = info.get("_filename")
        if filename:
            if mode == "audio_only":
                filename = os.path.splitext(filename)[0] + f".{audio_format}"
            if os.path.isfile(filename):
                return os.path.abspath(filename)

        raise RuntimeError("VideoDownloader: could not resolve downloaded file path from yt-dlp info")
