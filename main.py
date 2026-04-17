import json
import requests
import time
import streamlit as st

# -------------------------------
# 🌐 PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="SignSpeak AI 👋", layout="wide", page_icon="🤟")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Space+Grotesk', sans-serif; }
    .stApp { background: #0a0a0f; color: #e8e8f0; }
    .block-container { padding: 2rem 3rem; }
    h1 { color: #a78bfa !important; font-size: 2.4rem !important; }
    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #4f46e5);
        color: white; border: none; border-radius: 12px;
        padding: 0.6rem 1.6rem; font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(124,58,237,0.4); }
    .stCodeBlock, code { background: #1a1a2e !important; border-radius: 10px; }
    .step-box {
        background: #12121f;
        border: 1px solid #2a2a4a;
        border-radius: 14px;
        padding: 1.2rem 1.6rem;
        margin: 0.6rem 0;
    }
    .status-success { color: #34d399; font-weight: 600; }
    .status-info { color: #60a5fa; }
</style>
""", unsafe_allow_html=True)

st.title("🤟 SignSpeak AI")
st.caption("🎧 Voice → 🧠 ISL Gloss → 🎬 AI Sign Language Video")

# -------------------------------
# 🔑 SESSION STATE
# -------------------------------
for key in ["transcription", "isl_data", "video_url", "video_status", "prediction_id"]:
    if key not in st.session_state:
        st.session_state[key] = None

# -------------------------------
# 🔑 API KEYS
# -------------------------------
groq_key = st.secrets.get("GROQ_API_KEY", "")
replicate_token = st.secrets.get("REPLICATE_API_TOKEN", "")

with st.sidebar:
    st.header("🔑 Configuration")
    if not groq_key:
        groq_key = st.text_input("Groq API Key", type="password", help="Get free key at console.groq.com")
    if not replicate_token:
        replicate_token = st.text_input("Replicate Token", type="password", help="Get free token at replicate.com")

    st.markdown("---")
    st.markdown("**Model Used:**")
    st.markdown("- 🎙️ Whisper Large v3 (Groq)")
    st.markdown("- 🧠 LLaMA 3.3 70B (Groq)")
    st.markdown("- 🎬 minimax/video-01 (Replicate)")

    st.markdown("---")
    if st.button("🔄 Reset All"):
        for key in ["transcription", "isl_data", "video_url", "video_status", "prediction_id"]:
            st.session_state[key] = None
        st.rerun()


# -------------------------------
# 🎤 TRANSCRIBE AUDIO
# -------------------------------
def transcribe_audio(audio_bytes):
    try:
        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {groq_key}"}
        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
            "model": (None, "whisper-large-v3"),
            "language": (None, "en"),
            "response_format": (None, "json")
        }
        res = requests.post(url, headers=headers, files=files, timeout=30)
        res.raise_for_status()
        return res.json().get("text", "")
    except requests.exceptions.HTTPError as e:
        st.error(f"Groq Transcription HTTP Error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Transcription Error: {e}")
        return None


# -------------------------------
# 🧠 ISL TRANSLATION
# -------------------------------
def get_isl_translation(text):
    try:
        system_prompt = (
            "You are an expert Indian Sign Language (ISL) linguist. "
            "Convert the given English sentence into ISL. "
            "ISL follows Subject-Object-Verb order and drops articles/prepositions. "
            "Return ONLY a valid JSON object with these exact keys:\n"
            "{\n"
            '  "gloss": "ISL gloss words in correct order",\n'
            '  "video_prompt": "A short cinematic description of a person signing each word: [gloss]. '
            'Show clear hand shapes, front-facing view, neutral background, professional lighting, '
            'realistic human, 5-8 seconds"\n'
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
            "response_format": {"type": "json_object"},
            "temperature": 0.3
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        res.raise_for_status()
        return json.loads(res.json()["choices"][0]["message"]["content"])
    except requests.exceptions.HTTPError as e:
        st.error(f"Groq ISL HTTP Error {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        st.error(f"ISL Translation Error: {e}")
        return None


# -------------------------------
# 🎬 START VIDEO GENERATION (Async)
# -------------------------------
def start_video_generation(prompt):
    try:
        url = "https://api.replicate.com/v1/models/minimax/video-01/predictions"
        headers = {
            "Authorization": f"Token {replicate_token}",
            "Content-Type": "application/json",
            "Prefer": "respond-async"
        }
        data = {
            "input": {
                "prompt": prompt,
                "prompt_optimizer": True
            }
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        res.raise_for_status()
        prediction = res.json()
        return prediction.get("id"), prediction.get("status")
    except requests.exceptions.HTTPError as e:
        st.warning(f"minimax/video-01 unavailable ({e.response.status_code}), trying fallback model...")
        return start_video_fallback(prompt)
    except Exception as e:
        st.error(f"Video Generation Error: {e}")
        return None, None


def start_video_fallback(prompt):
    try:
        url = "https://api.replicate.com/v1/predictions"
        headers = {
            "Authorization": f"Token {replicate_token}",
            "Content-Type": "application/json"
        }
        data = {
            "version": "beecf59c4aee8d81bf04f0381033dfa10dc16e845b4ae00d281e2fa377e48a9f",
            "input": {
                "prompt": prompt,
                "negative_prompt": "blurry, low quality, distorted hands, extra fingers",
                "num_frames": 16,
                "num_inference_steps": 25,
                "guidance_scale": 7.5
            }
        }
        res = requests.post(url, headers=headers, json=data, timeout=30)
        res.raise_for_status()
        prediction = res.json()
        return prediction.get("id"), prediction.get("status")
    except Exception as e:
        st.error(f"Fallback Video Error: {e}")
        return None, None


# -------------------------------
# 🔄 POLL VIDEO STATUS
# -------------------------------
def poll_video_status(prediction_id):
    try:
        url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
        headers = {"Authorization": f"Token {replicate_token}"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        prediction = res.json()
        status = prediction.get("status")
        output = prediction.get("output")
        error = prediction.get("error")
        video_url = None
        if output:
            if isinstance(output, list):
                video_url = output[0]
            elif isinstance(output, str):
                video_url = output
        return status, video_url, error
    except Exception as e:
        return "error", None, str(e)


# -------------------------------
# 🧠 ARCHITECTURE DIAGRAM FUNCTIONS
# -------------------------------
def get_system_architecture_dot():
    dot = """
    digraph SignSpeakPipeline {
        graph [
            rankdir=TB
            fontname="Helvetica"
            fontsize=11
            splines=ortho
            nodesep=0.6
            ranksep=0.7
            bgcolor="#0a0a0f"
            label="SignSpeak AI — End-to-End Speech-to-ISL Video Pipeline"
            labelfontsize=13
            labelfontcolor="#e8e8f0"
            labelloc=t
        ]
        node [
            shape=rectangle
            style="filled,rounded"
            fontname="Helvetica"
            fontsize=10
            fontcolor="#0a0a0f"
            width=2.4
            height=0.55
            penwidth=1.5
        ]
        edge [
            color="#a0a0c0"
            fontname="Helvetica"
            fontsize=9
            fontcolor="#c0c0d0"
            penwidth=1.5
            arrowsize=0.8
        ]

        // ── INPUT STAGE ─────────────────────────────────────────
        subgraph cluster_input {
            label="INPUT"
            fontcolor="#90caf9"
            fontsize=10
            fontname="Helvetica Bold"
            style="dashed"
            color="#1e3a5f"
            bgcolor="#0d1b2e"

            S  [label="S(t)  |  Speech Input\n[Microphone / Audio File]"
                fillcolor="#1565c0" fontcolor="white"]
            FE [label="Feature Extraction\n[MFCC / Log-Mel Spectrogram]"
                fillcolor="#1976d2" fontcolor="white"]
        }

        // ── ASR STAGE ────────────────────────────────────────────
        subgraph cluster_asr {
            label="ASR  —  Automatic Speech Recognition"
            fontcolor="#90caf9"
            fontsize=10
            fontname="Helvetica Bold"
            style="dashed"
            color="#1e3a5f"
            bgcolor="#0d1b2e"

            ASR_IN  [label="Input Layer\n[MFCC Feature Vectors  ×  T]"
                     fillcolor="#0d47a1" fontcolor="white"]
            BILSTM  [label="BiLSTM / Transformer Encoder\n[Hidden dim=512, Heads=8]"
                     fillcolor="#1565c0" fontcolor="white"]
            ATTN    [label="Attention Layer\n[Multi-Head Self-Attention]"
                     fillcolor="#1976d2" fontcolor="white"]
            FC      [label="Fully Connected Layer\n[FC-1024  →  FC-512]"
                     fillcolor="#1e88e5" fontcolor="white"]
            SOFTMAX [label="Softmax Output\n[Vocabulary Logits]"
                     fillcolor="#2196f3" fontcolor="white"]
            DECODE  [label="CTC / Beam Search Decoder\n[α=0.5, beam_width=100]"
                     fillcolor="#42a5f5" fontcolor="white"]
            TEXT    [label="Transcribed Text  T\n[English String Output]"
                     fillcolor="#1976d2" fontcolor="white"]
        }

        // ── NLP STAGE ────────────────────────────────────────────
        subgraph cluster_nlp {
            label="NLP PROCESSING  —  ISL Grammar Engine"
            fontcolor="#fff176"
            fontsize=10
            fontname="Helvetica Bold"
            style="dashed"
            color="#4a3f00"
            bgcolor="#1a1500"

            TOK  [label="Tokenization\n[WordPiece / BPE]"
                  fillcolor="#f9a825" fontcolor="#0a0a0f"]
            STOP [label="Stopword Removal\n[Articles / Prepositions]"
                  fillcolor="#f57f17" fontcolor="white"]
            KW   [label="Keyword Extraction\n[TF-IDF / RAKE]"
                  fillcolor="#e65100" fontcolor="white"]
            ISL  [label="ISL Grammar Conversion\n[SOV Reordering  |  LLaMA-3.3-70B]"
                  fillcolor="#bf360c" fontcolor="white"]
            GLOSS[label="ISL Gloss Sequence  G\n[Ordered Sign Tokens]"
                  fillcolor="#d84315" fontcolor="white"]
        }

        // ── CNN GESTURE STAGE ────────────────────────────────────
        subgraph cluster_cnn {
            label="GESTURE MAPPING  —  CNN Sign Classifier"
            fontcolor="#a5d6a7"
            fontsize=10
            fontname="Helvetica Bold"
            style="dashed"
            color="#1b4f1e"
            bgcolor="#0a1f0b"

            CNN_IN [label="Input Image\n[224×224×3  RGB Frame]"
                    fillcolor="#1b5e20" fontcolor="white"]
            CONV1  [label="Conv2D  (64, 3×3)  +  ReLU\n[BatchNorm  |  stride=1]"
                    fillcolor="#2e7d32" fontcolor="white"]
            POOL1  [label="MaxPooling2D  (2×2)\n[Feature Map: 112×112×64]"
                    fillcolor="#388e3c" fontcolor="white"]
            CONV2  [label="Conv2D  (128, 3×3)  +  ReLU\n[BatchNorm  |  stride=1]"
                    fillcolor="#43a047" fontcolor="white"]
            FLAT   [label="Flatten\n[→ 1D Feature Vector]"
                    fillcolor="#4caf50" fontcolor="white"]
            DENSE  [label="Dense Layer\n[FC-512  →  Dropout(0.5)]"
                    fillcolor="#66bb6a" fontcolor="white"]
            GSMAX  [label="Softmax\n[N Gesture Classes Output]"
                    fillcolor="#81c784" fontcolor="#0a0a0f"]
            GMAP   [label="Gesture → Token Mapping\n[Lookup Table / Embedding]"
                    fillcolor="#388e3c" fontcolor="white"]
        }

        // ── SEQUENCE & RENDER STAGE ──────────────────────────────
        subgraph cluster_render {
            label="SEQUENCE GENERATOR  &  VIDEO RENDERER"
            fontcolor="#ef9a9a"
            fontsize=10
            fontname="Helvetica Bold"
            style="dashed"
            color="#4a0000"
            bgcolor="#1a0000"

            SEQ  [label="Sequence Generator\n[Temporal Gesture Ordering]"
                  fillcolor="#b71c1c" fontcolor="white"]
            FGEN [label="Frame Generation\n[minimax/video-01  |  Replicate API]"
                  fillcolor="#c62828" fontcolor="white"]
            FSTITCH[label="Frame Stitching\n[FPS=25  |  Duration=5–8s]"
                    fillcolor="#d32f2f" fontcolor="white"]
            ENC  [label="Video Encoding\n[H.264 / MP4  |  720p]"
                  fillcolor="#e53935" fontcolor="white"]
        }

        // ── OUTPUT STAGE ─────────────────────────────────────────
        V [label="V  |  ISL Video Output\n[Rendered Sign Language Video]"
           fillcolor="#4a148c" fontcolor="white" width=3.0]

        // ── EDGES ─────────────────────────────────────────────────
        S      -> FE      [label="raw audio"]
        FE     -> ASR_IN  [label="feature matrix"]
        ASR_IN -> BILSTM  [label="x_t ∈ ℝ^d"]
        BILSTM -> ATTN    [label="h_t (fwd+bwd)"]
        ATTN   -> FC      [label="context vector"]
        FC     -> SOFTMAX [label="logits"]
        SOFTMAX-> DECODE  [label="P(y|x)"]
        DECODE -> TEXT    [label="token sequence"]
        TEXT   -> TOK     [label="string T"]
        TOK    -> STOP    [label="token list"]
        STOP   -> KW      [label="filtered tokens"]
        KW     -> ISL     [label="keywords"]
        ISL    -> GLOSS   [label="SOV reorder"]
        GLOSS  -> CNN_IN  [label="gloss[i]"]
        CNN_IN -> CONV1   [label="pixel tensor"]
        CONV1  -> POOL1   [label="feature maps"]
        POOL1  -> CONV2   [label="pooled maps"]
        CONV2  -> FLAT    [label="deep features"]
        FLAT   -> DENSE   [label="1D vector"]
        DENSE  -> GSMAX   [label="activations"]
        GSMAX  -> GMAP    [label="class_id"]
        GMAP   -> SEQ     [label="gesture token"]
        SEQ    -> FGEN    [label="ordered sequence"]
        FGEN   -> FSTITCH [label="frames[]"]
        FSTITCH-> ENC     [label="frame buffer"]
        ENC    -> V       [label="mp4 stream"]
    }
    """
    return dot


def get_asr_detail_dot():
    dot = """
    digraph ASR_Detail {
        graph [
            rankdir=TB
            fontname="Helvetica"
            fontsize=11
            splines=ortho
            nodesep=0.5
            ranksep=0.55
            bgcolor="#0a0a0f"
            label="ASR Model — Detailed Layer Architecture (Whisper / BiLSTM-Attention)"
            labelfontsize=12
            labelfontcolor="#e8e8f0"
            labelloc=t
        ]
        node [
            shape=rectangle
            style="filled,rounded"
            fontname="Helvetica"
            fontsize=9
            fontcolor="white"
            width=3.2
            height=0.5
            penwidth=1.2
        ]
        edge [
            color="#7090b0"
            fontname="Helvetica"
            fontsize=8
            fontcolor="#a0b8c8"
            penwidth=1.3
            arrowsize=0.75
        ]

        AUDIO  [label="Raw Audio  S(t)\n[16 kHz PCM waveform]"                       fillcolor="#0d47a1"]
        MFCC   [label="MFCC / Log-Mel Spectrogram\n[80 mel-bins × T frames]"          fillcolor="#0d47a1"]
        NORM   [label="Layer Normalization\n[zero-mean, unit-variance per feature]"    fillcolor="#1565c0"]
        EMBED  [label="Linear Projection + Positional Encoding\n[d_model = 512]"       fillcolor="#1565c0"]

        subgraph cluster_enc {
            label="Transformer Encoder Stack  (N=6 layers)"
            fontcolor="#90caf9"
            style="dashed"
            color="#1e3a5f"
            bgcolor="#0b1828"

            MHSA   [label="Multi-Head Self-Attention\n[H=8 heads, d_k=64, d_v=64]"    fillcolor="#1565c0"]
            ADD1   [label="Add & Layer Norm"                                            fillcolor="#1976d2"]
            FFN    [label="Feed-Forward Network\n[FC-2048 → ReLU → FC-512]"            fillcolor="#1565c0"]
            ADD2   [label="Add & Layer Norm"                                            fillcolor="#1976d2"]
        }

        BILSTM [label="BiLSTM Layer\n[hidden=256 × 2 directions = 512]"               fillcolor="#1976d2"]
        ATTN2  [label="Additive Attention (Bahdanau)\n[score = v tanh(W1 h + W2 s)]"  fillcolor="#1e88e5"]
        CTX    [label="Context Vector  c_t\n[weighted sum of encoder states]"          fillcolor="#1e88e5"]
        FC1    [label="Fully Connected  FC-1024\n[ReLU activation]"                   fillcolor="#2196f3"]
        DROP   [label="Dropout  (p=0.3)"                                               fillcolor="#1976d2"]
        FC2    [label="Fully Connected  FC-512\n[ReLU activation]"                    fillcolor="#2196f3"]
        SM     [label="Softmax\n[|V| = vocab size logits]"                             fillcolor="#42a5f5" fontcolor="#0a0a0f"]
        CTC    [label="CTC Loss / Beam Search Decoder\n[beam_width=100, lm_weight=0.5]" fillcolor="#1565c0"]
        OUT    [label="Text Output  T\n[English token sequence]"                       fillcolor="#0d47a1"]

        AUDIO -> MFCC  [label="waveform"]
        MFCC  -> NORM  [label="spectrogram matrix"]
        NORM  -> EMBED [label="normalized features"]
        EMBED -> MHSA  [label="d_model=512"]
        MHSA  -> ADD1
        ADD1  -> FFN
        FFN   -> ADD2
        ADD2  -> BILSTM [label="encoder output  h"]
        BILSTM-> ATTN2  [label="hidden states  h_t"]
        ATTN2 -> CTX    [label="alignment weights  α_t"]
        CTX   -> FC1    [label="c_t ∈ ℝ^512"]
        FC1   -> DROP
        DROP  -> FC2
        FC2   -> SM     [label="pre-softmax logits"]
        SM    -> CTC    [label="P(y|x)"]
        CTC   -> OUT    [label="decoded sequence"]
    }
    """
    return dot


def get_cnn_detail_dot():
    dot = """
    digraph CNN_Detail {
        graph [
            rankdir=TB
            fontname="Helvetica"
            fontsize=11
            splines=ortho
            nodesep=0.5
            ranksep=0.55
            bgcolor="#0a0a0f"
            label="CNN Gesture Classifier — Detailed Layer Architecture"
            labelfontsize=12
            labelfontcolor="#e8e8f0"
            labelloc=t
        ]
        node [
            shape=rectangle
            style="filled,rounded"
            fontname="Helvetica"
            fontsize=9
            fontcolor="white"
            width=3.4
            height=0.5
            penwidth=1.2
        ]
        edge [
            color="#60a878"
            fontname="Helvetica"
            fontsize=8
            fontcolor="#90c8a0"
            penwidth=1.3
            arrowsize=0.75
        ]

        INPUT [label="Input Image\n[224 × 224 × 3  RGB]"                                       fillcolor="#1b5e20"]
        BN0   [label="Batch Normalization\n[per-channel mean/var normalization]"                fillcolor="#1b5e20"]

        subgraph cluster_block1 {
            label="Convolutional Block 1"
            fontcolor="#a5d6a7"
            style="dashed"
            color="#2e6b30"
            bgcolor="#0a1f0b"
            C1    [label="Conv2D  (64 filters, 3×3, stride=1, pad=same)\n[Output: 224×224×64]"  fillcolor="#2e7d32"]
            BN1   [label="Batch Normalization  +  ReLU"                                         fillcolor="#388e3c"]
            C2    [label="Conv2D  (64 filters, 3×3, stride=1, pad=same)\n[Output: 224×224×64]"  fillcolor="#2e7d32"]
            BN2   [label="Batch Normalization  +  ReLU"                                         fillcolor="#388e3c"]
            P1    [label="MaxPooling2D  (2×2, stride=2)\n[Output: 112×112×64]"                 fillcolor="#43a047"]
            D1    [label="Dropout  (p=0.25)"                                                    fillcolor="#388e3c"]
        }

        subgraph cluster_block2 {
            label="Convolutional Block 2"
            fontcolor="#a5d6a7"
            style="dashed"
            color="#2e6b30"
            bgcolor="#0a1f0b"
            C3    [label="Conv2D  (128 filters, 3×3, stride=1, pad=same)\n[Output: 112×112×128]" fillcolor="#2e7d32"]
            BN3   [label="Batch Normalization  +  ReLU"                                          fillcolor="#388e3c"]
            C4    [label="Conv2D  (128 filters, 3×3, stride=1, pad=same)\n[Output: 112×112×128]" fillcolor="#2e7d32"]
            BN4   [label="Batch Normalization  +  ReLU"                                          fillcolor="#388e3c"]
            P2    [label="MaxPooling2D  (2×2, stride=2)\n[Output: 56×56×128]"                   fillcolor="#43a047"]
            D2    [label="Dropout  (p=0.25)"                                                     fillcolor="#388e3c"]
        }

        subgraph cluster_block3 {
            label="Convolutional Block 3"
            fontcolor="#a5d6a7"
            style="dashed"
            color="#2e6b30"
            bgcolor="#0a1f0b"
            C5    [label="Conv2D  (256 filters, 3×3, stride=1, pad=same)\n[Output: 56×56×256]"  fillcolor="#2e7d32"]
            BN5   [label="Batch Normalization  +  ReLU"                                          fillcolor="#388e3c"]
            P3    [label="MaxPooling2D  (2×2, stride=2)\n[Output: 28×28×256]"                   fillcolor="#43a047"]
        }

        FLAT  [label="GlobalAveragePooling2D  →  Flatten\n[Output dim: 256]"                    fillcolor="#4caf50" fontcolor="#0a0a0f"]
        FC1   [label="Dense  FC-512\n[ReLU  |  L2 reg λ=1e-4]"                                 fillcolor="#388e3c"]
        D3    [label="Dropout  (p=0.5)"                                                         fillcolor="#2e7d32"]
        FC2   [label="Dense  FC-256\n[ReLU]"                                                    fillcolor="#388e3c"]
        SM    [label="Softmax  →  N Gesture Classes\n[e.g. N=500 ISL signs]"                   fillcolor="#66bb6a" fontcolor="#0a0a0f"]
        GMAP  [label="Gesture Class → ISL Token Mapping\n[Index → Sign Label Lookup]"          fillcolor="#43a047"]

        INPUT -> BN0
        BN0   -> C1
        C1    -> BN1
        BN1   -> C2
        C2    -> BN2
        BN2   -> P1
        P1    -> D1
        D1    -> C3  [label="112×112×64"]
        C3    -> BN3
        BN3   -> C4
        C4    -> BN4
        BN4   -> P2
        P2    -> D2
        D2    -> C5  [label="56×56×128"]
        C5    -> BN5
        BN5   -> P3
        P3    -> FLAT [label="28×28×256"]
        FLAT  -> FC1
        FC1   -> D3
        D3    -> FC2
        FC2   -> SM
        SM    -> GMAP [label="argmax(p)"]
    }
    """
    return dot


# -------------------------------
# 🎤 AUDIO INPUT SECTION
# -------------------------------
st.markdown("---")
col_main, col_info = st.columns([2, 1])

with col_main:
    st.subheader("Step 1 — 🎙️ Record Your Voice")
    audio = st.audio_input("Click the mic icon and speak clearly in English")

with col_info:
    st.markdown("""
    <div class="step-box">
    <b>📌 How it works:</b><br><br>
    1️⃣ Record your voice<br>
    2️⃣ AI transcribes speech<br>
    3️⃣ Translated to ISL gloss<br>
    4️⃣ Video generated showing signing
    </div>
    """, unsafe_allow_html=True)

# Transcription trigger
if audio and not st.session_state.transcription:
    if not groq_key:
        st.error("⚠️ Please enter your Groq API key in the sidebar.")
    else:
        with st.spinner("🎧 Transcribing your audio with Whisper..."):
            text = transcribe_audio(audio.getvalue())
        if text:
            st.session_state.transcription = text
            with st.spinner("🧠 Translating to Indian Sign Language..."):
                st.session_state.isl_data = get_isl_translation(text)
            st.rerun()

# -------------------------------
# 📊 OUTPUT SECTION
# -------------------------------
if st.session_state.transcription:
    st.markdown("---")
    st.subheader("Step 2 — 📝 Results")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🗣️ Transcribed Speech:**")
        st.success(st.session_state.transcription)

        if st.session_state.isl_data:
            st.markdown("**📘 ISL Gloss (sign order):**")
            st.code(st.session_state.isl_data.get("gloss", "N/A"), language="text")

            st.markdown("**🎬 Video Prompt:**")
            with st.expander("View prompt sent to AI"):
                st.write(st.session_state.isl_data.get("video_prompt", ""))

    with col2:
        st.markdown("**🎬 ISL Sign Language Video:**")

        if not st.session_state.prediction_id and not st.session_state.video_url:
            if st.button("🎬 Generate ISL Video", use_container_width=True):
                if not replicate_token:
                    st.error("⚠️ Please enter your Replicate token in the sidebar.")
                elif st.session_state.isl_data:
                    prompt = st.session_state.isl_data.get("video_prompt", "")
                    with st.spinner("🚀 Submitting video generation job..."):
                        pred_id, status = start_video_generation(prompt)
                    if pred_id:
                        st.session_state.prediction_id = pred_id
                        st.session_state.video_status = status
                        st.rerun()

        if st.session_state.prediction_id and not st.session_state.video_url:
            status, video_url, error = poll_video_status(st.session_state.prediction_id)
            st.session_state.video_status = status

            if status in ("starting", "processing"):
                st.info(f"⏳ Video is being generated... Status: **{status}**")
                st.markdown("_This typically takes 30–90 seconds. Refresh to check progress._")
                if st.button("🔃 Check Status"):
                    st.rerun()

                progress_bar = st.progress(0)
                for i in range(30):
                    time.sleep(1)
                    progress_bar.progress((i + 1) / 30)
                    s, v, e = poll_video_status(st.session_state.prediction_id)
                    if s == "succeeded" and v:
                        st.session_state.video_url = v
                        st.session_state.video_status = "succeeded"
                        progress_bar.progress(1.0)
                        st.rerun()
                        break
                    elif s == "failed":
                        st.session_state.video_status = "failed"
                        st.error(f"❌ Video generation failed: {e}")
                        break
                else:
                    st.warning("Still processing... click 'Check Status' to refresh.")

            elif status == "succeeded" and video_url:
                st.session_state.video_url = video_url
                st.rerun()

            elif status == "failed":
                st.error(f"❌ Generation failed: {error}")
                st.markdown("Try clicking Reset and recording again.")

        if st.session_state.video_url:
            st.markdown('<p class="status-success">✅ Video Ready!</p>', unsafe_allow_html=True)
            st.video(st.session_state.video_url)
            st.markdown(f"[📥 Download Video]({st.session_state.video_url})", unsafe_allow_html=False)

# -------------------------------
# 🧠 ARCHITECTURE VISUALIZATION SECTION
# -------------------------------
st.markdown("---")
st.subheader("🔬 Model Architecture Inspector")
st.caption("Visualize the full deep learning pipeline and individual model internals.")

arch_col1, arch_col2 = st.columns(2)

with arch_col1:
    show_arch = st.button("🧠 Show Model Architecture", use_container_width=True)

with arch_col2:
    show_nn = st.button("📊 Show Detailed Neural Network", use_container_width=True)

if show_arch:
    st.markdown("#### End-to-End SignSpeak AI — System Architecture")
    st.caption("Full pipeline: Speech Input → Feature Extraction → ASR → NLP → CNN Gesture Mapping → Video Rendering → ISL Output")
    st.graphviz_chart(get_system_architecture_dot(), use_container_width=True)
    st.markdown("""
    <div class="step-box">
    <b>🗺️ Pipeline Stages:</b>&nbsp;
    <span style="color:#90caf9">■ Speech / ASR (Blue)</span> &nbsp;|&nbsp;
    <span style="color:#fff176">■ NLP / ISL Grammar (Yellow)</span> &nbsp;|&nbsp;
    <span style="color:#a5d6a7">■ CNN Gesture (Green)</span> &nbsp;|&nbsp;
    <span style="color:#ef9a9a">■ Video Render (Red)</span> &nbsp;|&nbsp;
    <span style="color:#ce93d8">■ Output (Purple)</span>
    </div>
    """, unsafe_allow_html=True)

if show_nn:
    st.markdown("#### Detailed Neural Network Architectures")
    nn_tab1, nn_tab2 = st.tabs(["🎙️ ASR Model Layers", "🤚 CNN Gesture Classifier Layers"])

    with nn_tab1:
        st.caption("Whisper-style BiLSTM + Transformer Encoder with Attention and CTC decoding")
        st.graphviz_chart(get_asr_detail_dot(), use_container_width=True)
        st.markdown("""
        <div class="step-box">
        <b>ASR Layer Summary:</b><br>
        MFCC (80 bins × T) → LayerNorm → Linear Projection (d=512) → 
        Multi-Head Self-Attention (H=8) × 6 layers → BiLSTM (hidden=256×2) → 
        Bahdanau Attention → FC-1024 → Dropout → FC-512 → Softmax → CTC Beam Decode
        </div>
        """, unsafe_allow_html=True)

    with nn_tab2:
        st.caption("3-block CNN with BatchNorm, MaxPooling, GlobalAvgPool, and Softmax gesture classification")
        st.graphviz_chart(get_cnn_detail_dot(), use_container_width=True)
        st.markdown("""
        <div class="step-box">
        <b>CNN Layer Summary:</b><br>
        Input (224×224×3) → [Conv2D-64 → BN → ReLU] × 2 → MaxPool → 
        [Conv2D-128 → BN → ReLU] × 2 → MaxPool → Conv2D-256 → MaxPool → 
        GlobalAvgPool → FC-512 → Dropout(0.5) → FC-256 → Softmax (N classes) → 
        Gesture-to-Token Lookup
        </div>
        """, unsafe_allow_html=True)

# -------------------------------
# 📌 FOOTER
# -------------------------------
st.markdown("---")
st.caption("sign")
