import os
import logging
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from core.engine import CognitiveEngine

# Disable Flask's default verbose logging to keep your terminal clean
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

print("\n[System] Booting Cognitive Matrix for Web...")
brain = CognitiveEngine()

@app.route('/ask', methods=['POST'])
def ask_jarvis():
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "No query provided"}), 400
        
    user_input = data['query']
    print(f"\n[iPhone] Harjas: {user_input}")
    
    try:
        # Route the iPhone's text through the exact same 70B brain and memory
        response = brain.process(user_input)
        print(f"[JARVIS] {response}")
        
        return jsonify({"response": response}), 200
    except Exception as e:
        print(f"[API Error] {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("[System] JARVIS Mobile Gateway Online. Listening on port 5001.")
    app.run(host='0.0.0.0', port=5001)