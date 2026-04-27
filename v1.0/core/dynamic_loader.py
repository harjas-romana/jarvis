import os
import importlib.util
from core.telemetry import logger

class DynamicLoader:
    def __init__(self, tools_dir: str):
        self.tools_dir = tools_dir
        self.registry = {}
        self._loaded_schemas = []

    def auto_discover(self) -> list:
        """Dynamically loads Python files and extracts TOOL_SCHEMA and execute()."""
        self.registry.clear()
        self._loaded_schemas.clear()
        
        if not os.path.exists(self.tools_dir):
            return []

        for filename in sorted(os.listdir(self.tools_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                self._load_single_tool(filename)
                    
        return list(self._loaded_schemas)

    def _load_single_tool(self, filename: str) -> bool:
        """Loads a single tool file. Returns True on success."""
        module_name = filename[:-3]
        filepath = os.path.join(self.tools_dir, filename)
        
        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "TOOL_SCHEMA") and hasattr(module, "execute"):
                tool_name = module.TOOL_SCHEMA["name"]
                self.registry[tool_name] = module.execute
                schema = {"type": "function", "function": module.TOOL_SCHEMA}
                self._loaded_schemas.append(schema)
                logger.info(f"Hot-loaded tool: {tool_name}")
                return True
        except Exception as e:
            logger.error(f"Failed to load tool {filename}: {e}")
        return False

    def hot_reload(self) -> list:
        """
        Re-scans /tools/ and loads any NEW tools that aren't already in the registry.
        Returns the full updated schema list for re-binding to the LLM.
        """
        if not os.path.exists(self.tools_dir):
            return list(self._loaded_schemas)
        
        new_tools_loaded = 0
        for filename in sorted(os.listdir(self.tools_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                # Check if any schema already has this module's tool loaded
                filepath = os.path.join(self.tools_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(module_name, filepath)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, "TOOL_SCHEMA") and hasattr(module, "execute"):
                        tool_name = module.TOOL_SCHEMA["name"]
                        if tool_name not in self.registry:
                            self.registry[tool_name] = module.execute
                            schema = {"type": "function", "function": module.TOOL_SCHEMA}
                            self._loaded_schemas.append(schema)
                            new_tools_loaded += 1
                            logger.info(f"HOT-RELOAD: New tool discovered and loaded: {tool_name}")
                except Exception as e:
                    logger.error(f"Hot-reload failed for {filename}: {e}")
        
        if new_tools_loaded > 0:
            logger.info(f"HOT-RELOAD complete. {new_tools_loaded} new tool(s) added. Total: {len(self.registry)}")
        
        return list(self._loaded_schemas)
    
    def remove_tool(self, name: str) -> bool:
        """Unloads a broken tool from the live registry."""
        if name in self.registry:
            del self.registry[name]
            self._loaded_schemas = [s for s in self._loaded_schemas if s["function"]["name"] != name]
            logger.info(f"Removed tool '{name}' from registry.")
            return True
        return False

    def execute_tool(self, name: str, args: dict):
        """Fires the physical python code."""
        if name in self.registry:
            try:
                logger.info(f"Executing {name} with args: {args}")
                return self.registry[name](**args)
            except Exception as e:
                logger.error(f"Execution crashed for {name}: {e}", exc_info=True)
                return f"Tool Execution Error: {e}"
        return f"Tool '{name}' not found in registry. Available: {', '.join(self.registry.keys())}"
    
    def get_tool_count(self) -> int:
        return len(self.registry)