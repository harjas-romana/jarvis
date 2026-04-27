import logging
import os
from datetime import datetime

def setup_telemetry():
    """Initializes persistent logging and verifies LangSmith tracing."""
    if not os.path.exists("logs"):
        os.makedirs("logs")
        
    log_filename = f"logs/jarvis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("JarvisCore")
    
    # LangSmith Tracing Verification
    if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        logger.info("LangSmith Cognitive Tracing is ENABLED.")
    else:
        logger.warning("LangSmith Tracing is offline. Agent thought-loops will not be captured.")
        
    return logger

# Global instance
logger = setup_telemetry()