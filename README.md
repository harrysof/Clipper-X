# Clipper X

Clipper X is a local desktop tool for finding and cutting short-form clips from long videos. It can use YouTube subtitles, local subtitle files, or WhisperX-generated captions, then asks a local GGUF model through `llama-server` to identify self-contained YouTube Shorts/TikTok moments.

The app is currently implemented in `main.py` with a Tkinter UI.

## What It Does

Clipper X runs this pipeline:

1. Load a YouTube URL or local video file.
2. Download or locate subtitles, or generate fresh captions with WhisperX.
3. Parse captions into timestamped transcript blocks.
4. Chunk the transcript into overlapping analysis windows.
5. Start `llama-server` with the selected GGUF model.
6. Ask the model to find viral, self-contained short-form moments.
7. Expand candidate timestamps into complete clips.
8. Let you manually choose candidates from a review window.
9. Cut selected clips with FFmpeg.
10. Write a `manifest.txt` with hook, context, reason, score, and file path.

## Requirements

- Windows
- Python 3.12
- FFmpeg in `PATH`
- yt-dlp in `PATH`
- `requests`
- llama.cpp `llama-server.exe`
- A GGUF chat/instruct model
- Optional: WhisperX for better captions

The current script expects paths to `llama-server.exe` and a model folder defined near the top of `main.py`. Edit those variables to match your local setup before running.

## Running

Use Python 3.12:

```powershell
py -3.12 main.py
```

There is also a `run.bat` file in the project folder.

## Main Settings

### Source

- `YouTube URL`: downloads the video and subtitle files with `yt-dlp`.
- `Local Video File`: uses a video already on disk.

For local video mode, Clipper X looks for a matching `.srt` or `.vtt` next to the video.

### Captions

- `Auto (SRT then WhisperX)`: use existing/downloaded subtitles first; use WhisperX only if no subtitle file exists.
- `Existing SRT only`: require an existing subtitle file.
- `WhisperX`: ignore existing subtitles and generate fresh captions.

Choose `WhisperX` when YouTube auto-captions are messy, repetitive, or poorly timed.

### WhisperX

- `WhisperX Model`: `small` is a good first test. `medium` is more accurate but slow on CPU.
- `Device`: use `cpu` on Windows with an AMD GPU.

The app extracts a 16 kHz mono WAV with FFmpeg before calling WhisperX. Generated captions are saved in:

```text
{output folder}\whisperx_captions
```

### Clip Controls

- `Max Clips`: maximum clips you can select/export.
- `Max Chunks`: transcript chunks to analyze. `0` means all chunks.
- `Min Clip Seconds`: minimum final clip length.
- `Max Clip Seconds`: maximum final clip length.

For quick testing, use a small chunk count like `1` or `2`. For a full run, use `0`.

## Local Model Prompt

The model is asked to return JSON objects with:

```json
{
  "start_time": 0.0,
  "end_time": 30.0,
  "context": "one sentence describing what happens at this moment",
  "reason": "one sentence why a viewer would stop scrolling for this",
  "hook": "2-3 word thumbnail title for this clip",
  "score": 8
}
```

Only moments scoring `6` or higher are accepted.

## Output

Clipper X writes:

```text
{output folder}\clips\
{output folder}\manifest.txt
```

Clip filenames look like:

```text
clip_01_score8.mp4
```

The manifest includes the hook, context, reason, score, timestamps, and output file path.

## Remembered Settings

Clipper X saves UI settings to:

```text
clipharvester_settings.json
```

It remembers paths, caption mode, WhisperX settings, model path, clip limits, and source mode between runs.

Delete that file to reset remembered settings.

## WhisperX Setup

Install WhisperX with:

```powershell
py -3.12 -m pip install whisperx
```

Or from a local wheel:

```powershell
py -3.12 -m pip install "path\to\whisperx.whl"
```

If imports fail after install, repair missing packages with:

```powershell
py -3.12 -m pip install --force-reinstall pandas scipy scikit-learn
py -3.12 -m pip check
```

## AMD GPU Note

On Windows with an AMD GPU, use WhisperX with:

```text
Device: cpu
Compute type: int8
```

The normal WhisperX GPU path uses CUDA, which is for NVIDIA GPUs. AMD acceleration is not cleanly supported by this Windows Python setup.

## Troubleshooting

### `No module named whisperx`

WhisperX is not installed in the Python environment running the app.

```powershell
py -3.12 -m pip install whisperx
```

### `No module named pandas`, `scipy`, or `sklearn`

Repair the broken dependency:

```powershell
py -3.12 -m pip install --force-reinstall pandas scipy scikit-learn
```

### `torchcodec is not installed correctly`

This warning may appear from pyannote. Clipper X passes WhisperX an extracted WAV instead of the original MP4, which avoids many video/audio decoding issues.

### WhisperX Looks Stuck

The first run may download a model from Hugging Face. `medium` on CPU can be slow. Test with `small` first.

### Model Finds Candidates But None Are Selected

Candidates must pass validation:

- score must be at least `6`
- final expanded duration must fit your min/max clip settings
- timestamps must be valid

Try increasing `Max Clip Seconds` or lowering `Min Clip Seconds`.

## Project Files

```text
main.py         Main Tkinter app and pipeline
run.bat         Convenience launcher
test_api.py     Manual llama-server API smoke test
test_llama.py   Manual llama-cpp-python smoke test
models\         Local GGUF models and llama logs
```

## Current Limitations

- Hard-coded local paths still need a proper settings UI.
- WhisperX word-level timestamps are not yet used for caption burn-in or cleanup editing.
- Clips are cut with FFmpeg stream copy, so cuts may land near keyframes rather than exact frames.
- Reframing to 9:16, burned captions, thumbnail generation, and final render presets are planned but not implemented yet.
