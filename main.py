pip install groq
import os
import json
from groq import Groq

# 1. SETUP: Initialize the Groq Client
# Ensure you have set the environment variable GROQ_API_KEY
# or replace os.environ.get(...) with your actual key string.
client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

# 2. CONFIGURATION: The "Brain" of the operation
# This exact prompt forces the AI to follow your specific rules and JSON schema.
SYSTEM_INSTRUCTION = """
You are an expert AI reasoning engine specialized in sign-language translation, 
linguistic restructuring, and motion-sequence generation.

You are running via the GROQ API.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CORE OBJECTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Convert spoken English (from voice input) into Indian Sign Language (ISL) 
motion instructions that will be used to generate a SIGN LANGUAGE VIDEO.

You MUST NOT generate images or videos yourself.
You ONLY generate structured JSON instructions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 DATASET CONTEXT (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The system uses the Kaggle dataset: "Indian Sign Language (ISL) – prathumarikeri"
Assume:
• Each sign token matches gestures in this dataset.
• If a word is not available, spell it using alphabet signs.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 YOUR RESPONSIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Convert English sentence into ISL grammar (SOV structure).
2. Remove fillers (is, am, are, the).
3. Output a SEQUENCE of sign instructions.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📤 OUTPUT FORMAT (STRICT JSON ONLY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON. No markdown. No explanations.
Example:
{
  "spoken_text": "Please open your notebooks",
  "isl_sequence": [
    { "sign_id": "PLEASE", "duration_ms": 700, "handshape": "FLAT_PALM", "expression": "POLITE" }
  ]
}
"""

def generate_isl_sequence(spoken_text):
    """
    Sends text to Groq and returns a parsed dictionary of ISL instructions.
    """
    try:
        print(f"🎤 Processing Input: '{spoken_text}'...")

        # 3. THE API CALL
        # We use Llama 3 (70b) for high reasoning capability and strict instruction following.
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_INSTRUCTION
                },
                {
                    "role": "user",
                    "content": spoken_text
                }
            ],
            temperature=0.1, # Low temperature = more deterministic/consistent output
            response_format={"type": "json_object"} # Forces strict JSON mode
        )

        # 4. PARSING RESPONSE
        response_content = completion.choices[0].message.content
        isl_data = json.loads(response_content)
        
        return isl_data

    except json.JSONDecodeError:
        return {"error": "Failed to parse JSON from Groq response."}
    except Exception as e:
        return {"error": str(e)}

# --- EXECUTION BLOCK ---
if __name__ == "__main__":
    # Example Input: A typical classroom command
    input_text = "Good morning students, please open your math books."
    
    # Get the ISL Instructions
    result = generate_isl_sequence(input_text)
    
    # Print the clean JSON output
    print("\n✅ ISL GENERATION SUCCESSFUL:\n")
    print(json.dumps(result, indent=2))
