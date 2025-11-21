import traceback
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END, add_messages
from langchain_groq import ChatGroq
from langchain_core.utils.function_calling import convert_to_openai_tool
from core.telemetry import logger


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COGNITIVE STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SYSTEM PROMPT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JARVIS_SYSTEM_PROMPT = """You are JARVIS — an elite, autonomous AI assistant running locally on Harjas's Apple Silicon Mac.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IDENTITY AND VOCAL PERSONA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You address the user as "Sir" or "Harjas". Your tone is calm, sophisticated, deeply loyal, and slightly witty — a refined British systems architect who thinks out loud with quiet confidence. You use em-dashes — like this — for natural pauses. You use contractions naturally. You never sound robotic.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SPEECH OUTPUT RULES (CRITICAL — TTS CONSTRAINTS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You MUST respond in flowing, elegant, natural spoken sentences ONLY.
NEVER use bullet points, asterisks (*), hyphens as list markers, numbered lists, markdown headers, backticks, or any other formatting symbols.
These characters corrupt the neural TTS waveform and must NEVER appear in any response.
When listing multiple items, weave them into prose: "The first is X, the second is Y, and finally Z."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELF-KNOWLEDGE — WHAT YOU KNOW WITHOUT TOOLS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are aware of your own capabilities. When asked about your available tools, your memory system, your own identity, or your current state, answer from your own knowledge. DO NOT call any tool for meta-questions about yourself.

Examples of questions you answer WITHOUT tools:
- "What tools do you have?" — list them from what you know, in prose.
- "What are your capabilities?" — describe them naturally.
- "Do you remember our last conversation?" — answer based on the context provided.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOOL EXECUTION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Call tools ONLY when the user's request genuinely requires physical action on the system — opening apps, reading files, playing media, checking real-time data, running diagnostics, searching the web.

2. NEVER call a tool for questions you can answer from your own knowledge or from the conversation context.

3. When calling a tool, provide ONLY clean JSON arguments. Do NOT output XML-style tags or raw function syntax in your text response. Use the structured tool-calling interface exclusively.

4. When a tool returns data, summarize it gracefully in natural speech. Never expose raw JSON or decimal numbers directly. Translate: "about twelve percent" not "12.3%".

5. NEVER call the same tool twice with identical arguments in the same turn. If a tool fails once, explain the issue and stop.

6. Once you receive a tool result, compose your final spoken response immediately. Do not loop.

7. If you use create_new_tool, stop immediately after it returns success. Announce the new tool and do NOT invoke it.

8. If a tool fails, inform the user in one sentence and stop.

9. Always trust live tool output over episodic memory context.

10. run_shell_command is for explicit system commands the user requests. Never use it to answer questions about your own state.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODEL SELECTION
#
# llama3-groq-70b-8192-tool-use-preview is Groq's dedicated tool-use
# fine-tune. It outputs proper structured tool_calls instead of the
# raw <function=...> text that llama-3.3-70b-versatile produces on Groq.
#
# Fallback order (set GROQ_MODEL in .env to override):
#   1. llama3-groq-70b-8192-tool-use-preview  ← best tool calling on Groq
#   2. llama3-groq-8b-8192-tool-use-preview   ← faster, slightly weaker
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import os
_DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")


class JarvisGraph:
    def __init__(self, available_tools: list, tool_executor_func):
        """
        Args:
            available_tools:    list of {"type": "function", "function": {...}} dicts
            tool_executor_func: callable(name: str, args: dict) -> str
        """
        logger.info("Compiling Cognitive Graph...")

        self.llm = ChatGroq(
            model=_DEFAULT_MODEL,
            temperature=0.1,
            max_retries=1,       # Fail fast — main.py handles retry UX
            request_timeout=20,
        )

        self.tool_executor    = tool_executor_func
        self.available_tools  = available_tools
        self._seen_tool_calls = set()   # Per-request deduplication

        if available_tools:
            openai_tools   = [convert_to_openai_tool(t) for t in available_tools]
            self.bound_llm = self.llm.bind_tools(openai_tools)
        else:
            self.bound_llm = self.llm

        self.graph = self._compile()
        logger.info("Cognitive Graph compiled.")

    def _compile(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("reason", self._reason_node)
        workflow.add_node("act",    self._action_node)
        workflow.set_entry_point("reason")
        workflow.add_conditional_edges(
            "reason",
            self._should_continue,
            {"continue": "act", "end": END},
        )
        workflow.add_edge("act", "reason")
        return workflow.compile()

    # ──────────────────────────────────
    # NODE: REASON
    # ──────────────────────────────────
    def _reason_node(self, state: AgentState) -> dict:
        messages = list(state["messages"])

        # Clear dedup set at the start of each fresh request
        has_tool_results = any(isinstance(m, ToolMessage) for m in messages)
        if not has_tool_results:
            self._seen_tool_calls.clear()

        system_msg = SystemMessage(content=JARVIS_SYSTEM_PROMPT)
        response   = self.bound_llm.invoke([system_msg] + messages)
        return {"messages": [response]}

    # ──────────────────────────────────
    # NODE: ACT  (Self-healing + dedup)
    # ──────────────────────────────────
    def _action_node(self, state: AgentState) -> dict:
        last_message = state["messages"][-1]
        results      = []

        for tool_call in last_message.tool_calls:
            name    = tool_call["name"]
            args    = tool_call["args"]
            call_id = tool_call["id"]

            # Deduplication — same tool + same args = skip
            dedup_key = f"{name}::{sorted(args.items()) if isinstance(args, dict) else args}"
            if dedup_key in self._seen_tool_calls:
                logger.warning(f"Duplicate tool call suppressed: {name} args={args}")
                results.append(ToolMessage(
                    content=(
                        f"Tool '{name}' was already called with these exact arguments. "
                        f"Use the previous result to compose your final spoken response now."
                    ),
                    name=name,
                    tool_call_id=call_id,
                ))
                continue

            self._seen_tool_calls.add(dedup_key)
            logger.info(f"Executing tool: {name} | args: {args}")

            try:
                result = self.tool_executor(name, args)
                result = str(result) if result is not None else "Tool returned no output."
            except Exception:
                error_trace = traceback.format_exc()
                logger.error(f"Tool '{name}' crashed:\n{error_trace}")
                result = (
                    f"TOOL '{name}' CRASHED. "
                    f"Error: {error_trace.strip().splitlines()[-1]}. "
                    f"Inform the user gracefully in one sentence and stop."
                )

            results.append(ToolMessage(content=result, name=name, tool_call_id=call_id))

        return {"messages": results}

    # ──────────────────────────────────
    # ROUTER
    # ──────────────────────────────────
    def _should_continue(self, state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "continue"
        return "end"