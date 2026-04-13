import streamlit as st
import json
import requests
import replicate
from replicate.client import Client

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide")
st.title("🗣️ SignSpeak AI: Video Generation")
st.caption("🎧 Audio → 🧠 ISL Gloss → 🤖 AI Video Avatar")

# -------------------------------
# 🔑 SESSION STATE INITIALIZATION
# -------------------------------
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "isl_data" not in st.session_state:
    st.session_state.isl_data = None
if "video_url" not in st.session_state:
    st.session_state.video_url = None

# -------------------------------
# 🔑 SIDEBAR / KEYS
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", "")
replicate_token = st.secrets.get("REPLICATE_API_TOKEN", "")

with st.sidebar:
    st.header("🔑 API Configuration")
    if not groq_key: 
        groq_key = st.text_input("Groq API Key", type="password")
    if not replicate_token: 
        replicate_token = st.text_input("Replicate Token", type="password")
    
    st.divider()
    if st.button("🗑️ Reset Application"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# -------------------------------
# 🛠️ HELPER FUNCTIONS
# -------------------------------

def transcribe_audio(audio_bytes):
    """Transcribe audio using Groq Whisper-v3"""
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"), 
            "model": (None, "whisper-large-v3")
        }
        response = requests.post(url, headers=headers, files=files)
        return response.json().get("text", "")
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

def get_isl_translation(text):
    """Convert spoken text to ISL Gloss and detailed visual prompt"""
    system_prompt = (
        "You are an ISL (Indian Sign Language) expert. Convert English to ISL. "
        "Respond ONLY in valid JSON format: "
        "{"
        "\"gloss\": \"UPPERCASE ISL SYMBOLS\","
        "\"visual_description\": \"Detailed movement description for an AI video model to perform these specific signs clearly.\""
        "}"
    )
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt}, 
            {"role": "user", "content": text}
        ],
        "response_format": {"type": "json_object"}
    }
    try:
        res = requests.post(url, headers=headers, json=data)
        return json.loads(res.json()["choices"][0]["message"]["content"])
    except Exception as e:
        st.error(f"Translation Error: {e}")
        return None

def generate_video(visual_prompt):
    """Generate AI video using Replicate Minimax (Fixed binary error)"""
    try:
        client = Client(api_token=replicate_token)
        # We add specific style instructions to ensure the avatar is visible and moving
        full_prompt = (
            f"High quality, realistic person performing Indian Sign Language movements for: {visual_prompt}. "
            "Neutral background, front-facing, visible hands and upper body, 4k resolution."
        )
        
        output = client.run(
            "minimax/video-01",
            input={
                "prompt": full_prompt,
                "prompt_optimizer": True
            }
        )
        
        # CRITICAL FIX: Extract the URL string from the Replicate response
        # Replicate often returns a list [URL] or a generator object.
        if isinstance(output, list):
            return str(output[0])
        elif isinstance(output, str):
            return output
        else:
            # Handle generator or file objects
            return str(output)
            
    except Exception as e:
        st.error(f"Replicate Generation Error: {e}")
        return None

# -------------------------------
# 🎤 MAIN USER INTERFACE
# -------------------------------
st.subheader("🎤 Step 1: Record or Speak")
audio_input = st.audio_input("Click the microphone to record")

# Process Audio
if audio_input and st.session_state.transcription is None:
    with st.spinner("🎧 Listening and Transcribing..."):
        text = transcribe_audio(audio_input.getvalue())
        if text:
            st.session_state.transcription = text
            with st.spinner("🧠 Translating to Indian Sign Language..."):
                st.session_state.isl_data = get_isl_translation(text)
            st.rerun()

# Display Results
if st.session_state.transcription:
    st.info(f"🗣️ **Recognized Speech:** {st.session_state.transcription}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📘 ISL Gloss")
        if st.session_state.isl_data:
            st.code(st.session_state.isl_data.get("gloss"), language="txt")
            st.caption("Grammar structure for Indian Sign Language.")

    with col2:
        st.subheader("🎬 AI Generation")
        
        # Button to trigger generation
        if st.button("🎥 Generate AI Sign Video"):
            if not replicate_token:
                st.error("Please add your Replicate Token in the sidebar.")
            else:
                with st.spinner("⏳ Generating video (usually takes 40-60 seconds)..."):
                    prompt = st.session_state.isl_data.get("visual_description")
                    video_url = generate_video(prompt)
                    if video_url:
                        st.session_state.video_url = video_url
                        st.success("✅ Video Generated!")
                    else:
                        st.error("Failed to generate video. Please try again.")

        # Display the video permanently once generated
        if st.session_state.video_url:
            try:
                # Ensure it is a string URL
                video_src = str(st.session_state.video_url)
                st.video(video_src)
                st.write(f"🔗 [Direct Video Link]({video_src})")
            except Exception as playback_error:
                st.error("The video was generated but cannot be played in the browser.")
                st.write(f"Try opening the link directly: {st.session_state.video_url}")

st.divider()
st.caption("Note: AI generation requires a valid Replicate API token with balance.")
