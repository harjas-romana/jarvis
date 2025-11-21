import asyncio
import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ZERO-LEAK LOGGING — file-only, no stdout corruption
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(_log_dir, exist_ok=True)
_log_file = os.path.join(_log_dir, f"jarvis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

for _h in logging.root.handlers[:]:
    if isinstance(_h, logging.StreamHandler) and not isinstance(_h, logging.FileHandler):
        logging.root.removeHandler(_h)

logging.basicConfig(
    filename=_log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True,
)

for _noisy in ["httpx", "httpcore", "chromadb", "opentelemetry",
               "urllib3", "langchain", "langsmith", "faster_whisper",
               "pyannote", "torch", "lightning"]:
    logging.getLogger(_noisy).setLevel(logging.ERROR)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Imports (after logging is locked down)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from langchain_core.messages import HumanMessage

from core.telemetry import logger
from core.dynamic_loader import DynamicLoader
from core.agent_graph import JarvisGraph
from audio.stt import SensoryPipeline
from audio.tts import get_tts_manager
from memory.vector_store import VectorStore

console = Console()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CONSTANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MIN_COMMAND_WORDS    = 2      # Reject single-word blips
POST_TTS_COOLDOWN    = 2.5   # Seconds to wait after speaking before listening again
GRAPH_RECURSION_CAP  = 5     # Hard cap on tool-call loops per request

# Whisper partial-wake / noise outputs to silently discard
_NOISE_EXACT = {
    "you", "thank you", "thanks", "okay", "ok",
    "hmm", "uh", "um", "ah", "oh", "bye", "hey",
    "jarvis", "javis", "java", "jarvice", "javas",   # bare wake-word echoes
}

# Prefix rewrites: if the transcription *starts with* any key, strip it.
# Ordered from longest to shortest to avoid partial matches.
_WAKE_REWRITES = [
    ("jarvis, ",   ""),
    ("javis, ",    ""),
    ("java is, ",  ""),
    ("javas, ",    ""),
    ("jarvice, ",  ""),
    ("java is ",   ""),
    ("javas ",     ""),
    ("jarvis ",    ""),
    ("javis ",     ""),
    ("jarvice ",   ""),
]


class JarvisOrchestrator:
    def __init__(self):
        self.running      = False
        self.tools_loader = DynamicLoader(os.path.join(os.path.dirname(__file__), "tools"))
        self.sensory      = SensoryPipeline()
        self.tts          = get_tts_manager()
        self.memory       = VectorStore()
        self.available_tools = []
        self.graph_brain  = None
        self.event_log    = []   # Sidebar activity feed

        # ── Rich layout ──
        self.layout = Layout()
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=5),
        )
        self.layout["main"].split_row(
            Layout(name="output"),
            Layout(name="sidebar", ratio=1, minimum_size=45),
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # BOOT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async def _initialize_systems(self):
        self.available_tools = self.tools_loader.auto_discover()
        logger.info(f"Boot: Loaded {len(self.available_tools)} tools.")

        try:
            self.graph_brain = JarvisGraph(
                self.available_tools,
                self.tools_loader.execute_tool,
            )
        except Exception as e:
            logger.critical(f"Brain init failed: {e}")
            console.print(f"[bold red]FATAL: {e}[/bold red]")
            sys.exit(1)

        self.running = True
        await self._boot_greeting()

    async def _boot_greeting(self):
        hour = datetime.now().hour
        if   hour < 12: salutation = "Good morning"
        elif hour < 17: salutation = "Good afternoon"
        else:           salutation = "Good evening"

        tool_count   = len(self.available_tools)
        memory_count = self.memory.get_memory_count()

        if memory_count > 0:
            greeting = (
                f"{salutation}, Sir. All systems are online — "
                f"{tool_count} cognitive tools loaded, "
                f"{memory_count} episodic memories on file. "
                f"I'm ready when you are."
            )
        else:
            greeting = (
                f"{salutation}, Sir. JARVIS is fully operational. "
                f"{tool_count} tools loaded and standing by."
            )

        logger.info(f"Boot greeting: {greeting}")
        self._push_event(greeting, "cyan")
        await self._speak(greeting)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DASHBOARD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _refresh_dashboard(self, output: str, state: str) -> None:
        tool_count = len(self.tools_loader.registry)
        mem_count  = self.memory.get_memory_count()

        self.layout["header"].update(Panel(
            f"[bold cyan]JARVIS PROTO-AGI[/bold cyan] | "
            f"State: [bold yellow]{state}[/bold yellow] | "
            f"Tools: [green]{tool_count}[/green] | "
            f"Memories: [blue]{mem_count}[/blue]"
        ))

        self.layout["main"]["output"].update(
            Panel(output, title="[green]Neural Output[/green]")
        )

        sidebar = f"[bold underline]Cognitive Tools ({tool_count})[/bold underline]\n"
        for name in sorted(self.tools_loader.registry.keys()):
            sidebar += f"  [cyan]·[/cyan] {name}\n"
        sidebar += "\n[bold underline]Event Horizon[/bold underline]\n"
        for entry in self.event_log[-10:]:
            sidebar += f"  {entry}\n"
        self.layout["main"]["sidebar"].update(
            Panel(sidebar, title="[blue]System Registry[/blue]")
        )

        self.layout["footer"].update(
            Panel(
                f"[bold yellow]Sensory Array[/bold yellow] >> "
                f"[blink green]RING BUFFER ACTIVE[/blink green]"
            )
        )

    def _push_event(self, message: str, color: str = "magenta"):
        snippet = message[:50] + ("…" if len(message) > 50 else "")
        self.event_log.append(f"[{color}]{snippet}[/{color}]")
        # Keep log bounded — no unbounded memory growth
        if len(self.event_log) > 60:
            self.event_log = self.event_log[-40:]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # INPUT SANITIZATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _clean_command(self, raw: str) -> str:
        """
        Returns a cleaned command string, or '' if the input should be discarded.
          1. Strip whitespace.
          2. Discard if fewer than MIN_COMMAND_WORDS words.
          3. Discard known noise / bare wake-word echoes.
          4. Strip leading wake-word prefix variants.
          5. Re-check word count after stripping.
        """
        text = raw.strip()
        if not text:
            return ""

        if len(text.split()) < MIN_COMMAND_WORDS:
            logger.info(f"Discarded short transcription: '{text}'")
            return ""

        if text.lower() in _NOISE_EXACT:
            logger.info(f"Discarded noise: '{text}'")
            return ""

        lower = text.lower()
        for prefix, replacement in _WAKE_REWRITES:
            if lower.startswith(prefix):
                text  = (replacement + text[len(prefix):]).strip()
                lower = text.lower()
                break   # One rewrite pass is enough

        if len(text.split()) < MIN_COMMAND_WORDS:
            logger.info(f"Discarded after wake-strip: '{text}'")
            return ""

        return text

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # TTS  (purely sequential — no threading, no flags needed)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async def _speak(self, text: str) -> None:
        """
        Speak and block until TTS + cooldown are complete.
        The main loop is a single async chain — there is no other coroutine
        that could call listen_pipeline() while we are awaiting here.
        No is_speaking flag is needed.
        """
        try:
            await self.tts.speak(text)
        except Exception as e:
            logger.error(f"TTS error: {e}")
        finally:
            await asyncio.sleep(POST_TTS_COOLDOWN)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HOT-RELOAD
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    def _check_hot_reload(self) -> None:
        signal_path = os.path.join(
            os.path.dirname(__file__), "config", ".hot_reload_signal"
        )
        if not os.path.exists(signal_path):
            return
        try:
            logger.info("Hot-reload signal detected. Rebuilding cognitive graph.")
            self.available_tools = self.tools_loader.hot_reload()
            self.graph_brain = JarvisGraph(
                self.available_tools,
                self.tools_loader.execute_tool,
            )
            os.remove(signal_path)
            self._push_event("New tool assimilated — graph rebuilt.", "cyan")
        except Exception as e:
            logger.error(f"Hot-reload failed: {e}")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAIN LOOP
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async def run_loop(self):
        await self._initialize_systems()

        with Live(self.layout, refresh_per_second=8, screen=True):
            while self.running:
                try:
                    self._refresh_dashboard("Awaiting vocal input…", "LISTENING")

                    # ── 1. Listen ──
                    raw = await self.sensory.listen_pipeline()
                    if not raw:
                        continue

                    if raw == "[AUTH_FAILED]":
                        self._push_event("AUTH DENIED", "red")
                        logger.warning("Auth failed — unauthorized vocal signature.")
                        await self._speak("Unauthorized vocal signature. Access denied.")
                        continue

                    # ── 2. Sanitize ──
                    command = self._clean_command(raw)
                    if not command:
                        continue

                    self._push_event(f"USR: {command}", "white")
                    self._refresh_dashboard(f"Heard: {command}", "THINKING")
                    logger.info(f"User: {command}")

                    # ── 3. Episodic memory context (1 result — minimal overhead) ──
                    user_msg = command
                    try:
                        past = self.memory.search_memory(command, n_results=1)
                        if past and past.get("documents"):
                            docs = past["documents"]
                            if docs and docs[0] and docs[0][0] not in (
                                "Memory system inactive.", "Memory search error.", ""
                            ):
                                snippet  = docs[0][0][:250]
                                user_msg = (
                                    f"[Recent context: {snippet}]\n\n"
                                    f"Current request: {command}"
                                )
                    except Exception as mem_err:
                        logger.warning(f"Memory retrieval skipped: {mem_err}")

                    # ── 4. Invoke Cognitive Graph ──
                    self._refresh_dashboard(f"Processing: {command}", "COGNITIVE LOOP")
                    initial_state = {"messages": [HumanMessage(content=user_msg)]}

                    try:
                        final_state = await asyncio.to_thread(
                            self.graph_brain.graph.invoke,
                            initial_state,
                            {"recursion_limit": GRAPH_RECURSION_CAP},
                        )
                    except Exception as graph_err:
                        err = str(graph_err)
                        logger.error(f"Graph invocation failed: {err}")
                        self._push_event("ERR: Cognitive fault — recovered", "red")

                        if "429" in err:
                            reply = (
                                "Sir, I've hit the inference rate limit. "
                                "Give me a moment and try again."
                            )
                        elif "400" in err:
                            reply = (
                                "Sir, there was a malformed request to the cognitive engine. "
                                "Could you rephrase that?"
                            )
                        else:
                            reply = (
                                "Sir, I hit a temporary cognitive block but I've recovered. "
                                "Please go ahead."
                            )

                        await self._speak(reply)
                        continue

                    # ── 5. Extract response ──
                    messages = final_state.get("messages", [])
                    if not messages:
                        logger.warning("Graph returned no messages.")
                        continue

                    response = (messages[-1].content or "").strip()
                    if not response:
                        logger.warning("Graph returned an empty response.")
                        continue

                    self._push_event(f"SYS: {response}", "green")
                    logger.info(f"JARVIS: {response[:300]}")

                    # ── 6. Persist to episodic memory ──
                    try:
                        self.memory.store_interaction(command, response)
                        logger.info(
                            f"Stored interaction to episodic memory. "
                            f"Total: {self.memory.get_memory_count()}"
                        )
                    except Exception as mem_err:
                        logger.warning(f"Memory store failed: {mem_err}")

                    # ── 7. Speak ──
                    self._refresh_dashboard(response, "SPEAKING")
                    await self._speak(response)

                    # ── 8. Hot-reload check (after speaking, never blocks) ──
                    self._check_hot_reload()

                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    logger.error(f"Loop exception: {e}", exc_info=True)
                    self._push_event("SYS: Fault recovered", "red")
                    await asyncio.sleep(2)
                    continue


if __name__ == "__main__":
    try:
        orchestrator = JarvisOrchestrator()
        asyncio.run(orchestrator.run_loop())
    except KeyboardInterrupt:
        sys.exit(0)