import whisper
import torch
from pathlib import Path
from difflib import SequenceMatcher
import tkinter as tk
from tkinter import filedialog, ttk
import threading

class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Whisper 자막 생성기")
        self.root.geometry("600x400")

        
        # 파일 선택 프레임
        self.frame_files = ttk.LabelFrame(root, text="파일 선택", padding=10)
        self.frame_files.pack(fill="x", padx=10, pady=5)
        
        # 오디오 파일 선택
        ttk.Label(self.frame_files, text="오디오 파일:").grid(row=0, column=0, sticky="w")
        self.audio_path = tk.StringVar()
        ttk.Entry(self.frame_files, textvariable=self.audio_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(self.frame_files, text="찾아보기", command=self.select_audio).grid(row=0, column=2)
        
        # 대본 파일 선택
        ttk.Label(self.frame_files, text="대본 파일:").grid(row=1, column=0, sticky="w")
        self.script_path = tk.StringVar()
        ttk.Entry(self.frame_files, textvariable=self.script_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(self.frame_files, text="찾아보기", command=self.select_script).grid(row=1, column=2)
        
        # 출력 경로 선택
        ttk.Label(self.frame_files, text="출력 위치:").grid(row=2, column=0, sticky="w")
        self.output_path = tk.StringVar()
        ttk.Entry(self.frame_files, textvariable=self.output_path, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(self.frame_files, text="찾아보기", command=self.select_output).grid(row=2, column=2)
        
        # 모델 선택
        self.frame_options = ttk.LabelFrame(root, text="옵션", padding=10)
        self.frame_options.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(self.frame_options, text="대본 활용:").grid(row=1, column=0, sticky="w")
        self.script_mode = ttk.Combobox(self.frame_options, 
            values=["무조건", "강", "약"])
        self.script_mode.set("강")
        self.script_mode.grid(row=1, column=1, padx=5)

        ttk.Label(self.frame_options, text="모델 크기:").grid(row=0, column=0, sticky="w")
        self.model_size = ttk.Combobox(self.frame_options, values=["small", "medium", "large"])
        self.model_size.set("medium")
        self.model_size.grid(row=0, column=1, padx=5)
        
        # 진행 상태 표시
        self.progress_var = tk.StringVar(value="대기 중...")
        ttk.Label(root, textvariable=self.progress_var).pack(pady=10)
        
        # 실행 버튼
        ttk.Button(root, text="자막 생성", command=self.generate_subtitles).pack(pady=10)
        
    def select_audio(self):
        filename = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if filename:
            self.audio_path.set(filename)
    
    def select_script(self):
        filename = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if filename:
            self.script_path.set(filename)
    
    def select_output(self):
        folder = filedialog.askdirectory()
        if folder:
            self.output_path.set(folder)
    
    def generate_subtitles(self):
        def run():
            try:
                # 입력 파일 경로 검증
                if not self.audio_path.get():
                    raise ValueError("오디오 파일을 선택해주세요.")
                
                if not Path(self.audio_path.get()).exists():
                    raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {self.audio_path.get()}")
                
                self.progress_var.set("모델 로딩 중...")
                model = whisper.load_model(self.model_size.get())
                self.progress_var.set("자막 생성 중...")
                
                options = {
                    "language": "ko",
                    "task": "transcribe",
                    "initial_prompt": None
                }
                
                # 대본 파일 경로 검증
                if self.script_path.get():
                    script_path = Path(self.script_path.get())
                    if not script_path.exists():
                        raise FileNotFoundError(f"대본 파일을 찾을 수 없습니다: {self.script_path.get()}")
                    with open(script_path, 'r', encoding='utf-8') as f:
                        script = f.read().strip()
                        options["initial_prompt"] = script[:200]
                
                # 출력 경로 검증
                if self.output_path.get():
                    output_dir = Path(self.output_path.get())
                    if not output_dir.exists():
                        output_dir.mkdir(parents=True)
                
                if self.script_path.get():
                    with open(self.script_path.get(), 'r', encoding='utf-8') as f:
                        script = f.read().strip()
                        options["initial_prompt"] = script[:200]
                
                result = model.transcribe(self.audio_path.get(), **options)
                
                # 출력 경로 설정
                if self.output_path.get():
                    # 오디오 파일의 이름만 가져오기
                    audio_filename = Path(self.audio_path.get()).stem
                    # 출력 경로에 파일 이름 추가
                    srt_path = Path(self.output_path.get()) / f"{audio_filename}.srt"
                else:
                    # 기본 경로 (오디오 파일과 같은 위치)
                    srt_path = Path(self.audio_path.get()).with_suffix('.srt')
                
                with open(srt_path, 'w', encoding='utf-8') as f:
                    for i, segment in enumerate(result["segments"], start=1):
                        start = self.format_timestamp(segment["start"])
                        end = self.format_timestamp(segment["end"])
                        f.write(f"{i}\n{start} --> {end}\n{segment['text'].strip()}\n\n")
                
                self.progress_var.set("완료! 파일 저장됨: " + str(srt_path))
            except Exception as e:
                self.progress_var.set(f"오류 발생: {str(e)}")
        
        # 별도 스레드에서 실행// ... existing code ...
                
                # 대본 파일 읽기 및 처리
                script_text = ""
                if self.script_path.get():
                    with open(self.script_path.get(), 'r', encoding='utf-8') as f:
                        script_text = f.read().strip()
                        options["initial_prompt"] = script_text[:200]
                
                result = model.transcribe(self.audio_path.get(), **options)
                
                if script_text and self.script_mode.get() in ["무조건", "강", "약"]:
                    script_segments = script_text.split('\n')
                    whisper_text = result["text"].strip()
                    new_segments = []
                    
                    if self.script_mode.get() == "무조건":
                        # 위스퍼의 타임코드만 활용하고 텍스트는 대본 그대로 사용
                        script_idx = 0
                        for segment in result["segments"]:
                            if script_idx < len(script_segments) and script_segments[script_idx].strip():
                                new_segments.append({
                                    "text": script_segments[script_idx],
                                    "start": segment["start"],
                                    "end": segment["end"]
                                })
                                script_idx += 1
                    
                    else:  # "강" 또는 "약" 모드
                        similarity_threshold = 0.7 if self.script_mode.get() == "강" else 0.4
                        
                        for script_line in script_segments:
                            if not script_line.strip():
                                continue
                                
                            best_match = None
                            best_ratio = 0
                            best_start = 0
                            best_end = 0
                            
                            for segment in result["segments"]:
                                ratio = SequenceMatcher(None, script_line, segment["text"]).ratio()
                                if ratio > best_ratio:
                                    best_ratio = ratio
                                    best_match = segment["text"]
                                    best_start = segment["start"]
                                    best_end = segment["end"]
                            
                            if best_match:
                                # "강" 모드에서는 유사도가 높을 때만 대본 사용
                                final_text = script_line if (best_ratio >= similarity_threshold) else best_match
                                new_segments.append({
                                    "text": final_text,
                                    "start": best_start,
                                    "end": best_end
                                })
                    
                    result["segments"] = new_segments
                
                # 대본이 있는 경우, 대본의 문장 구분을 기준으로 세그먼트 조정
                if script_text:
                    script_segments = script_text.split('\n')
                    whisper_text = result["text"].strip()
                    
                    # 대본의 각 줄과 가장 유사한 부분을 찾아 새로운 세그먼트 생성
                    new_segments = []
                    current_time = 0
                    
                    for script_line in script_segments:
                        if not script_line.strip():  # 빈 줄 건너뛰기
                            continue
                            
                        best_match = None
                        best_ratio = 0
                        best_start = 0
                        best_end = 0
                        
                        # 기존 세그먼트들을 검사하여 가장 유사한 부분 찾기
                        for segment in result["segments"]:
                            ratio = SequenceMatcher(None, script_line, segment["text"]).ratio()
                            if ratio > best_ratio:
                                best_ratio = ratio
                                best_match = segment["text"]
                                best_start = segment["start"]
                                best_end = segment["end"]
                        
                        if best_match:
                            new_segments.append({
                                "text": script_line,
                                "start": best_start,
                                "end": best_end
                            })
                
                

        threading.Thread(target=run, daemon=True).start()
    
    def format_timestamp(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

if __name__ == "__main__":
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()