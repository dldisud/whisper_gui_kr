# Whisper 한글 자막 생성기

WAV/MP4 등에서 한국어 SRT를 만드는 Tk 프로그램입니다. Adobe Premiere에서 오버워치 하이라이트 자막으로 쓰는 것을 전제로 합니다.

## 1. 프로그램 설치하기

### 1-1. Python 설치
1. [Python 공식 홈페이지](https://www.python.org/downloads/)에 접속합니다.
2. "Download Python" 버튼을 클릭합니다. (파이썬 3.9 ~ 3.11 추천)
3. 다운로드된 설치 파일을 실행합니다.
4. 설치 시 **"Add python.exe to PATH"** 옵션을 반드시 체크해주세요!
5. "Install Now"를 클릭하여 설치를 완료합니다.

### 1-2. ffmpeg 설치
Whisper는 WAV 파일을 읽을 때도 ffmpeg가 필요합니다.

- 명령 프롬프트/PowerShell에서: `winget install Gyan.FFmpeg`
- 또는 [ffmpeg 다운로드](https://ffmpeg.org/download.html) 후 설치 폴더의 `bin`을 PATH에 추가합니다.
- 설치 후 **새** PowerShell을 열고 `ffmpeg -version`이 출력되는지 확인합니다.

### 1-3. 파이썬 패키지 설치
6. 이 프로그램 폴더에서 Shift + 우클릭을 합니다.
7. "여기서 PowerShell 창 열기" 또는 "터미널에서 열기"를 선택합니다.
8. 아래 명령어를 복사하여 붙여넣고 Enter를 누릅니다:

```
python -m pip install -r requirements.txt
```

(`tkinter`는 pip 패키지가 아닙니다. Python 설치에 포함되어 있습니다.)

## 2. 프로그램 실행하기
9. `whisper_gui_kr.py` 파일을 더블클릭합니다.
   - 또는 PowerShell에서: `python whisper_gui_kr.py`
10. 프로그램이 실행되면 다음 순서대로 진행합니다:
   - "오디오 파일" 찾아보기로 WAV, MP3, MP4 등을 선택합니다.
   - (선택사항) "대본 파일" 찾아보기로 텍스트(.txt) 파일을 선택합니다.
   - "출력 위치"를 선택합니다. 비워두면 오디오와 같은 폴더에 `.srt`가 생깁니다.
   - "모델 크기"를 선택합니다. (처음 사용 시 모델을 다운로드받습니다)
   - "대본 활용" 방식을 선택합니다:
     * 무조건: 위스퍼 타임코드만 쓰고 대본 문구를 그대로 사용
     * 강: 대본 내용을 우선적으로 반영
     * 약: Whisper 인식 결과를 우선적으로 반영

## 3. 모델 크기 설명
- small: 빠르지만 정확도가 낮음
- medium: 적당한 속도와 정확도 (추천)
- large: 가장 정확하지만 느림

## 4. 주의사항
- 오디오는 WAV뿐 아니라 MP4/MP3/M4A 등도 가능합니다. 둘 다 **ffmpeg**가 필요합니다.
- 대본 파일은 UTF-8 또는 한글 Windows(메모장 ANSI/CP949) 텍스트(.txt)면 됩니다.
- 저장되는 SRT는 **UTF-8 BOM**입니다. Premiere에서 한글이 깨지면 이 파일을 그대로 쓰세요.
- 첫 실행 시 선택한 모델을 다운로드받으므로 시간이 걸릴 수 있습니다.
- 자막 생성 중에는 프로그램을 종료하지 마세요.

## 5. 문제 해결
### 프로그램이 실행되지 않는 경우:
11. Python이 제대로 설치되었는지 확인
   - 명령 프롬프트(cmd)에서 `python --version` 입력
12. 필요한 패키지가 설치되었는지 확인
   - `python -m pip install -r requirements.txt` 를 다시 실행
13. `ffmpeg -version`이 동작하는지 확인

### 오류 메시지가 표시되는 경우:
- 오류 메시지를 캡처하여 개발자에게 문의해주세요.

## 6. 작가용 가짜 SNS 사용
`fake_sns.py` 파일을 실행하면 게시글과 댓글을 간단히 작성할 수 있는 창이 뜹니다. 게시글을 선택한 후 댓글을 입력하면 목록에 추가됩니다.

```
python fake_sns.py
```
