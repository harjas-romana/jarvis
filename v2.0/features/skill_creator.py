import os
import re
import ast
import sys
import subprocess
from langchain_core.tools import tool
from groq import Groq

@tool
def create_new_skill(skill_filename: str, functionality_request: str) -> str:
    """
    CRITICAL TOOL: Use this to delegate the creation of a new Python tool to the Developer Agent.
    Do NOT write the code yourself. 
    Pass the 'skill_filename' (e.g. 'stock_api') and a plain English 'functionality_request' describing what the tool must do.
    """
    try:
        if not skill_filename.endswith(".py"):
            skill_filename += ".py"
            
        print(f"\n[Swarm] Waking up Developer Agent (GPT-OSS-120B via Groq) to write '{skill_filename}'...")
        
        # 1. Spin up the native Groq client for the OpenAI OSS model
        client = Groq()
        
        # 2. The Strict Developer Prompt with Dependency Injection Rules
        system_prompt = """
        You are an elite Senior Python Developer. Your job is to write LangChain @tool functions.
        You MUST output ONLY valid, raw Python code. Do not include markdown formatting, backticks, or conversational text.
        
        CRITICAL DEPENDENCY RULE: If your code requires third-party pip packages (e.g., yfinance, requests, psutil), your VERY FIRST LINE must be a comment starting with '# PIP: ' followed by the package names.
        Example: # PIP: yfinance pandas
        
        STRICT TEMPLATE TO FOLLOW:
        # PIP: any_required_pip_packages_here
        import os
        from langchain_core.tools import tool
        # Add any other required imports here
        
        @tool
        def function_name(query: str) -> str:
            '''A clear description of when the orchestrator should use this tool.'''
            try:
                # Core logic here
                return "SUCCESS: result"
            except Exception as e:
                return f"ERROR: {str(e)}"
        """
        
        user_message = f"Write a tool named {skill_filename.replace('.py', '')} that does the following: {functionality_request}"
        
        # 3. Generate the code using GPT-OSS-120B
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.0, # Deterministic logic
            reasoning_effort="medium", # Leverage the model's native CoT reasoning
            stream=False
        )
        
        raw_code = completion.choices[0].message.content.strip()
        
        # 4. Clean up accidental markdown
        clean_code = re.sub(r"^```python\n|```\n?$", "", raw_code, flags=re.MULTILINE).strip()
        
        # 5. [THE AUTO-INSTALLER]: Dynamically fetch and install pip packages into the Conda env
        first_line = clean_code.split('\n')[0].strip()
        if first_line.startswith("# PIP:"):
            packages = first_line.replace("# PIP:", "").strip().split()
            for pkg in packages:
                if pkg:
                    print(f"\n[Swarm] Auto-installing missing dependency: {pkg}...")
                    # Using sys.executable guarantees it installs into the 'jarvis' Conda env, not the global Mac env
                    subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"], check=False)
        
        # 6. AST Validation
        try:
            ast.parse(clean_code)
        except SyntaxError as e:
            return f"EXECUTION FAILED: The Developer Agent generated invalid Python syntax. Error: {str(e)}"
            
        if "@tool" not in clean_code:
            return "EXECUTION FAILED: The Developer Agent forgot the @tool decorator."
            
        # 7. Save to disk securely
        features_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(features_dir, skill_filename)
        
        protected_files = ["registry.py", "sandbox_executor.py", "skill_creator.py", "web_search.py", "__init__.py"]
        if skill_filename in protected_files:
            return f"SECURITY BLOCK: Cannot overwrite core system file '{skill_filename}'."
            
        with open(file_path, "w") as f:
            f.write(clean_code)
            
        return f"SUCCESS: The Developer Agent successfully wrote '{skill_filename}' and auto-installed its dependencies. Tell Mr. Harjas to restart the system to absorb it."
        
    except Exception as e:
        return f"SYSTEM ERROR: Swarm delegation failed: {str(e)}"