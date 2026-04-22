from __future__ import annotations

import os


class LoadAudioFromPath:
    """Load an audio file from an absolute path into ComfyUI's AUDIO type.

    Complements VideoDownloader's audio_only mode, which outputs a STRING path —
    this node consumes that path and produces the standard AUDIO dict
    ({"waveform": Tensor[B, C, T], "sample_rate": int}).

    Tries torchaudio first (what ComfyUI ships with), then falls back to
    soundfile so this works on minimal envs too.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_path": ("STRING", {"default": "", "multiline": False}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "load"
    CATEGORY = "audio"

    def load(self, audio_path: str):
        path = audio_path.strip()
        if not path:
            raise ValueError("LoadAudioFromPath: audio_path is empty")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"LoadAudioFromPath: file not found: {path}")

        errors: list[str] = []
        for loader in (_load_via_torchaudio, _load_via_soundfile):
            try:
                waveform, sample_rate = loader(path)
                break
            except Exception as e:  # noqa: BLE001 — collect all backend failures
                errors.append(f"{loader.__name__}: {type(e).__name__}: {e}")
        else:
            raise RuntimeError(
                "LoadAudioFromPath: all audio backends failed. "
                "Install one of: `pip install soundfile` or `pip install torchaudio torchcodec`.\n"
                + "\n".join(errors)
            )

        waveform = waveform.unsqueeze(0)  # [1, channels, time]
        return ({"waveform": waveform, "sample_rate": int(sample_rate)},)


def _load_via_torchaudio(path: str):
    import torchaudio

    waveform, sr = torchaudio.load(path)  # [channels, time]
    return waveform, int(sr)


def _load_via_soundfile(path: str):
    import soundfile as sf
    import torch

    data, sr = sf.read(path, dtype="float32", always_2d=True)  # [time, channels]
    waveform = torch.from_numpy(data.T).contiguous()  # [channels, time]
    return waveform, int(sr)
