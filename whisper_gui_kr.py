import shutil
import threading
from difflib import SequenceMatcher
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, ttk
except ImportError:  # pragma: no cover - stdlib Tk is missing on some Linux installs
    tk = None
    filedialog = None
    ttk = None


AUDIO_FILETYPES = [
    ("오디오/비디오", "*.wav *.mp3 *.m4a *.mp4 *.flac *.ogg *.mkv *.webm *.mov"),
    ("WAV files", "*.wav"),
    ("All files", "*.*"),
]
SCRIPT_FILETYPES = [
    ("Text files", "*.txt"),
    ("All files", "*.*"),
]
MODEL_SIZES = ("small", "medium", "large")
SCRIPT_MODES = ("무조건", "강", "약")
# 강 = 대본을 더 쉽게 채택, 약 = Whisper 결과를 더 쉽게 유지
SCRIPT_MODE_THRESHOLDS = {"강": 0.4, "약": 0.7}


def format_timestamp(seconds):
    """SRT timestamp with rounded milliseconds (Whisper writer style)."""
    milliseconds = int(round(max(float(seconds), 0.0) * 1000.0))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def read_text_auto(path):
    """Read a script, accepting UTF-8 (with/without BOM) and Korean Windows CP949."""
    raw = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return raw.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").strip()


def write_srt(path, segments):
    """Write SRT with UTF-8 BOM so Premiere on Windows shows Korean correctly."""
    path = Path(path)
    lines = []
    for i, segment in enumerate(segments, start=1):
        start = format_timestamp(segment["start"])
        end = format_timestamp(max(segment["end"], segment["start"]))
        text = str(segment.get("text", "")).strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    with open(path, "w", encoding="utf-8-sig", newline="\r\n") as handle:
        handle.write("\n".join(lines))
        if lines:
            handle.write("\n")
    return path


def resolve_srt_path(audio_path, output_dir=""):
    audio_path = Path(audio_path)
    if output_dir:
        return Path(output_dir) / f"{audio_path.stem}.srt"
    return audio_path.with_suffix(".srt")


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def align_segments(segments, script_text, mode):
    """Apply 무조건 / 강 / 약 script alignment to Whisper segments."""
    segments = list(segments or [])
    script_lines = [line.strip() for line in str(script_text).splitlines() if line.strip()]
    if not script_lines or not segments:
        return segments

    mode = (mode or "").strip()
    if mode == "무조건":
        aligned = []
        for index, segment in enumerate(segments):
            text = script_lines[index] if index < len(script_lines) else segment.get("text", "")
            aligned.append({
                "text": text,
                "start": segment["start"],
                "end": segment["end"],
            })
        if len(script_lines) > len(aligned):
            extra = " ".join(script_lines[len(aligned):])
            aligned[-1]["text"] = f"{aligned[-1]['text']} {extra}".strip()
        return aligned

    threshold = SCRIPT_MODE_THRESHOLDS.get(mode, SCRIPT_MODE_THRESHOLDS["강"])
    used = set()
    aligned = []
    for script_line in script_lines:
        best_index = None
        best_ratio = -1.0
        for index, segment in enumerate(segments):
            if index in used:
                continue
            ratio = SequenceMatcher(None, script_line, str(segment.get("text", "")).strip()).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_index = index
        if best_index is None:
            continue
        used.add(best_index)
        segment = segments[best_index]
        text = script_line if best_ratio >= threshold else segment.get("text", "")
        aligned.append({
            "text": text,
            "start": segment["start"],
            "end": segment["end"],
        })
    for index, segment in enumerate(segments):
        if index not in used:
            aligned.append({
                "text": segment.get("text", ""),
                "start": segment["start"],
                "end": segment["end"],
            })
    aligned.sort(key=lambda item: (item["start"], item["end"]))
    return aligned


def import_whisper():
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "openai-whisper가 설치되어 있지 않습니다. "
            "PowerShell에서 pip install -r requirements.txt 를 실행하세요."
        ) from exc
    return whisper


def transcribe_audio_to_srt(
    audio_path,
    script_path="",
    output_dir="",
    script_mode="강",
    model_size="medium",
    transcribe_fn=None,
    progress=None,
    require_ffmpeg=True,
):
    """Transcribe audio and write a Korean SRT. transcribe_fn is injectable for tests."""
    def emit(message):
        if progress:
            progress(message)

    audio_path = Path(audio_path)
    if not str(audio_path):
        raise ValueError("오디오 파일을 선택해주세요.")
    if not audio_path.exists():
        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {audio_path}")

    if require_ffmpeg and not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg를 찾을 수 없습니다. ffmpeg를 설치하고 PATH에 추가한 뒤 다시 시도하세요."
        )

    if model_size not in MODEL_SIZES:
        raise ValueError(f"지원하지 않는 모델 크기입니다: {model_size}")

    script_text = ""
    if script_path:
        script_file = Path(script_path)
        if not script_file.exists():
            raise FileNotFoundError(f"대본 파일을 찾을 수 없습니다: {script_path}")
        script_text = read_text_auto(script_file)

    emit("모델 로딩 중...")
    if transcribe_fn is None:
        whisper = import_whisper()
        model = whisper.load_model(model_size)

        def transcribe_fn(path, options):
            return model.transcribe(path, **options)

    options = {
        "language": "ko",
        "task": "transcribe",
    }
    try:
        import torch
        options["fp16"] = bool(torch.cuda.is_available())
    except Exception:
        options["fp16"] = False
    if script_text:
        options["initial_prompt"] = script_text[:200]

    emit("자막 생성 중...")
    result = transcribe_fn(str(audio_path), options) or {}
    segments = list(result.get("segments") or [])
    if script_text:
        segments = align_segments(segments, script_text, script_mode)

    srt_path = resolve_srt_path(audio_path, output_dir)
    if output_dir:
        srt_path.parent.mkdir(parents=True, exist_ok=True)
    write_srt(srt_path, segments)
    emit("완료! 파일 저장됨: " + str(srt_path))
    return srt_path


class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper 자막 생성기")
        self.root.geometry("600x420")
        self._running = False

        self.frame_files = ttk.LabelFrame(root, text="파일 선택", padding=10)
        self.frame_files.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.frame_files, text="오디오 파일:").grid(row=0, column=0, sticky="w")
        self.audio_path = tk.StringVar()
        ttk.Entry(self.frame_files, textvariable=self.audio_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(self.frame_files, text="찾아보기", command=self.select_audio).grid(row=0, column=2)

        ttk.Label(self.frame_files, text="대본 파일:").grid(row=1, column=0, sticky="w")
        self.script_path = tk.StringVar()
        ttk.Entry(self.frame_files, textvariable=self.script_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(self.frame_files, text="찾아보기", command=self.select_script).grid(row=1, column=2)

        ttk.Label(self.frame_files, text="출력 위치:").grid(row=2, column=0, sticky="w")
        self.output_path = tk.StringVar()
        ttk.Entry(self.frame_files, textvariable=self.output_path, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(self.frame_files, text="찾아보기", command=self.select_output).grid(row=2, column=2)

        self.frame_options = ttk.LabelFrame(root, text="옵션", padding=10)
        self.frame_options.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.frame_options, text="모델 크기:").grid(row=0, column=0, sticky="w")
        self.model_size = ttk.Combobox(self.frame_options, values=list(MODEL_SIZES), state="readonly")
        self.model_size.set("medium")
        self.model_size.grid(row=0, column=1, padx=5)

        ttk.Label(self.frame_options, text="대본 활용:").grid(row=1, column=0, sticky="w")
        self.script_mode = ttk.Combobox(self.frame_options, values=list(SCRIPT_MODES), state="readonly")
        self.script_mode.set("강")
        self.script_mode.grid(row=1, column=1, padx=5)

        self.progress_var = tk.StringVar(value="대기 중...")
        ttk.Label(root, textvariable=self.progress_var, wraplength=560).pack(pady=10)

        self.generate_btn = ttk.Button(root, text="자막 생성", command=self.generate_subtitles)
        self.generate_btn.pack(pady=10)

    def select_audio(self):
        filename = filedialog.askopenfilename(filetypes=AUDIO_FILETYPES)
        if filename:
            self.audio_path.set(filename)

    def select_script(self):
        filename = filedialog.askopenfilename(filetypes=SCRIPT_FILETYPES)
        if filename:
            self.script_path.set(filename)

    def select_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)

    def set_progress(self, message):
        self.root.after(0, lambda m=message: self.progress_var.set(m))

    def generate_subtitles(self):
        if self._running:
            return
        self._running = True
        self.generate_btn.config(state="disabled")

        audio = self.audio_path.get().strip()
        script = self.script_path.get().strip()
        output_dir = self.output_path.get().strip()
        model_size = self.model_size.get().strip()
        script_mode = self.script_mode.get().strip()

        def run():
            try:
                transcribe_audio_to_srt(
                    audio,
                    script_path=script,
                    output_dir=output_dir,
                    script_mode=script_mode,
                    model_size=model_size,
                    progress=self.set_progress,
                )
            except Exception as exc:
                self.set_progress(f"오류 발생: {exc}")
            finally:
                self.root.after(0, self._generation_finished)

        threading.Thread(target=run, daemon=True).start()

    def _generation_finished(self):
        self._running = False
        self.generate_btn.config(state="normal")


def main():
    if tk is None:
        raise SystemExit(
            "tkinter를 찾을 수 없습니다. Windows에서는 Python을 다시 설치하고 "
            "Add python.exe to PATH 를 체크하세요."
        )
    root = tk.Tk()
    WhisperGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
