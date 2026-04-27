import os
import asyncio
from typing import List
from pydantic import BaseModel, Field, field_validator, ValidationError
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

console = Console()

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
PROFILE_PATH = os.path.join(CONFIG_DIR, "user_profile.json")

class UserProfile(BaseModel):
    """
    Pydantic V2 Model enforcing strict schemas for the internal state memory.
    """
    name: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    academic_status: str = Field(..., min_length=1)
    career_targets: List[str] = Field(default_factory=list)
    physical_baseline: str = Field(...)

    @field_validator('career_targets', mode='before')
    @classmethod
    def split_targets(cls, v):
        if isinstance(v, str):
            # Convert comma separated string to list enforcing clean breaks
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

async def run_wizard():
    """
    A sophisticated interactive terminal UI bootstrapping baseline memory variables.
    """
    console.print(Panel.fit("[bold cyan]INITIALIZING PROJECT JARVIS V3.0 BOOTLOADER[/bold cyan]"))
    console.print("[yellow]No user profile detected in /config. Bootstrapping Baseline Memory...[/yellow]\n")

    # Await asyncio.to_thread wrapper around Rich prompts natively unblocks the event loop, 
    # preventing Groq's async stream and other engine threads from freezing while awaiting keystrokes.
    name = await asyncio.to_thread(Prompt.ask, "[cyan]1. Sir, what is your preferred name?[/cyan]")
    title = await asyncio.to_thread(Prompt.ask, "[cyan]2. What is your designated title or status?[/cyan]")
    academic_status = await asyncio.to_thread(Prompt.ask, "[cyan]3. What is your academic context? (e.g. B.Tech CSE 2026)[/cyan]")
    career_targets = await asyncio.to_thread(Prompt.ask, "[cyan]4. Career targets? (comma-separated)[/cyan]")
    physical_baseline = await asyncio.to_thread(Prompt.ask, "[cyan]5. Physical baseline context? (e.g. recovering, optimal)[/cyan]")

    try:
        profile = UserProfile(
            name=name,
            title=title,
            academic_status=academic_status,
            career_targets=career_targets,
            physical_baseline=physical_baseline
        )
    except ValidationError as e:
        console.print(f"[bold red]Validation Error against Pydantic V2 Schema:[/bold red] {e}")
        return False

    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
            
        # Write the strictly validated JSON string back to disk
        with open(PROFILE_PATH, "w") as f:
            f.write(profile.model_dump_json(indent=4))
            
        console.print("\n[bold green][SYSTEM] Bootloader sequence complete. Memory serialized to disk.[/bold green]")
        return True
        
    except PermissionError as pe:
        # Throws expected PermissionError if macOS natively denies read/write access to /config or execution directory
        console.print(f"[bold red][CRITICAL ERROR] OS Permission Denied when writing to {PROFILE_PATH}: {pe}[/bold red]")
        console.print("[bold yellow]Please ensure your terminal has disk write access and repeat boot sequence.[/bold yellow]")
        return False
    except Exception as e:
         console.print(f"[bold red][ERROR] Unexpected File I/O Error: {e}[/bold red]")
         return False

async def check_and_run_wizard():
    if not os.path.exists(PROFILE_PATH):
        await run_wizard()
    else:
        # Expected to silently continue boots if state exists
        pass
