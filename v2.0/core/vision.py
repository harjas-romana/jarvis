import subprocess
import base64
import os

def capture_screen_base64() -> str:
    """
    Natively triggers macOS screencapture, reads the bytes, 
    converts to Base64, and wipes the temporary file.
    """
    temp_path = "/tmp/jarvis_optic_nerve.jpg"
    
    try:
        # -x: Silent mode (no camera shutter sound)
        # -t jpg: Force JPEG format for smaller payload
        # -C: Capture the cursor as well
        subprocess.run(["screencapture", "-x", "-t", "jpg", "-C", temp_path], check=True)
        
        # Read and encode
        with open(temp_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            
        # Security/Storage cleanup: Wipe the image so we don't clog the SSD
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return encoded_string
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"macOS screencapture utility failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to encode screen capture: {str(e)}")