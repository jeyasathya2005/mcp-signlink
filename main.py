import streamlit as st
import os
import json
import requests
import replicate

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide")
st.title("🗣️ SignSpeak AI (Universal)")
st.caption("🎧 Audio → 🧠 ISL → 🎥 Video | Multi-Model Support")

# -------------------------------
# 🔑 API KEYS
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", "")
replicate_key = st.secrets.get("REPLICATE_API_TOKEN", "")

with st.sidebar:
    st.header("🔑 API Config")

    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")

    if not replicate_key:
        replicate_key = st.text_input("Replicate Token", type="password")

    st.divider()

    # -------------------------------
    # 🧠 MODEL SELECTION
    # -------------------------------
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

        headers = {
            "Authorization": f"Bearer {groq_key}"
        }

        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
            "model": (None, "whisper-large-v3")
        }

        response = requests.post(url, headers=headers, files=files)

        if response.status_code != 200:
            st.error(response.text)
            return None

        return response.json().get("text", "")

    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

# -------------------------------
# 🌐 UNIVERSAL LLM CALL
# -------------------------------
def call_llm(model, messages):

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code != 200:
        return None

    return response.json()["choices"][0]["message"]["content"]

# -------------------------------
# 🧠 TEXT → ISL (WITH FALLBACK)
# -------------------------------
def get_isl(text):

    system_prompt = """
    Convert English sentence to Indian Sign Language (ISL).

    Respond ONLY in JSON:
    {
      "spoken_text": "",
      "isl_gloss": "",
      "rendering_prompt": ""
    }
    """

    MODELS = [
        selected_model,
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": text}
    ]

    for model in MODELS:
        try:
            result = call_llm(model, messages)

            if not result:
                continue

            # Clean JSON
            result = result.strip().replace("```json", "").replace("```", "")

            st.success(f"✅ Model used: {model}")

            return json.loads(result)

        except:
            continue

    st.error("❌ All models failed")
    return None

# -------------------------------
# 🎥 VIDEO GENERATION
# -------------------------------
def generate_video(prompt):
    try:
        os.environ["REPLICATE_API_TOKEN"] = replicate_key

        output = replicate.run(
            "minimax/video-01",
            input={
                "prompt": prompt,
                "prompt_optimizer": True
            }
        )

        if isinstance(output, list):
            return output[0]

        return output

    except Exception as e:
        st.error(f"Video Error: {e}")
        return None

# -------------------------------
# 🎤 MAIN UI
# -------------------------------
st.subheader("🎤 Record Voice")
audio = st.audio_input("Speak something")

if audio and groq_key:

    audio_bytes = audio.getvalue()

    # Step 1: Speech → Text
    with st.spinner("🎧 Transcribing..."):
        text = transcribe_audio(audio_bytes)

    if text:
        st.success(f"🗣️ You said: {text}")

        # Step 2: Text → ISL
        with st.spinner("🧠 Converting to ISL..."):
            isl_data = get_isl(text)

        if isl_data:
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📘 ISL Output")
                st.json(isl_data)
                st.info(f"GLOSS: {isl_data.get('isl_gloss')}")

            with col2:
                st.subheader("🎥 Video Output")

                if st.button("🎬 Generate Video"):
                    video_url = generate_video(
                        isl_data.get("rendering_prompt")
                    )

                    if video_url:
                        st.video(video_url)
                        st.success("✅ Video Generated!")

# -------------------------------
# FOOTER
# -------------------------------
st.divider()
st.caption("⚡ Universal AI System | Groq + Multi-Model + Replicate")
