# 🧠 JARVIS v2.0: The Conscious Core

Yoo 👋 Welcome to the JARVIS repo. Ngl, if you're looking for a basic glorified Siri that just sets timers, you're in the wrong place. 

JARVIS is a fully autonomous, multimodal digital co-developer and best friend. He is engineered specifically for macOS (runs flawlessly on a MacBook Pro) and bridges the gap between terminal scripts and actual AGI. No servant vibes here—strictly professional collaborator energy. 

## 🚀 TL;DR / The Vibe
We got tired of slow, rate-limited chatbots. So we built a system that has live internet access, asynchronous RAG memory, spatial screen awareness, and emotive vocal synthesis. The architecture is modular, decoupled, and goes crazy hard on inference speed. fr fr.

## ⚙️ Tech Stack (The Brains & Brawn)
The backend is heavily optimized for token efficiency and zero-latency execution.

* **Core Engine:** `llama-3.3-70b-versatile` running via Groq API. (Absolute unit of a model, responses in milliseconds).
* **Audio Subsystem (TTS):** Cartesia AI (`sonic-3` model). Using PyAudio to stream raw `pcm_f32le` bytes via Server-Sent Events (SSE). Bro literally pauses, breathes, and changes emotions mid-sentence using SSML tags. 
* **Episodic Memory:** ChromaDB vector store acting as the RAG backend.
* **Working Memory:** LangChain `short_term_memory` arrays with strict guardrails to prevent context amnesia and token bloating.
* **Swarm Framework:** LangGraph ReAct agents for background coding tasks.

## 🔥 Key Features

### 🕸️ System 3: The Nightly Web Spider
JARVIS doesn't wait for you to tell him things. `spider.py` runs asynchronously, scraping ArXiv for AI research and HackerNews for tech trends. It drops the data as text files directly into the knowledge base.

### 📚 The RAG Daemon
A background `watchdog` thread that silently monitors the `knowledge_base/` dir. The second a new PDF or spider scrape drops, the daemon chunks it, embeds it into ChromaDB, and pings JARVIS's cognitive matrix so he instantly knows about it. No manual DB updates required. W architecture.

### 👁️ The Optic Nerve (Ambient Vision)
Uses native macOS `screencapture` and `sips` downscaling combined with multimodal Llama vision models. JARVIS can literally "see" what's on your screen and proactively comment on your code without you typing a single word. 

### 🌍 Live Tool Execution
Integrated `DuckDuckGoSearchRun` so his 70B brain can pull live geopolitical news, API docs, or LPG/Petrol prices on the fly. Built with strict guardrails to prevent JSON hallucination loops. 

## 💻 Setup & Installation

You wanna run this? Bet. 

1. **Clone the repo & set up conda:**
   ```bash
   git clone https://github.com/harjas-romana/jarvis.git
   conda create -n jarvis python=3.10
   conda activate jarvis
   ```
2. **Install dependencies:**
   ```bash
   pip install langchain-groq langchain-community cartesia pyaudio duckduckgo-search watchdog chromadb PyPDF2 feedparser
   ```
3. **Env Vars:**
   Create a `.env` file in the root. You need these or the app will crash and burn tbh.
   ```env
   GROQ_API_KEY=your_groq_key
   CARTESIA_API_KEY=your_cartesia_key
   ```
4. **Boot it up:**
   ```bash
   python main.py
   ```

## 📜 Versioning & Git History
Just a heads up if you're looking through the commit logs: the v1.0 foundational commits go back to **November 2025**, while the massive v2.0 AGI overhaul (Swarm, TTS, Optic Nerve) hits the timeline in **April 2026**. 

## 🗺️ Roadmap (What's next?)
We are currently at roughly 32% completion of the final AGI vision. Next up on the grind:
* **Phase 6 (The Ghost in the Machine):** Integrating Picovoice Porcupine for an always-on wake word. Throwing the keyboard away permanently.
* **Phase 7 (OS Puppet Master):** Native AppleScript integration so JARVIS can control Docker containers, close Safari tabs, and manage Do Not Disturb modes natively. 
* **Phase 8 (GraphRAG):** Upgrading from semantic search to a full Knowledge Graph to map project dependencies.