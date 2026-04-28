import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from swarm.tools import create_project_workspace, write_code_file, execute_python_in_jarvis_env

def run_autonomous_coder(instructions: str) -> str:
    """Spins up the LangGraph Swarm to execute a coding task."""
    api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(api_key=api_key, model="llama-3.3-70b-versatile", temperature=0.1)
    
    tools = [create_project_workspace, write_code_file, execute_python_in_jarvis_env]
    
    system_prompt = """
    You are an elite Autonomous Software Engineer. 
    You have the ability to create directories, write code files, and execute them in a secure conda environment.
    
    WORKFLOW:
    1. If the user wants a new project, use 'create_project_workspace' first.
    2. Write the necessary files using 'write_code_file'. (e.g., app.py, package.json, etc.)
    3. If it is a Python script, you MUST use 'execute_python_in_jarvis_env' to test it.
    4. If the test fails, read the error, rewrite the file using 'write_code_file', and test again.
    5. When everything works (or if it's a project that just needs scaffolding), finish the task and summarize what you built.
    """
    
    # Version-proof initialization (no modifier kwargs)
    agent_executor = create_react_agent(llm, tools)
    
    # Inject the system prompt directly into the conversational state
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=instructions)
    ]
    
    # Run the swarm
    result = agent_executor.invoke({"messages": messages})
    
    final_output = result["messages"][-1].content
    return final_output