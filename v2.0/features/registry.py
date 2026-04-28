import os
import importlib
from langchain_core.tools import BaseTool

def load_all_tools():
    """Dynamically sweeps the features directory and safely loads unique LangChain tools."""
    tools_dict = {} # Use a dictionary to prevent duplicate tool registrations by name
    features_dir = os.path.dirname(__file__)
    
    for filename in os.listdir(features_dir):
        if filename.endswith(".py") and filename not in ["__init__.py", "registry.py"]:
            module_name = filename[:-3]
            try:
                # Import the module dynamically
                module = importlib.import_module(f"features.{module_name}")
                
                # Scan for any object that inherits from BaseTool (the @tool decorator)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, BaseTool):
                        # Add to dictionary, using the tool's name as the unique key
                        tools_dict[attr.name] = attr
                        
            except Exception as e:
                print(f"[Registry Error] Failed to load module {module_name}: {e}")
                
    # Return as a flat list for LangChain
    return list(tools_dict.values())