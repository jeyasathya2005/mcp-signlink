import streamlit as st
import json
import requests

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak Search 👋", layout="wide")
st.title("🗣️ SignSpeak AI (Video Finder)")
st.caption("🎧 Audio → 🧠 ISL Gloss → 🔍 Web Video Retrieval")

# -------------------------------
# 🔑 SESSION STATE INITIALIZATION
# -------------------------------
if "transcription" not in st.session_state:
    st.session_state.transcription = None
if "isl_data" not in st.session_state:
    st.session_state.isl_data = None
if "video_link" not in st.session_state:
    st.session_state.video_link = None

# -------------------------------
# 🔑 SIDEBAR CONFIG
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", "")
google_key = st.secrets.get("GOOGLE_API_KEY", "")
google_cx = st.secrets.get("GOOGLE_CSE_ID", "")

with st.sidebar:
    st.header("🔑 API Config")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password")
    if not google_key:
        google_key = st.text_input("Google API Key", type="password")
    if not google_cx:
        google_cx = st.text_input("Search Engine ID (CX)", type="password")
    
    st.divider()
    if st.button("🗑️ Reset App"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# -------------------------------
# 🛠️ HELPER FUNCTIONS
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

def get_isl_search_query(text):
    """Converts spoken text into ISL Gloss and a Search Query"""
    system_prompt = (
        "Convert English to Indian Sign Language (ISL). "
        "Provide a JSON response with: "
        "1. 'isl_gloss': The ISL symbols. "
        "2. 'search_query': A optimized string to find a sign language video on YouTube for this specific phrase."
    )
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    data = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
        "response_format": {"type": "json_object"}
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        st.error(f"LLM Error: {e}")
        return None

def find_video_on_web(query):
    """Searches YouTube/Web for the sign language video"""
    # We append "Indian Sign Language" to ensure the results are relevant
    full_query = f"{query} Indian Sign Language sign"
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": google_key,
        "cx": google_cx,
        "q": full_query,
        "num": 1,  # Get the top result
        "safe": "active"
    }
    try:
        response = requests.get(search_url, params=params)
        results = response.json()
        if "items" in results:
            return results["items"][0]["link"]
        return None
    except Exception as e:
        st.error(f"Search Error: {e}")
        return None

# -------------------------------
# 🎤 MAIN UI
# -------------------------------
st.subheader("🎤 Step 1: Record Voice")
audio = st.audio_input("Ask for a sign (e.g., 'How to say Hello?')")

if audio:
    if st.session_state.transcription is None:
        with st.spinner("🎧 Transcribing..."):
            st.session_state.transcription = transcribe_audio(audio.getvalue())
        
        if st.session_state.transcription:
            with st.spinner("🧠 Analyzing ISL..."):
                st.session_state.isl_data = get_isl_search_query(st.session_state.transcription)
            st.rerun()

# --- RESULTS AREA ---
if st.session_state.transcription:
    st.info(f"🗣️ **Recognized:** {st.session_state.transcription}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📘 ISL Gloss")
        if st.session_state.isl_data:
            st.code(st.session_state.isl_data.get("isl_gloss"), language="txt")
            st.caption("This is the grammar structure for Indian Sign Language.")

    with col2:
        st.subheader("🎥 Video Reference")
        
        if st.button("🔍 Search for Video"):
            if not google_key or not google_cx:
                st.warning("Please provide Google API keys in the sidebar.")
            else:
                with st.spinner("🌐 Searching the web for real ISL videos..."):
                    query = st.session_state.isl_data.get("search_query")
                    video_url = find_video_on_web(query)
                    if video_url:
                        st.session_state.video_link = video_url
                    else:
                        st.error("No relevant video found.")

        # Show the video if found
        if st.session_state.video_link:
            st.success("Found a matching video!")
            # Streamlit st.video automatically handles YouTube links
            st.video(st.session_state.video_link)
            st.write(f"🔗 [Source Link]({st.session_state.video_link})")

st.divider()
st.caption("Note: This version searches for real human-recorded videos from the web rather than generating AI avatars.")
