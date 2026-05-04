import os
import time
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import dotenv
dotenv.load_dotenv()
from core.graph_engine import GraphEngine
from core.sentient_daemon import SentientDaemon

console = Console()

class JarvisOS:
    def __init__(self):
        self._boot_sequence()
        self.daemon = SentientDaemon(check_interval=5)
        self.brain = GraphEngine()
        
    def _boot_sequence(self):
        os.system('clear' if os.name == 'posix' else 'cls')
        boot_text = """
[bold cyan]JARVIS v3.1 - AGENTIC OS (STABLE)[/bold cyan]
[dim]Kernel: LangGraph State Machine (MemorySaver Enabled)[/dim]
[dim]Tools: Pydantic Strict Mode[/dim]
[green]Status: ONLINE[/green]
        """
        console.print(Panel(boot_text, title="SYSTEM BOOT", border_style="cyan"))
        
    def run(self):
        self.daemon.start()
        time.sleep(1)
        
        console.print("[dim italic]System listening... (Type 'exit' to terminate)[/dim italic]\n")
        
        try:
            while True:
                # Inside main.py while True loop:
                user_input = console.input("[bold blue]Harjas:[/bold blue] ")
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    self._shutdown()
                    break
                    
                # THE RELOAD BRIDGE
                if user_input.strip() == r'\reload':
                    self.brain.hot_reload()
                    console.print("[bold green]JARVIS:[/bold green] Neural pathways refreshed, Sir. I am ready.\n")
                    continue
                
                if not user_input.strip():
                    continue

                env_context = self.daemon.get_environmental_context()
                augmented_input = f"[Telemetry: {env_context}]\nUser Query: {user_input}"
                
                with console.status("[bold green]JARVIS is reasoning...[/bold green]", spinner="dots"):
                    response = self.brain.process(augmented_input)
                
                console.print(f"\n[bold green]JARVIS:[/bold green]")
                console.print(Markdown(response))
                console.print("\n" + "─"*50 + "\n")
                
        except KeyboardInterrupt:
            self._shutdown()

    def _shutdown(self):
        console.print("\n[bold red]Initiating shutdown sequence...[/bold red]")
        self.daemon.stop()
        console.print("[dim]Daemon terminated. State saved. Goodbye, Sir.[/dim]")
        exit(0)

if __name__ == "__main__":
    jarvis = JarvisOS()
    jarvis.run()