import numpy as np
import openwakeword
from openwakeword.model import Model

class WakeWordDetector:
    def __init__(self):
        print("\033[1;36m[SYSTEM] Initializing OpenWakeWord Engine (ONNX Mode)...\033[0m")
        try:
            print("\033[1;33m[SYSTEM] Verifying/Downloading default WakeWord models...\033[0m")
            openwakeword.utils.download_models()
            
            # [FIXED]: Switched back to the native 'hey_jarvis' model
            self.engine = Model(
                wakeword_models=["hey_jarvis"], 
                inference_framework="onnx"
            )
            self.sample_rate = 16000
            self.frame_length = 1280 
            print("\033[1;32m[SYSTEM] OpenWakeWord Engine loaded successfully.\033[0m")
        except Exception as e:
            print(f"\033[1;31m[SYSTEM] Failed to load OpenWakeWord Engine: {e}\033[0m")
            self.engine = None
            self.sample_rate = 16000
            self.frame_length = 1280

    def process(self, pcm_data: bytes) -> bool:
        """Takes raw audio bytes, converts to numpy array, and calculates wake probability."""
        if not self.engine:
            return False
        
        audio_array = np.frombuffer(pcm_data, dtype=np.int16)
        prediction = self.engine.predict(audio_array)
        
        # Check the prediction dictionary for the "hey_jarvis" trigger
        for model_name, score in prediction.items():
            if "jarvis" in model_name.lower() and score > 0.5:
                return True
                
        return False