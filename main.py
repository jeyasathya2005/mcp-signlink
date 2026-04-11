import streamlit as st
import os
import json
import requests
import replicate
from replicate.client import Client
import tempfile

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide")
st.title("🗣️ SignSpeak AI (Universal)")
st.caption("🎧 Audio → 🧠 ISL → 🎥 Video")

# -------------------------------
# 🔑 SESSION STATE INITIALIZATION
# -------------------------------
if "isl_data" not in st.session_state:
    st.session_state.isl_data = None
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "video_url" not in st.session_state:
    st.session_state.video_url = None

# -------------------------------
# 🔑 SIDEBAR CONFIG
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", "")
replicate_token = st.secrets.get("REPLICATE_API_TOKEN", "")

with st.sidebar:
    st.header("🔑 API Config")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")
    if not replicate_token:
        replicate_token = st.text_input("Replicate Token", type="password")

    st.divider()
    MODEL_OPTIONS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"]
    selected_model = st.selectbox("🧠 Select Model", MODEL_OPTIONS)

# -------------------------------
# 🎧 FUNCTIONS
# -------------------------------
def transcribe_audio(audio_bytes):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav"), "model": (None, "whisper-large-v3")}
        response = requests.post(url, headers=headers, files=files)
        return response.json().get("text", "") if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

def get_isl(text):
    system_prompt = 'Convert English to Indian Sign Language. Respond ONLY in JSON: {"spoken_text": "", "isl_gloss": "", "rendering_prompt": ""}'
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {"model": selected_model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}], "temperature": 0.2}
    try:
        response = requests.post(url, headers=headers, json=data)
        res_text = response.json()["choices"][0]["message"]["content"]
        return json.loads(res_text.strip().replace("```json", "").replace("```", ""))
    except Exception as e:
        st.error(f"LLM Error: {e}")
        return None

def generate_video(prompt, token):
    try:
        client = Client(api_token=token)
        # minimax/video-01 returns a URL or a generator yielding a URL
        output = client.run("minimax/video-01", input={"prompt": prompt, "prompt_optimizer": True})
        
        # Ensure we get the actual URL string
        if isinstance(output, list):
            return output[0]
        return output
    except Exception as e:
        st.error(f"Replicate Error: {e}")
        return None

# -------------------------------
# 🎤 MAIN UI
# -------------------------------
st.subheader("🎤 Record Voice")
audio = st.audio_input("Speak something")

# Clear state if a NEW audio is recorded
if audio:
    audio_bytes = audio.getvalue()
    if st.session_state.transcription is None:
        with st.spinner("🎧 Transcribing..."):
            st.session_state.transcription = transcribe_audio(audio_bytes)
        if st.session_state.transcription:
            with st.spinner("🧠 Converting to ISL..."):
                st.session_state.isl_data = get_isl(st.session_state.transcription)

# --- DISPLAY AREA ---
if st.session_state.transcription:
    st.success(f"🗣️ You said: {st.session_state.transcription}")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📘 ISL Output")
        if st.session_state.isl_data:
            st.json(st.session_state.isl_data)
            st.info(f"GLOSS: {st.session_state.isl_data.get('isl_gloss')}")

    with col2:
        st.subheader("🎥 Video Output")
        
        # 1. Video Generation Button
        if st.button("🎬 Generate Video"):
            if not replicate_token:
                st.error("Please enter Replicate Token in sidebar.")
            else:
                with st.spinner("🎞️ Generating video (usually takes 30-60s)..."):
                    video_res = generate_video(st.session_state.isl_data.get("rendering_prompt"), replicate_token)
                    if video_res:
                        st.session_state.video_url = video_res # Save to state!
                    else:
                        st.error("Generation failed. Check your Replicate balance/token.")

        # 2. Permanent Video Display (Visible after generation)
        if st.session_state.video_url:
            st.video(st.session_state.video_url)
            st.success("✅ Video Ready!")
            st.write(f"[Direct Video Link]({st.session_state.video_url})")

st.divider()
st.caption("⚡ Fixed Video Persistence and State Management")
