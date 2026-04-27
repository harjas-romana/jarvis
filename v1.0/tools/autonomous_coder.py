import os
import re
import subprocess
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

TOOL_SCHEMA = {
    "name": "create_new_tool",
    "description": "Autonomously engineers, compiles, and deploys a brand new Python tool into the live system. Only requires a name and plain-english instructions.",
    "parameters": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "A snake_case filename without .py (e.g., 'weather_checker')."
            },
            "requirements": {
                "type": "string",
                "description": "Plain english description of what the tool should do."
            }
        },
        "required": ["tool_name", "requirements"]
    }
}

# Hardcoded reference paths
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SANDBOX = os.path.join(_ROOT, "sandbox", "temp_workspace")
_TOOLS = os.path.join(_ROOT, "tools")
_SIGNAL = os.path.join(_ROOT, "config", ".hot_reload_signal")

# Protected filenames that cannot be overwritten
_PROTECTED = {
    "autonomous_coder.py", "shell_executor.py", "media_controller.py",
    "devops_agent.py", "app_launcher.py", "file_manager.py",
    "clipboard_manager.py", "notification_sender.py", "web_search.py",
    "voice_settings.py", "career_proxy.py",
}

# The system prompt for the hidden secondary LLM — the actual code generator
_CODER_SYSTEM_PROMPT = """You are an elite Python code generator. You output ONLY raw Python code. No markdown. No explanations. No commentary.

Every tool you create MUST follow this exact template structure:

import os  # or whatever imports are needed

TOOL_SCHEMA = {
    "name": "<tool_name>",
    "description": "<what it does>",
    "parameters": {
        "type": "object",
        "properties": {
            "<param_name>": {
                "type": "string",
                "description": "<param description>"
            }
        },
        "required": ["<param_name>"]
    }
}

def execute(<param_name>: str) -> str:
    try:
        # tool logic here
        return "result string"
    except Exception as e:
        return f"Error: {str(e)}"

RULES:
1. Output ONLY the raw Python code. No triple backticks. No markdown fences. No "Here is the code" preamble.
2. The TOOL_SCHEMA dict and execute() function are MANDATORY.
3. execute() must accept keyword arguments matching the TOOL_SCHEMA properties.
4. execute() must always return a string.
5. Use subprocess for any shell/OS operations.
6. Keep it simple and robust. Wrap everything in try/except.
"""


def _strip_markdown_fences(text: str) -> str:
    """Aggressively removes any markdown code fences the LLM might sneak in."""
    # Remove ```python ... ``` blocks
    text = re.sub(r'```python\s*\n?', '', text)
    text = re.sub(r'```\s*\n?', '', text)
    # Remove leading prose lines before the first import/TOOL_SCHEMA
    lines = text.split('\n')
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('import ') or stripped.startswith('from ') or stripped.startswith('TOOL_SCHEMA') or stripped.startswith('#'):
            start_idx = i
            break
    return '\n'.join(lines[start_idx:]).strip()


def execute(tool_name: str, requirements: str) -> str:
    """
    The Inception Pattern:
    1. Receives plain-english requirements (no code in JSON)
    2. Spawns a hidden secondary LLM to generate raw Python
    3. Writes to sandbox, compiles, validates, migrates, signals hot-reload
    """
    # Sanitize tool name
    tool_name = tool_name.strip().replace(" ", "_").replace("-", "_").lower()
    if tool_name.endswith(".py"):
        tool_name = tool_name[:-3]
    
    filename = f"{tool_name}.py"
    
    # Safety: don't overwrite core tools
    if filename in _PROTECTED:
        return f"BLOCKED: Cannot overwrite protected system tool '{filename}'."
    
    os.makedirs(_SANDBOX, exist_ok=True)
    os.makedirs(os.path.dirname(_SIGNAL), exist_ok=True)
    sandbox_path = os.path.join(_SANDBOX, filename)
    final_path = os.path.join(_TOOLS, filename)

    try:
        # ── STEP 1: Spawn hidden secondary LLM to generate raw Python ──
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return "FAILED: GROQ_API_KEY not found in environment."
        
        coder_llm = ChatGroq(
            api_key=api_key, 
            model="llama-3.1-8b-instant", 
            temperature=0.0,  # Zero temp for deterministic code output
            max_tokens=4096
        )
        
        user_prompt = (
            f"Create a Python tool named '{tool_name}'. "
            f"Requirements: {requirements}. "
            f"The TOOL_SCHEMA 'name' field must be exactly '{tool_name}'. "
            f"Output ONLY raw Python code. Nothing else."
        )
        
        response = coder_llm.invoke([
            SystemMessage(content=_CODER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ])
        
        raw_code = _strip_markdown_fences(response.content)
        
        if not raw_code or len(raw_code) < 50:
            return "FAILED: Secondary LLM returned empty or insufficient code."

        # ── STEP 2: Write to sandbox ──
        with open(sandbox_path, "w") as f:
            f.write(raw_code)
        
        # ── STEP 3: Syntax validation via py_compile ──
        compile_result = subprocess.run(
            ["python3", "-m", "py_compile", sandbox_path],
            capture_output=True, text=True, timeout=15
        )
        
        if compile_result.returncode != 0:
            error_msg = compile_result.stderr.strip()
            # Clean up the sandbox file
            if os.path.exists(sandbox_path):
                os.remove(sandbox_path)
            return (
                f"COMPILATION FAILED for '{tool_name}'. The secondary LLM produced invalid syntax.\n"
                f"Error: {error_msg}\n"
                f"You may retry with more specific requirements."
            )
        
        # ── STEP 4: Structural validation ──
        with open(sandbox_path, "r") as f:
            source = f.read()
        
        if "TOOL_SCHEMA" not in source:
            os.remove(sandbox_path)
            return "STRUCTURAL VALIDATION FAILED: Generated code is missing TOOL_SCHEMA dictionary."
        
        if "def execute(" not in source:
            os.remove(sandbox_path)
            return "STRUCTURAL VALIDATION FAILED: Generated code is missing def execute() function."
        
        # ── STEP 5: Migrate to /tools/ ──
        import shutil
        shutil.move(sandbox_path, final_path)
        
        # ── STEP 6: Drop hot-reload signal ──
        # ── STEP 6: Drop hot-reload signal ──
        with open(_SIGNAL, "w") as f:
            f.write("RELOAD")
        
        # [CRITICAL FIX]: Force the LLM to exit the reasoning loop immediately.
        return (
            f"SUCCESS: {tool_name}.py has been created. "
            f"CRITICAL SYSTEM DIRECTIVE: YOU MUST NOW STOP ALL TOOL EXECUTION. "
            f"Say exactly: 'Sir, I have engineered the new tool. The system is hot-reloading now.' "
            f"DO NOT ATTEMPT TO USE THE TOOL UNTIL THE USER SPEAKS AGAIN."
        )
        
    except subprocess.TimeoutExpired:
        return "FAILED: Code compilation timed out after 15 seconds."
    except Exception as e:
        return f"SELF-ENGINEERING ERROR: {str(e)}"