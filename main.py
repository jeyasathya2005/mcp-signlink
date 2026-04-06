import streamlit as st
import os
import json
import requests
import replicate

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide")

st.title("🗣️ SignSpeak AI")
st.caption("🎧 Audio → 🧠 ISL → 🎥 AI Video")

# -------------------------------
# 🔑 API KEYS (STREAMLIT CLOUD SAFE)
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", None)
replicate_key = st.secrets.get("REPLICATE_API_TOKEN", None)

with st.sidebar:
    st.header("🔑 API Status")

    if groq_key:
        st.success("Groq Connected ✅")
    else:
        groq_key = st.text_input("Enter GROQ API Key", type="password")

    if replicate_key:
        st.success("Replicate Connected ✅")
    else:
        replicate_key = st.text_input("Enter Replicate Token", type="password")

# -------------------------------
# 🎧 AUDIO → TEXT (WHISPER)
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
# 🧠 TEXT → ISL (LLAMA)
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

    try:
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "llama3-70b-8192",
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]
        }

        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            st.error(response.text)
            return None

        content = response.json()["choices"][0]["message"]["content"]

        # CLEAN JSON
        content = content.strip().replace("```json", "").replace("```", "")

        return json.loads(content)

    except Exception as e:
        st.error(f"ISL Error: {e}")
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

        # Handle list output
        if isinstance(output, list):
            return output[0]
        return output

    except Exception as e:
        st.error(f"Video Error: {e}")
        return None

# -------------------------------
# 🎤 MAIN FLOW
# -------------------------------
st.subheader("🎤 Record Voice")

audio = st.audio_input("Speak now")

if audio and groq_key:

    audio_bytes = audio.getvalue()

    # Step 1: Transcription
    with st.spinner("🎧 Transcribing..."):
        text = transcribe_audio(audio_bytes)

    if text:
        st.success(f"🗣️ You said: {text}")

        # Step 2: ISL Conversion
        with st.spinner("🧠 Converting to ISL..."):
            isl_data = get_isl(text)

        if isl_data:
            col1, col2 = st.columns(2)

            # LEFT: JSON
            with col1:
                st.subheader("📘 ISL Output")
                st.json(isl_data)
                st.info(f"GLOSS: {isl_data.get('isl_gloss')}")

            # RIGHT: VIDEO
            with col2:
                st.subheader("🎥 AI Video")

                if st.button("🎬 Generate Video"):
                    video_url = generate_video(
                        isl_data.get("rendering_prompt")
                    )

                    if video_url:
                        st.video(video_url)
                        st.success("✅ Video Ready!")

# -------------------------------
# FOOTER
# -------------------------------
st.divider()
st.caption("Built with ❤️ using Streamlit + Groq + Replicate")
