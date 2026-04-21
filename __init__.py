from .nodes.downloader import VideoDownloader

NODE_CLASS_MAPPINGS = {
    "VideoDownloader": VideoDownloader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoDownloader": "Video Downloader (yt-dlp)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
