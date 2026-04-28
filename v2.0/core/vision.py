import subprocess
import base64
import os

def capture_screen_base64() -> str:
    """Takes a silent macOS screenshot and returns it as a base64 string."""
    filepath = "/tmp/jarvis_optic_nerve.jpg"
    
    # -x: Mute the camera shutter sound
    # -C: Capture the cursor so JARVIS knows exactly what you are pointing at
    # -t: Format as JPG to save payload size
    subprocess.run(["screencapture", "-x", "-C", "-t", "jpg", filepath], check=True)
    
    with open(filepath, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    # Clean up the temporary file immediately
    if os.path.exists(filepath):
        os.remove(filepath)
        
    return encoded_string