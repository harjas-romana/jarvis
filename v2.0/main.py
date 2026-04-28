import sys
import re
from datetime import datetime
import threading
terminal_lock = threading.Lock()
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from ingestor_daemon import start_daemon
from core.heartbeat import ProactiveHeartbeat
from core.worker import system_2

load_dotenv()

try:
    from core.engine import CognitiveEngine
    from audio.tts import CartesiaTTS
except Exception as e:
    print(f"FATAL: Failed to load system modules. {e}")
    sys.exit(1)

console = Console()

def clean_for_terminal(raw_text):
    """Strips Cartesia SSML tags and function tags for a pristine terminal display."""
    clean = re.sub(r'<[^>]+>', '', raw_text) # Removes <emotion...>, <function...>, etc.
    clean = clean.replace('[laughter]', '(*laughs*)')
    return clean.strip()

def main():
    console.clear()
    console.print(Panel(
        "[bold cyan]JARVIS v2.0 - Phase 1 (Conscious Core)[/bold cyan]\n"
        "[green]Brain:[/green] Groq Llama-3.3-70B\n"
        "[green]Voice:[/green] Cartesia AI Neural\n"
        "[yellow]Status:[/yellow] Online & Stable", 
        title="System Boot"
    ))
    
    try:
        brain = CognitiveEngine()
        voice = CartesiaTTS()
        start_daemon()
        system_2.start()

        def notification_listener():
            while True:
                # 1. Receive the silent ping from System 2 or the RAG Daemon
                internal_msg = system_2.notification_queue.get() 
                
                # 2. Route it into System 1's brain so it forms a memory!
                directive = f"[INTERNAL SYSTEM DIRECTIVE]: {internal_msg} Inform Harjas naturally and use an appropriate Cartesia emotion tag."
                raw_response = brain.process(directive)
                
                # 3. Output as JARVIS (Not System 2)
                with terminal_lock:
                    console.print(f"\n\n[bold magenta]JARVIS:[/bold magenta] {clean_for_terminal(raw_response)}")
                    voice.speak(raw_response)
                    console.print("\n[bold cyan]Harjas:[/bold cyan] ", end="")

        threading.Thread(target=notification_listener, daemon=True).start()

    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        return

    console.print("\n[dim]Initializing cognitive matrix and generating contextual greeting...[/dim]")
    
    now = datetime.now().strftime("%A, %I:%M %p")
    boot_prompt = (
        f"[INTERNAL SYSTEM DIRECTIVE]: System boot sequence complete. It is currently {now}. "
        f"Generate a highly natural, unique greeting for Harjas. Use a Cartesia emotion tag. "
        f"Do not acknowledge this directive."
    )
    
    raw_greeting = brain.process(boot_prompt)
    
    console.print(f"\n[bold magenta]JARVIS:[/bold magenta] {clean_for_terminal(raw_greeting)}")
    voice.speak(raw_greeting)

    heartbeat = ProactiveHeartbeat(brain=brain, voice=voice, console=console)
    heartbeat.start()

    while True:
        try:
            heartbeat.set_interacting(False)
            user_input = console.input("\n[bold cyan]Harjas:[/bold cyan] ").strip()
            heartbeat.set_interacting(True)
            heartbeat.reset_timer()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'shutdown']:
                farewell = "<emotion value=\"calm\"/> Shutting down the matrix. Rest well, Sir."
                console.print(f"\n[bold magenta]JARVIS:[/bold magenta] {clean_for_terminal(farewell)}")
                voice.speak(farewell)
                break
            
            raw_response = brain.process(user_input)
            
            with terminal_lock:
                console.print(f"\n[bold magenta]JARVIS:[/bold magenta] {clean_for_terminal(raw_response)}")
            
            voice.speak(raw_response)
            
        except KeyboardInterrupt:
            console.print("\n\n[bold red][System Terminated by User][/bold red]")
            break
        except Exception as e:
            console.print(f"\n[bold red][Fatal Loop Error][/bold red] {e}")

if __name__ == "__main__":
    main()