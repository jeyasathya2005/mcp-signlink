import streamlit as st
import os
import json
import requests
import replicate
from replicate.client import Client # Import explicit Client
import tempfile

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide")
st.title("🗣️ SignSpeak AI (Universal)")
st.caption("🎧 Audio → 🧠 ISL → 🎥 Video")

# -------------------------------
# 🔑 API KEYS & SESSION STATE
# -------------------------------
# Use session state to store results so they don't disappear on button clicks
if "isl_data" not in st.session_state:
    st.session_state.isl_data = None
if "transcription" not in st.session_state:
    st.session_state.transcription = None

groq_key = st.secrets.get("GROQ_API_KEY", "")
replicate_token = st.secrets.get("REPLICATE_API_TOKEN", "")

with st.sidebar:
    st.header("🔑 API Config")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")
    if not replicate_token:
        replicate_token = st.text_input("Replicate Token", type="password")

    st.divider()
    MODEL_OPTIONS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
        "gemma2-9b-it"
    ]
    selected_model = st.selectbox("🧠 Select Model", MODEL_OPTIONS)

# -------------------------------
# 🎧 AUDIO → TEXT
# -------------------------------
def transcribe_audio(audio_bytes):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
            "model": (None, "whisper-large-v3")
        }
        response = requests.post(url, headers=headers, files=files)
        if response.status_code != 200:
            st.error(f"Transcription Error: {response.text}")
            return None
        return response.json().get("text", "")
    except Exception as e:
        st.error(f"Transcription Exception: {e}")
        return None

# -------------------------------
# 🧠 TEXT → ISL
# -------------------------------
def call_llm(model, messages):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {"model": model, "messages": messages, "temperature": 0.2}
    response = requests.post(url, headers=headers, json=data)
    return response.json()["choices"][0]["message"]["content"] if response.status_code == 200 else None

def get_isl(text):
    system_prompt = """Convert English to Indian Sign Language. Respond ONLY in JSON:
    {"spoken_text": "", "isl_gloss": "", "rendering_prompt": ""}"""
    
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
    
    try:
        result = call_llm(selected_model, messages)
        if result:
            result = result.strip().replace("```json", "").replace("```", "")
            return json.loads(result)
    except Exception as e:
        st.error(f"LLM Error: {e}")
    return None

# -------------------------------
# 🎥 VIDEO GENERATION (FIXED AUTH)
# -------------------------------
def generate_video(prompt, token):
    try:
        # FIX: Initialize an explicit client with the token
        client = Client(api_token=token)
        
        # Use the client instance instead of the global replicate.run
        output = client.run(
            "minimax/video-01",
            input={
                "prompt": prompt,
                "prompt_optimizer": True
            }
        )
        return output
    except Exception as e:
        st.error(f"Replicate Error: {e}")
        return None

def display_video(video_data):
    try:
        if isinstance(video_data, str) and video_data.startswith("http"):
            st.video(video_data)
        elif isinstance(video_data, list):
            st.video(video_data[0])
        elif isinstance(video_data, (bytes, bytearray)):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                tmp.write(video_data)
                st.video(tmp.name)
    except Exception as e:
        st.error(f"Display Error: {e}")

# -------------------------------
# 🎤 MAIN UI
# -------------------------------
st.subheader("🎤 Record Voice")
audio = st.audio_input("Speak something")

# Process audio only if it's new
if audio and groq_key:
    if st.session_state.transcription is None:
        with st.spinner("🎧 Transcribing..."):
            st.session_state.transcription = transcribe_audio(audio.getvalue())
        
        if st.session_state.transcription:
            with st.spinner("🧠 Converting to ISL..."):
                st.session_state.isl_data = get_isl(st.session_state.transcription)

# Display Results
if st.session_state.transcription:
    st.success(f"🗣️ You said: {st.session_state.transcription}")

    if st.session_state.isl_data:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📘 ISL Output")
            st.json(st.session_state.isl_data)
            st.info(f"GLOSS: {st.session_state.isl_data.get('isl_gloss')}")

        with col2:
            st.subheader("🎥 Video Output")
            if not replicate_token:
                st.warning("Please enter your Replicate Token in the sidebar.")
            else:
                if st.button("🎬 Generate Video"):
                    with st.spinner("🎞️ Generating video..."):
                        video_data = generate_video(
                            st.session_state.isl_data.get("rendering_prompt"),
                            replicate_token
                        )
                        if video_data:
                            display_video(video_data)
                            st.success("✅ Video Generated!")

st.divider()
st.caption("⚡ Fixed Authentication & State Handling")
