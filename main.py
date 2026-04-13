import streamlit as st
import json
import requests
from replicate.client import Client

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide")
st.title("🗣️ SignSpeak AI: Audio → ISL → Visual")
st.caption("🎧 Speech → 🧠 ISL Gloss → 🖼️ AI Visual")

# -------------------------------
# 🔑 SESSION STATE
# -------------------------------
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "isl_data" not in st.session_state:
    st.session_state.isl_data = None
if "image_url" not in st.session_state:
    st.session_state.image_url = None

# -------------------------------
# 🔑 API KEYS (Secrets or Input)
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", "")
replicate_token = st.secrets.get("REPLICATE_API_TOKEN", "")

with st.sidebar:
    st.header("🔑 API Keys")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")
    if not replicate_token:
        replicate_token = st.text_input("Replicate Token", type="password")

    if st.button("🔄 Reset"):
        st.session_state.clear()
        st.rerun()

# -------------------------------
# 🎤 TRANSCRIBE
# -------------------------------
def transcribe_audio(audio_bytes):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}

        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
            "model": (None, "whisper-large-v3")
        }

        res = requests.post(url, headers=headers, files=files)
        return res.json().get("text", "")

    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

# -------------------------------
# 🧠 ISL TRANSLATION
# -------------------------------
def get_isl_translation(text):
    try:
        system_prompt = (
            "Convert English to Indian Sign Language (ISL). "
            "Return JSON: {\"gloss\": \"...\", \"visual_description\": \"...\"}"
        )

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "response_format": {"type": "json_object"}
        }

        res = requests.post(url, headers=headers, json=data)
        return json.loads(res.json()["choices"][0]["message"]["content"])

    except Exception as e:
        st.error(f"ISL Error: {e}")
        return None

# -------------------------------
# 🖼️ GENERATE IMAGE (RELIABLE)
# -------------------------------
def generate_visual(prompt):
    try:
        client = Client(api_token=replicate_token)

        output = client.run(
            "stability-ai/sdxl",
            input={
                "prompt": f"A person performing Indian Sign Language: {prompt}, clear hands, front view",
                "width": 768,
                "height": 768
            }
        )

        if isinstance(output, list):
            return output[0]
        return output

    except Exception as e:
        st.error(f"Generation Error: {e}")
        return None

# -------------------------------
# 🎤 INPUT
# -------------------------------
st.subheader("🎤 Record Audio")
audio = st.audio_input("Speak something")

if audio and not st.session_state.transcription:
    with st.spinner("🎧 Transcribing..."):
        text = transcribe_audio(audio.getvalue())

        if text:
            st.session_state.transcription = text

            with st.spinner("🧠 Translating to ISL..."):
                st.session_state.isl_data = get_isl_translation(text)

            st.rerun()

# -------------------------------
# 📊 OUTPUT
# -------------------------------
if st.session_state.transcription:
    st.success(f"🗣️ {st.session_state.transcription}")

    col1, col2 = st.columns(2)

    # ISL Gloss
    with col1:
        st.subheader("📘 ISL Gloss")
        if st.session_state.isl_data:
            st.code(st.session_state.isl_data["gloss"])

    # Visual
    with col2:
        st.subheader("🎨 Visual Output")

        if st.button("Generate Visual"):
            with st.spinner("🎨 Generating..."):
                prompt = st.session_state.isl_data["visual_description"]
                img = generate_visual(prompt)

                if img:
                    st.session_state.image_url = img

        if st.session_state.image_url:
            st.image(st.session_state.image_url)

st.caption("⚠️ Note: Add API keys in Streamlit secrets for deployment.")
