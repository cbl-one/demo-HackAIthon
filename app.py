# app.py
import os
from flask import Flask, session, request, jsonify, render_template
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# --- Azure OpenAI client setup
endpoint         = os.getenv("ENDPOINT_URL", "https://your-resource.openai.azure.com/")
deployment       = os.getenv("DEPLOYMENT_NAME", "gpt-4o")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2025-01-01-preview",
)

# --- Flask app
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")

# --- Define our four agents' system prompts
AGENTS = [
    {
        "name": "CuriousStudent",
        "system": "You are a very curious medical student. Ask probing how/why questions about the topic. Don't ask more than 5 questions and don't ask questions related to clincal features and diseases."
    },
    {
        "name": "VisualLearner",
        "system": "You are a visual learner. Ask the user to provide hand-drawn sketches or images to illustrate the topic."
    },
    {
        "name": "ClinicalLearner",
        "system": "You are a clinically oriented learner. Ask questions about the clinical importance and implications of the topic."
    },
    {
        "name": "Supervisor",
        "system": "You are a supervising educator. Generate a detailed report on what the user explained well, gaps, and study tips."
    },
]

def init_session():
    session["agent_index"] = 0
    session["histories"] = [[] for _ in AGENTS]

def call_agent(user_message):
    idx = session["agent_index"]
    # build the messages list
    msgs = [{"role": "system", "content": AGENTS[idx]["system"]}]
    # include this agent's past history
    msgs += session["histories"][idx]
    # add the new user message
    msgs.append({"role": "user", "content": user_message})
    # call Azure OpenAI
    resp = client.chat.completions.create(
        model=deployment,
        messages=msgs,
        max_tokens=800,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
    )
    text = resp.choices[0].message.content
    # update history
    session["histories"][idx].append({"role": "user", "content": user_message})
    session["histories"][idx].append({"role": "assistant", "content": text})
    return text

@app.route("/", methods=["GET"])
def index():
    session.clear()
    init_session()
    return render_template("index.html")

@app.route("/message", methods=["POST"])
def message():
    user_text = request.json.get("text", "").strip()
    reply = call_agent(user_text)
    current = AGENTS[session["agent_index"]]["name"]
    needs_upload = (current == "VisualLearner")
    # if the agent signaled it's done with its questions, advance
    # e.g. check for a sentinel like "[DONE]" in reply or have front-end button
    # For simplicity, we'll advance after each round automatically:
    session["agent_index"] = min(session["agent_index"] + 1, len(AGENTS) - 1)
    return jsonify({
        "agent":       current,
        "response":    reply,
        "needsUpload": needs_upload
    })

@app.route("/upload", methods=["POST"])
def upload():
    img = request.files["image"]
    fn = img.filename
    path = os.path.join("static", "uploads", fn)
    img.save(path)
    # feed image markdown back into the same agent
    md = f"![](uploads/{fn})"
    reply = call_agent(md)
    return jsonify({
        "agent":    AGENTS[session["agent_index"]]["name"],
        "response": reply
    })

if __name__ == "__main__":
    app.run(debug=True)
