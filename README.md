# Zafar - AI Freight Dispatcher

Zafar is an AI-powered voice assistant for freight dispatching built using Twilio, Flask, OpenAI, and Google Text-to-Speech. It simulates a professional dispatcher named **Zafar** who handles broker calls, negotiates loads, and remembers context across the conversation.

## 🌐 Features

- Simulates a live dispatcher conversation via Twilio Voice API
- Understands speech input and replies using GPT-3.5
- Converts AI responses to natural-sounding speech via Google TTS
- Context memory using short-term in-memory history
- Filler audio interjections for a more natural experience
- Deployed on Render / Ngrok

---

## 🚀 Technologies Used

- Python (Flask)
- Twilio Voice API
- OpenAI GPT-3.5
- Google Cloud Text-to-Speech
- Render or Ngrok (for webhook exposure)

---

## 🛠 Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/zafar.git
cd zafar
```

### 2. Set up environment variables

Create a `.env` file or export them manually:

```bash
export OPENAI_API_KEY=your_openai_api_key
export GOOGLE_TTS_API_KEY=your_google_tts_key
```

### 3. Add your filler MP3s

Place your `.mp3` filler files in:

```
static/fillers/
```

### 4. Run Flask locally

```bash
python3 main.py
```

Ensure port `8000` is free or change it in `main.py`.

---

## 📞 Twilio Setup

### 1. Buy a phone number

- Go to [Twilio Console](https://www.twilio.com/console)

### 2. Configure voice webhook

- Set the **Voice webhook** to:

```
https://your-ngrok-or-render-url.com/voice
```

Ensure it's a `POST` request.

---

## 📦 Making a Call via Curl

```bash
curl -X POST https://api.twilio.com/2010-04-01/Accounts/YOUR_SID/Calls.json \
  --data-urlencode "Url=https://your-public-url/voice" \
  --data-urlencode "To=+17472123561" \
  --data-urlencode "From=+15716199102" \
  -u "YOUR_SID:YOUR_AUTH_TOKEN"
```

---

## 💡 Tips

- Make sure `.mp3` files are under 1MB for fast streaming.
- Use a production-ready deployment like Render, Fly.io, or Heroku if moving beyond Ngrok.
- Memory is session-based (`CallSid`) and short-term. Consider Redis for persistent memory if needed.

---


---

## 📄 License

MIT
