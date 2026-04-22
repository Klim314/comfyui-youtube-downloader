from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from .load_audio import _load_via_soundfile, _load_via_torchaudio


# Small curated fallback used when the audio-separator manifest can't be read
# at node-registration time (bad install, offline, etc). Keeps `INPUT_TYPES`
# from hanging or exploding during ComfyUI startup.
_FALLBACK_MODELS = [
    "model_bs_roformer_ep_317_sdr_12.9755.ckpt",
    "UVR-MDX-NET-Inst_HQ_3.onnx",
    "UVR_MDXNET_KARA.onnx",
    "htdemucs.yaml",
    "2_HP-UVR.pth",
]


def _list_model_filenames() -> list[str]:
    try:
        from audio_separator.separator import Separator

        sep = Separator(info_only=True)
        models = sep.get_simplified_model_list()
        filenames = sorted(models.keys())
        if filenames:
            return filenames
        print("[comfyui-karaoke] AudioSeparator: model manifest was empty, using fallback list", file=sys.stderr)
    except Exception as e:  # noqa: BLE001
        print(
            f"[comfyui-karaoke] AudioSeparator: could not load model manifest "
            f"({type(e).__name__}: {e}) — using fallback list. "
            f"Check that `audio-separator` is installed in ComfyUI's Python environment.",
            file=sys.stderr,
        )
    return list(_FALLBACK_MODELS)


def _model_dir_candidates() -> list[str]:
    try:
        import folder_paths  # provided by ComfyUI

        registered = folder_paths.get_folder_paths("audio_separator") or []
        if registered:
            return list(registered)
    except Exception:
        pass
    return [os.path.expanduser("~/.audio-separator/models")]


def _resolve_models_dir(model_filename: str | None = None) -> str:
    """Pick the directory audio-separator should load/download this model from.

    If the model file already exists in any registered folder (e.g. one the
    user added via extra_model_paths.yaml), use that folder. Otherwise use
    the first registered folder — which is where a fresh download will land.
    """
    candidates = _model_dir_candidates()
    if model_filename:
        for path in candidates:
            if os.path.isfile(os.path.join(path, model_filename)):
                return path
    first = candidates[0]
    os.makedirs(first, exist_ok=True)
    return first


class AudioSeparator:
    """Split an AUDIO into two stems using python-audio-separator.

    Stem semantics vary by model — for a vocal model, primary is usually
    Vocals and secondary is Instrumental, but swap them at the wire if the
    chosen model differs. The node does not rename outputs based on model
    metadata because ComfyUI RETURN_NAMES are static.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "model_filename": (_list_model_filenames(),),
                "output_format": (["wav", "flac"], {"default": "wav"}),
            },
        }

    RETURN_TYPES = ("AUDIO", "AUDIO")
    RETURN_NAMES = ("primary_stem", "secondary_stem")
    FUNCTION = "separate"
    CATEGORY = "karaoke/separation"

    def separate(self, audio: dict, model_filename: str, output_format: str):
        from audio_separator.separator import Separator

        waveform = audio["waveform"]
        sample_rate = int(audio["sample_rate"])

        if waveform.dim() == 3:
            waveform = waveform.squeeze(0)  # [C, T]

        tmp_dir = Path(tempfile.mkdtemp(prefix="audio_separator_"))
        try:
            input_path = tmp_dir / "input.wav"
            _save_wav(str(input_path), waveform, sample_rate)

            separator = Separator(
                model_file_dir=_resolve_models_dir(model_filename),
                output_dir=str(tmp_dir),
                output_format=output_format.upper(),
            )
            separator.load_model(model_filename=model_filename)
            stem_paths = separator.separate(str(input_path))

            if not stem_paths or len(stem_paths) < 2:
                raise RuntimeError(
                    f"AudioSeparator: expected at least 2 stem files, got {stem_paths!r}"
                )

            primary_path = _resolve_stem_path(stem_paths[0], tmp_dir)
            secondary_path = _resolve_stem_path(stem_paths[1], tmp_dir)

            return (_load_audio_dict(primary_path), _load_audio_dict(secondary_path))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def _save_wav(path: str, waveform, sample_rate: int) -> None:
    errors: list[str] = []
    try:
        import torchaudio

        torchaudio.save(path, waveform.detach().cpu().float(), sample_rate)
        return
    except Exception as e:  # noqa: BLE001
        errors.append(f"torchaudio.save: {type(e).__name__}: {e}")

    try:
        import soundfile as sf

        data = waveform.detach().cpu().float().numpy().T  # [time, channels]
        sf.write(path, data, sample_rate)
        return
    except Exception as e:  # noqa: BLE001
        errors.append(f"soundfile.write: {type(e).__name__}: {e}")

    raise RuntimeError("AudioSeparator: failed to write input wav\n" + "\n".join(errors))


def _load_audio_dict(path: str) -> dict:
    errors: list[str] = []
    for loader in (_load_via_torchaudio, _load_via_soundfile):
        try:
            waveform, sr = loader(path)
            return {"waveform": waveform.unsqueeze(0), "sample_rate": int(sr)}
        except Exception as e:  # noqa: BLE001
            errors.append(f"{loader.__name__}: {type(e).__name__}: {e}")
    raise RuntimeError(
        f"AudioSeparator: could not load stem file {path}\n" + "\n".join(errors)
    )


def _resolve_stem_path(candidate: str, base: Path) -> str:
    if os.path.isfile(candidate):
        return os.path.abspath(candidate)
    joined = base / candidate
    if joined.is_file():
        return str(joined)
    raise FileNotFoundError(f"AudioSeparator: stem file not found: {candidate}")
