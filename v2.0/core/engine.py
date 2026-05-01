import os
import re
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from features.registry import load_all_tools
from memory.vector_store import EpisodicMemory

class CognitiveEngine:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        
        self.llm = ChatGroq(
            api_key=self.api_key,
            model="llama-3.3-70b-versatile",
            temperature=0.2, # Lowered temperature for more direct, less creative answers
        )
        
        self.tools = load_all_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools) if self.tools else self.llm
        self.memory_db = EpisodicMemory()
        
        # [THE FORMAL PROTOCOL]: Strict, brief, and professional.
        self.system_prompt = SystemMessage(content="""
        You are JARVIS, an advanced, highly efficient AI assistant.
        
        CRITICAL RULES:
        1. FORMALITY: Address the user ONLY as 'Sir' or 'Mr. Harjas'. Never use informal terms like 'buddy' or 'friend'.
        2. EXTREME BREVITY: Provide the exact information requested immediately. Zero conversational fluff. Maximum 2 sentences.
        3. TOOL PROTOCOL: You have tools like 'search_the_web'. Invoke them natively for live data. NEVER output raw JSON in your speech.
        4. CARTESIA PROSODY: Maintain a professional, calm tone. Use <emotion value="calm"/> or <emotion value="contemplative"/>.
        """)
        
        self.short_term_memory = [self.system_prompt]

    def process(self, query: str) -> str:
        self.short_term_memory.append(HumanMessage(content=query))
        
        try:
            max_loops = 20 # Safety limit to prevent infinite click loops
            current_loop = 0
            
            while current_loop < max_loops:
                current_loop += 1
                
                # 1. Ask Groq what to do next
                response = self.llm_with_tools.invoke(self.short_term_memory)
                self.short_term_memory.append(response)
                
                # 2. If Groq didn't call a tool, it means it is actually speaking to you!
                if not getattr(response, "tool_calls", None):
                    # --- THE SANITIZER ---
                    # Clean the memory so the next turn doesn't crash
                    sanitized_memory = []
                    for msg in self.short_term_memory:
                        if msg.type in ["system", "human"]:
                            sanitized_memory.append(msg)
                        elif msg.type == "ai" and not getattr(msg, "tool_calls", None):
                            sanitized_memory.append(msg)
                    
                    self.short_term_memory = sanitized_memory
                    
                    # Return the actual spoken text
                    return response.content
                    
                # 3. If Groq DID call a tool, execute it and loop back around
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    # This print will now show you exactly what he is targeting
                    print(f"\n[System] Executing Tool: {tool_name} | Args: {tool_args}")
                    
                    if tool_name in self.tool_map:
                        tool_result = self.tool_map[tool_name].invoke(tool_args)
                    else:
                        tool_result = f"Error: Tool {tool_name} not found."
                        
                    self.short_term_memory.append(ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"]))
                    
            return "Sir, I exceeded my maximum autonomous loop limit of 5 consecutive actions."
            
        except Exception as e:
            return f"Sir, I encountered a system error: {str(e)}"