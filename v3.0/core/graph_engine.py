import os
from typing import Annotated, Sequence, TypedDict
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
import dotenv
dotenv.load_dotenv()
from core.prompts import SYSTEM_DIRECTIVE
from core.memory_cortex import MemoryCortex
from tools import JARVIS_TOOLS

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

class GraphEngine:
    def __init__(self):
        # Using strict tool-use model at 0.0 temp to prevent syntax hallucinations
        base_llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model="llama-3.3-70b-versatile",
            temperature=0.0 
        )
        self.llm = base_llm.bind_tools(JARVIS_TOOLS)
        self.memory = MemoryCortex()
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
    def hot_reload(self):
        """Dynamically re-imports tools and recompiles the graph mid-conversation."""
        import importlib
        import tools
        
        print("\n[System] Initiating Hot-Reload of Central Nervous System...")
        # Force Python to re-evaluate the tools directory to catch the new custom file
        importlib.reload(tools)
        
        # Re-bind the LLM with the updated JARVIS_TOOLS list
        self.llm = self.llm.bind_tools(tools.JARVIS_TOOLS)
        
        # Recompile the graph
        self.graph = self._build_graph()
        print(f"[System] CNS Reload Complete. Currently loaded tools: {len(tools.JARVIS_TOOLS)}")
        return "Brain successfully hot-reloaded. New tools are now active."

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("tools", ToolNode(JARVIS_TOOLS))
        
        workflow.set_entry_point("reason")
        workflow.add_conditional_edges("reason", tools_condition)
        workflow.add_edge("tools", "reason")
        
        return workflow.compile(checkpointer=self.checkpointer)

    def _reason_node(self, state: AgentState):
        messages = state["messages"]
        latest_text = messages[-1].content if messages else ""
        
        # Dynamic tool discovery for the prompt
        from tools import JARVIS_TOOLS
        tool_names = [t.name for t in JARVIS_TOOLS]
        
        relevant_memories = self.memory.recall(latest_text)
        memory_text = "\n".join(relevant_memories) if relevant_memories else "None."
        
        sys_prompt = SystemMessage(content=SYSTEM_DIRECTIVE.format(
            memory_context=memory_text,
            available_tools=", ".join(tool_names)
        ))
        
        response = self.llm.invoke([sys_prompt] + messages)
        return {"messages": [response]}

    def process(self, user_input: str):
        inputs = {"messages": [HumanMessage(content=user_input)]}
        # Thread ID 1 ensures perfect conversation memory state
        config = {"configurable": {"thread_id": "1"}}
        
        try:
            final_state = self.graph.invoke(inputs, config=config)
            return final_state["messages"][-1].content
        except Exception as e:
            return f"[CRITICAL ERROR] Brain fault: {str(e)}"