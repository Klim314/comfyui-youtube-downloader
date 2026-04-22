from .nodes.downloader import VideoDownloader
from .nodes.load_audio import LoadAudioFromPath

NODE_CLASS_MAPPINGS = {
    "VideoDownloader": VideoDownloader,
    "LoadAudioFromPath": LoadAudioFromPath,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "VideoDownloader": "Video Downloader (yt-dlp)",
    "LoadAudioFromPath": "Load Audio (from path)",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
