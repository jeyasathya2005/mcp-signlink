import streamlit as st
import os
import json
import time
import tempfile
from groq import Groq
import replicate

# Page Config
st.set_page_config(page_title="SignSpeak AI (Replicate)", page_icon="👋", layout="wide")

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
        groq_key = st.text_input("Groq API Key", type="password")
    if not replicate_key:
        replicate_key = st.text_input("Replicate API Token", type="password", help="Get this from replicate.com/account")
    
    st.divider()
    st.info("System: Replicate (Minimax) Node")

# --- 2. AI MODULES ---

def transcribe_audio(client, audio_bytes):
    """Module 1: HEARING (Groq Whisper)"""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name

        with open(tmp_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(tmp_file_path, file.read()),
                model="whisper-large-v3",
                response_format="json",
                temperature=0.0
            )
        os.remove(tmp_file_path)
        return transcription.text
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None

def get_isl_instructions(client, text):
    """Module 2: BRAIN (Groq Llama-3)"""
    system_prompt = """
    You are the SignSpeak Engine. Convert spoken English to Indian Sign Language (ISL) parameters.
    Output JSON only. Schema:
    {
      "spoken_text": string,
      "isl_gloss": string,
      "rendering_prompt": string
    }
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Reasoning Error: {e}")
        return None

def generate_video(prompt):
    """Module 3: VISION (Replicate - Minimax)"""
    if not replicate_key:
        st.warning("Replicate API Token required for video.")
        return None
    
    # Set the token in environment for the library to pick up
    os.environ["REPLICATE_API_TOKEN"] = replicate_key

    try:
        st.write("🎞️ Rendering with **Minimax** (via Replicate)...")
        
        # We use Minimax because it currently has SOTA motion for human subjects
        output = replicate.run(
            "minimax/video-01",
            input={
                "prompt": prompt,
                "prompt_optimizer": True
            }
        )
        
        # Replicate returns the URL directly (or a FileOutput object acting as a string)
        return str(output)

    except Exception as e:
        st.error(f"Replicate Error: {e}")
        return None

# --- 3. MAIN UI FLOW ---

st.title("🗣️ SignSpeak: Replicate Edition")
st.caption("Powered by Groq Whisper, Llama 3, and Minimax")

st.subheader("1. Voice Input")
audio_value = st.audio_input("Record your command")

if audio_value and groq_key:
    groq_client = Groq(api_key=groq_key)
    
    with st.spinner("🎧 Transcribing audio..."):
        transcribed_text = transcribe_audio(groq_client, audio_value.read())
    
    if transcribed_text:
        st.success(f"You said: \"{transcribed_text}\"")
        
        with st.spinner("🧠 Converting to ISL Structure..."):
            isl_data = get_isl_instructions(groq_client, transcribed_text)
            
        if isl_data:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("2. ISL Logic")
                st.json(isl_data)
                st.info(f"GLOSS: {isl_data.get('isl_gloss')}")
            
            with col2:
                st.subheader("3. Video Output")
                render_prompt = isl_data.get('rendering_prompt')
                
                if st.button("🎬 Generate AI Video", type="primary"):
                    if render_prompt:
                        video_url = generate_video(render_prompt)
                        if video_url:
                            st.video(video_url)
                            st.success("Video Generated Successfully!")
                            st.caption(f"Source: {video_url}")
