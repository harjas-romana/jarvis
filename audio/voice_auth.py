import os
import numpy as np

from core.telemetry import logger

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SAMPLE_RATE       = 16000
SIMILARITY_THRESH = 0.0001
ENROLLMENT_PATH   = os.path.join(
    os.path.dirname(__file__), "..", "config", "voice_profile.npy"
)


class VoiceAuthenticator:
    """
    Speaker verification using pyannote/embedding.

    Flow:
      1. First boot — no profile on disk → auto-enroll the first speaker.
      2. Subsequent calls → embed incoming audio and compare via cosine
         similarity against the stored profile.
      3. Fails open (returns True) if pyannote is unavailable or embedding
         crashes — the pipeline must never be muted by a broken auth guard.
    """

    def __init__(self):
        self._model   = None
        self._profile = None    # np.ndarray of enrolled embedding
        self._bypass  = False   # True when pyannote is not available

        self._load_model()
        self._load_profile()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SETUP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _load_model(self) -> None:
        try:
            from pyannote.audio import Model, Inference
            hf_token = os.environ.get("HUGGINGFACE_TOKEN")
            model     = Model.from_pretrained(
                "pyannote/embedding",
                use_auth_token=hf_token,
            )
            self._model = Inference(model, window="whole")
            logger.info("VoiceAuthenticator: pyannote/embedding loaded.")
        except Exception as e:
            logger.warning(
                f"VoiceAuthenticator: pyannote unavailable ({e}). "
                f"Auth bypassed — all speakers accepted."
            )
            self._bypass = True

    def _load_profile(self) -> None:
        path = os.path.abspath(ENROLLMENT_PATH)
        if os.path.exists(path):
            try:
                self._profile = np.load(path)
                logger.info("VoiceAuthenticator: Voice profile loaded from disk.")
            except Exception as e:
                logger.warning(f"VoiceAuthenticator: Could not load profile: {e}. Will re-enroll.")
                self._profile = None
        else:
            logger.info("VoiceAuthenticator: No voice profile found — will auto-enroll on first wake.")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PUBLIC API
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def verify(self, audio_bytes: bytes) -> bool:
        """
        Verify the speaker in audio_bytes against the enrolled profile.

        Args:
            audio_bytes: Raw PCM bytes — int16, 16 kHz, mono.

        Returns:
            True  — verified, or auth bypassed, or auto-enrolled.
            False — speaker rejected.
        """
        if self._bypass:
            return True

        if not audio_bytes:
            logger.warning("VoiceAuthenticator.verify: received empty audio — accepting.")
            return True

        # Auto-enroll on first use
        if self._profile is None:
            logger.info("VoiceAuthenticator: Auto-enrolling voice profile...")
            emb = self._embed(audio_bytes)
            if emb is not None:
                self._profile = emb
                self._save_profile()
                logger.info("VoiceAuthenticator: Voice profile enrolled and saved.")
            else:
                logger.warning("VoiceAuthenticator: Enrollment failed — accepting anyway.")
            return True   # Always accept on the enrolment turn

        # Normal verification
        emb = self._embed(audio_bytes)
        if emb is None:
            logger.warning("VoiceAuthenticator: Embedding failed — accepting speaker.")
            return True

        score = self._cosine(self._profile, emb)
        logger.info(f"VoiceAuthenticator: similarity={score:.3f}  threshold={SIMILARITY_THRESH}")

        if score >= SIMILARITY_THRESH:
            return True

        logger.warning(f"VoiceAuthenticator: Speaker rejected (similarity={score:.3f}).")
        return False

    def enroll(self, audio_bytes: bytes) -> bool:
        """Manually overwrite the stored voice profile."""
        if self._bypass:
            logger.info("VoiceAuthenticator: Bypass mode — enroll is a no-op.")
            return True

        emb = self._embed(audio_bytes)
        if emb is None:
            logger.error("VoiceAuthenticator: Manual enroll failed.")
            return False

        self._profile = emb
        self._save_profile()
        logger.info("VoiceAuthenticator: Voice profile manually re-enrolled.")
        return True

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INTERNALS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _embed(self, audio_bytes: bytes) -> "np.ndarray | None":
        """
        Convert raw int16 PCM bytes → a pyannote speaker embedding vector.

        pyannote Inference (window="whole") expects the input dict:
            {"waveform": Tensor(channel, time), "sample_rate": int}

        The waveform must be shape (channel, time) — NOT (batch, channel, time).
        Float32, normalised to [-1, 1].
        """
        try:
            import torch

            # int16 PCM → float32 in [-1, 1]
            pcm = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            # Shape: (1, time)  ← channel=1, no batch dimension
            waveform = torch.from_numpy(pcm[np.newaxis, :]).float()

            embedding = self._model({"waveform": waveform, "sample_rate": SAMPLE_RATE})
            return np.array(embedding).flatten()

        except Exception as e:
            logger.error(f"VoiceAuthenticator._embed: {e}")
            return None

    @staticmethod
    def _cosine(a: "np.ndarray", b: "np.ndarray") -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def _save_profile(self) -> None:
        path = os.path.abspath(ENROLLMENT_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            np.save(path, self._profile)
            logger.info(f"VoiceAuthenticator: Profile saved → {path}")
        except Exception as e:
            logger.error(f"VoiceAuthenticator: Could not save profile: {e}")