import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PyPDF2 import PdfReader
from memory.vector_store import EpisodicMemory
from core.worker import system_2

class RAGIngestor(FileSystemEventHandler):
    def __init__(self, watch_dir):
        self.watch_dir = watch_dir
        self.memory = EpisodicMemory()

    def process_file(self, filepath, is_boot_sweep=False):
        filename = os.path.basename(filepath)
        try:
            content = ""
            if filepath.endswith((".txt", ".md", ".py", ".json")):
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
            elif filepath.endswith(".pdf"):
                reader = PdfReader(filepath)
                for page in reader.pages:
                    content += page.extract_text() + "\n"
                    
            if content:
                chunks = [content[i:i+1000] for i in range(0, len(content), 1000)]
                for i, chunk in enumerate(chunks):
                    self.memory.store_interaction("SYSTEM_DOCUMENT", f"Source: {filename} (Part {i+1})\nContent: {chunk}")
                
                # [THE FIX]: Only notify System 1 if this is a NEW file, not a boot sweep
                if not is_boot_sweep and (filename.startswith("task_") or filename.startswith("spider_")):
                    system_2.notification_queue.put("The background research task is complete and fully committed to your memory. Ask Harjas if he wants a summary or the raw text.")
                    
        except Exception as e:
            if not is_boot_sweep:
                system_2.notification_queue.put(f"My RAG ingestion system encountered an error: {str(e)}")

    def on_created(self, event):
        if event.is_directory:
            return
        time.sleep(1) # Give the OS time to finish writing the file
        self.process_file(event.src_path, is_boot_sweep=False)

def start_daemon():
    watch_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")
    os.makedirs(watch_dir, exist_ok=True)
    
    event_handler = RAGIngestor(watch_dir)
    
    print("[RAG Daemon] Sweeping existing knowledge base files silently...")
    for filename in os.listdir(watch_dir):
        filepath = os.path.join(watch_dir, filename)
        if os.path.isfile(filepath):
            event_handler.process_file(filepath, is_boot_sweep=True)
            
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=False)
    daemon_thread = threading.Thread(target=observer.start, daemon=True)
    daemon_thread.start()
    return observer