import os
import pyaudio
from cartesia import Cartesia

class CartesiaTTS:
    def __init__(self):
        self.api_key = os.getenv("CARTESIA_API_KEY")
        if not self.api_key:
            print("[Audio Subsystem Error] CARTESIA_API_KEY is missing from .env")
            
        # self.client = Cartesia(api_key=self.api_key)
        
        # self.voice_id = "f786b574-daa5-4673-aa0c-cbe3e8534c02" 
        
        self.p = pyaudio.PyAudio()

    def speak(self, text: str):
        if not text or not self.api_key:
            return
            
        try:
            stream = self.p.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                output=True
            )
            
            # [THE SDK FIX]: Cartesia yields a ChunkEvent object now, not a dictionary.
            # [THE SDK FIX]: Targeting the Sonic-3 model for SSML support
            for event in self.client.tts.sse(
                model_id="sonic-3", # <-- UPGRADED FROM 'sonic'
                transcript=text,
                voice={
                    "mode": "id",
                    "id": self.voice_id
                },
                output_format={
                    "container": "raw",
                    "encoding": "pcm_f32le",
                    "sample_rate": 44100,
                },
            ):
                # Access the attribute via dot notation
                if event.audio:
                    stream.write(event.audio)
                
            stream.stop_stream()
            stream.close()
            
        except Exception as e:
            print(f"\n[Audio Subsystem Error] Failed to generate/play speech: {str(e)}")

    def __del__(self):
        try:
            self.p.terminate()
        except:
            pass