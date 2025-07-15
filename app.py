from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse, Gather
import openai
import requests
import base64
import os
from collections import defaultdict

import random  # add if not already there

# --- Variations for Zafar's filler catchphrases ---
FILLER_PHRASES = [
    "got_it.mp3",
    "one_sec.mp3",
    "sure_give_me_one_moment.mp3",
    "okay_let_me_check.mp3"
]


conversation_memory = defaultdict(list)

import os
openai.api_key = os.getenv("OPENAI_API_KEY")
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY")
NGROK_URL = "https://zafar-oshz.onrender.com"

app = Flask(__name__)
os.makedirs("static", exist_ok=True)

# --- Session Memory (short-term in-memory context) ---
session_context = {}
last_call_sid = None

# --- Helper: Generate GPT reply ---
def generate_ai_response(session_id, user_input, is_new_call):
    history = session_context.get(session_id, [])
    system_prompt = {
        "role": "system",
        "content": """
You are a professional freight dispatcher for a trucking company called Quadrix and your name is Zafar. You are speaking to a broker on a live phone call. Your goal is to find a load for your available driver.

Start by politely introducing yourself and your company. Then ask the broker if they have any available loads.
Generate a realistic human phone conversation between a dispatcher and a broker. Make the dialogue flow naturally — avoid repeating the same information like load number multiple times. Keep it concise, coherent, and professional, like an actual logistics call.

If they do, ask follow-up questions to gather the following details:
- Pickup location and time
- Delivery location and time
- Commodity
- Rate
- Load requirements (e.g., driver assist, pallet exchange, special equipment, etc.)
- If the load is already covered or still available

- You are capable of bargaining and negotiating. If the user is trying to make a deal, buy or sell something, or negotiate a price or terms, you should respond confidently, make counteroffers (usually with more of a rate than the user gives), ask questions, and try to reach agreement. 
Maintain a friendly, confident tone. Keep each reply under 2 sentences unless more is requested.
You must remember all previously shared details in this call: the load number, pickup, delivery, commodity, rate, requirements. 
Never ask the same question twice if you already know the answer. Instead, confirm or clarify.
"""
    }

    messages = [system_prompt] + history + ([{"role": "user", "content": user_input}] if user_input else [])
    client = openai.OpenAI(api_key=openai.api_key)
    reply = client.chat.completions.create(model="gpt-3.5-turbo", messages=messages)
    answer = reply.choices[0].message.content.strip()

    if is_new_call:
        answer = "Hello! This is Zafar from Quadrix Dispatch. I'm calling regarding load number 125569, from Tashkent to New York. Can you share the rate on that one?"

    session_context[session_id] = messages + [{"role": "assistant", "content": answer}]
    return answer

# --- Helper: Convert text to MP3 using Google TTS ---
def synthesize_speech(text):
    try:
        response = requests.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}",
            json={
                "input": {"text": text},
                "voice": {
                    "languageCode": "en-US",
                    "name": "en-US-Wavenet-B"
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": 1.2,
                    "pitch": 2.0
                }
            }
        )
        response.raise_for_status()
        audio_content = response.json()["audioContent"]
        with open("static/response.mp3", "wb") as f:
            f.write(base64.b64decode(audio_content))
        return f"{NGROK_URL}/static/response.mp3"

    except Exception as e:
        print("🔁 TTS fallback due to:", e)
        response = requests.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}",
            json={
                "input": {"text": text},
                "voice": {
                    "languageCode": "en-US",
                    "name": "en-US-Wavenet-D"
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": 1.8
                }
            }
        )
        response.raise_for_status()
        audio_content = response.json()["audioContent"]
        with open("static/response.mp3", "wb") as f:
            f.write(base64.b64decode(audio_content))
        return f"{NGROK_URL}/static/response.mp3"

# --- Handle incoming call ---
@app.route("/voice", methods=["GET", "POST"])
def voice():
    if request.method == "GET":
        print("⚠️ GET request to /voice")
        response = VoiceResponse()
        response.say("This endpoint expects a POST request. Please configure your webhook to use POST.")
        response.hangup()
        return str(response)

    print("📞 /voice hit with:", request.form)
    call_sid = request.form.get("CallSid", "default")
    global last_call_sid
    is_new_call = call_sid != last_call_sid
    last_call_sid = call_sid

    if is_new_call:
        session_context[call_sid] = []

    ai_reply = generate_ai_response(call_sid, "", is_new_call=True)
    audio_url = synthesize_speech(ai_reply)

    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/process",
        method="POST",
        timeout=10,
        speech_timeout="auto",
        barge_in=True
    )
    gather.play(audio_url)
    response.append(gather)

    response.say("I didn't hear anything. Goodbye.")
    response.hangup()
    return str(response)


@app.route("/process", methods=["POST"])
def process():
    print("📡 /process hit with:", request.form)
    call_sid = request.form.get("CallSid", "default")
    user_input = request.form.get("SpeechResult", "").strip()
    confidence = float(request.form.get("Confidence", "1.0"))

    print(f"🎤 User said: {user_input} (confidence: {confidence:.2f})")

    if not user_input or confidence < 0.3:
        user_input = "Sorry, I didn't catch that. Could you repeat?"
        ai_reply = generate_ai_response(call_sid, user_input, is_new_call=False)
        audio_url = synthesize_speech(ai_reply)

        vr = VoiceResponse()
        gather = Gather(
            input="speech",
            action="/process",
            method="POST",
            timeout=7,
            speech_timeout=1.5,
            barge_in=True
        )
        gather.play(audio_url)
        vr.append(gather)
        vr.say("I didn't hear anything. Goodbye.")
        vr.hangup()
        return str(vr)

    # 🔑 Save what the user said for the follow-up
    session_context[f"{call_sid}_pending_input"] = user_input

    # 🔊 Play a random filler phrase, then redirect to /continue for real reply
    chosen_filler = random.choice(FILLER_PHRASES)
    print(f"🔊 Playing filler: {chosen_filler}")

    vr = VoiceResponse()
    vr.play(f"{NGROK_URL}/static/fillers/{chosen_filler}")
    vr.redirect("/continue")
    return str(vr)


@app.route("/continue", methods=["POST"])
def continue_process():
    print("🚦 /continue hit")

    call_sid = request.form.get("CallSid", "default")
    user_input = session_context.get(f"{call_sid}_pending_input", "Could you repeat that?")

    try:
        ai_reply = generate_ai_response(call_sid, user_input, is_new_call=False)
        audio_url = synthesize_speech(ai_reply)
    except Exception as e:
        print("❌ Error in /continue:", e)
        ai_reply = "Something went wrong. Please try again later."
        audio_url = synthesize_speech(ai_reply)

    vr = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/process",
        method="POST",
        timeout=7,
        speech_timeout=1.5,
        barge_in=True
    )
    gather.play(audio_url)
    vr.append(gather)
    vr.say("I didn't hear anything. Goodbye.")
    vr.hangup()
    return str(vr)


@app.errorhandler(Exception)
def handle_error(e):
    print("🔥 Server error:", e)
    response = VoiceResponse()
    response.say("We are sorry, an unexpected error occurred.")
    response.hangup()
    return str(response)

@app.route("/hangup", methods=["POST"])
def hangup():
    call_sid = request.form.get("CallSid")
    print(f"📞 Call ended: {call_sid}")
    if call_sid in session_context:
        del session_context[call_sid]
        print(f"🧹 Cleared session for {call_sid}")
    return ("", 204)

if __name__ == "__main__":
    app.run(debug=True, port=8000)