import os
import asyncio
import queue
import wave
import tempfile
import time

try:
    import pyaudio
    from faster_whisper import WhisperModel
    AUDIO_LIBS_AVAILABLE = True
except ImportError:
    AUDIO_LIBS_AVAILABLE = False

from audio.voice_auth import VoiceAuthenticator
from audio.wake_word import WakeWordDetector
from core.telemetry import logger


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RECORD_SECONDS      = 7      # Max dictation window after wake word
AUTH_SECONDS        = 2      # Short window for speaker verification
PRE_SPEECH_DELAY    = 0.35   # Pause after wake to let user begin speaking
RING_BUFFER_MAXSIZE = 1000   # Max frames in ring buffer


class SensoryPipeline:
    """
    Continuous audio pipeline:
      ring-buffer stream → wake-word detection → voice auth → Whisper STT

    All blocking I/O runs inside a dedicated thread via asyncio.to_thread,
    keeping the main event loop free.
    """

    def __init__(self):
        self.wwd          = WakeWordDetector()
        self.pa           = None
        self.whisper      = None
        self.audio_stream = None
        self.ring_buffer  = None

        # Authenticator is optional — if it fails to init, we bypass auth
        try:
            self.authenticator = VoiceAuthenticator()
        except Exception as e:
            logger.warning(f"VoiceAuthenticator failed to init: {e} — auth bypassed.")
            self.authenticator = None

        if not AUDIO_LIBS_AVAILABLE:
            logger.error("pyaudio / faster-whisper missing. Audio engine offline.")
            return

        self.pa          = pyaudio.PyAudio()
        self.ring_buffer = queue.Queue(maxsize=RING_BUFFER_MAXSIZE)

        logger.info("Loading local Whisper model into memory...")
        self.whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
        logger.info("Whisper model ready.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STREAM MANAGEMENT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _open_continuous_stream(self) -> None:
        """Open a non-blocking PyAudio stream that feeds the ring buffer."""
        if not self.wwd.engine:
            logger.error("WakeWordDetector engine not loaded — cannot open stream.")
            return

        def _callback(in_data, frame_count, time_info, status):
            if status:
                logger.warning(f"PyAudio stream status flag: {status}")
            if not self.ring_buffer.full():
                self.ring_buffer.put_nowait(in_data)
            return (in_data, pyaudio.paContinue)

        self.audio_stream = self.pa.open(
            rate=self.wwd.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.wwd.frame_length,
            stream_callback=_callback,
        )
        self.audio_stream.start_stream()
        logger.info("Continuous audio stream opened.")

    def _flush_ring_buffer(self) -> None:
        """Drain all stale frames so the next recording starts clean."""
        with self.ring_buffer.mutex:
            self.ring_buffer.queue.clear()

    def _collect_frames(self, seconds: float) -> list:
        """Collect up to `seconds` worth of frames from the ring buffer."""
        frames_needed = int(self.wwd.sample_rate / self.wwd.frame_length * seconds)
        frames = []
        for _ in range(frames_needed):
            try:
                frames.append(self.ring_buffer.get(timeout=1.0))
            except queue.Empty:
                break
        return frames

    def close(self) -> None:
        """Graceful teardown — call on application exit."""
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except Exception as e:
                logger.warning(f"Error closing audio stream: {e}")
        if self.pa:
            try:
                self.pa.terminate()
            except Exception as e:
                logger.warning(f"Error terminating PyAudio: {e}")
        logger.info("SensoryPipeline closed.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PUBLIC ASYNC ENTRY POINT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async def listen_pipeline(self) -> str | None:
        """
        Async wrapper — runs the blocking loop in a thread pool worker.

        Returns:
          str             — transcribed command
          "[AUTH_FAILED]" — wake detected but voice auth rejected
          None            — silence / noise / empty transcription
        """
        if not AUDIO_LIBS_AVAILABLE:
            logger.error("Audio libraries unavailable. Cannot listen.")
            await asyncio.sleep(5)
            return None

        if not self.wwd.engine:
            logger.error("OpenWakeWord engine not loaded. Ears are offline.")
            await asyncio.sleep(5)
            return None

        return await asyncio.to_thread(self._sync_listen_loop)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BLOCKING LISTEN LOOP  (runs in thread)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _sync_listen_loop(self) -> str | None:
        # Lazily open the stream on first entry
        if not self.audio_stream or not self.audio_stream.is_active():
            self._open_continuous_stream()

        # Clear any audio buffered while we were processing / speaking
        self._flush_ring_buffer()

        # ── PHASE 1: Wake-word detection ──
        while True:
            try:
                pcm = self.ring_buffer.get(timeout=1.0)
            except queue.Empty:
                continue

            if self.wwd.process(pcm):
                logger.info("Wake word detected.")
                break

        # ── PHASE 2: Voice authentication ──
        time.sleep(PRE_SPEECH_DELAY)   # Let the user start speaking
        self._flush_ring_buffer()      # Discard the wake-word audio itself

        auth_frames = self._collect_frames(AUTH_SECONDS)
        auth_audio  = b"".join(auth_frames)

        auth_passed = self._run_auth(auth_audio)
        if not auth_passed:
            return "[AUTH_FAILED]"

        # ── PHASE 3: Full dictation window ──
        # Reuse auth audio as the start; collect the remaining seconds
        logger.info("Listening for command…")
        remaining_frames = self._collect_frames(RECORD_SECONDS - AUTH_SECONDS)
        all_frames       = auth_frames + remaining_frames
        audio_data       = b"".join(all_frames)

        if not audio_data:
            logger.warning("No audio captured after wake word.")
            return None

        # ── PHASE 4: Whisper transcription ──
        return self._transcribe(audio_data)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AUTH HELPER — isolated so errors can't crash the pipeline
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _run_auth(self, audio_bytes: bytes) -> bool:
        """
        Call authenticator.verify() safely.
        If the authenticator is None, misconfigured, or raises any exception,
        we fail open (return True) so the pipeline keeps working.
        """
        if self.authenticator is None:
            return True   # Auth was bypassed at init — let everyone through

        # Gracefully handle missing or renamed methods
        verify_fn = getattr(self.authenticator, "verify", None)
        if verify_fn is None:
            logger.warning(
                "VoiceAuthenticator has no 'verify' method. "
                "Auth bypassed — update voice_auth.py."
            )
            return True

        try:
            return bool(verify_fn(audio_bytes))
        except Exception as e:
            logger.error(f"VoiceAuthenticator.verify raised: {e} — auth bypassed.")
            return True   # Fail open: a broken auth guard must never mute JARVIS

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TRANSCRIPTION HELPER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _transcribe(self, audio_data: bytes) -> str | None:
        """Write audio to a temp WAV, run Whisper, return transcription or None."""
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                with wave.open(tmp_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(self.pa.get_sample_size(pyaudio.paInt16))
                    wf.setframerate(self.wwd.sample_rate)
                    wf.writeframes(audio_data)

            segments, info = self.whisper.transcribe(
                tmp_path,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
                condition_on_previous_text=False,
            )
            transcription = "".join(seg.text for seg in segments).strip()

            # Discard if VAD removed virtually all audio
            if info.duration > 0 and info.duration_after_vad < 0.5:
                logger.info(
                    f"VAD removed {info.duration - info.duration_after_vad:.2f}s "
                    f"of {info.duration:.2f}s — discarding as silence."
                )
                return None

        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return None
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

        if not transcription:
            logger.info("Whisper returned empty transcription.")
            return None

        logger.info(f"Heard: {transcription}")
        return transcription