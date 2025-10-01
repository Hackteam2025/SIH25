# 🎯 FloatChat - Quick Setup Guide

## ✅ COMPLETED INTEGRATION

✅ **Modified your existing voice pipeline** to call FastAPI instead of MCP
✅ **Added voice tab** to React frontend
✅ **Created unified API** for both voice and chat queries
✅ **No complex dependencies** - uses SQLite database

## 🚀 Quick Test (3 commands)

### 1. Start Backend
```bash
cd /Users/prada/Desktop/coding/FloatChat_SIH/FloatChat_SIH/backend
python -m app.main
```

### 2. Start Frontend
```bash
cd /Users/prada/Desktop/coding/FloatChat_SIH/FloatChat_SIH/frontend
npm run dev
```

### 3. Test Voice AI (Optional)
```bash
cd /Users/prada/Desktop/coding/FloatChat_SIH/FloatChat_SIH/voice_ai
python oceanographic_voice_pipeline.py
```

## 📱 What Works Now

**Frontend (http://localhost:5173):**
- ✅ Dashboard with ocean data stats
- ✅ Chat interface (type questions)
- ✅ **Voice AI tab** (browser speech recognition)
- ✅ Map visualization
- ✅ Real-time data display

**Backend (http://localhost:8000):**
- ✅ `/api/query` - Natural language queries
- ✅ `/api/voice/query` - Voice-optimized responses
- ✅ Connects to existing SQLite database
- ✅ RAG-powered responses

**Voice AI (Advanced):**
- ✅ Professional Pipecat pipeline
- ✅ Multi-language support (11 Indian + English)
- ✅ Calls your FastAPI backend
- ✅ Text-to-speech responses

## 🎤 Demo Flow

1. **Open frontend** → Click "Voice AI" tab
2. **Click microphone** → Speak: "Show me temperature data"
3. **See real-time response** → AI queries database and responds
4. **Hear spoken answer** → Browser reads response aloud

## 🔧 Environment Setup (Optional)

Copy `.env.example` to `.env` and add your API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## 🎯 For Hackathon Demo

**Minimum viable:** Just run backend + frontend
**Full experience:** Add voice pipeline with API keys
**Presentation ready:** All 3 components running

**Your original sophisticated voice pipeline now works with the simple SQLite setup!**