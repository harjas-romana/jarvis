import subprocess
import json

TOOL_SCHEMA = {
    "name": "web_search",
    "description": "Searches the web for current information using DuckDuckGo. Use this for questions about current events, weather, facts, or anything requiring up-to-date knowledge.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query (e.g. 'weather in Chandigarh today', 'latest iPhone price')"
            }
        },
        "required": ["query"]
    }
}

def execute(query: str) -> str:
    """Searches the web via DuckDuckGo Instant Answer API and curl."""
    try:
        # DuckDuckGo Instant Answer API (free, no key required)
        url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
        
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "10", url],
            capture_output=True, text=True, timeout=15
        )
        
        if result.returncode != 0:
            return f"Web search failed: could not reach DuckDuckGo."
        
        data = json.loads(result.stdout)
        
        # Extract the best available answer
        parts = []
        
        # Abstract (direct answer)
        if data.get("Abstract"):
            parts.append(f"Summary: {data['Abstract']}")
            if data.get("AbstractSource"):
                parts.append(f"Source: {data['AbstractSource']}")
                
        # Answer (computational / factual)
        if data.get("Answer"):
            parts.append(f"Answer: {data['Answer']}")
            
        # Related topics (fallback)
        if not parts and data.get("RelatedTopics"):
            for topic in data["RelatedTopics"][:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    parts.append(f"- {topic['Text'][:200]}")
        
        if parts:
            return "\n".join(parts)
        
        # If DuckDuckGo API gave nothing, try a basic curl scrape of lite.duckduckgo.com
        lite_result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "10", 
             f"https://lite.duckduckgo.com/lite/?q={query.replace(' ', '+')}"],
            capture_output=True, text=True, timeout=15
        )
        
        if lite_result.stdout:
            # Extract text between result snippets (crude but functional)
            from html.parser import HTMLParser
            
            class SnippetParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.snippets = []
                    self.in_snippet = False
                    
                def handle_starttag(self, tag, attrs):
                    for attr in attrs:
                        if attr == ("class", "result-snippet"):
                            self.in_snippet = True
                            
                def handle_data(self, data):
                    if self.in_snippet:
                        self.snippets.append(data.strip())
                        self.in_snippet = False
            
            parser = SnippetParser()
            parser.feed(lite_result.stdout)
            
            if parser.snippets:
                return "Web results:\n" + "\n".join([f"- {s}" for s in parser.snippets[:3]])
        
        return f"No clear results found for '{query}'. The query may be too specific or DuckDuckGo had no instant answer."
        
    except json.JSONDecodeError:
        return "Web search returned invalid data."
    except subprocess.TimeoutExpired:
        return "Web search timed out."
    except Exception as e:
        return f"Web search error: {str(e)}"
