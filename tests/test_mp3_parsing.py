"""
Tests for mp3_parsing.py, run against real ffmpeg/ffprobe with small
synthetic media generated on the fly (ffmpeg's "lavfi" virtual input - no
fixture files committed to the repo, nothing to download). Same technique
this project's old integration suite used for extract_audio()/
probe_media_info() before this project became a single-purpose mp3
conversion tool.

Needs real ffmpeg/ffprobe on PATH; the whole module skips cleanly (not a
failure) if they are missing - e.g. in a sandboxed review environment with
no ffmpeg installed. Run for real on a machine with ffmpeg to verify:

    python -m unittest tests.test_mp3_parsing -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# The actual package lives under src/mp3_parsing/ (config.py,
# ffmpeg_tools.py, progress.py, converter.py, gui.py, cli.py) - point
# sys.path at src/ so "import mp3_parsing" resolves to that package the
# same way it resolved to the single mp3_parsing.py file before the
# project was split into modules.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import mp3_parsing

FFMPEG_BIN = mp3_parsing.FFMPEG_BIN
FFPROBE_BIN = mp3_parsing.FFPROBE_BIN

try:
    mp3_parsing.check_ffmpeg_available()
    _FFMPEG_AVAILABLE = True
except RuntimeError:
    _FFMPEG_AVAILABLE = False


def _make_test_video(path: str, seconds: float, with_audio: bool = True) -> None:
    """Tiny synthetic .mp4 via ffmpeg's lavfi virtual input: a color video
    track plus (optionally) a sine-wave audio track."""
    cmd = [FFMPEG_BIN, "-y", "-f", "lavfi", "-i", f"color=c=black:s=64x64:d={seconds}"]
    if with_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
    cmd += ["-c:v", "libx264", "-t", str(seconds)]
    cmd += ["-c:a", "aac"] if with_audio else ["-an"]
    cmd += [path]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate test video: {result.stderr[-2000:]}")


def _make_test_wav(path: str, seconds: float) -> None:
    """Tiny synthetic .wav (sine tone) via ffmpeg's lavfi virtual input -
    covers the second input format mp3_parsing.py is meant to accept."""
    cmd = [
        FFMPEG_BIN, "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate test wav: {result.stderr[-2000:]}")


def _probe(path: str) -> dict:
    result = subprocess.run(
        [FFPROBE_BIN, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout)


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg/ffprobe not found on PATH")
class TestHasAudioTrack(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mp3_parsing_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_true_for_a_file_with_audio(self):
        path = os.path.join(self.tmp_dir, "clip.mp4")
        _make_test_video(path, seconds=2, with_audio=True)
        self.assertTrue(mp3_parsing.has_audio_track(path))

    def test_false_for_a_file_with_no_audio(self):
        path = os.path.join(self.tmp_dir, "silent.mp4")
        _make_test_video(path, seconds=2, with_audio=False)
        self.assertFalse(mp3_parsing.has_audio_track(path))


@unittest.skipUnless(_FFMPEG_AVAILABLE, "ffmpeg/ffprobe not found on PATH")
class TestConvertToMp3(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="mp3_parsing_test_")
        self.out_dir = os.path.join(self.tmp_dir, "out")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_converts_an_mp4_video_to_mp3(self):
        video_path = os.path.join(self.tmp_dir, "clip.mp4")
        _make_test_video(video_path, seconds=2, with_audio=True)

        output_path = mp3_parsing.convert_to_mp3(video_path, output_dir=self.out_dir)

        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(os.path.basename(output_path), "clip.mp3")
        info = _probe(output_path)
        audio_streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
        self.assertEqual(len(audio_streams), 1)
        self.assertEqual(audio_streams[0]["codec_name"], "mp3")
        self.assertAlmostEqual(float(info["format"]["duration"]), 2, delta=0.5)

    def test_converts_a_wav_file_to_mp3(self):
        # The other input format this tool is explicitly meant to accept,
        # not just .mp4.
        wav_path = os.path.join(self.tmp_dir, "tone.wav")
        _make_test_wav(wav_path, seconds=2)

        output_path = mp3_parsing.convert_to_mp3(wav_path, output_dir=self.out_dir)

        self.assertTrue(os.path.exists(output_path))
        self.assertEqual(os.path.basename(output_path), "tone.mp3")
        info = _probe(output_path)
        self.assertEqual(info["streams"][0]["codec_name"], "mp3")

    def test_preserves_mono_channel_count_rather_than_forcing_stereo(self):
        # sine= is mono by default - the point of not passing -ac is that
        # mp3_parsing.py must not silently upmix it to stereo.
        wav_path = os.path.join(self.tmp_dir, "mono.wav")
        _make_test_wav(wav_path, seconds=1)

        output_path = mp3_parsing.convert_to_mp3(wav_path, output_dir=self.out_dir)

        info = _probe(output_path)
        self.assertEqual(info["streams"][0]["channels"], 1)

    def test_raises_for_nonexistent_file(self):
        with self.assertRaises(RuntimeError):
            mp3_parsing.convert_to_mp3(os.path.join(self.tmp_dir, "does_not_exist.mp4"), output_dir=self.out_dir)

    def test_raises_when_no_audio_track(self):
        path = os.path.join(self.tmp_dir, "silent.mp4")
        _make_test_video(path, seconds=2, with_audio=False)
        with self.assertRaises(RuntimeError):
            mp3_parsing.convert_to_mp3(path, output_dir=self.out_dir)

    def test_creates_the_output_directory_if_missing(self):
        video_path = os.path.join(self.tmp_dir, "clip2.mp4")
        _make_test_video(video_path, seconds=1, with_audio=True)
        nested_out = os.path.join(self.tmp_dir, "does", "not", "exist", "yet")

        output_path = mp3_parsing.convert_to_mp3(video_path, output_dir=nested_out)

        self.assertTrue(os.path.exists(output_path))

    def test_overwrites_an_existing_output_file(self):
        video_path = os.path.join(self.tmp_dir, "clip3.mp4")
        _make_test_video(video_path, seconds=1, with_audio=True)

        first = mp3_parsing.convert_to_mp3(video_path, output_dir=self.out_dir)
        first_mtime = os.path.getmtime(first)
        second = mp3_parsing.convert_to_mp3(video_path, output_dir=self.out_dir)

        self.assertEqual(first, second)
        self.assertTrue(os.path.exists(second))
        # Not a strict guarantee on some filesystems (mtime resolution),
        # but the real assertion is the call above did not raise/refuse to
        # overwrite - ffmpeg's "-y" flag is what this locks in.
        self.assertGreaterEqual(os.path.getmtime(second), first_mtime)


if __name__ == "__main__":
    unittest.main()
