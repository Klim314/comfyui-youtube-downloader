# ComfyUI Karaoke

ComfyUI custom node pack for building karaoke pipelines. Currently covers the **source** and **stem separation** stages — fetch a track from the web, split it into vocal / instrumental stems, and hand the result off to downstream nodes. Future stages (pitch shift, lyric transcription, lyric sync, video render) will be added incrementally.

Ships four nodes:

- **Video Downloader (yt-dlp)** — fetch a URL to disk, output the file path. Supports cookie-based auth for Premium / members-only content.
- **Load Audio (from path)** — read a STRING path into ComfyUI's `AUDIO` type, so `audio_only` downloads compose directly with audio-consuming nodes.
- **String → AudioPath** — retype a STRING as `AUDIOPATH` for packs (e.g. UVR5) whose inputs demand that nominal type.
- **Audio Separator** — run MDX / VR / Demucs / MDXC models via [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator) to split an `AUDIO` into two stems.

## Features

- Download video (merged to mp4) or audio only (mp3/m4a/opus/wav/flac/aac/vorbis)
- Optional `cookies.txt` for Premium / age-gated / members-only content
- Path-based outputs that compose with [VideoHelperSuite](https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite) (`VHS_LoadVideo`) for video, and with the bundled `Load Audio (from path)` node for audio-only flows
- Stem separation with any model supported by `audio-separator` — models are auto-downloaded to `ComfyUI/models/audio_separator/` on first use and cached across runs

## Install

### Manual

```bash
cd ComfyUI/custom_nodes
git clone git@github.com:Klim314/comfyui-karaoke.git
cd comfyui-karaoke
pip install -r requirements.txt
```

### With UV (for development)

```bash
uv sync
```

### CPU-only environments

`requirements.txt` pulls `audio-separator[gpu]` by default (CUDA). On machines without a GPU, install the CPU variant instead:

```bash
pip install audio-separator[cpu]
```

### External dependency

`audio_only` mode requires **ffmpeg** on your PATH. Video merging to mp4 also uses ffmpeg. Install via your package manager (`winget install Gyan.FFmpeg`, `brew install ffmpeg`, `apt install ffmpeg`, etc.).

## Usage

### Video Downloader (yt-dlp)

Category: `video/download`.

#### Inputs

| Input | Type | Notes |
|---|---|---|
| `url` | STRING | The video URL |
| `mode` | `video` \| `audio_only` | Pick output kind |
| `output_dir` | STRING | Defaults to `ComfyUI/output/downloads` |
| `filename_template` | STRING | yt-dlp template, default `%(title)s.%(ext)s` |
| `audio_format` | dropdown | Only used when `mode=audio_only` |
| `format_override` | STRING | Raw yt-dlp `-f` string; overrides mode default when set |
| `cookies_file` | STRING | Path to a `cookies.txt` (Netscape format) |

#### Outputs

- `file_path` (STRING) — absolute path to the downloaded file
- `title` (STRING)
- `duration` (FLOAT) — seconds

### Load Audio (from path)

Category: `audio`. Reads an audio file at a given path and returns ComfyUI's standard `AUDIO` type — a dict of `{"waveform": Tensor[1, channels, time], "sample_rate": int}`. Sample rate is preserved as-is; no resampling.

- **Input**: `audio_path` (STRING)
- **Output**: `AUDIO`

Uses `torchaudio.load()` under the hood, with a `soundfile` fallback.

### String → AudioPath

Category: `audio/utils`. Passes a STRING through unchanged but retypes it as `AUDIOPATH`, which is what some audio packs (notably UVR5 forks) declare on their inputs. ComfyUI's type matching is strict/nominal, so without this step a plain STRING won't wire.

- **Input**: `path` (STRING)
- **Output**: `AUDIOPATH`

### Audio Separator

Category: `karaoke/separation`. Runs a source-separation model on an incoming `AUDIO` and returns two stems as `AUDIO`.

#### Inputs

| Input | Type | Notes |
|---|---|---|
| `audio` | AUDIO | Standard ComfyUI audio dict |
| `model_filename` | dropdown | Model to run (pulled from `audio-separator`'s manifest, falls back to a curated list) |
| `output_format` | `wav` \| `flac` | Intermediate file format used during separation |

#### Outputs

- `primary_stem` (AUDIO) — first stem the model produces (e.g. Vocals for a vocal model)
- `secondary_stem` (AUDIO) — second stem (e.g. Instrumental)
- `model` (STRING) — the selected `model_filename`, passed through so downstream save nodes can compose filenames like `vocals_<model>.wav`

Stem semantics depend on the model; the names are deliberately generic. Consult the model's documentation to know which stem is which.

Models are downloaded on demand to `ComfyUI/models/audio_separator/` and reused thereafter. Outside a ComfyUI environment (e.g. running the smoke test standalone), the default cache location is `~/.audio-separator/models/`.

#### Using a shared models folder (`extra_model_paths.yaml`)

If you already have a models folder mounted elsewhere (shared between UIs, on a separate drive, etc.), point ComfyUI at it via `extra_model_paths.yaml`:

```yaml
my-setup:
  base_path: /mnt/models
  audio_separator: audio_separator/
```

The node searches every registered `audio_separator` folder for the selected model. If the file is already present in any of them, that folder is used directly (no re-download). If it isn't present anywhere, the first registered folder is used for the fresh download — entries in `extra_model_paths.yaml` load before custom nodes, so a configured external path takes precedence over the default `ComfyUI/models/audio_separator/`.

### Typical wiring

```
Video Downloader (mode=audio_only)  ──►  Load Audio (from path) ──► Audio Separator ──► primary_stem (AUDIO)
                                                                                     └─► secondary_stem (AUDIO)

Video Downloader (mode=video)       ──►  VHS_LoadVideo ──► IMAGE + AUDIO
Video Downloader (mode=audio_only)  ──►  String → AudioPath    ──► UVR5 (external pack)
```

## Using Premium / authenticated downloads

Export your browser cookies to a Netscape-format `cookies.txt`:

1. Install a cookie exporter extension (e.g. "Get cookies.txt LOCALLY" for Chrome/Firefox).
2. While logged in to the target site, export cookies for that domain.
3. Save the file somewhere ComfyUI can read (e.g. `ComfyUI/user/cookies.txt`).
4. Set the node's `cookies_file` input to that absolute path.

**Security note**: the cookie file grants session access to your account. Keep it out of shared folders and out of version control.

## Caching behavior

ComfyUI caches node outputs by input hash. Same URL + same options = no re-download on repeated queue runs. Change the URL or delete the file manually to force a fresh download. The same applies to `Audio Separator` — identical waveform + model = cached stems.

## Roadmap

Stages beyond stem separation are planned but not yet implemented: pitch shifting, lyric transcription (Whisper), lyric sync (LRC/SRT), and karaoke video rendering with burned-in lyrics.
