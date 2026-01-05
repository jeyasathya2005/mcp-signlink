import streamlit as st
import os
import json
import time
from groq import Groq
import google.generativeai as genai

# Page Config
st.set_page_config(page_title="Groq ISL Engine", page_icon="⚡", layout="wide")

# --- CSS for the "Dark Mode" Terminal Look ---
st.markdown("""
<style>
    .stApp { background-color: #050505; color: white; }
    .stTextInput > div > div > input { background-color: #1a1a1a; color: white; border: 1px solid #333; }
    .stButton > button { background-color: #ffffff; color: black; font-weight: bold; }
    .stMarkdown code { background-color: #1a1a1a; color: #00ff00; }
</style>
""", unsafe_allow_html=True)

# --- 1. SETUP KEYS ---
# Try to get keys from Secrets (Streamlit Cloud) or Environment
groq_key = os.environ.get("GROQ_API_KEY")
google_key = os.environ.get("GOOGLE_API_KEY")

# Fallback: Sidebar Input for Keys if not in environment
with st.sidebar:
    st.header("🔑 API Configuration")
    if not groq_key:
        groq_key = st.text_input("Enter GROQ API Key", type="password")
    if not google_key:
        google_key = st.text_input("Enter Google API Key (Optional)", type="password")
    
    st.divider()
    st.info("System Status: Online")

# --- 2. LOGIC FUNCTIONS ---
def get_groq_client():
    if not groq_key:
        return None
    return Groq(api_key=groq_key)

SYSTEM_INSTRUCTION = """You are the SignSpeak GROQ Reasoning Engine.
Task: Translate spoken English into Indian Sign Language (ISL) gloss.
Output MUST be a valid JSON object.
Mandatory Schema:
{
  "spoken_text": string,
  "isl_sequence": [
    { "sign_id": string, "duration_ms": number, "expression": "SMILE" | "NEUTRAL" | "POLITE" | "FROWN" }
  ],
  "rendering_prompt": string
}"""

def process_text(client, text):
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": text}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"Groq Error: {e}")
        return None

# --- 3. UI LAYOUT ---
st.title("⚡ GROQ ISL ENGINE")
st.caption("Llama-3.3-70b Reasoning Node")

# Input Section
col1, col2 = st.columns([3, 1])
with col1:
    # We use text_input instead of Microphone for Cloud compatibility
    # (Browser mics require special JS components in Streamlit)
    user_input = st.text_input("Input Command", placeholder="Type what you want to say...")

with col2:
    process_btn = st.button("🚀 PROCESS", use_container_width=True)

# Processing Logic
if process_btn and user_input and groq_key:
    client = get_groq_client()
    
    with st.status("Processing...", expanded=True) as status:
        st.write("🧠 Connecting to Groq Inference Engine...")
        data = process_text(client, user_input)
        
        if data:
            st.write("✅ ISL Sequence Generated")
            status.update(label="Complete", state="complete", expanded=False)
            
            # Display Results
            st.subheader("Inference Result")
            
            # 1. Visual JSON
            st.json(data)
            
            # 2. Gloss View
            gloss_sequence = [item['sign_id'] for item in data.get('isl_sequence', [])]
            st.success(f"ISL GLOSS: {' → '.join(gloss_sequence)}")
            
            # 3. Video Render (Optional)
            if google_key and data.get("rendering_prompt"):
                st.divider()
                st.write("🎬 **Video Production Node (Google Veo)**")
                st.info("Video generation requires a whitelisted Google Vertex AI Project.")
                # (Video logic placeholder - usually requires Cloud bucket storage for Streamlit)
        else:
            status.update(label="Failed", state="error")

elif process_btn and not groq_key:
    st.warning("Please enter your GROQ API Key in the sidebar.")
