import os
import re
import sys
import time
import json
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import timedelta

try:
    import requests
except ImportError:
    requests = None

LLAMA_SERVER_PATH = r" "
MODELS_FOLDER_DEFAULT = r" "
WHISPERX_WHEEL_PATH = r" "
SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clipharvester_settings.json")

class ClipHarvesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Clipper X")
        self.root.geometry("850x790")
        self.root.minsize(600, 540)
        self.server_process = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Main frame
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Source Selection
        source_frame = ttk.Frame(main_frame)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(source_frame, text="Source:").pack(side=tk.LEFT, padx=(0, 20))
        self.source_var = tk.StringVar(value="url")
        ttk.Radiobutton(source_frame, text="YouTube URL", variable=self.source_var, value="url", command=self.toggle_source).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(source_frame, text="Local Video File", variable=self.source_var, value="local", command=self.toggle_source).pack(side=tk.LEFT)

        # URL Input
        self.url_frame = ttk.Frame(main_frame)
        self.url_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.url_frame, text="YouTube URL:").pack(side=tk.LEFT, padx=(0, 10))
        self.url_var = tk.StringVar()
        ttk.Entry(self.url_frame, textvariable=self.url_var).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Local File Input
        self.local_frame = ttk.Frame(main_frame)
        ttk.Label(self.local_frame, text="Local Video:").pack(side=tk.LEFT, padx=(0, 13))
        self.local_var = tk.StringVar()
        ttk.Entry(self.local_frame, textvariable=self.local_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(self.local_frame, text="Browse", command=self.browse_local_video).pack(side=tk.LEFT)

        # Output Folder Input
        self.folder_frame = ttk.Frame(main_frame)
        self.folder_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.folder_frame, text="Output Folder:").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_var = tk.StringVar()
        ttk.Entry(self.folder_frame, textvariable=self.folder_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(self.folder_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT)

        # Model Input
        self.model_frame = ttk.Frame(main_frame)
        self.model_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.model_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 48))
        self.model_var = tk.StringVar()
        ttk.Entry(self.model_frame, textvariable=self.model_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        ttk.Button(self.model_frame, text="Browse", command=self.browse_model).pack(side=tk.LEFT)

        # Caption Options
        caption_frame = ttk.Frame(main_frame)
        caption_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(caption_frame, text="Captions:").pack(side=tk.LEFT, padx=(0, 22))
        self.caption_mode_var = tk.StringVar(value="Auto (SRT then WhisperX)")
        ttk.Combobox(
            caption_frame,
            textvariable=self.caption_mode_var,
            values=["Auto (SRT then WhisperX)", "Existing SRT only", "WhisperX"],
            state="readonly",
            width=24
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(caption_frame, text="WhisperX Model:").pack(side=tk.LEFT, padx=(0, 8))
        self.whisperx_model_var = tk.StringVar(value="small")
        ttk.Combobox(
            caption_frame,
            textvariable=self.whisperx_model_var,
            values=["tiny", "base", "small", "medium", "large-v2", "large-v3"],
            width=10
        ).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(caption_frame, text="Device:").pack(side=tk.LEFT, padx=(0, 8))
        self.whisperx_device_var = tk.StringVar(value="cpu")
        ttk.Combobox(
            caption_frame,
            textvariable=self.whisperx_device_var,
            values=["cpu", "cuda"],
            width=7
        ).pack(side=tk.LEFT)

        # Pipeline Options
        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(options_frame, text="Max Clips:").pack(side=tk.LEFT, padx=(0, 9))
        self.max_clips_var = tk.StringVar(value="20")
        ttk.Spinbox(options_frame, from_=1, to=100, textvariable=self.max_clips_var, width=6).pack(side=tk.LEFT, padx=(0, 25))
        ttk.Label(options_frame, text="Max Chunks (0 = all):").pack(side=tk.LEFT, padx=(0, 9))
        self.max_chunks_var = tk.StringVar(value="0")
        ttk.Spinbox(options_frame, from_=0, to=999, textvariable=self.max_chunks_var, width=6).pack(side=tk.LEFT)

        clip_length_frame = ttk.Frame(main_frame)
        clip_length_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(clip_length_frame, text="Min Clip Seconds:").pack(side=tk.LEFT, padx=(0, 9))
        self.min_clip_seconds_var = tk.StringVar(value="25")
        ttk.Spinbox(clip_length_frame, from_=15, to=90, textvariable=self.min_clip_seconds_var, width=6).pack(side=tk.LEFT, padx=(0, 25))
        ttk.Label(clip_length_frame, text="Max Clip Seconds:").pack(side=tk.LEFT, padx=(0, 9))
        self.max_clip_seconds_var = tk.StringVar(value="60")
        ttk.Spinbox(clip_length_frame, from_=15, to=120, textvariable=self.max_clip_seconds_var, width=6).pack(side=tk.LEFT)

        # Progress and Status
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status_frame, textvariable=self.status_var, font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        self.start_btn = ttk.Button(btn_frame, text="Start Pipeline", command=self.start_pipeline)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(btn_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.open_btn = ttk.Button(btn_frame, text="Open Clips Folder", command=self.open_clips_folder, state=tk.DISABLED)
        self.open_btn.pack(side=tk.LEFT)

        # Log Area
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(log_frame, state=tk.DISABLED, wrap=tk.WORD, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.load_settings()

        # Initial checks
        self.root.after(100, self.check_dependencies)

    def toggle_source(self):
        if self.source_var.get() == "url":
            self.local_frame.pack_forget()
            self.url_frame.pack(fill=tk.X, pady=(0, 10), before=self.folder_frame)
        else:
            self.url_frame.pack_forget()
            self.local_frame.pack(fill=tk.X, pady=(0, 10), before=self.folder_frame)

    def get_settings(self):
        return {
            "source": self.source_var.get(),
            "url": self.url_var.get(),
            "local_video": self.local_var.get(),
            "output_folder": self.folder_var.get(),
            "model_file": self.model_var.get(),
            "caption_mode": self.caption_mode_var.get(),
            "whisperx_model": self.whisperx_model_var.get(),
            "whisperx_device": self.whisperx_device_var.get(),
            "max_clips": self.max_clips_var.get(),
            "max_chunks": self.max_chunks_var.get(),
            "min_clip_seconds": self.min_clip_seconds_var.get(),
            "max_clip_seconds": self.max_clip_seconds_var.get(),
        }

    def load_settings(self):
        if not os.path.exists(SETTINGS_PATH):
            return

        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        self.source_var.set(settings.get("source", self.source_var.get()))
        self.url_var.set(settings.get("url", self.url_var.get()))
        self.local_var.set(settings.get("local_video", self.local_var.get()))
        self.folder_var.set(settings.get("output_folder", self.folder_var.get()))
        self.model_var.set(settings.get("model_file", self.model_var.get()))
        self.caption_mode_var.set(settings.get("caption_mode", self.caption_mode_var.get()))
        self.whisperx_model_var.set(settings.get("whisperx_model", self.whisperx_model_var.get()))
        self.whisperx_device_var.set(settings.get("whisperx_device", self.whisperx_device_var.get()))
        self.max_clips_var.set(settings.get("max_clips", self.max_clips_var.get()))
        self.max_chunks_var.set(settings.get("max_chunks", self.max_chunks_var.get()))
        self.min_clip_seconds_var.set(settings.get("min_clip_seconds", self.min_clip_seconds_var.get()))
        self.max_clip_seconds_var.set(settings.get("max_clip_seconds", self.max_clip_seconds_var.get()))
        self.toggle_source()

    def save_settings(self):
        try:
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.get_settings(), f, indent=2)
        except OSError as e:
            self.log(f"[WARNING] Could not save settings: {e}")

    def browse_local_video(self):
        file = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.webm"), ("All Files", "*.*")])
        if file:
            self.local_var.set(file)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_var.set(folder)
            
    def browse_model(self):
        os.makedirs(MODELS_FOLDER_DEFAULT, exist_ok=True)
        file = filedialog.askopenfilename(initialdir=MODELS_FOLDER_DEFAULT, filetypes=[("GGUF Models", "*.gguf"), ("All Files", "*.*")])
        if file:
            self.model_var.set(file)

    def open_clips_folder(self):
        folder = self.folder_var.get()
        clips_folder = os.path.join(folder, "clips")
        if os.path.exists(clips_folder):
            os.startfile(clips_folder)

    def log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def set_status(self, msg, progress=None):
        def _update():
            self.status_var.set(msg)
            if progress is not None:
                self.progress_var.set(progress)
        self.root.after(0, _update)

    def check_dependencies(self):
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.log("[OK] ffmpeg found in PATH.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[WARNING] ffmpeg not found in PATH! Stage 6 will fail.")
            messagebox.showwarning("Missing Dependency", "ffmpeg is not found in PATH. Please install ffmpeg.")
            
        try:
            subprocess.run(["yt-dlp", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.log("[OK] yt-dlp found in PATH.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[WARNING] yt-dlp not found in PATH! Stage 1 will fail.")
            messagebox.showwarning("Missing Dependency", "yt-dlp is not found in PATH. Please install yt-dlp.")

        if requests is None:
            self.log("[WARNING] 'requests' library not installed! Inference will fail.")
            messagebox.showwarning("Missing Dependency", "The 'requests' Python library is not installed. Please run 'pip install requests'.")

        if not os.path.exists(LLAMA_SERVER_PATH):
            self.log(f"[WARNING] llama-server.exe not found at {LLAMA_SERVER_PATH}!")
            messagebox.showwarning("Missing Dependency", f"llama-server.exe is missing!\nExpected at: {LLAMA_SERVER_PATH}")

        try:
            subprocess.run([sys.executable, "-m", "whisperx", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            self.log("[OK] WhisperX found.")
        except (subprocess.CalledProcessError, FileNotFoundError):
            if os.path.exists(WHISPERX_WHEEL_PATH):
                self.log(f"[WARNING] WhisperX is not installed. Wheel found at: {WHISPERX_WHEEL_PATH}")
            else:
                self.log("[WARNING] WhisperX is not installed and the configured wheel path was not found.")

    def on_close(self):
        self.save_settings()
        self.stop_server()
        self.root.destroy()
        
    def start_pipeline(self):
        source_type = self.source_var.get()
        url = self.url_var.get().strip()
        local_video = self.local_var.get().strip()
        folder = self.folder_var.get().strip()
        model_file = self.model_var.get().strip()
        caption_mode = self.caption_mode_var.get()
        whisperx_model = self.whisperx_model_var.get().strip()
        whisperx_device = self.whisperx_device_var.get().strip()
        max_clips_text = self.max_clips_var.get().strip()
        max_chunks_text = self.max_chunks_var.get().strip()
        min_clip_seconds_text = self.min_clip_seconds_var.get().strip()
        max_clip_seconds_text = self.max_clip_seconds_var.get().strip()

        try:
            max_clips = int(max_clips_text)
            max_chunks = int(max_chunks_text)
            min_clip_seconds = float(min_clip_seconds_text)
            max_clip_seconds = float(max_clip_seconds_text)
        except ValueError:
            messagebox.showerror("Error", "Clip counts and clip seconds must be valid numbers.")
            return

        if source_type == "url" and not url:
            messagebox.showerror("Error", "Please enter a YouTube URL.")
            return
        if source_type == "local" and not local_video:
            messagebox.showerror("Error", "Please select a local video file.")
            return
        if not folder:
            messagebox.showerror("Error", "Please select an output folder.")
            return
        if not model_file:
            messagebox.showerror("Error", "Please select a model file.")
            return
        if caption_mode in ("Auto (SRT then WhisperX)", "WhisperX") and not whisperx_model:
            messagebox.showerror("Error", "Please enter a WhisperX model name.")
            return
        if whisperx_device not in ("cpu", "cuda"):
            messagebox.showerror("Error", "WhisperX device must be cpu or cuda.")
            return
        if max_clips < 1:
            messagebox.showerror("Error", "Max clips must be at least 1.")
            return
        if max_chunks < 0:
            messagebox.showerror("Error", "Max chunks must be 0 or higher.")
            return
        if min_clip_seconds < 15:
            messagebox.showerror("Error", "Min clip seconds must be at least 15.")
            return
        if max_clip_seconds < min_clip_seconds:
            messagebox.showerror("Error", "Max clip seconds must be greater than or equal to min clip seconds.")
            return

        self.save_settings()

        self.start_btn.config(state=tk.DISABLED)
        self.open_btn.config(state=tk.DISABLED)
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        threading.Thread(
            target=self.run_pipeline,
            args=(
                source_type, url, local_video, folder, model_file,
                caption_mode, whisperx_model, whisperx_device,
                max_clips, max_chunks, min_clip_seconds, max_clip_seconds
            ),
            daemon=True
        ).start()

    def run_pipeline(
        self, source_type, url, local_video, folder, model_file,
        caption_mode, whisperx_model, whisperx_device,
        max_clips, max_chunks, min_clip_seconds, max_clip_seconds
    ):
        try:
            self.log("=== Pipeline Started ===")
            chunks_label = "all" if max_chunks == 0 else str(max_chunks)
            self.log(
                f"Settings: max clips={max_clips}, max chunks={chunks_label}, "
                f"clip length={min_clip_seconds:g}-{max_clip_seconds:g}s"
            )
            
            if source_type == "url":
                self.set_status("Stage 1/7: Downloading", 5)
                require_subtitles = caption_mode == "Existing SRT only"
                video_file, srt_file = self.stage_1_download(url, folder, require_subtitles=require_subtitles)
            else:
                self.set_status("Stage 1/7: Locating local files", 5)
                video_file = local_video
                srt_file = self.find_local_srt(video_file)
                if not srt_file and caption_mode == "Existing SRT only":
                    raise RuntimeError("Could not find a matching .srt or .vtt file next to the video.")
                self.log(f"Using local video: {video_file}")
                if srt_file:
                    self.log(f"Using local subs: {srt_file}")

            if caption_mode == "WhisperX" or (caption_mode == "Auto (SRT then WhisperX)" and not srt_file):
                self.set_status("Stage 2/7: Transcribing with WhisperX", 15)
                srt_file = self.stage_whisperx_transcribe(video_file, folder, whisperx_model, whisperx_device)
            elif not srt_file:
                raise RuntimeError("No subtitle file available.")
            
            self.set_status("Stage 2/7: Parsing SRT", 20)
            captions = self.stage_2_parse_srt(srt_file)
            
            self.set_status("Stage 3/7: Chunking", 30)
            chunks = self.stage_3_chunking(captions)
            if max_chunks > 0 and len(chunks) > max_chunks:
                original_chunk_count = len(chunks)
                chunks = chunks[:max_chunks]
                self.log(f"Limiting analysis to first {len(chunks)} of {original_chunk_count} chunks.")
            
            self.set_status("Loading model...", 40)
            candidates = self.stage_4_analysis(chunks, model_file)
            
            self.set_status("Stage 5/7: Selecting Candidates", 70)
            prepared_candidates = self.stage_5_selection(
                candidates, video_file, max_clips, captions, min_clip_seconds, max_clip_seconds
            )
            if not prepared_candidates:
                raise RuntimeError("No valid candidates found after time validation.")

            self.set_status("Waiting for clip selection...", 75)
            selected_clips = self.choose_candidates(prepared_candidates, max_clips)
            if not selected_clips:
                raise RuntimeError("No clips were selected.")
            
            self.set_status("Stage 6/7: Cutting Clips", 80)
            self.stage_6_cut_clips(selected_clips, video_file, folder)
            
            self.set_status("Stage 7/7: Creating Manifest", 95)
            self.stage_7_manifest(selected_clips, folder)
            
            self.set_status("Done!", 100)
            self.log("\n=== Pipeline Completed Successfully ===")
            self.root.after(0, lambda: self.open_btn.config(state=tk.NORMAL))
            self.root.after(0, self.open_clips_folder)

        except Exception as e:
            self.log(f"\n[ERROR] Pipeline failed: {str(e)}")
            self.set_status("Failed!", 0)
        finally:
            self.stop_server()
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

    def find_local_srt(self, video_file):
        base_path, _ = os.path.splitext(video_file)
        for ext in ['.srt', '.vtt', '.en.srt', '.en.vtt', '.en-US.srt']:
            srt_path = base_path + ext
            if os.path.exists(srt_path):
                return srt_path
        
        directory = os.path.dirname(video_file)
        base_name = os.path.basename(base_path)
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.startswith(base_name) and (file.endswith(".srt") or file.endswith(".vtt")):
                    return os.path.join(directory, file)
        return None

    def stage_whisperx_transcribe(self, video_file, folder, whisperx_model, whisperx_device):
        self.log("Generating captions with WhisperX...")
        output_dir = os.path.join(folder, "whisperx_captions")
        os.makedirs(output_dir, exist_ok=True)

        audio_file = self.extract_audio_for_whisperx(video_file, output_dir)

        compute_type = "float16" if whisperx_device == "cuda" else "int8"
        cmd = [
            sys.executable,
            "-m", "whisperx",
            audio_file,
            "--model", whisperx_model,
            "--device", whisperx_device,
            "--compute_type", compute_type,
            "--language", "en",
            "--output_dir", output_dir,
            "--output_format", "srt",
            "--vad_method", "silero",
            "--segment_resolution", "sentence",
            "--condition_on_previous_text", "False",
            "--verbose", "True"
        ]

        self.log(f"Running: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        for line in process.stdout:
            line = line.strip()
            if line:
                self.log(line)
        process.wait()

        if process.returncode != 0:
            install_hint = f"Install it with: {sys.executable} -m pip install \"{WHISPERX_WHEEL_PATH}\""
            raise RuntimeError(f"WhisperX transcription failed. {install_hint}")

        base_name = os.path.splitext(os.path.basename(audio_file))[0]
        expected_srt = os.path.join(output_dir, base_name + ".srt")
        if os.path.exists(expected_srt):
            self.log(f"WhisperX captions saved to: {expected_srt}")
            return expected_srt

        srt_files = [
            os.path.join(output_dir, name)
            for name in os.listdir(output_dir)
            if name.lower().endswith(".srt")
        ]
        if not srt_files:
            raise RuntimeError("WhisperX completed but no .srt file was found.")

        latest_srt = max(srt_files, key=os.path.getmtime)
        self.log(f"WhisperX captions saved to: {latest_srt}")
        return latest_srt

    def extract_audio_for_whisperx(self, video_file, output_dir):
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        audio_file = os.path.join(output_dir, base_name + "_whisperx.wav")
        self.log(f"Extracting audio for WhisperX: {audio_file}")

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_file,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", "pcm_s16le",
            audio_file
        ]
        process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
        if process.returncode != 0:
            raise RuntimeError(f"Failed to extract audio for WhisperX: {process.stderr}")
        return audio_file

    def stage_1_download(self, url, folder, require_subtitles=True):
        self.log("Starting download with yt-dlp...")
        os.makedirs(folder, exist_ok=True)
        
        base_name = f"video_{int(time.time())}"
        output_template = os.path.join(folder, f"{base_name}.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "--write-subs",
            "--write-auto-subs",
            "--sub-lang", "en",
            "--sub-format", "srt",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_template,
            url
        ]
        
        self.log(f"Running: {' '.join(cmd)}")
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        for line in process.stdout:
            if "[download]" in line or "[info]" in line or "Destination:" in line:
                self.log(line.strip())
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError("yt-dlp download failed.")
            
        video_file = None
        srt_file = None
        
        for file in os.listdir(folder):
            if file.startswith(base_name):
                full_path = os.path.join(folder, file)
                if file.endswith(".mp4") or file.endswith(".mkv") or file.endswith(".webm"):
                    video_file = full_path
                elif file.endswith(".srt") or file.endswith(".vtt"):
                    srt_file = full_path
                    
        if not video_file:
            raise RuntimeError("Downloaded video file not found.")
        if not srt_file and require_subtitles:
            raise RuntimeError("Subtitle file not found. Video might not have English subtitles.")
            
        self.log(f"Video saved to: {video_file}")
        if srt_file:
            self.log(f"Subs saved to: {srt_file}")
        else:
            self.log("No downloaded subtitles found; WhisperX can generate captions next.")
        return video_file, srt_file

    def stage_2_parse_srt(self, srt_file):
        self.log("Parsing SRT file...")
        with open(srt_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        blocks = re.split(r'\n\s*\n', content.strip())
        captions = []
        
        def parse_time(time_str):
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            return float(time_str)

        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                idx = lines[0]
                times = lines[1].split('-->')
                if len(times) == 2:
                    start_sec = parse_time(times[0].strip())
                    end_sec = parse_time(times[1].strip())
                    text = " ".join([l.strip() for l in lines[2:]])
                    
                    text = re.sub(r'<[^>]+>', '', text)
                    text = text.replace('\\N', ' ').strip()
                    
                    if text:
                        captions.append({
                            "index": idx,
                            "start_seconds": start_sec,
                            "end_seconds": end_sec,
                            "text": text
                        })
        
        cleaned_captions = []
        last_text = None
        for cap in captions:
            if cap['text'] != last_text:
                cleaned_captions.append(cap)
                last_text = cap['text']
            else:
                cleaned_captions[-1]['end_seconds'] = cap['end_seconds']
                
        self.log(f"Parsed {len(cleaned_captions)} unique caption blocks.")
        if not cleaned_captions:
            raise RuntimeError("No captions could be parsed from the SRT.")
        return cleaned_captions

    def stage_3_chunking(self, captions):
        self.log("Chunking captions (3-4 mins, 30s overlap)...")
        chunks = []
        if not captions:
            return chunks
            
        target_duration = 210  # 3.5 minutes
        overlap = 30
        
        current_chunk_caps = []
        chunk_start_time = captions[0]['start_seconds']
        
        i = 0
        while i < len(captions):
            cap = captions[i]
            current_chunk_caps.append(cap)
            
            duration = cap['end_seconds'] - chunk_start_time
            
            if duration >= target_duration or i == len(captions) - 1:
                chunk_text = []
                for c in current_chunk_caps:
                    chunk_text.append(f"[{c['start_seconds']:.2f} - {c['end_seconds']:.2f}] {c['text']}")
                
                chunks.append({
                    "start": chunk_start_time,
                    "end": cap['end_seconds'],
                    "text": "\n".join(chunk_text)
                })
                
                if i == len(captions) - 1:
                    break
                    
                overlap_target = cap['end_seconds'] - overlap
                next_start_idx = i
                for j in range(len(current_chunk_caps)-1, -1, -1):
                    if current_chunk_caps[j]['start_seconds'] <= overlap_target:
                        next_start_idx = i - (len(current_chunk_caps) - 1 - j)
                        break
                        
                i = next_start_idx
                current_chunk_caps = []
                if i < len(captions):
                    chunk_start_time = captions[i]['start_seconds']
            else:
                i += 1
                
        self.log(f"Created {len(chunks)} chunks.")
        return chunks

    def start_llama_server(self, model_file):
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"Model file not found: {model_file}")
            
        self.log(f"Starting llama-server with model {model_file}...")
        cmd = [
            LLAMA_SERVER_PATH,
            "-m", model_file,
            "-ngl", "100",
            "--port", "8080",
            "-c", "8192",
            "--reasoning-format", "none",
            "--no-webui"
        ]
        
        server_log_path = os.path.join(os.path.dirname(model_file), "llama_server.log")
        self.log(f"Server log: {server_log_path}")
        self._server_log_file = open(server_log_path, "w")
        self.server_process = subprocess.Popen(
            cmd,
            stdout=self._server_log_file,
            stderr=self._server_log_file
        )
        self.root.after(0, lambda: self.stop_btn.config(state=tk.NORMAL))
        
        for i in range(60):
            self.set_status(f"Starting model server... ({i}s)")
            try:
                resp = requests.get("http://127.0.0.1:8080/health", timeout=1)
                if resp.status_code == 200:
                    self.log("llama-server is ready!")
                    return
            except Exception:
                pass
            time.sleep(1)
            
        raise RuntimeError("llama-server failed to start within 60 seconds.")

    def stop_server(self):
        if self.server_process is not None:
            self.log("Stopping llama-server...")
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except Exception as e:
                self.log(f"[ERROR] Failed to kill server: {e}")
            self.server_process = None
        if hasattr(self, '_server_log_file') and self._server_log_file:
            try:
                self._server_log_file.close()
            except Exception:
                pass
            self._server_log_file = None
        self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))

    def stage_4_analysis(self, chunks, model_file):
        self.start_llama_server(model_file)
        
        self.log("Starting analysis via HTTP API...")
        all_candidates = []
        
        system_prompt = (
            "You are a viral short-form video analyst. Your job is to find self-contained moments in a transcript that would perform well as YouTube Shorts or TikTok clips (20-60 seconds).\n\n"
            "CONTEXT:\n"
            "- Timestamps are in seconds from the start of the video\n"
            "- The transcript may lack punctuation or have irregular formatting\n"
            "- This is a clip that will be watched by someone with zero prior context\n\n"
            "WHAT TO LOOK FOR:\n"
            "- Strong punchlines or joke payoffs with clear setup\n"
            "- Surprising, counterintuitive, or shocking statements\n"
            "- Emotional peaks (excitement, anger, disbelief, laughter)\n"
            "- Highly quotable standalone opinions or declarations\n"
            "- Controversy or strong takes that provoke a reaction\n"
            "- Clear setup + payoff structure that resolves within the clip\n\n"
            "STRICT RULES:\n"
            "- The clip must make complete sense to someone who has never seen the full video\n"
            "- Start at the setup or hook, never mid-thought\n"
            "- End only after the punchline, payoff, or thought fully resolves\n"
            "- Do not pick moments that rely on earlier context to land\n"
            "- Do not pick moments that fade out or trail off without resolution\n"
            "- Ignore filler, transitions, introductions, and topic changes\n\n"
            "Return ONLY a valid JSON array. No explanation, no markdown, no preamble, no trailing text. If no moments qualify, return an empty array [].\n\n"
            "Each object must have exactly these fields:\n"
            "{\n"
            '  "start_time": float (seconds),\n'
            '  "end_time": float (seconds),\n'
            '  "context": "one sentence describing what happens at this moment",\n'
            '  "reason": "one sentence why a viewer would stop scrolling for this",\n'
            '  "hook": "2-3 word thumbnail title for this clip",\n'
            '  "score": integer 1-10\n'
            "}\n\n"
            "Only include moments scoring 6 or higher. A 10 means someone would immediately share this clip."
        )

        for idx, chunk in enumerate(chunks):
            self.set_status(f"Stage 4/7: Analyzing chunk {idx+1}/{len(chunks)}")
            self.log(f"Analyzing chunk {idx+1}/{len(chunks)} [{chunk['start']:.1f}s to {chunk['end']:.1f}s]...")
            
            payload = {
                "model": "local",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"/no_think\nTranscript:\n{chunk['text']}"}
                ],
                "max_tokens": 4096,
                "temperature": 0.3,
                "repeat_penalty": 1.1,
                "stream": False,
                "thinking": False
            }

            try:
                response = requests.post(
                    "http://127.0.0.1:8080/v1/chat/completions",
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                
                try:
                    output_text = response.json()["choices"][0]["message"]["content"].strip()
                    candidates = self.extract_json_array(output_text)
                    all_candidates.extend(candidates)
                    self.log(f"Found {len(candidates)} candidates in chunk {idx+1}.")
                except json.JSONDecodeError:
                    self.log(f"[ERROR] Failed to parse JSON for chunk {idx+1}. Model output was:\n{output_text}")
                    
            except requests.RequestException as e:
                self.log(f"[ERROR] HTTP request failed on chunk {idx+1}: {str(e)}")
                if e.response is not None:
                    self.log(f"Server response: {e.response.text}")
            except Exception as e:
                self.log(f"[ERROR] Inference failed on chunk {idx+1}: {str(e)}")

        self.log(f"Total candidates before deduplication: {len(all_candidates)}")
        unique_candidates = []
        for cand in all_candidates:
            if not self.is_valid_candidate_object(cand):
                continue
            is_dup = False
            for u_cand in unique_candidates:
                if not (cand.get('end_time', 0) < u_cand.get('start_time', 0) or cand.get('start_time', 0) > u_cand.get('end_time', 0)):
                    is_dup = True
                    if cand.get('score', 0) > u_cand.get('score', 0):
                        u_cand.update(cand)
                    break
            if not is_dup:
                unique_candidates.append(cand)
                
        self.log(f"Total candidates after deduplication: {len(unique_candidates)}")
        return unique_candidates

    @staticmethod
    def extract_json_array(output_text):
        clean_text = re.sub(r'<think>[\s\S]*?</think>', '', output_text, flags=re.DOTALL).strip()
        clean_text = re.sub(r'^```json\s*', '', clean_text)
        clean_text = re.sub(r'^```\s*', '', clean_text)
        clean_text = re.sub(r'\s*```$', '', clean_text)

        decoder = json.JSONDecoder()
        empty_candidate_array = None
        for match in re.finditer(r'\[', clean_text):
            try:
                value, _ = decoder.raw_decode(clean_text[match.start():])
            except json.JSONDecodeError:
                continue

            if value == []:
                empty_candidate_array = value
                continue

            if (
                isinstance(value, list)
                and all(ClipHarvesterApp.is_valid_candidate_object(item) for item in value)
            ):
                return value

        if empty_candidate_array is not None:
            return empty_candidate_array

        raise json.JSONDecodeError("No JSON array found in model output", clean_text, 0)

    @staticmethod
    def is_valid_candidate_object(candidate):
        if not isinstance(candidate, dict):
            return False
        required = ("start_time", "end_time", "context", "reason", "hook", "score")
        return all(key in candidate for key in required)

    def stage_5_selection(self, candidates, video_file, max_clips, captions, min_duration, max_duration):
        self.log("Selecting and validating candidates...")
        cmd = ["ffmpeg", "-i", video_file]
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, errors="replace")
        _, stderr = process.communicate()
        
        video_duration = 999999.0
        dur_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})", stderr)
        if dur_match:
            h, m, s = dur_match.groups()
            video_duration = int(h) * 3600 + int(m) * 60 + float(s)
            
        valid_candidates = []
        for cand in candidates:
            try:
                raw_start = float(cand.get('start_time', 0))
                raw_end = float(cand.get('end_time', 0))
                score = int(cand.get('score', 0))
                
                if raw_start >= raw_end:
                    continue

                start, end = self.expand_candidate_range(
                    captions, raw_start, raw_end, video_duration, min_duration, max_duration
                )
                duration = end - start

                if min_duration <= duration <= max_duration and score >= 6:
                    cand = dict(cand)
                    cand['start_time'] = start
                    cand['end_time'] = end
                    cand['raw_start_time'] = raw_start
                    cand['raw_end_time'] = raw_end
                    cand['score'] = score
                    cand['caption'] = self.caption_text_for_range(captions, start, end)
                    valid_candidates.append(cand)
            except (ValueError, KeyError):
                continue
                
        valid_candidates.sort(key=lambda x: x['score'], reverse=True)
        self.log(f"Prepared {len(valid_candidates)} selectable candidates. You can choose up to {max_clips}.")
        return valid_candidates

    @staticmethod
    def expand_candidate_range(captions, raw_start, raw_end, video_duration, min_duration, max_duration):
        raw_start = max(0.0, raw_start)
        raw_end = min(video_duration, raw_end)

        overlap_indexes = [
            idx for idx, cap in enumerate(captions)
            if cap.get('end_seconds', 0) >= raw_start and cap.get('start_seconds', 0) <= raw_end
        ]

        if overlap_indexes:
            start_idx = max(0, overlap_indexes[0] - 1)
            end_idx = min(len(captions) - 1, overlap_indexes[-1] + 2)
            start = max(0.0, captions[start_idx]['start_seconds'] - 1.0)
            end = min(video_duration, captions[end_idx]['end_seconds'] + 2.0)
        else:
            start_idx = None
            end_idx = None
            start = max(0.0, raw_start - 3.0)
            end = min(video_duration, raw_end + 8.0)

        expand_after_turns = 0
        while end - start < min_duration:
            grew = False
            if end_idx is not None and end_idx < len(captions) - 1 and expand_after_turns < 3:
                end_idx += 1
                end = min(video_duration, captions[end_idx]['end_seconds'] + 2.0)
                expand_after_turns += 1
                grew = True
            elif start_idx is not None and start_idx > 0:
                start_idx -= 1
                start = max(0.0, captions[start_idx]['start_seconds'] - 1.0)
                expand_after_turns = 0
                grew = True
            elif end_idx is not None and end_idx < len(captions) - 1:
                end_idx += 1
                end = min(video_duration, captions[end_idx]['end_seconds'] + 2.0)
                grew = True
            else:
                extra = min_duration - (end - start)
                start = max(0.0, start - extra * 0.25)
                end = min(video_duration, end + extra * 0.75)
                grew = True

            if not grew or start <= 0.0 and end >= video_duration:
                break

        if end - start < min_duration:
            missing = min_duration - (end - start)
            end = min(video_duration, end + missing)
            start = max(0.0, start - max(0.0, min_duration - (end - start)))

        completion_extends = 0
        while end_idx is not None and end_idx < len(captions) - 1 and end - start < max_duration:
            current_text = captions[end_idx].get('text', '').strip()
            next_cap = captions[end_idx + 1]
            gap = next_cap.get('start_seconds', 0) - captions[end_idx].get('end_seconds', 0)
            if gap > 4.0:
                break
            if current_text.endswith(('.', '!', '?', '"')) and end - start >= min_duration:
                break
            potential_end = min(video_duration, next_cap['end_seconds'] + 2.0)
            if potential_end - start > max_duration:
                break
            end_idx += 1
            end = potential_end
            completion_extends += 1
            if completion_extends >= 4:
                break

        if end - start > max_duration:
            preferred_end = min(video_duration, start + max_duration)
            if raw_end <= preferred_end:
                end = preferred_end
            else:
                end = min(video_duration, raw_end + 4.0)
                start = max(0.0, end - max_duration)

        return round(start, 2), round(end, 2)

    @staticmethod
    def caption_text_for_range(captions, start, end):
        lines = []
        for cap in captions:
            cap_start = cap.get('start_seconds', 0)
            cap_end = cap.get('end_seconds', 0)
            if cap_end >= start and cap_start <= end:
                text = cap.get('text', '').strip()
                if text:
                    lines.append(text)
        return " ".join(lines)

    def choose_candidates(self, candidates, max_clips):
        selection_event = threading.Event()
        result = {"clips": []}

        def show_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("Choose Clips")
            dialog.geometry("850x560")
            dialog.minsize(700, 430)
            dialog.transient(self.root)

            outer = ttk.Frame(dialog, padding=10)
            outer.pack(fill=tk.BOTH, expand=True)

            ttk.Label(outer, text=f"Select up to {max_clips} clips to cut.").pack(anchor=tk.W, pady=(0, 8))

            body = ttk.Frame(outer)
            body.pack(fill=tk.BOTH, expand=True)

            list_frame = ttk.Frame(body)
            list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, exportselection=False, width=58)
            list_scroll = ttk.Scrollbar(list_frame, command=listbox.yview)
            listbox.configure(yscrollcommand=list_scroll.set)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            preview_frame = ttk.Frame(body)
            preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
            preview = tk.Text(preview_frame, state=tk.DISABLED, wrap=tk.WORD, height=18)
            preview_scroll = ttk.Scrollbar(preview_frame, command=preview.yview)
            preview.configure(yscrollcommand=preview_scroll.set)
            preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)

            def format_time(seconds):
                return str(timedelta(seconds=int(seconds)))

            def duration(clip):
                return clip['end_time'] - clip['start_time']

            for idx, clip in enumerate(candidates):
                preview_text = clip.get('caption') or clip.get('context') or clip.get('hook') or ''
                preview_text = " ".join(preview_text.split())
                if len(preview_text) > 72:
                    preview_text = preview_text[:69] + "..."
                label = (
                    f"{idx + 1:02d}. score {clip.get('score', 0)} | {clip.get('hook', 'Untitled')} | "
                    f"{format_time(clip['start_time'])}-{format_time(clip['end_time'])} "
                    f"({duration(clip):.1f}s) | {preview_text}"
                )
                listbox.insert(tk.END, label)

            for idx in range(min(max_clips, len(candidates))):
                listbox.selection_set(idx)

            def show_preview(_event=None):
                indexes = listbox.curselection()
                if not indexes:
                    text = "No candidate selected."
                else:
                    clip = candidates[indexes[0]]
                    text = (
                        f"Candidate {indexes[0] + 1:02d}\n"
                        f"Time: {format_time(clip['start_time'])} -> {format_time(clip['end_time'])}\n"
                        f"Model Moment: {format_time(clip.get('raw_start_time', clip['start_time']))} -> {format_time(clip.get('raw_end_time', clip['end_time']))}\n"
                        f"Duration: {duration(clip):.1f}s\n"
                        f"Score: {clip.get('score', 0)}\n\n"
                        f"Hook:\n{clip.get('hook', '')}\n\n"
                        f"Context:\n{clip.get('context', '')}\n\n"
                        f"Caption:\n{clip.get('caption', '')}\n\n"
                        f"Reason:\n{clip.get('reason', '')}"
                    )
                preview.config(state=tk.NORMAL)
                preview.delete(1.0, tk.END)
                preview.insert(tk.END, text)
                preview.config(state=tk.DISABLED)

            def finish_with_selection():
                indexes = listbox.curselection()
                if not indexes:
                    messagebox.showerror("No Selection", "Please select at least one candidate.", parent=dialog)
                    return
                if len(indexes) > max_clips:
                    messagebox.showerror("Too Many Clips", f"Please select {max_clips} clips or fewer.", parent=dialog)
                    return
                result["clips"] = [candidates[i] for i in indexes]
                dialog.destroy()
                selection_event.set()

            def cancel_selection():
                result["clips"] = []
                dialog.destroy()
                selection_event.set()

            btn_frame = ttk.Frame(outer)
            btn_frame.pack(fill=tk.X, pady=(10, 0))
            ttk.Button(btn_frame, text="Cut Selected", command=finish_with_selection).pack(side=tk.RIGHT)
            ttk.Button(btn_frame, text="Cancel", command=cancel_selection).pack(side=tk.RIGHT, padx=(0, 10))
            ttk.Button(btn_frame, text="Select Top", command=lambda: (listbox.selection_clear(0, tk.END), [listbox.selection_set(i) for i in range(min(max_clips, len(candidates)))], show_preview())).pack(side=tk.LEFT)
            ttk.Button(btn_frame, text="Clear", command=lambda: (listbox.selection_clear(0, tk.END), show_preview())).pack(side=tk.LEFT, padx=(10, 0))

            listbox.bind("<<ListboxSelect>>", show_preview)
            dialog.protocol("WM_DELETE_WINDOW", cancel_selection)
            show_preview()
            dialog.grab_set()
            dialog.focus_set()

        self.root.after(0, show_dialog)
        selection_event.wait()
        self.log(f"User selected {len(result['clips'])} clips.")
        return result["clips"]

    def stage_6_cut_clips(self, clips, video_file, folder):
        clips_dir = os.path.join(folder, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        self.log(f"Cutting clips into {clips_dir}...")
        
        for idx, clip in enumerate(clips):
            clip_num = str(idx + 1).zfill(2)
            score = clip['score']
            out_name = f"clip_{clip_num}_score{score}.mp4"
            out_path = os.path.join(clips_dir, out_name)
            
            self.log(f"Cutting {out_name} ({clip['start_time']:.1f}s -> {clip['end_time']:.1f}s)...")
            
            cmd = [
                "ffmpeg",
                "-y",
                "-ss", str(clip['start_time']),
                "-to", str(clip['end_time']),
                "-i", video_file,
                "-c", "copy",
                out_path
            ]
            
            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except subprocess.CalledProcessError as e:
                self.log(f"[ERROR] Failed to cut {out_name}: {e.stderr.decode('utf-8', errors='replace')}")

    def stage_7_manifest(self, clips, folder):
        manifest_path = os.path.join(folder, "manifest.txt")
        self.log(f"Generating manifest at {manifest_path}...")
        
        def format_time(seconds):
            return str(timedelta(seconds=int(seconds)))
            
        with open(manifest_path, "w", encoding="utf-8") as f:
            for idx, clip in enumerate(clips):
                clip_num = str(idx + 1).zfill(2)
                score = clip['score']
                start_fmt = format_time(clip['start_time'])
                end_fmt = format_time(clip['end_time'])
                
                f.write(f"[CLIP {clip_num}] score={score} | {start_fmt} --> {end_fmt}\n")
                f.write(f"Hook: {clip.get('hook', '')}\n")
                f.write(f"Context: {clip.get('context', '')}\n")
                f.write(f"Reason: {clip.get('reason', '')}\n")
                f.write(f"File: clips/clip_{clip_num}_score{score}.mp4\n")
                f.write("---\n\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = ClipHarvesterApp(root)
    root.mainloop()
