import os
import feedparser
from datetime import datetime

class WebSpider:
    def __init__(self):
        # ArXiv Artificial Intelligence & HackerNews feeds
        self.feeds = {
            "ArXiv_AI": "http://export.arxiv.org/rss/cs.AI",
            "HackerNews": "https://hnrss.org/frontpage?points=100" # Only top tier posts
        }
        
        # Point to the existing RAG knowledge base
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.kb_dir = os.path.join(root_dir, "knowledge_base")
        os.makedirs(self.kb_dir, exist_ok=True)

    def scrape_and_store(self):
        print("[System 3 Spider] Waking up. Initiating data sweep...")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        for source, url in self.feeds.items():
            try:
                print(f"[System 3 Spider] Parsing {source}...")
                feed = feedparser.parse(url)
                
                content = f"SYSTEM 3 DAILY BRIEFING\nSource: {source}\nDate: {today_str}\n\n"
                
                # Grab the top 5 entries from each feed to keep the DB clean
                for entry in feed.entries[:5]:
                    content += f"TITLE: {entry.title}\n"
                    # Clean up basic HTML tags often found in descriptions
                    clean_desc = entry.description.replace("<p>", "").replace("</p>", "\n")
                    content += f"SUMMARY: {clean_desc}\n"
                    content += f"LINK: {entry.link}\n"
                    content += "-" * 40 + "\n"
                
                # Drop it into the Knowledge Base
                filename = f"spider_{source}_{today_str}.txt"
                filepath = os.path.join(self.kb_dir, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                    
                print(f"[System 3 Spider] Successfully dropped {filename} for RAG ingestion.")
                
            except Exception as e:
                print(f"[System 3 Spider] Failed to scrape {source}: {e}")

if __name__ == "__main__":
    # When run via CRON or terminal, execute the sweep
    spider = WebSpider()
    spider.scrape_and_store()