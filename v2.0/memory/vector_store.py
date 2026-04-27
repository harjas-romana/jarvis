import os
import chromadb
from chromadb.config import Settings
from datetime import datetime

class EpisodicMemory:
    def __init__(self):
        # Isolate the database storage strictly to the memory folder
        self.persist_directory = os.path.join(os.path.dirname(__file__), "chroma_db")
        os.makedirs(self.persist_directory, exist_ok=True)
        
        try:
            # Initialize persistent local ChromaDB
            self.client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # HNSW Cosine Similarity for flawless semantic matching
            self.collection = self.client.get_or_create_collection(
                name="jarvis_episodic_memory",
                metadata={"hnsw:space": "cosine"} 
            )
        except Exception as e:
            print(f"\n[Memory Error] Failed to initialize VectorDB: {e}")
            self.collection = None

    def store_interaction(self, role: str, content: str):
        """Embeds and stores a conversational turn into long-term memory."""
        if not self.collection or not content.strip():
            return
            
        try:
            timestamp = datetime.now().isoformat()
            doc_id = f"{role}_{timestamp}"
            
            self.collection.add(
                documents=[content],
                metadatas=[{"role": role, "timestamp": timestamp}],
                ids=[doc_id]
            )
        except Exception as e:
            pass # Silently fail on storage error to prevent crashing the main loop

    def search_memory(self, query: str, n_results: int = 3) -> str:
        """Searches the vector database and applies a Time-Decay algorithm to prioritize recent context."""
        if not self.collection:
            return ""
            
        try:
            count = self.collection.count()
            if count == 0:
                return ""
                
            # Fetch a larger pool to allow for time-based re-ranking
            fetch_count = min(10, count) 
            
            results = self.collection.query(
                query_texts=[query],
                n_results=fetch_count,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results or not results["documents"][0]:
                return ""

            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0] # Lower distance = higher semantic similarity
            
            # [TIME-DECAY ALGORITHM]
            scored_memories = []
            now = datetime.now()
            
            for doc, meta, distance in zip(docs, metas, distances):
                try:
                    mem_time = datetime.fromisoformat(meta.get("timestamp", now.isoformat()))
                    hours_old = (now - mem_time).total_seconds() / 3600.0
                    
                    # Decay Penalty: Add 0.05 to the distance for every 24 hours of age
                    # This artificially pushes older memories lower down the rank
                    time_penalty = (hours_old / 24.0) * 0.05 
                    final_score = distance + time_penalty
                    
                    scored_memories.append((final_score, doc, meta))
                except Exception:
                    # Fallback if timestamp parsing fails
                    scored_memories.append((distance, doc, meta))
                    
            # Sort by the new time-weighted score (lowest is best)
            scored_memories.sort(key=lambda x: x[0])
            
            # Take the top N results after time-decay re-ranking
            top_memories = scored_memories[:n_results]
            
            context_str = "RELEVANT PAST MEMORIES (Sorted by Relevance & Recency):\n"
            for _, doc, meta in top_memories:
                role = meta.get("role", "unknown").upper()
                time_str = meta.get("timestamp", "").split("T")[0] 
                context_str += f"- [{time_str}] {role}: {doc}\n"
                
            return context_str
            
        except Exception as e:
            return ""