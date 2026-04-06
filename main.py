import streamlit as st
import os
import json
import time
import tempfile
import requests
import replicate

# Page Config
st.set_page_config(page_title="SignSpeak AI ", page_icon="👋", layout="wide")

# --- CSS Styling ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .stButton > button { background-color: #00bf72; color: white; border-radius: 8px; }
    .stAudio { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP KEYS ---
groq_key = os.environ.get("GROQ_API_KEY")
replicate_key = os.environ.get("REPLICATE_API_TOKEN")

with st.sidebar:
    st.header("🔑 Configuration")
    if not groq_key:
        groq_key = st.text_input("DATABASE API Key", type="password")
    if not replicate_key:
        replicate_key = st.text_input("Authentication API Token", type="password")

    st.divider()
    st.info("System: Replicate (Minimax) Node")

# -------------------------------
# 🎧 MODULE 1: AUDIO → TEXT
# -------------------------------
def transcribe_audio(audio_bytes):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"

        headers = {
            "Authorization": f"Bearer {groq_key}"
        }

        files = {
            "file": ("audio.wav", audio_bytes),
            "model": (None, "whisper-large-v3")
        }

        response = requests.post(url, headers=headers, files=files)
        result = response.json()

        return result.get("text", "")

    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

# -------------------------------
# 🧠 MODULE 2: TEXT → ISL LOGIC
# -------------------------------
def get_isl_instructions(text):
    system_prompt = """
    You are the SignSpeak Engine. Convert spoken English to Indian Sign Language (ISL).
    Output JSON only:
    {
      "spoken_text": "",
      "isl_gloss": "",
      "rendering_prompt": ""
    }
    """

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama3-70b-8192",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        result = response.json()

        content = result["choices"][0]["message"]["content"]

        return json.loads(content)

    except Exception as e:
        st.error(f"Reasoning Error: {e}")
        return None

# -------------------------------
# 🎥 MODULE 3: VIDEO GENERATION
# -------------------------------
def generate_video(prompt):
    if not replicate_key:
        st.warning("Replicate API Token required")
        return None

    os.environ["REPLICATE_API_TOKEN"] = replicate_key

    try:
        st.write("🎞️ Generating Video...")

        output = replicate.run(
            "minimax/video-01",
            input={
                "prompt": prompt,
                "prompt_optimizer": True
            }
        )

        return str(output)

    except Exception as e:
        st.error(f"Replicate Error: {e}")
        return None

# -------------------------------
# 🌐 MAIN UI
# -------------------------------
st.title("🗣️ SignSpeak: Replicate Edition")
st.caption("Groq Whisper + LLaMA + Minimax Video")

st.subheader("1. Voice Input")
audio_value = st.audio_input("Record your command")

if audio_value and groq_key:

    with st.spinner("🎧 Transcribing audio..."):
        transcribed_text = transcribe_audio(audio_value.read())

    if transcribed_text:
        st.success(f"You said: \"{transcribed_text}\"")

        with st.spinner("🧠 Converting to ISL..."):
            isl_data = get_isl_instructions(transcribed_text)

        if isl_data:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("2. ISL Logic")
                st.json(isl_data)
                st.info(f"GLOSS: {isl_data.get('isl_gloss')}")

            with col2:
                st.subheader("3. Video Output")
                prompt = isl_data.get("rendering_prompt")

                if st.button("🎬 Generate AI Video"):
                    video_url = generate_video(prompt)

                    if video_url:
                        st.video(video_url)
                        st.success("Video Generated Successfully!")
