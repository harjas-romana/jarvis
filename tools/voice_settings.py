from audio.tts import get_tts_manager

TOOL_SCHEMA = {
    "name": "toggle_voice_engine",
    "description": "Switches the TTS engine between local macOS and Premium Cloud Voice.",
    "parameters": {
        "type": "object",
        "properties": {
            "activate_premium": {
                "type": "boolean",
                "description": "Set to true to activate premium voice, false for local OS fallback."
            }
        },
        "required": ["activate_premium"]
    }
}

def execute(activate_premium: bool) -> str:
    """Executes the TTS toggle via the Singleton TTSManager."""
    mgr = get_tts_manager()
    result = mgr.toggle_premium_voice(activate_premium)
    return result