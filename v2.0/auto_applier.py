import asyncio
import json
import os
from aiohttp import web
from playwright.async_api import async_playwright

# --- CONFIGURATION ---
MAX_TABS = 30
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "my_data")
JSON_PATH = os.path.join(DATA_DIR, "quick_fill.json")
USER_DATA_DIR = os.path.join(DATA_DIR, "browser_profile") # Saves your login cookies

# State Management
app_state = {
    "queue": [],      # URLs waiting to be opened
    "active": {},     # URLs currently open {url: page_object}
    "completed": []   # URLs you submitted and closed
}

def load_profile():
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

# --- THE BRUTALIST UI ---
HTML_UI = """
<!DOCTYPE html>
<html>
<head>
    <title>CYBORG APPLIER COMMAND</title>
    <style>
        body { background: #000; color: #fff; font-family: monospace; margin: 0; padding: 20px; }
        h1 { border-bottom: 2px solid #fff; padding-bottom: 10px; text-transform: uppercase; }
        .container { display: flex; gap: 20px; }
        .panel { border: 1px solid #444; padding: 15px; flex: 1; }
        textarea { width: 100%; height: 100px; background: #111; color: #fff; border: 1px solid #666; font-family: monospace; padding: 10px; }
        button { background: #fff; color: #000; border: none; padding: 10px 20px; font-weight: bold; cursor: pointer; text-transform: uppercase; margin-top: 10px; }
        button:hover { background: #ccc; }
        .status-row { padding: 8px 0; border-bottom: 1px dashed #333; word-break: break-all; }
        .badge { display: inline-block; padding: 2px 6px; font-size: 10px; font-weight: bold; margin-right: 10px; }
        .badge.active { background: #fff; color: #000; }
        .badge.done { background: #333; color: #888; text-decoration: line-through; }
    </style>
</head>
<body>
    <h1>Cyborg Applier [HITL Protocol]</h1>
    <div class="container">
        <div class="panel">
            <h3>1. Input Target URLs</h3>
            <p>Paste job links (one per line). Amazon, Workday, Greenhouse supported.</p>
            <textarea id="urlInput"></textarea>
            <button onclick="addUrls()">Inject Queue</button>
        </div>
        <div class="panel">
            <h3>2. System Telemetry</h3>
            <p>Active Tabs: <span id="tabCount">0</span> / 30</p>
            <div id="trackerList"></div>
        </div>
    </div>

    <script>
        async function addUrls() {
            const urls = document.getElementById('urlInput').value.split('\\n').filter(u => u.trim() !== '');
            await fetch('/add', { method: 'POST', body: JSON.stringify({urls}), headers: {'Content-Type': 'application/json'} });
            document.getElementById('urlInput').value = '';
            pollState();
        }

        async function pollState() {
            const res = await fetch('/state');
            const data = await res.json();
            
            document.getElementById('tabCount').innerText = Object.keys(data.active).length;
            
            let html = '';
            // Render Active
            for (const url of Object.keys(data.active)) {
                html += `<div class="status-row"><span class="badge active">OPEN</span> ${url}</div>`;
            }
            // Render Completed
            data.completed.forEach(url => {
                html += `<div class="status-row"><span class="badge done">SUBMITTED</span> ${url}</div>`;
            });
            
            document.getElementById('trackerList').innerHTML = html;
        }

        setInterval(pollState, 2000);
        pollState();
    </script>
</body>
</html>
"""

# --- WEB SERVER ROUTES ---
async def handle_index(request):
    return web.Response(text=HTML_UI, content_type='text/html')

async def handle_add(request):
    data = await request.json()
    for url in data.get('urls', []):
        url = url.strip()
        if url and url not in app_state["queue"] and url not in app_state["active"]:
            app_state["queue"].append(url)
    return web.json_response({"status": "ok"})

async def handle_state(request):
    return web.json_response({
        "queue": app_state["queue"],
        "active": list(app_state["active"].keys()),
        "completed": app_state["completed"]
    })

# --- THE BROWSER SWARM ---
async def browser_loop():
    profile_data = load_profile()
    
    async with async_playwright() as p:
        print("\n[System] Booting Persistent Chromium Context...")
        # Persistent context saves cookies. You only log in to Workday ONCE.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 800}
        )
        
        # Universal Heuristic Script: Scans any HTML structure and injects data
        # Universal Heuristic Script: Scans any HTML structure and injects data
        injector_script = """
        (profile) => {
            console.log("JARVIS ATS Injector Armed.");
            
            // Helper to force React/Vue to recognize the input
            const triggerEvents = (el) => {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.style.border = '2px solid #00ff00'; // Green border for success
                el.style.backgroundColor = '#e6ffe6';
            };

            // 1. EXACT ATS MATCHING (Greenhouse & Lever specifics)
            const exactMap = {
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'email': profile.email,
                'phone': profile.phone,
                'job_application[first_name]': profile.first_name,
                'job_application[last_name]': profile.last_name,
                'job_application[email]': profile.email,
                'job_application[phone]': profile.phone,
                'name': profile.first_name + " " + profile.last_name, // Lever
                'urls[LinkedIn]': profile.linkedin,
                'urls[GitHub]': profile.github
            };

            for (const [key, value] of Object.entries(exactMap)) {
                // Find by ID or Name attribute
                let el = document.getElementById(key) || document.querySelector(`input[name="${key}"]`);
                if (el && el.type !== 'hidden' && !el.value) {
                    el.value = value;
                    triggerEvents(el);
                }
            }

            // 2. HEURISTIC FALLBACK (For custom questions, URLs, etc.)
            // Merge base profile with custom answers for the fallback scanner
            const heuristicMap = {
                'linkedin': profile.linkedin,
                'github': profile.github,
                'website': profile.github,
                'portfolio': profile.github,
                'university': profile.university,
                'school': profile.university,
                'grad': profile.graduation_year,
                'year': profile.graduation_year,
                ...(profile.custom_answers || {})
            };

            const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea');
            inputs.forEach(el => {
                if (el.value !== "") return; // Skip if already filled
                
                const identifier = (el.name + " " + el.id + " " + el.placeholder).toLowerCase();
                
                for (const [key, value] of Object.entries(heuristicMap)) {
                    if (identifier.includes(key.toLowerCase())) {
                        el.value = value;
                        triggerEvents(el);
                        break;
                    }
                }
            });
        }
        """

        while True:
            # 1. Enforce the 30 Tab Limit
            if len(app_state["active"]) < MAX_TABS and app_state["queue"]:
                url = app_state["queue"].pop(0)
                
                try:
                    page = await context.new_page()
                    app_state["active"][url] = page
                    print(f"[Engine] Opening and Injecting: {url}")
                    
                    await page.goto(url, wait_until="domcontentloaded")
                    await asyncio.sleep(2) # Let React hydrate
                    
                    # Fire the Universal Injector
                    await page.evaluate(injector_script, profile_data)
                    
                    # 2. Attach Event Listener: When you manually close the tab, mark it done
                    def handle_close(closed_page, closed_url=url):
                        if closed_url in app_state["active"]:
                            del app_state["active"][closed_url]
                            app_state["completed"].insert(0, closed_url) # Add to top of completed list
                            print(f"[Human-in-the-Loop] Submitted and Closed: {closed_url}")
                            
                    page.on("close", handle_close)
                    
                except Exception as e:
                    print(f"[Error] Failed to load {url}: {e}")
                    if url in app_state["active"]:
                        del app_state["active"][url]
            
            await asyncio.sleep(1) # Prevent CPU maxing

# --- EXECUTION ---
async def main():
    # Setup Web Server
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_post('/add', handle_add)
    app.router.add_get('/state', handle_state)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 8080)
    
    print("\n==============================================")
    print(" CYBORG APPLIER ONLINE")
    print(" Control Panel: http://localhost:8080")
    print("==============================================\n")
    
    # Run Web Server and Browser Loop concurrently
    await asyncio.gather(
        site.start(),
        browser_loop()
    )

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    asyncio.run(main())