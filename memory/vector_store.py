import os
import uuid
from datetime import datetime
from core.telemetry import logger

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False


# Hardcoded baseline context — injected if the memory is empty
_USER_BASELINE = (
    "The user is Harjas Partap Singh Romana, a Software Development Engineer "
    "specializing in React, LLMs, Docker, and AWS. He is actively targeting FAANG-level roles "
    "and hits the gym regularly. He built this JARVIS system himself. "
    "He prefers concise, direct communication and values autonomy in his AI systems."
)


class VectorStore:
    def __init__(self, persist_dir: str = "./config/chroma"):
        self.persist_dir = persist_dir
        self.collection = None
        
        if CHROMA_AVAILABLE:
            try:
                os.makedirs(persist_dir, exist_ok=True)
                self.client = chromadb.PersistentClient(path=self.persist_dir)
                self.collection = self.client.get_or_create_collection(
                    name="episodic_memory",
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"VectorStore initialized. {self.collection.count()} memories on disk.")
            except Exception as e:
                logger.error(f"ChromaDB init failed: {e}")
                self.collection = None
        else:
            logger.warning("ChromaDB not installed. Episodic memory is offline.")

    def store_interaction(self, user_input: str, assistant_response: str):
        """
        Stores a conversational pair as a single document for semantic retrieval.
        Format: "User: <input> | JARVIS: <response>"
        """
        if not self.collection:
            return
        
        try:
            doc_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            # Combine both sides of the conversation into a single retrievable document
            combined = f"User: {user_input} | JARVIS: {assistant_response}"
            
            self.collection.add(
                documents=[combined],
                metadatas=[{
                    "timestamp": timestamp,
                    "user_input": user_input[:200],  # Truncate metadata to prevent bloat
                }],
                ids=[doc_id]
            )
            logger.info(f"Stored interaction to episodic memory. Total: {self.collection.count()}")
        except Exception as e:
            logger.error(f"Failed to store interaction: {e}")

    def search_memory(self, query: str, n_results: int = 1) -> dict:
        """
        Semantic similarity search against episodic memory.
        Returns tight results (default n=1) to prevent token bloat.
        """
        if not self.collection or self.collection.count() == 0:
            return {"documents": [["Memory system inactive."]]}
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )
            return results
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return {"documents": [["Memory search error."]]}

    def get_user_summary(self) -> str:
        """
        Returns the most recent user context for boot greetings and system prompts.
        Falls back to hardcoded baseline if memory is empty.
        """
        if not self.collection or self.collection.count() == 0:
            return _USER_BASELINE
        
        try:
            # Pull the 3 most recent interactions for context
            results = self.collection.get(
                limit=3,
                include=["documents", "metadatas"]
            )
            
            if results and results.get("documents"):
                docs = results["documents"]
                if docs:
                    recent_context = " | ".join(docs[-3:])
                    return f"{_USER_BASELINE} Recent activity: {recent_context[:500]}"
            
            return _USER_BASELINE
            
        except Exception as e:
            logger.error(f"get_user_summary failed: {e}")
            return _USER_BASELINE

    def get_memory_count(self) -> int:
        """Returns total number of stored memories."""
        if self.collection:
            return self.collection.count()
        return 0
