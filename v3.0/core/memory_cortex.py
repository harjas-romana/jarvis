import os
import uuid
import chromadb
from chromadb.utils import embedding_functions

class MemoryCortex:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "jarvis_memory")
        os.makedirs(self.db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="core_memories",
            embedding_function=self.ef
        )

    def store_fact(self, fact_text: str, category: str = "general"):
        memory_id = str(uuid.uuid4())
        self.collection.add(
            documents=[fact_text],
            metadatas=[{"category": category}],
            ids=[memory_id]
        )

    def recall(self, query: str, n_results: int = 3) -> list:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count())
        )
        if results and results['documents']:
            return results['documents'][0]
        return []