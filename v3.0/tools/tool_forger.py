import os
import subprocess
import ast
import re
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

class ForgeToolInput(BaseModel):
    tool_name: str = Field(description="The exact python filename to create (e.g., 'weather_agent').")
    objective: str = Field(description="Detailed description of what the tool must do.")
    pip_dependencies: list[str] = Field(description="List of python packages needed.")

@tool(args_schema=ForgeToolInput)
def forge_new_tool(tool_name: str, objective: str, pip_dependencies: list[str]) -> str:
    """
    META-CRITICAL TOOL: Use this to write and install a NEW python tool for yourself.
    """
    # 1. Standard Library Filter (Prevents pip errors for 'json', 'os', etc.)
    # tools/tool_forger.py
    std_libs = ["json", "os", "sys", "re", "math", "datetime", "time","subprocess", "inspect", "typing", "getpass", "hashlib"]
    clean_deps = [d for d in pip_dependencies if d.lower() not in std_libs]

    if clean_deps:
        print(f"[Meta-Agent] Installing dependencies: {clean_deps}")
        try:
            subprocess.run(f"conda run -n jarvis pip install {' '.join(clean_deps)}", shell=True, check=True)
        except Exception as e:
            return f"FORGE ERROR: Dependency install failed: {str(e)}"

    # 2. Forge the Code (Instruction: NO API KEYS)
    try:
        coder = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model="openai/gpt-oss-120b", temperature=0.0)
        sys_prompt = """You are an elite Python tool forger. 
        CRITICAL: Prioritize PUBLIC APIs or WEB SCRAPING that DOES NOT require an API Key.
        For example: Use 'wttr.in' for weather, not OpenWeatherMap.
        
        REQUIREMENTS:
        - Output ONLY valid Python code.
        - Use @tool(args_schema=YourPydanticClass).
        - No conversational text, no markdown backticks outside the code.
        - Ensure all imports are included."""
        
        response = coder.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=objective)])
        
        # Clean markdown
        code = re.search(r'```(?:python|py)?\n?(.*?)```', response.content, re.DOTALL | re.IGNORECASE)
        code = code.group(1).strip() if code else response.content.strip()
        
        # AST Blueprint Check
        ast.parse(code)
        
        file_path = os.path.join(os.path.dirname(__file__), "custom", f"{tool_name}.py")
        with open(file_path, "w") as f:
            f.write(code)
            
        return f"SUCCESS: Tool '{tool_name}' forged without API requirements. Sir, type '\\reload' to activate."
    except Exception as e:
        return f"FORGE ERROR: {str(e)}"