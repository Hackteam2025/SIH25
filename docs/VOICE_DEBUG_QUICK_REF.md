# Voice AI Quick Debug Reference Card 🔍

## 🎯 What to Watch For

### Browser Console (F12)

#### ✅ Good Signs
```
🎉 [Pipecat] User connected to Daily room
✅ [Pipecat] Bot is ready for conversation!
🎤 [User] Started speaking          ← VAD detecting your voice
👤 [User Transcript]: { text: "..." } ← STT working
🤖 [Bot] Started speaking            ← Bot responding
```

#### ❌ Warning Signs
```
❌ [Pipecat Error]: ...
❌ [Voice AI] Connection failed: ...
(No 🎤 [User] Started speaking when you talk) ← VAD not detecting
(No 👤 [User Transcript] after speaking) ← STT not working
```

### Backend Terminal

#### ✅ Good Signs
```
✅ Voice bot is now listening for audio input...
👤 First participant joined: user-123
```

#### ❌ Warning Signs
```
💥 Error in voice bot: ...
ImportError: ...
Bot process failed to start
```

## 🧪 Test Sequence

1. **Start Backend** → Wait for "✅ Voice bot is now listening..."
2. **Open Browser Console (F12)** → Keep it visible
3. **Click "Start Voice AI"** → Watch for connection logs
4. **Grant Mic Permission** → Browser prompt
5. **Speak "Hello"** → Watch for 🎤 and 👤 logs
6. **Wait for Bot** → Watch for 🤖 logs

## 🐛 Quick Fixes

### Problem: No 🎤 [User] Started speaking

**Cause**: VAD not detecting voice

**Fix**:
```python
# In pipecat_bot.py line 93-94
"threshold": 0.3,      # Lower = more sensitive (default: 0.5)
"min_volume": 0.4      # Lower = more sensitive (default: 0.6)
```

### Problem: Invalid Token

**Cause**: Fixed in latest code, but if still occurs:

**Check**:
- Backend shows: "Created/using Daily room with meeting token" ✅
- Not: "using API key as token" ❌

### Problem: Import Errors

**Cause**: Wrong Pipecat version or import paths

**Verify**:
```bash
python verify_voice_setup.py
```

Should show:
```
✅ SonioxSTTService import path correct
✅ GroqLLMService import path correct
✅ DailyTransport import path correct
```

## 📊 Log Analysis

### Scenario 1: Nothing Happens

**Symptoms**: No logs at all when clicking "Start Voice AI"

**Check**:
1. Is backend running? (Should see "Voice bot is now listening...")
2. Correct backend URL? (Console shows: `🌐 [Voice AI] Backend URL: http://localhost:8001`)
3. API keys configured? (`python verify_voice_setup.py`)

### Scenario 2: Connects But No Speech Detection

**Symptoms**:
- ✅ "Bot is ready for conversation!"
- ❌ No 🎤 logs when speaking

**Check**:
1. Microphone permissions granted?
2. Correct microphone selected in browser settings?
3. Try speaking louder
4. Lower VAD threshold (see Quick Fix above)

### Scenario 3: Speech Detected But No Transcript

**Symptoms**:
- ✅ 🎤 [User] Started speaking
- ❌ No 👤 [User Transcript]

**Check**:
1. Backend logs for Soniox errors
2. `SONIOX_API_KEY` in `.env`
3. Internet connection (Soniox is cloud-based)

### Scenario 4: Transcript But No Bot Response

**Symptoms**:
- ✅ 👤 [User Transcript] appears
- ❌ No 🤖 [Bot] Started speaking

**Check**:
1. Backend logs for Groq/Sarvam errors
2. `GROQ_API_KEY` and `SARVAM_API_KEY` in `.env`
3. API rate limits

## 🎤 Testing Phrases

### English
- "Hello, can you hear me?"
- "What is an ARGO float?"
- "Tell me about ocean temperature"

### Hindi (After clicking "हिंदी में बदलें")
- "नमस्ते, क्या आप मुझे सुन सकते हैं?"
- "ARGO फ्लोट क्या है?"
- "समुद्र के तापमान के बारे में बताएं"

## 📋 Share This When Reporting Issues

If you encounter problems, share:

1. **Last 10-15 console logs** (the emoji-marked ones)
2. **Backend terminal output** (from bot initialization)
3. **What you said** vs **what appeared in logs**
4. **Output of**: `python verify_voice_setup.py`

## 🔗 Full Documentation

- Detailed guide: `docs/VOICE_AI_LOGGING_GUIDE.md`
- Setup verification: `python verify_voice_setup.py`
- Testing guide: `docs/PHASE3_READY_TO_TEST.md`

---

**Current Status**: ✅ All checks passed, ready to test!

**Test command**: `python run_mvp.py`
