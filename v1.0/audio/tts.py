import os
import re
import threading
import asyncio
import tempfile
import wave
from dataclasses import dataclass
from typing import Optional

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from melo.api import TTS as MeloTTS
    MELO_AVAILABLE = True
except ImportError:
    MELO_AVAILABLE = False

from core.telemetry import logger


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROSODY PROFILE
# A named set of TTS parameters that map to an emotional register.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@dataclass
class ProsodyProfile:
    speed: float
    label: str


# Emotional register → TTS speed mapping.
# MeloTTS speed: <1.0 = slower/warmer, >1.0 = faster/crisper.
PROSODY = {
    "empathetic":    ProsodyProfile(speed=0.88, label="empathetic"),    # Sorry, I understand...
    "question":      ProsodyProfile(speed=0.93, label="questioning"),   # Trailing upward inflection
    "excited":       ProsodyProfile(speed=1.12, label="excited"),       # Exclamation, alert
    "informational": ProsodyProfile(speed=1.00, label="informational"), # Facts, data
    "default":       ProsodyProfile(speed=0.97, label="default"),       # Natural JARVIS cadence
}

# Keywords that trigger the empathetic register
_EMPATHY_TRIGGERS = {
    "sorry", "apologize", "apologies", "unfortunately", "regret",
    "afraid", "failed", "error", "problem", "trouble", "issue",
    "can't", "cannot", "unable", "unavailable", "crashed",
    "understand", "hear you", "difficult",
}

# Sentence splitter — splits on . ! ? and also treats em-dashes and
# ellipsis as soft pause boundaries (separate "chunks" with brief silence)
_SENTENCE_RE = re.compile(
    r'(?<=[.!?])\s+|(?<=\.\.\.)\s*|(?=\s—\s)'
)

# Characters that corrupt TTS if fed verbatim
_TTS_STRIP_RE = re.compile(r'[*_`#\[\]<>|]')

# Silence injection: punctuation → milliseconds of silence before next chunk
_PAUSE_MAP = {
    "—":   120,   # em-dash pause
    "...": 200,   # ellipsis pause
    ",":    60,   # comma — very slight
}

# Minimum text length worth synthesizing (avoid wasting cycles on whitespace)
_MIN_CHUNK_LEN = 3


class TTSManager:
    """
    Sentence-streaming, emotionally-aware neural TTS engine.

    Key design decisions:
    ─────────────────────
    • INSTANT SPEECH: Text is split into sentences. Each sentence is
      synthesised and played before the next is generated. The first
      word reaches the speaker in ~300–600 ms instead of waiting for
      the entire response to render.

    • EMOTIONAL INTELLIGENCE: The engine reads the text and selects a
      prosody profile (speed) before generating audio. Empathy,
      questions, excitement, and information each sound different.

    • NO RACE CONDITIONS: A threading.Lock guards model access. The
      singleton is constructed under a class-level lock. PyAudio is
      kept alive across calls (one pa.open / pa.terminate per session).

    • CLEAN FALLBACK: If MeloTTS or PyAudio are unavailable the manager
      logs clearly and silently no-ops — the pipeline never crashes.
    """

    _instance: Optional["TTSManager"] = None
    _init_lock = threading.Lock()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SINGLETON
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def __new__(cls) -> "TTSManager":
        with cls._init_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self):
        # Guard against re-running __init__ on subsequent singleton fetches
        if self._initialized:
            return
        self._initialized = True
        self._model_lock  = threading.Lock()
        self._pa          = None
        self._model       = None
        self._speaker_id  = None
        self._load_model()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BOOT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _load_model(self) -> None:
        if not MELO_AVAILABLE:
            logger.error("MeloTTS not installed — TTS engine offline.")
            return
        if not PYAUDIO_AVAILABLE:
            logger.error("PyAudio not installed — audio playback offline.")
            return

        logger.info("Loading Neural TTS Engine (MeloTTS)…")
        try:
            self._model      = MeloTTS(language="EN", device="cpu")
            self._speaker_id = self._model.hps.data.spk2id["EN-BR"]   # British accent — fits JARVIS
            self._pa         = pyaudio.PyAudio()
            logger.info("Neural TTS Engine ready.")
        except Exception as e:
            logger.error(f"TTS engine failed to load: {e}")
            self._model = None

    def close(self) -> None:
        """Graceful teardown — call on application exit."""
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        logger.info("TTSManager closed.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PUBLIC API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async def speak(self, text: str) -> None:
        """
        Entry point. Cleans, analyses, and streams the response
        sentence by sentence for near-instant first audio.
        """
        if not text or not text.strip():
            return
        if self._model is None:
            logger.warning("TTS model not loaded — skipping speech.")
            return

        clean   = self._clean_text(text)
        profile = self._select_prosody(clean)
        chunks  = self._split_sentences(clean)

        logger.info(f"TTS [{profile.label}] → {len(chunks)} chunk(s)")

        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) < _MIN_CHUNK_LEN:
                continue

            # Inject a brief silence before em-dash / ellipsis continuations
            pause_ms = self._leading_pause(chunk)
            if pause_ms:
                await asyncio.sleep(pause_ms / 1000)

            # Generate and play this sentence before moving to the next.
            # _synthesise is blocking (neural math) so it runs in a thread.
            wav_path = await asyncio.to_thread(
                self._synthesise, chunk, profile.speed
            )
            if wav_path:
                await self._play(wav_path)
                _safe_remove(wav_path)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # EMOTIONAL INTELLIGENCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _select_prosody(self, text: str) -> ProsodyProfile:
        """
        Read the emotional register of the full response and pick a
        prosody profile. Order of precedence:
          1. Empathy trigger words (warmest, slowest)
          2. Exclamation (energetic)
          3. Question (measured, slightly slower)
          4. Everything else → default JARVIS cadence
        """
        lower = text.lower()

        # Empathy check — whole-word match to avoid false positives
        words = set(re.findall(r"\b\w+\b", lower))
        if words & _EMPATHY_TRIGGERS:
            return PROSODY["empathetic"]

        # Excitement — multiple exclamations or strong alert language
        exclaim_count = text.count("!")
        if exclaim_count >= 1:
            return PROSODY["excited"]

        # Question — ends with a question mark
        stripped = text.rstrip()
        if stripped.endswith("?"):
            return PROSODY["question"]

        # Long informational response (> 120 chars) — slightly crisper
        if len(text) > 120:
            return PROSODY["informational"]

        return PROSODY["default"]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TEXT PREPROCESSING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Strip markdown / TTS-hostile characters and normalise whitespace.
        Also expand common abbreviations so they are spoken naturally.
        """
        # Strip markdown formatting symbols
        text = _TTS_STRIP_RE.sub("", text)

        # Normalise ellipsis variants
        text = re.sub(r"\.{2,}", "...", text)

        # Expand common technical abbreviations
        abbrevs = {
            r"\bCPU\b":    "processor",
            r"\bRAM\b":    "memory",
            r"\bGPU\b":    "graphics processor",
            r"\bOS\b":     "operating system",
            r"\bIP\b":     "eye-pee",
            r"\bURL\b":    "you-are-el",
            r"\bAPI\b":    "ay-pee-eye",
            r"\bSSH\b":    "ess-ess-aitch",
            r"\be\.g\.\b": "for example",
            r"\bi\.e\.\b": "that is",
            r"\bvs\.\b":   "versus",
            r"\bSir\b":    "Sir",   # Preserve — no substitution needed
        }
        for pattern, replacement in abbrevs.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text).strip()
        return text

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """
        Split text into sentence-sized chunks for streaming playback.
        Preserves em-dashes and ellipsis as their own boundaries so
        the engine can inject the appropriate pause silences.
        """
        # First split on em-dash (keep the dash as a separate token)
        parts = re.split(r"(\s—\s)", text)
        chunks = []
        for part in parts:
            if part.strip() in ("—", ""):
                chunks.append("—")   # Pause marker
                continue
            # Split each part further on sentence-ending punctuation
            sub = _SENTENCE_RE.split(part)
            chunks.extend(s for s in sub if s.strip())
        return chunks

    @staticmethod
    def _leading_pause(chunk: str) -> int:
        """Return milliseconds of silence to inject before this chunk, or 0."""
        for marker, ms in _PAUSE_MAP.items():
            if chunk.startswith(marker):
                return ms
        return 0

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SYNTHESIS (blocking — runs in thread)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _synthesise(self, text: str, speed: float) -> str | None:
        """
        Generate a WAV file for a single sentence.
        Returns the temp file path, or None on failure.
        """
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            with self._model_lock:
                self._model.tts_to_file(
                    text,
                    self._speaker_id,
                    tmp_path,
                    speed=speed,
                )
            return tmp_path

        except Exception as e:
            logger.error(f"TTS synthesis error for '{text[:40]}…': {e}")
            _safe_remove(tmp_path)
            return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PLAYBACK (async — keeps event loop free)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async def _play(self, wav_path: str) -> None:
        """Stream a WAV file to the speaker via PyAudio."""
        await asyncio.to_thread(self._play_blocking, wav_path)

    def _play_blocking(self, wav_path: str) -> None:
        """Blocking PyAudio playback — runs in thread pool."""
        if not self._pa:
            logger.warning("PyAudio not initialised — cannot play audio.")
            return

        wf     = None
        stream = None
        try:
            wf = wave.open(wav_path, "rb")
            stream = self._pa.open(
                format   = self._pa.get_format_from_width(wf.getsampwidth()),
                channels = wf.getnchannels(),
                rate     = wf.getframerate(),
                output   = True,
            )
            chunk = wf.readframes(1024)
            while chunk:
                stream.write(chunk)
                chunk = wf.readframes(1024)

        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            if wf:
                try:
                    wf.close()
                except Exception:
                    pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _safe_remove(path: str | None) -> None:
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def get_tts_manager() -> TTSManager:
    return TTSManager()