import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import whisper_gui_kr as gui


class FormatTimestampTests(unittest.TestCase):
    def test_rounds_fractional_milliseconds_instead_of_truncating(self):
        # Old code: int((2.296 - 2) * 1000) == 295 because 0.296 * 1000 is 295.999...
        self.assertEqual(gui.format_timestamp(2.296), "00:00:02,296")

    def test_rounds_near_second_boundary(self):
        self.assertEqual(gui.format_timestamp(1.9996), "00:00:02,000")
        self.assertEqual(gui.format_timestamp(59.9996), "00:01:00,000")

    def test_hours_and_zero(self):
        self.assertEqual(gui.format_timestamp(0), "00:00:00,000")
        self.assertEqual(gui.format_timestamp(3661.5), "01:01:01,500")

    def test_negative_clamped(self):
        self.assertEqual(gui.format_timestamp(-1.2), "00:00:00,000")


class SrtWriteTests(unittest.TestCase):
    def test_writes_utf8_bom_and_korean_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.srt"
            gui.write_srt(path, [{"start": 0, "end": 1.5, "text": " 안녕하세요 "}])
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(b"\xef\xbb\xbf"), raw[:8])
            text = raw.decode("utf-8-sig")
            self.assertIn("1\r\n", raw.decode("utf-8-sig"))
            self.assertIn("00:00:00,000 --> 00:00:01,500", text.replace("\r\n", "\n"))
            self.assertIn("안녕하세요", text)

    def test_uses_crlf_for_premiere_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.srt"
            gui.write_srt(path, [{"start": 0, "end": 1, "text": "안녕"}])
            raw = path.read_bytes()
            self.assertIn(b"\r\n", raw)
            self.assertNotIn(b"\n\n", raw.replace(b"\r\n", b""))


class ScriptReadTests(unittest.TestCase):
    def test_reads_utf8_and_cp949(self):
        with tempfile.TemporaryDirectory() as tmp:
            utf8 = Path(tmp) / "utf8.txt"
            utf8.write_bytes("대본 한 줄".encode("utf-8"))
            self.assertEqual(gui.read_text_auto(utf8), "대본 한 줄")

            bom = Path(tmp) / "bom.txt"
            bom.write_bytes("대본".encode("utf-8-sig"))
            self.assertEqual(gui.read_text_auto(bom), "대본")

            cp949 = Path(tmp) / "cp949.txt"
            cp949.write_bytes("대본 한 줄".encode("cp949"))
            self.assertEqual(gui.read_text_auto(cp949), "대본 한 줄")


class AlignSegmentsTests(unittest.TestCase):
    def test_unconditional_skips_blank_script_lines(self):
        segments = [
            {"text": "첫번째", "start": 0, "end": 1},
            {"text": "두번째", "start": 1, "end": 2},
            {"text": "세번째", "start": 2, "end": 3},
        ]
        script = "첫번째\n\n세번째\n"
        aligned = gui.align_segments(segments, script, "무조건")
        self.assertEqual([item["text"] for item in aligned], ["첫번째", "세번째", "세번째"])

    def test_unconditional_keeps_extra_script_on_last_cue(self):
        segments = [{"text": "안녕", "start": 0, "end": 1}]
        aligned = gui.align_segments(segments, "안녕\n하세요", "무조건")
        self.assertEqual(aligned[0]["text"], "안녕 하세요")

    def test_strong_weak_do_not_reuse_the_same_timestamp(self):
        segments = [
            {"text": "안녕하세요 반갑습니다", "start": 0, "end": 2},
            {"text": "다른말", "start": 2, "end": 3},
        ]
        script = "안녕\n하세요\n반갑습니다"
        aligned = gui.align_segments(segments, script, "강")
        pairs = [(item["start"], item["end"]) for item in aligned]
        self.assertEqual(len(pairs), len(set(pairs)))

    def test_weak_mode_keeps_whisper_when_similarity_is_medium(self):
        segments = [{"text": "이것은 인식", "start": 0, "end": 1}]
        # "이것은 대본" vs "이것은 인식" ≈ 0.667: 강(0.4) uses script, 약(0.7) keeps Whisper
        aligned_strong = gui.align_segments(segments, "이것은 대본", "강")
        aligned_weak = gui.align_segments(segments, "이것은 대본", "약")
        self.assertEqual(aligned_strong[0]["text"], "이것은 대본")
        self.assertEqual(aligned_weak[0]["text"], "이것은 인식")


class TranscribeFlowTests(unittest.TestCase):
    def test_writes_srt_after_alignment_not_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "clip.wav"
            audio.write_bytes(b"RIFF")
            script = Path(tmp) / "script.txt"
            script.write_text("대본 한 줄\n", encoding="utf-8")

            def fake_transcribe(path, options):
                self.assertEqual(path, str(audio))
                self.assertEqual(options["language"], "ko")
                self.assertIn("initial_prompt", options)
                return {
                    "text": "위스퍼 인식",
                    "segments": [{"text": "위스퍼 인식", "start": 1.0, "end": 2.296}],
                }

            srt_path = gui.transcribe_audio_to_srt(
                audio,
                script_path=script,
                output_dir=tmp,
                script_mode="무조건",
                transcribe_fn=fake_transcribe,
                require_ffmpeg=False,
            )
            body = srt_path.read_text(encoding="utf-8-sig")
            self.assertIn("대본 한 줄", body)
            self.assertNotIn("위스퍼 인식", body)
            self.assertIn("00:00:02,296", body)

    def test_default_srt_path_is_beside_audio(self):
        audio = Path("/videos/highlight.mp4")
        self.assertEqual(gui.resolve_srt_path(audio, ""), Path("/videos/highlight.srt"))
        self.assertEqual(
            gui.resolve_srt_path(audio, "/out"),
            Path("/out") / "highlight.srt",
        )

    def test_missing_audio_raises(self):
        with self.assertRaises(FileNotFoundError):
            gui.transcribe_audio_to_srt(
                "/no/such/file.wav",
                transcribe_fn=lambda path, options: {"segments": []},
                require_ffmpeg=False,
            )

    def test_missing_ffmpeg_raises_korean_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "clip.wav"
            audio.write_bytes(b"RIFF")
            with patch.object(gui, "ffmpeg_available", return_value=False):
                with self.assertRaises(RuntimeError) as ctx:
                    gui.transcribe_audio_to_srt(
                        audio,
                        transcribe_fn=lambda path, options: {"segments": []},
                        require_ffmpeg=True,
                    )
        self.assertIn("ffmpeg", str(ctx.exception))


class RequirementsTests(unittest.TestCase):
    def test_requirements_does_not_list_tkinter(self):
        text = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertNotIn("tkinter", text)
        self.assertIn("openai-whisper", text)

    def test_readme_names_real_gui_file_and_pip_command(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("whisper_gui_kr.py", text)
        self.assertNotIn("whisper_gui.py", text)
        self.assertIn("pip install -r requirements.txt", text)


if __name__ == "__main__":
    unittest.main()
