import os
from langchain_groq import ChatGroq
from core.telemetry import logger


class JarvisEngine:
    """
    Thin wrapper around ChatGroq.
    JarvisGraph imports this class so the LLM configuration
    lives in one place — changing the model or parameters here
    applies everywhere automatically.
    """

    # Default model — 70b is significantly better at tool routing
    # than 8b-instant. Use the env var to override for local testing.
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            logger.critical("GROQ_API_KEY missing from .env — engine cannot ignite.")
            raise ValueError("GROQ_API_KEY missing.")

        model = os.environ.get("GROQ_MODEL", self.DEFAULT_MODEL)

        self.llm = ChatGroq(
            api_key=api_key,
            model=model,
            temperature=0.1,
            max_retries=1,       # Fail fast — main.py handles the retry UX
            request_timeout=15,  # Hard cap per call; prevents 22s hangs
        )

        logger.info(f"ChatGroq engine initialized — model: {model}")

    def get_model(self) -> ChatGroq:
        """Returns the raw LangChain LLM for JarvisGraph to bind tools to."""
        return self.llm