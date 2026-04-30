# import time
# import threading
# import random
# import os
# from datetime import datetime
# from langchain_groq import ChatGroq
# from langchain_core.messages import HumanMessage, SystemMessage
# from core.vision import capture_screen_base64

# class ProactiveHeartbeat:
#     def __init__(self, brain, voice, console, base_interval=60):
#         self.brain = brain
#         self.voice = voice
#         self.console = console
#         self.base_interval = base_interval
#         self.running = False
#         self.last_interaction = time.time()
#         self.is_interacting = False 
        
#         # [NEW]: Dedicated Vision Cortex
#         self.vision_llm = ChatGroq(
#             api_key=os.getenv("GROQ_API_KEY"), 
#             model="meta-llama/llama-4-scout-17b-16e-instruct", 
#             temperature=0.4
#         )

#     def reset_timer(self):
#         self.last_interaction = time.time()
        
#     def set_interacting(self, state: bool):
#         self.is_interacting = state

#     def start(self):
#         self.running = True
#         threading.Thread(target=self._loop, daemon=True).start()

#     def _loop(self):
#         while self.running:
#             target_wait = random.randint(self.base_interval, int(self.base_interval * 2.5))
#             time.sleep(5) 
            
#             if not self.running:
#                 break
                
#             if self.is_interacting:
#                 self.reset_timer()
#                 continue
                
#             time_since_last = time.time() - self.last_interaction
            
#             if time_since_last >= target_wait:
#                 try:
#                     # 1. Fire the Optic Nerve
#                     base64_image = capture_screen_base64()
#                     now = datetime.now().strftime("%I:%M %p")
                    
#                     # 2. Frame the Directive
#                     system_rules = "You are JARVIS. Speak in 1-2 sentences max. Address the user as 'Sir' or 'Harjas'. Use Cartesia XML emotion tags like <emotion value='curious'/>."
                    
#                     prompt = (
#                         f"[INTERNAL SYSTEM DIRECTIVE]: It is currently {now}. Look at the attached screenshot of Harjas's screen. "
#                         f"Generate a spontaneous, highly natural check-in based EXACTLY on what he is doing. "
#                         f"Do NOT say 'I see you are looking at...'. Just smoothly bring up the topic on the screen."
#                     )
                    
#                     # 3. Multimodal Payload
#                     messages = [
#                         SystemMessage(content=system_rules),
#                         HumanMessage(content=[
#                             {"type": "text", "text": prompt},
#                             {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
#                         ])
#                     ]
                    
#                     # 4. Process and Speak
#                     response = self.vision_llm.invoke(messages)
#                     raw_text = response.content.strip()
                    
#                     # Clean the tags for the terminal display
#                     from main import clean_for_terminal
#                     display_text = clean_for_terminal(raw_text)
                    
#                     self.console.print(f"\n\n[bold green]JARVIS (Vision):[/bold green] {display_text}")
#                     self.voice.speak(raw_text)
#                     self.console.print("\n[bold cyan]Harjas:[/bold cyan] ", end="")
                    
#                     self.reset_timer()
#                 except Exception as e:
#                     # [DEBUG FIX]: Stop failing silently so we can see the crash
#                     self.console.print(f"\n[dim red][Vision Cortex Error]: {str(e)}[/dim red]")
#                     self.console.print("\n[bold cyan]Harjas:[/bold cyan] ", end="")
#                     self.reset_timer()


import time
import threading
import random
import os
from datetime import datetime
from openai import OpenAI # Swapped to standard OpenAI client for LM Studio
from core.vision import capture_screen_base64

class ProactiveHeartbeat:
    def __init__(self, brain, voice, console, base_interval=60):
        self.brain = brain
        self.voice = voice
        self.console = console
        self.base_interval = base_interval
        self.running = False
        self.last_interaction = time.time()
        self.is_interacting = False 
        
        # [THE EDGE VISION CORTEX]: 100% Offline and Private. 
        # Pointing strictly to your local LM Studio instance.
        self.vision_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

    def reset_timer(self):
        self.last_interaction = time.time()
        
    def set_interacting(self, state: bool):
        self.is_interacting = state

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _loop(self):
        while self.running:
            target_wait = random.randint(self.base_interval, int(self.base_interval * 2.5))
            time.sleep(5) 
            
            if not self.running:
                break
                
            if self.is_interacting:
                self.reset_timer()
                continue
                
            time_since_last = time.time() - self.last_interaction
            
            if time_since_last >= target_wait:
                try:
                    # 1. Fire the Local Optic Nerve
                    base64_image = capture_screen_base64()
                    now = datetime.now().strftime("%I:%M %p")
                    
                    system_rules = "You are JARVIS. Speak in 1-2 sentences max. Address the user as 'Sir' or 'Mr. Harjas'. Use Cartesia XML emotion tags like <emotion value='curious'/>."
                    prompt = (
                        f"[INTERNAL SYSTEM DIRECTIVE]: It is currently {now}. Look at the attached screenshot of Harjas's screen. "
                        f"Generate a spontaneous, highly natural check-in based EXACTLY on what he is doing. "
                        f"Do NOT say 'I see you are looking at...'. Just smoothly bring up the topic on the screen."
                    )
                    
                    # 2. Process locally via LM Studio
                    response = self.vision_client.chat.completions.create(
                        model="glm-4.6v-flash", # Explicitly target the loaded vision model
                        messages=[
                            {"role": "system", "content": system_rules},
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                                ]
                            }
                        ],
                        max_tokens=100,
                        temperature=0.4
                    )
                    
                    raw_text = response.choices[0].message.content.strip()
                    
                    # Clean the tags for the terminal display
                    from main import clean_for_terminal
                    display_text = clean_for_terminal(raw_text)
                    
                    self.console.print(f"\n\n[bold green]JARVIS (Heartbeat):[/bold green] {display_text}")
                    self.voice.speak(raw_text)
                    self.console.print("\n[bold cyan]Harjas:[/bold cyan] ", end="")
                    
                    self.reset_timer()
                except Exception as e:
                    self.console.print(f"\n[dim red][Vision Cortex Error]: {str(e)}[/dim red]")
                    self.console.print("\n[bold cyan]Harjas:[/bold cyan] ", end="")
                    self.reset_timer()