# Voice AI Enhanced Logging - Debug Guide

## What Was Added

### Frontend Logging (Browser Console)

Added comprehensive event logging to `PipecatVoiceChat.tsx`:

#### **1. Connection Callbacks**
```typescript
callbacks: {
  onConnected: () => console.log('🎉 [Pipecat] User connected to Daily room'),
  onDisconnected: () => console.log('👋 [Pipecat] User disconnected from Daily room'),
  onTransportStateChanged: (state) => console.log('🔄 [Pipecat] Transport state:', state),
  onBotConnected: () => console.log('🤖 [Pipecat] Bot connected to room'),
  onBotDisconnected: () => console.log('🤖 [Pipecat] Bot disconnected from room'),
  onBotReady: () => console.log('✅ [Pipecat] Bot is ready for conversation!'),
}
```

#### **2. ALL RTVI Events**
Now logging ALL events including:
- `Connected` / `Disconnected`
- `TransportStateChanged`
- `BotReady`
- `UserStartedSpeaking` / `UserStoppedSpeaking` ← **This will show when you speak!**
- `BotStartedSpeaking` / `BotStoppedSpeaking`
- `UserTranscript` ← **This will show what you said!**
- `BotTranscript` ← **This will show what bot said!**
- `Metrics`
- `Error`

#### **3. Connection Flow**
```typescript
console.log('🎤 [Voice AI] Starting connection...');
console.log('🌐 [Voice AI] Backend URL:', BACKEND_URL);
console.log('📞 [Voice AI] Calling /voice/connect...');
console.log('✅ [Voice AI] Connected successfully!', response);
```

### Backend Logging (Terminal/run_mvp.py)

Enhanced bot logging with clear stages:

```python
logger.info("=" * 60)
logger.info("🤖 VOICE BOT STARTING")
logger.info("=" * 60)
logger.info("🔧 Initializing Daily transport...")
logger.info("🎤 Initializing Soniox STT...")
logger.info("🧠 Initializing Groq LLM...")
logger.info("🔊 Initializing Sarvam AI TTS...")
logger.info("💬 Setting up conversation context...")
logger.info("🔗 Building Pipecat pipeline...")
logger.info("⚙️ Creating pipeline task...")
logger.info("🚀 Starting voice bot pipeline...")
logger.info("✅ Voice bot is now listening for audio input...")
```

Event handlers:
```python
logger.info(f"👤 First participant joined: {participant_id}")
logger.info(f"👋 Participant left: {participant_id}")
logger.info(f"📞 Call state updated: {state}")
```

## Expected Log Flow

### When You Click "Start Voice AI"

**Browser Console:**
```
🎤 [Voice AI] Starting connection...
🌐 [Voice AI] Backend URL: http://localhost:8001
📞 [Voice AI] Calling /voice/connect...
[Pipecat Client] Fetching from http://localhost:8001/voice/connect
[Pipecat Client] Received response...
🔄 [Pipecat] Transport state: authenticating
🔄 [Pipecat] Transport state: connecting
🎉 [Pipecat] User connected to Daily room
📡 [RTVI Event] Connected: {...}
🔄 [Pipecat] Transport state: connected
🤖 [Pipecat] Bot connected to room
✅ [Pipecat] Bot is ready for conversation!
📡 [RTVI Event] BotReady: {...}
✅ [Voice AI] Connected successfully! {...}
```

**Backend Terminal (run_mvp.py):**
```
[Agno Agent Server] INFO Voice connect request for session: voice-1759330750
[Agno Agent Server] INFO Using pre-configured Daily room: https://...
[Agno Agent Server] INFO Starting bot subprocess for room: https://...
[Agno Agent Server] INFO Bot subprocess started with PID: 12345
[Agno Agent Server] INFO Created/using Daily room with meeting token

============================================================
🤖 VOICE BOT STARTING
============================================================
🔧 Initializing Daily transport...
🎤 Initializing Soniox STT...
🧠 Initializing Groq LLM...
🔊 Initializing Sarvam AI TTS...
💬 Setting up conversation context...
🔗 Building Pipecat pipeline...
⚙️ Creating pipeline task...
🚀 Starting voice bot pipeline...
✅ Voice bot is now listening for audio input...
👤 First participant joined: user-123
```

### When You Speak "Hello"

**Browser Console:**
```
🎤 [User] Started speaking
📡 [RTVI Event] UserStartedSpeaking: {...}
🎤 [User] Stopped speaking
📡 [RTVI Event] UserStoppedSpeaking: {...}
👤 [User Transcript]: { text: "Hello", final: true }
📡 [RTVI Event] UserTranscript: { text: "Hello", final: true }
```

**Backend Terminal:**
```
(Soniox STT processes audio)
(Groq LLM generates response)
(Sarvam AI TTS synthesizes voice)
```

### When Bot Responds

**Browser Console:**
```
🤖 [Bot] Started speaking
📡 [RTVI Event] BotStartedSpeaking: {...}
🤖 [Bot Transcript]: { text: "Hello! I'm FloatChat..." }
📡 [RTVI Event] BotTranscript: {...}
🤖 [Bot] Stopped speaking
📡 [RTVI Event] BotStoppedSpeaking: {...}
```

## Debugging Tips

### If You Don't See User Transcript:

1. **Check microphone permissions**:
   - Browser should prompt for mic access
   - Check browser settings if denied

2. **Check for UserStartedSpeaking events**:
   ```
   🎤 [User] Started speaking  ← Should appear when you talk
   ```
   If missing: VAD (Voice Activity Detection) isn't detecting your voice

3. **Check Soniox STT in backend logs**:
   ```
   🎤 Initializing Soniox STT...  ← Should appear during startup
   ```

### If Bot Doesn't Respond:

1. **Check BotReady event**:
   ```
   ✅ [Pipecat] Bot is ready for conversation!  ← Must appear
   ```

2. **Check backend bot logs for errors**:
   ```
   💥 Error in voice bot: ...  ← Look for this
   ```

3. **Check participant joined event**:
   ```
   👤 First participant joined: ...  ← Bot knows you're there
   ```

## Quick Debug Checklist

- [ ] Backend shows: `✅ Voice bot is now listening for audio input...`
- [ ] Frontend shows: `✅ [Pipecat] Bot is ready for conversation!`
- [ ] Frontend shows: `👤 First participant joined: ...` in backend
- [ ] When speaking: `🎤 [User] Started speaking` appears
- [ ] When speaking: `👤 [User Transcript]: ...` appears
- [ ] Bot responds: `🤖 [Bot] Started speaking` appears

## Files Modified

- `sih25/FRONTEND_REACT/src/components/voice/PipecatVoiceChat.tsx`
- `sih25/VOICE_AI/pipecat_bot.py`

## Testing

1. Restart backend: `python run_mvp.py`
2. Refresh frontend
3. Open browser DevTools Console (F12)
4. Click "Start Voice AI"
5. Watch the logs flow! 📊

All events are now visible with clear emoji markers for easy scanning! 🎉
