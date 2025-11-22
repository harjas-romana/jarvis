class AffectiveEngine:
    def __init__(self):
        # Stress keywords indicating urgency, fatigue, or frustration.
        self.stress_markers = [
            "tired", "exhausted", "hurt", "pain", "frustrated", 
            "stop", "hurry", "quick", "stress", "urgently", 
            "hospital", "fatigue", "foot pain"
        ]

    def analyze(self, transcript: str) -> dict:
        """
        Analyzes the STT transcript for markers indicating stress or fatigue.
        Returns a dictionary with the stress boolean flag and raw score.
        """
        transcript_lower = transcript.lower()
        score = 0
        
        for marker in self.stress_markers:
            if marker in transcript_lower:
                score += 1
                
        is_stressed = score > 0
        
        return {
            "stressed": is_stressed,
            "score": score
        }
