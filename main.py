import streamlit as st
import os
import json
import time
import tempfile
from groq import Groq
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="SignSpeak AI", page_icon="👋", layout="wide")

# --- CSS Styling ---
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .stButton > button { background-color: #ff4b4b; color: white; border-radius: 8px; }
    .stAudio { width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP KEYS ---
groq_key = os.environ.get("GROQ_API_KEY")
google_key = os.environ.get("GOOGLE_API_KEY")

with st.sidebar:
    st.header("🔑 Configuration")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")
    if not google_key:
        google_key = st.text_input("Google API Key", type="password")
    
    st.divider()
    st.info("Status: Ready to Process")

# --- 2. AI MODULES ---

def transcribe_audio(client, audio_bytes):
    """Module 1: HEARING (Groq Whisper)"""
    try:
        # Groq API requires a file-like object with a name
        # We create a temporary file to handle the stream
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_file_path = tmp_file.name

        with open(tmp_file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(tmp_file_path, file.read()),
                model="whisper-large-v3", # State-of-the-art multilingual model
                response_format="json",
                temperature=0.0
            )
        
        # Cleanup temp file
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
      "isl_gloss": string (The grammatical order of signs, e.g., "BOOK OPEN PLEASE"),
      "rendering_prompt": string (A visual description for a video generator, e.g., "A cinematic shot of an Indian teacher signing 'Open Book' with a smile, studio lighting, 4k")
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
    """Module 3: VISION (Google Veo)"""
    if not google_key:
        st.warning("Google API Key required for video generation.")
        return None
        
    try:
        genai.configure(api_key=google_key)
        # Check for available models, prioritizing Veo
        # Note: Veo access depends on your Google AI Studio allowlist status
        model_name = "veo-3.1-generate-preview" 
        
        st.write(f"🎞️ Requesting video from: `{model_name}`...")
        model = genai.GenerativeModel(model_name)
        
        # Veo generation is asynchronous (it takes time)
        operation = model.generate_videos(
            prompt=prompt,
            config={'number_of_videos': 1, 'aspect_ratio': '16:9'}
        )
        
        # Polling loop
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while not operation.done:
            status_text.text("Rendering neural video... (this may take ~30-60s)")
            time.sleep(5)
            progress_bar.progress(50)
            
        progress_bar.progress(100)
        
        if operation.result:
            return operation.result # Returns the video resource/URL
        else:
            st.error("Video generation completed but returned no result.")
            return None
            
    except Exception as e:
        st.error(f"Video Generation Error: {e}")
        return None

# --- 3. MAIN UI FLOW ---

st.title("🗣️ SignSpeak: Voice-to-Video")
st.caption("Powered by Groq Whisper, Llama 3, and Google Veo")

# A. VOICE INPUT
st.subheader("1. Voice Input")
audio_value = st.audio_input("Record your command")

if audio_value and groq_key:
    client = Groq(api_key=groq_key)
    
    # B. PROCESS PIPELINE
    with st.spinner("🎧 Transcribing audio..."):
        # 1. Transcribe
        transcribed_text = transcribe_audio(client, audio_value.read())
    
    if transcribed_text:
        st.success(f"You said: \"{transcribed_text}\"")
        
        with st.spinner("🧠 Converting to ISL Structure..."):
            # 2. Reason
            isl_data = get_isl_instructions(client, transcribed_text)
            
        if isl_data:
            # Display Logic
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("2. ISL Logic")
                st.json(isl_data)
                st.info(f"GLOSS: {isl_data.get('isl_gloss')}")
            
            with col2:
                st.subheader("3. Video Output")
                render_prompt = isl_data.get('rendering_prompt')
                
                # 3. Generate Video
                if st.button("🎬 Generate AI Video", type="primary"):
                    if render_prompt:
                        video_result = generate_video(render_prompt)
                        if video_result:
                            st.video(video_result.video.uri)
                            st.success("Video Generated Successfully!")
                    else:
                        st.warning("No rendering prompt available.")
