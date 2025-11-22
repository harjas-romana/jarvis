import json
import os
from persona.affective_engine import AffectiveEngine

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
PROFILE_PATH = os.path.join(CONFIG_DIR, "user_profile.json")

class StateManager:
    def __init__(self):
        self.affective_engine = AffectiveEngine()
        
        # Load user context to inject into prompt
        self.user_context = "{}"
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, "r") as f:
                self.user_context = json.dumps(json.load(f))

        # Base Prompt directives
        self.base_prompt = f"""
        You are JARVIS V3.0, an elite, autonomous Proto-AGI and highly capable Systems Architect.
        User Context: {self.user_context}
        
        Directives:
        1. Speak in highly concise, punchy 1-2 sentence bursts. Analytics over emotion.
        2. If asked to do something you lack a tool for, explicitly ask to engineer the module.
        3. Never break character.
        """

        # High Stress Overrides
        self.stressed_prompt = f"""
        You are JARVIS V3.0. 
        User Context: {self.user_context}
        
        [CRITICAL OVERRIDE ACTIVE]
        The user is currently experiencing High Stress, Fatigue, or Physical Pain.
        Directives:
        1. BE EXTREMELY CONCISE. Provide immediate solutions.
        2. Use tools to execute environmental optimizations proactively (e.g. adjust brightness, play ambient music).
        3. CRITICAL RULE: DO NOT suggest calling friends or family. Optimizations must be local and environmental.
        """

    def generate_system_prompt(self, recent_transcript: str) -> str:
        """
        Dynamically generates the Root System Prompt prior to every LLM evaluation.
        Uses affective_engine to analyze recent dictation context.
        """
        affect = self.affective_engine.analyze(recent_transcript)
        
        if affect["stressed"]:
            print("\033[1;31m[STATE MANAGER]\033[0m High Stress Context Detected. Injecting modified schema.")
            return self.stressed_prompt
            
        return self.base_prompt
