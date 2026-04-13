import streamlit as st
import os
import json
import requests
import replicate
from replicate.client import Client
import time

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
    MODEL_OPTIONS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    selected_model = st.selectbox("🧠 Select Model", MODEL_OPTIONS)
    
    if st.button("🗑️ Clear Cache"):
        st.session_state.transcription = None
        st.session_state.isl_data = None
        st.session_state.video_url = None
        st.rerun()

# -------------------------------
# 🎧 FUNCTIONS
# -------------------------------
def transcribe_audio(audio_bytes):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}
        files = {"file": ("audio.wav", audio_bytes, "audio/wav"), "model": (None, "whisper-large-v3")}
        response = requests.post(url, headers=headers, files=files)
        if response.status_code == 200:
            return response.json().get("text", "")
        return None
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

def get_isl(text):
    # Updated system prompt to ensure the video model gets a RICH visual description
    system_prompt = (
        "Convert English to Indian Sign Language (ISL). "
        "Respond ONLY in JSON format: "
        "{"
        "\"spoken_text\": \"original text\","
        "\"isl_gloss\": \"UPPERCASE GLOSS SYMBOLS\","
        "\"rendering_prompt\": \"A high-quality video of a person performing Indian Sign Language for: [Describe the movement in detail here]\""
        "}"
    )
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {
        "model": selected_model, 
        "messages": [
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": f"Convert this to ISL: {text}"}
        ], 
        "temperature": 0.2
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        res_text = response.json()["choices"][0]["message"]["content"]
        # Clean potential markdown
        clean_json = res_text.strip().replace("```json", "").replace("```", "")
        return json.loads(clean_json)
    except Exception as e:
        st.error(f"LLM Error: {e}")
        return None

def generate_video(prompt, token):
    try:
        client = Client(api_token=token)
        # We use a more descriptive prompt structure for Minimax
        full_prompt = f"{prompt}. High quality, 4k, realistic person, neutral background, clear hand gestures."
        
        output = client.run(
            "minimax/video-01",
            input={
                "prompt": full_prompt,
                "prompt_optimizer": True
            }
        )
        
        # Minimax returns a URL string or a list containing the URL
        if isinstance(output, list):
            return output[0]
        return output
    except Exception as e:
        st.error(f"Replicate Error: {e}")
        return None

# -------------------------------
# 🎤 MAIN UI
# -------------------------------
st.subheader("🎤 Step 1: Record Voice")
audio = st.audio_input("Speak something")

# Logic: If new audio is detected and we haven't processed it yet
if audio:
    # Check if this audio is different from what we processed
    current_audio_bytes = audio.getvalue()
    
    if st.session_state.transcription is None:
        with st.spinner("🎧 Transcribing..."):
            st.session_state.transcription = transcribe_audio(current_audio_bytes)
        
        if st.session_state.transcription:
            with st.spinner("🧠 Converting to ISL Gloss..."):
                st.session_state.isl_data = get_isl(st.session_state.transcription)
            st.rerun()

# --- DISPLAY AREA ---
if st.session_state.transcription:
    st.info(f"🗣️ **You said:** {st.session_state.transcription}")

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📘 ISL Interpretation")
        if st.session_state.isl_data:
            st.success(f"**ISL Gloss:** {st.session_state.isl_data.get('isl_gloss')}")
            with st.expander("View Raw JSON Data"):
                st.json(st.session_state.isl_data)

    with col2:
        st.subheader("🎥 Video Generation")
        
        # Generate Video Button
        if st.button("🎬 Generate Sign Language Video"):
            if not replicate_token:
                st.error("Please enter Replicate Token in sidebar.")
            else:
                with st.spinner("🎞️ Generating video (Takes ~60 seconds)..."):
                    video_res = generate_video(
                        st.session_state.isl_data.get("rendering_prompt"), 
                        replicate_token
                    )
                    if video_res:
                        st.session_state.video_url = video_res
                        st.success("Video Generated Successfully!")
                    else:
                        st.error("Failed to generate video.")

        # Persistent Video Display
        if st.session_state.video_url:
            st.video(st.session_state.video_url)
            st.write(f"🔗 [Download / Direct Link]({st.session_state.video_url})")

st.divider()
st.caption("⚡ Hint: If the video is too short, try speaking a longer sentence. The AI generates based on the visual prompt length.")
