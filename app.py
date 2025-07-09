from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

app = Flask(__name__,template_folder="templates")

client = MongoClient("mongodb://localhost:27017/")
db = client.github_webhooks
collection = db.events

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/webhook',methods=['POST'])
def webhook():
    event = request.json
    event_type = request.headers.get("X-GitHub-Event","").upper()
    
    table = {
        "request_id": None,
        "author": None,
        "action": None,
        "from": None,
        "to": None,
        "timestamp": datetime.now(timezone.utc)
    }
    
    if event_type == "PUSH":
        ref = event.get("ref","")
        if ref.startswith("refs/heads/"):
            table["request_id"] = event.get("head_commit",{}).get("id") or event.get("after")
            table["author"] = event.get("pusher",{}).get("name")
            table["action"] = "PUSH"
            table["from"] = None
            table["to"] = ref.split("/")[-1]
        
    elif event_type == "PULL_REQUEST":
        pr = event.get("pull_request",{})
        action = event.get("action")
        
        if pr.get("merged") and action == "closed":
            table["request_id"] = str(pr.get("id"))
            table["author"] = pr.get("user",{}).get("login")
            table["action"] = "MERGE"
            table["from"] = pr.get("head",{}).get("ref")
            table["to"] = pr.get("base",{}).get("ref")
        
        elif action == "opened":
            table["request_id"] = str(pr.get("id"))
            table["author"] = pr.get("user",{}).get("login")
            table["action"] = "PULL_REQUEST"
            table["from"] = pr.get("head",{}).get("ref")
            table["to"] = pr.get("base",{}).get("ref")
    else:
        return jsonify({"message":"Unsupported GitHub event"}), 400
    
    result = collection.insert_one(table)
    return jsonify({"status":"stored","inserted_id":str(result.inserted_id)}), 200

@app.route('/events',methods=['GET'])
def get_events():
    since = datetime.now(timezone.utc) - timedelta(seconds = 15)
    events = list(collection.find({"timestamp":{"$gte":since}}).sort("timestamp",-1))
    for event in events:
        event['_id'] = str(event['_id'])
    return jsonify(events)