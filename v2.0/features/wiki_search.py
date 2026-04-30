# PIP: wikipedia
import os
from langchain_core.tools import tool
import wikipedia

@tool
def wiki_search(query: str) -> str:
    '''Summarize a Wikipedia article for the given query. Use when you need a concise overview of a topic.'''
    try:
        summary = wikipedia.summary(query, sentences=3, auto_suggest=True, redirect=True)
        return f"SUCCESS: {summary}"
    except Exception as e:
        return f"ERROR: {str(e)}"