import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


import json
from datetime import datetime
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from memory.vector_store import EpisodicMemory

class ReflectionDaemon:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.llm = ChatGroq(
            api_key=self.api_key,
            model="llama-3.3-70b-versatile",
            temperature=0.2, # Low temp for analytical extraction
        )
        self.memory = EpisodicMemory()
        
        # We will save the consolidated facts directly into the RAG folder
        # so the ingestor picks it up automatically!
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.identity_file = os.path.join(root_dir, "knowledge_base", "core_identity.txt")

    def run_reflection(self):
        print("\n[Reflection Daemon] Initiating memory consolidation...")
        if not self.memory.collection:
            return

        try:
            # Fetch the most recent 50 interactions
            results = self.memory.collection.get(
                limit=50,
                include=["documents", "metadatas"]
            )
            
            if not results or not results["documents"]:
                print("[Reflection Daemon] Not enough data to reflect on.")
                return

            raw_logs = ""
            for doc, meta in zip(results["documents"], results["metadatas"]):
                role = meta.get("role", "unknown")
                raw_logs += f"{role.upper()}: {doc}\n"

            system_prompt = SystemMessage(content="""
            You are JARVIS's background analytical engine. 
            Review the provided conversation logs between JARVIS and Harjas.
            Extract permanent, updated facts about Harjas (preferences, current projects, ongoing routines, hardware setup).
            Output ONLY a concise bulleted list of core facts. Do not include temporary greetings or irrelevant chatter.
            """)
            
            response = self.llm.invoke([
                system_prompt,
                HumanMessage(content=f"LOGS:\n{raw_logs}")
            ])
            
            new_facts = response.content.strip()
            
            # Save the facts to the knowledge base
            with open(self.identity_file, "w") as f:
                f.write(f"USER CORE IDENTITY & PREFERENCES (Last Updated: {datetime.now().strftime('%Y-%m-%d')})\n\n")
                f.write(new_facts)
                
            print(f"[Reflection Daemon] Memory consolidated. Identity file updated.")
            
        except Exception as e:
            print(f"[Reflection Daemon] Consolidation failed: {e}")

if __name__ == "__main__":
    # You can trigger this manually, or run it via a cron job
    daemon = ReflectionDaemon()
    daemon.run_reflection()