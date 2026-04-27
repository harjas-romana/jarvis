import os
import time
import multiprocessing
from datetime import datetime
from langchain_groq import ChatGroq
from swarm.coder import run_autonomous_coder

def system_2_worker_loop(task_queue, notification_queue):
    api_key = os.getenv("GROQ_API_KEY")
    llm = ChatGroq(api_key=api_key, model="llama-3.3-70b-versatile", temperature=0.2)
    
    while True:
        try:
            task = task_queue.get()
            if task is None:
                break
                
            task_id = task.get("id")
            task_type = task.get("type")
            payload = task.get("payload")

            if task_type == "code_project":
                result = run_autonomous_coder(payload)
            else:
                prompt = f"Act as an expert technical researcher. Harjas requested this deep dive: '{payload}'. Write a highly detailed, comprehensive technical report."
                response = llm.invoke(prompt)
                result = response.content
            
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            kb_dir = os.path.join(root_dir, "knowledge_base")
            os.makedirs(kb_dir, exist_ok=True)
            output_file = os.path.join(kb_dir, f"task_{task_id}.txt")
            
            with open(output_file, "w") as f:
                f.write(f"SYSTEM 2 TASK REPORT\nTask Type: {task_type}\nTimestamp: {datetime.now().isoformat()}\n\n{result}")
                
        except Exception as e:
            # Send the error to System 1's brain
            notification_queue.put(f"My background worker encountered a critical error: {str(e)}")

class BackgroundManager:
    def __init__(self):
        self.task_queue = multiprocessing.Queue()
        self.notification_queue = multiprocessing.Queue() 
        self.worker_process = multiprocessing.Process(
            target=system_2_worker_loop, 
            args=(self.task_queue, self.notification_queue),
            daemon=True 
        )
        
    def start(self):
        self.worker_process.start()
        
    def submit_task(self, task_type: str, payload: str):
        task_id = int(time.time())
        self.task_queue.put({"id": task_id, "type": task_type, "payload": payload})
        return task_id

system_2 = BackgroundManager()