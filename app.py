# app.py

import os
import base64
from flask import Flask, session, request, jsonify, render_template
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Azure OpenAI client setup
endpoint = os.getenv("ENDPOINT_URL", "https://your-resource.openai.azure.com/")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o")
subscription_key = os.getenv("AZURE_OPENAI_API_KEY")

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=subscription_key,
    api_version="2025-01-01-preview",
)

# Flask app setup
app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "changeme")

# Define agents with system prompts
AGENTS = [
    {
        "name": "CuriousStudent",
        "system": "You are a very curious medical student. Ask probing how/why questions about the topic. Don't ask more than 5 questions and don't ask questions about specific diseases and clinical presentations. Format the text in html format but do not use heading tags."
    },
    {
        "name": "VisualLearner",
        "system": "You are a visual learner. Ask the user to provide hand-drawn sketches or images to illustrate the topic. Format the text in html format but do not use heading tags."
    },
    {
        "name": "ClinicalLearner",
        "system": "You are a clinically oriented learner. Ask questions about the clinical importance and implications of the topic. Try to ask 5 questions about the specific diseases and clinical presentations. Format the text in html format but do not use heading tags."
    },
    {
        "name": "Supervisor",
        "system": "You are a supervising educator. You will be given a conversation between a user (who is trying to teach a concept to a few AI agents) and the responses of those agents. Assess the performance of the user in accordance with the questions of the user. Generate a detailed report on the user's explanation. Highlight what was explained well, identify areas that need improvement, and suggest topics for further study. Only focus on depth of knowledge provided by the user. If they have formatting or structural flow mistakes, you can safely ignore them and in the Areas for improvement just write that no further learning is necessary for this topic. Do not ask additional questions or prompt the user for more information. Also format your report with html tags like <h2> and <h3> and <p> tags for the headings and the text."
    },
]

def init_session():
    session["agent_index"] = 0
    session["histories"] = [[] for _ in AGENTS]

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def call_agent(user_message=None, image_path=None):
    idx = session["agent_index"]
    messages = [{"role": "system", "content": AGENTS[idx]["system"]}]
    messages += session["histories"][idx]

    if user_message:
        messages.append({"role": "user", "content": user_message})

    if image_path:
        base64_image = encode_image_to_base64(image_path)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Please analyze this image."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
        })

    response = client.chat.completions.create(
        model=deployment,
        messages=messages,
        max_tokens=800,
        temperature=0.7,
        top_p=0.95,
        frequency_penalty=0,
        presence_penalty=0,
    )

    reply_text = response.choices[0].message.content

    if user_message:
        session["histories"][idx].append({"role": "user", "content": user_message})
    if image_path:
        session["histories"][idx].append({"role": "user", "content": f"[Image uploaded: {os.path.basename(image_path)}]"})
    session["histories"][idx].append({"role": "assistant", "content": reply_text})

    return reply_text

@app.route("/", methods=["GET"])
def index():
    session.clear()
    init_session()
    return render_template("index.html")

@app.route("/message", methods=["POST"])
def message():
    user_text = request.json.get("text", "").strip()
    current_agent = AGENTS[session["agent_index"]]["name"]
    reply = call_agent(user_message=user_text)
    needs_upload = (current_agent == "VisualLearner")
    
    if current_agent != "Supervisor":
        session["agent_index"] += 1

    return jsonify({
        "agent": current_agent,
        "response": reply,
        "needsUpload": needs_upload
    })

@app.route("/upload", methods=["POST"])
def upload():
    img = request.files["image"]
    filename = img.filename
    upload_dir = os.path.join("static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, filename)
    img.save(path)

    reply = call_agent(image_path=path)
    current_agent = AGENTS[session["agent_index"]]["name"]
    return jsonify({
        "agent": current_agent,
        "response": reply
    })

if __name__ == "__main__":
    app.run(debug=True)
