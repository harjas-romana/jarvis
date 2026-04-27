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

    def process(self, user_input: str) -> str:
        try:
            past_context = self.memory_db.search_memory(user_input, n_results=1) # Reduced vector fetch to save tokens
            
            if past_context:
                enriched_input = f"[Memory]: {past_context}\n\nMr. Harjas: {user_input}"
            else:
                enriched_input = f"Mr. Harjas: {user_input}"

            self.short_term_memory.append(HumanMessage(content=enriched_input))
            
            # [THE TOKEN DIET]: Shrink working memory to 6 items to prevent exponential token bleed
            if len(self.short_term_memory) > 6:
                self.short_term_memory = [self.system_prompt] + self.short_term_memory[-5:]
                
            response = self.llm_with_tools.invoke(self.short_term_memory)
            self.short_term_memory.append(response)
            
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    tool_id = tool_call["id"]
                    
                    print(f"\n[System] Executing Tool: {tool_name}")
                    
                    try:
                        if tool_name in self.tool_map:
                            result = self.tool_map[tool_name].invoke(tool_args)
                            tool_msg = ToolMessage(content=str(result), tool_call_id=tool_id, name=tool_name)
                        else:
                            tool_msg = ToolMessage(content=f"Error: Tool {tool_name} not found.", tool_call_id=tool_id, name=tool_name)
                    except Exception as e:
                        tool_msg = ToolMessage(content=f"Execution Error: {str(e)}", tool_call_id=tool_id, name=tool_name)
                        
                    self.short_term_memory.append(tool_msg)
                
                # Concise guardrail
                guardrail = HumanMessage(content="[INTERNAL DIRECTIVE]: Read the tool response above. Extract the exact data requested and answer concisely. No fluff.")
                self.short_term_memory.append(guardrail)
                    
                final_response = self.llm_with_tools.invoke(self.short_term_memory)
                self.short_term_memory.append(final_response)
                final_text = final_response.content.strip()
            else:
                final_text = response.content.strip()

            self.memory_db.store_interaction("user", user_input)
            self.memory_db.store_interaction("jarvis", final_text)

            return final_text
        except Exception as e:
            return f"<emotion value=\"apologetic\"/> Sir, I encountered a system error: {str(e)}"