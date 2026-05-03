import subprocess
import threading
import time

class SentientDaemon:
    def __init__(self, check_interval=5):
        print("[System] Booting Sentient Daemon (macOS Environmental Awareness)...")
        self.check_interval = check_interval
        self.active_app = "Unknown"
        self.running = False
        self.context_log = []

    def _get_active_window(self):
        """Pings the macOS Window Server to find the frontmost application."""
        try:
            # AppleScript to get the name of the currently active app
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=2)
            
            app_name = result.stdout.strip()
            return app_name if app_name else "Unknown"
        except Exception:
            return "System Unresponsive"

    def _monitor_loop(self):
        """The heartbeat loop running silently in the background."""
        while self.running:
            current_app = self._get_active_window()
            
            if current_app != self.active_app and current_app != "Unknown":
                # Context switch detected!
                self.active_app = current_app
                timestamp = time.strftime("%I:%M %p")
                
                # We log the context switch so the Brain can read it later
                log_entry = f"[{timestamp}] User shifted focus to: {self.active_app}"
                self.context_log.append(log_entry)
                
                # Keep the log from blowing up memory (retain last 10 actions)
                if len(self.context_log) > 10:
                    self.context_log.pop(0)
                    
            time.sleep(self.check_interval)

    def start(self):
        """Ignites the background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
    def stop(self):
        """Safely kills the daemon."""
        self.running = False

    def get_environmental_context(self) -> str:
        """Called by GraphEngine to inject real-time awareness into the LLM prompt."""
        if not self.active_app or self.active_app == "Unknown":
            return "User environment is currently idle or obscured."
            
        recent_history = "\n".join(self.context_log[-3:]) # Get last 3 app switches
        
        return (
            f"REAL-TIME ENVIRONMENT STATE:\n"
            f"The user is currently active inside: {self.active_app}.\n"
            f"Recent activity trace:\n{recent_history}"
        )

# SDE Unit Test
if __name__ == "__main__":
    daemon = SentientDaemon(check_interval=2)
    daemon.start()
    
    print("\n--- Daemon Sensory Test ---")
    print("Click on a different app (like your browser or Finder) for 3 seconds, then come back here.")
    
    try:
        # Keep the main thread alive for 15 seconds to let the daemon work
        for i in range(15):
            time.sleep(1)
            if i == 7:
                print("\n[Mid-Test Check] JARVIS's current perception:")
                print(daemon.get_environmental_context())
                
    except KeyboardInterrupt:
        pass
        
    daemon.stop()
    print("\n[Final Check] JARVIS's final perception:")
    print(daemon.get_environmental_context())