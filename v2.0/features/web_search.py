from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

# Initialize the free search engine
ddg_search = DuckDuckGoSearchRun()

@tool
def search_the_web(query: str) -> str:
    """
    Use this tool to search the live internet for recent news, events, or facts you do not know.
    If Harjas asks "what's new", "what happened", or asks about current events, USE THIS TOOL.
    """
    try:
        print(f"[System] Searching live internet for: {query}")
        results = ddg_search.invoke(query)
        return f"Live Web Results:\n{results}"
    except Exception as e:
        return f"Web search failed: {str(e)}"