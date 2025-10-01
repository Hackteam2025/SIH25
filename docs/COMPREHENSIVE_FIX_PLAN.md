# 🔧 FloatChat Comprehensive Fix Plan

**Date**: September 30, 2025
**Status**: Ready for Implementation
**Estimated Time**: 4-6 hours

---

## 🎯 Executive Summary

Your FloatChat application has **architectural fragmentation** preventing proper integration between frontend and backend. This document provides step-by-step fixes to restore full functionality.

**Current Issues**:
- ❌ Frontend bypasses backend APIs (talks directly to Supabase)
- ❌ Voice AI runs as isolated subprocess
- ❌ Chat interface cannot reach AGNO agent
- ❌ Visualizations use mock data instead of real database
- ❌ Supabase RLS blocking REST API access (401 errors)

**After Fixes**:
- ✅ Frontend properly integrates with backend APIs
- ✅ Voice AI integrated using Pipecat React SDK
- ✅ Chat routes through AGNO agent with MCP tools
- ✅ Visualizations fetch real data from Supabase
- ✅ All services communicate through proper architecture

---

## 📋 Fix Priority Order

### **Phase 1: Critical Database Access (15 minutes)**
1. Fix Supabase RLS policies to allow frontend access
2. Update environment variables for React frontend

### **Phase 2: Backend API Fixes (45 minutes)**
3. Fix DATAOPS import paths
4. Align AGENT API with frontend expectations
5. Connect visualizations to real data

### **Phase 3: Voice AI Migration (2 hours)**
6. Migrate from Python subprocess to Pipecat React SDK
7. Integrate voice with chat interface
8. Setup Daily.co WebRTC transport

### **Phase 4: Frontend Integration (1 hour)**
9. Remove direct Supabase bypass logic
10. Route all requests through backend APIs
11. Add proper error handling and fallbacks

### **Phase 5: Testing & Validation (30 minutes)**
12. End-to-end testing of all components
13. Performance optimization
14. Documentation updates

---

## 🔥 Phase 1: Critical Database Access

### **Fix 1.1: Enable Supabase REST API Access**

**Problem**: React frontend gets 401 errors when accessing Supabase REST API due to Row Level Security (RLS).

**Solution**: Create RLS policies to allow anonymous read access.

**File**: Run in Supabase SQL Editor (https://app.supabase.com/project/ampdkmvvytxlrdtmvmqv/editor/sql)

```sql
-- Allow anonymous users to read all tables
CREATE POLICY "Allow anonymous read profiles" ON profiles
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous read observations" ON observations
  FOR SELECT USING (true);

CREATE POLICY "Allow anonymous read floats" ON floats
  FOR SELECT USING (true);

-- Verify policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public';
```

**Verification**:
```bash
# Test from command line
curl -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     "https://ampdkmvvytxlrdtmvmqv.supabase.co/rest/v1/profiles?limit=1"
```

Expected: HTTP 200 with profile data

---

### **Fix 1.2: Update React Frontend Environment**

**Problem**: React frontend missing environment variables for Supabase access.

**File**: `sih25/FRONTEND_REACT/.env`

**Action**: Create new file with:

```env
# Supabase Configuration
VITE_SUPABASE_URL=https://ampdkmvvytxlrdtmvmqv.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFtcGRrbXZ2eXR4bHJkdG12bXF2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgxMDcwODgsImV4cCI6MjA3MzY4MzA4OH0.wwfhj7hg8erqjNLhyURk8heXTn2B6PqVgBaYei-xVIY

# Backend API URLs
VITE_API_URL=http://localhost:8000
VITE_AGENT_API_URL=http://localhost:8001
VITE_DATAOPS_API_URL=http://localhost:8002

# Voice AI Configuration
VITE_DAILY_API_KEY=a273b885a3f6631090693cd52b8d517dde53d352c492455ad75c8154425637f2
VITE_DAILY_ROOM_URL=https://pdv.daily.co/prada
```

**Verification**:
```bash
cd sih25/FRONTEND_REACT
bun run dev
# Open browser: http://localhost:5173
# Check console: Should see successful API calls
```

---

## 🔧 Phase 2: Backend API Fixes

### **Fix 2.1: Fix DATAOPS Import Paths**

**Problem**: DATAOPS/main.py uses incorrect relative imports.

**File**: `sih25/DATAOPS/main.py`

**Current Code (Lines 17-21)**:
```python
import sys
sys.path.append(str(Path(__file__).parent.parent))
from DATAOPS.PROFILES.main_orchestrator import argo_batch_pipeline  # ❌ WRONG
```

**Fixed Code**:
```python
# Remove sys.path manipulation
from sih25.DATAOPS.PROFILES.main_orchestrator import argo_batch_pipeline  # ✅ CORRECT
```

**Full Fix**:
```python
#!/usr/bin/env python3
"""
FastAPI DataOps Server for SIH25
"""
import os
import logging
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from pathlib import Path
import base64

# ✅ FIXED IMPORT
from sih25.DATAOPS.PROFILES.main_orchestrator import argo_batch_pipeline

# ... rest of the file stays the same
```

**Verification**:
```bash
cd /Users/prada/Desktop/coding/SIH25
uv run python -c "from sih25.DATAOPS.PROFILES.main_orchestrator import argo_batch_pipeline; print('✅ Import works!')"
```

---

### **Fix 2.2: Align AGENT API with Frontend**

**Problem**: Frontend sends different JSON structure than AGENT API expects.

**Current Situation**:
- **Frontend sends**: `{message: string, session_id: string, context: object}`
- **Backend expects**: `ChatRequest` model with those fields

**File**: `sih25/AGENT/api.py`

**No changes needed!** The API is actually correct. The issue is in the **Dash frontend**.

**File**: `sih25/FRONTEND/app.py`

**Current Code (Line 928)**:
```python
response = requests.post(
    f"{AGENT_API_URL}/agent/chat",
    json={
        "message": message,
        "session_id": session_id,
        "context": {"interface": "dashboard"}
    },
    timeout=30
)
```

**This is correct!** The real issue is that React frontend bypasses this entirely.

---

### **Fix 2.3: Connect Visualizations to Real Data**

**Problem**: Dash frontend generates fake data instead of querying database.

**File**: `sih25/FRONTEND/app.py`

**Current Code (Lines 416-471)**:
```python
def create_world_map():
    """Create interactive world map with ARGO float locations"""
    fig = go.Figure()

    # Sample ARGO float locations (Indian Ocean focus)
    import numpy as np

    # Generate realistic ARGO float positions
    lats = np.random.uniform(-60, 60, 25)  # ❌ FAKE DATA
    lons = np.random.uniform(-180, 180, 25)
    float_ids = [f"ARGO-{1000+i:04d}" for i in range(25)]
    temps = np.random.uniform(5, 30, 25)
```

**Fixed Code**:
```python
def create_world_map():
    """Create interactive world map with ARGO float locations"""
    import requests
    import numpy as np

    fig = go.Figure()

    try:
        # ✅ Fetch real data from MCP API
        response = requests.get(
            f"{MCP_API_URL}/tools/list_profiles",
            params={
                "min_lat": -90,
                "max_lat": 90,
                "min_lon": -180,
                "max_lon": 180,
                "max_results": 50
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            profiles = data.get("data", [])

            if profiles:
                lats = [p["latitude"] for p in profiles]
                lons = [p["longitude"] for p in profiles]
                float_ids = [p["profile_id"] for p in profiles]
                # Get temperature from observations if available
                temps = [p.get("temperature", 15.0) for p in profiles]
            else:
                # Fallback to empty state
                return create_empty_map_message()
        else:
            logger.warning(f"MCP API returned {response.status_code}, using sample data")
            return create_sample_map()

    except Exception as e:
        logger.error(f"Failed to fetch profiles: {e}")
        return create_sample_map()

    # Add temperature data for color coding
    fig.add_trace(go.Scattergeo(
        lat=lats,
        lon=lons,
        mode='markers',
        marker=dict(
            size=12,
            color=temps,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Surface Temp (°C)", x=1.02),
            line=dict(width=1, color='white')
        ),
        text=[f"{fid}<br>Temp: {temp:.1f}°C" for fid, temp in zip(float_ids, temps)],
        hovertemplate='<b>%{text}</b><br>Lat: %{lat:.2f}<br>Lon: %{lon:.2f}<extra></extra>',
        name="ARGO Floats"
    ))

    fig.update_layout(
        title={
            'text': f"🌍 Real-Time ARGO Float Network ({len(lats)} floats)",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#1e3c72'}
        },
        geo=dict(
            projection_type='natural earth',
            showland=True,
            landcolor='lightgray',
            showocean=True,
            oceancolor='lightblue',
            showlakes=True,
            lakecolor='lightblue',
            showcoastlines=True,
            coastlinecolor="RebeccaPurple"
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_sample_map():
    """Fallback sample map when API unavailable"""
    import numpy as np
    fig = go.Figure()

    lats = np.random.uniform(-60, 60, 25)
    lons = np.random.uniform(-180, 180, 25)
    temps = np.random.uniform(5, 30, 25)

    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons, mode='markers',
        marker=dict(size=12, color=temps, colorscale='Viridis'),
        name="Sample Data"
    ))

    fig.update_layout(
        title="🔌 Sample Data (API Offline)",
        geo=dict(projection_type='natural earth')
    )
    return fig
```

**Apply same pattern to**:
- `create_profile_plot()` (Lines 473-522)
- `create_timeseries_plot()` (Lines 524-575)

---

## 🎤 Phase 3: Voice AI Migration to Pipecat React

### **Fix 3.1: Install Pipecat React SDK**

**File**: `sih25/FRONTEND_REACT/package.json`

**Action**: Add dependencies

```bash
cd sih25/FRONTEND_REACT
bun add @pipecat-ai/client-js @pipecat-ai/client-react @pipecat-ai/daily-transport
```

---

### **Fix 3.2: Create Pipecat Voice Component**

**File**: `sih25/FRONTEND_REACT/src/components/voice/PipecatVoiceChat.tsx` (NEW FILE)

```typescript
import React, { useCallback, useEffect } from 'react';
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import {
  PipecatClientProvider,
  PipecatClientAudio,
  PipecatClientMicToggle,
  usePipecatClient,
  useRTVIClientEvent,
  usePipecatClientTransportState
} from '@pipecat-ai/client-react';
import { Mic, MicOff, Loader2 } from 'lucide-react';
import { Button } from '../ui/Button';

// Create Pipecat client instance
const pipecatClient = new PipecatClient({
  transport: new DailyTransport(),
  enableMic: true,
  enableCam: false,
  callbacks: {
    onConnected: () => console.log('🎤 User connected to voice'),
    onDisconnected: () => console.log('🔇 User disconnected from voice'),
    onBotReady: () => console.log('🤖 Bot ready for voice chat'),
    onBotConnected: () => console.log('🔗 Bot voice connected'),
  },
});

// Inner component that uses hooks
function VoiceControls({ onTranscript }: { onTranscript?: (text: string) => void }) {
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();

  // Listen for bot messages (transcriptions)
  useRTVIClientEvent(
    RTVIEvent.BotTranscript,
    useCallback((transcript: any) => {
      console.log('🎙️ Bot transcript:', transcript);
      onTranscript?.(transcript.text);
    }, [onTranscript])
  );

  // Listen for user transcript
  useRTVIClientEvent(
    RTVIEvent.UserTranscript,
    useCallback((transcript: any) => {
      console.log('👤 User said:', transcript.text);
    }, [])
  );

  const startVoice = async () => {
    try {
      // Connect to your voice backend endpoint
      const BACKEND_URL = import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8001';
      await client.connect({
        endpoint: `${BACKEND_URL}/voice/connect`,
        config: {
          session_id: `voice-${Date.now()}`
        }
      });
    } catch (error) {
      console.error('Failed to start voice:', error);
    }
  };

  const stopVoice = () => {
    client.disconnect();
  };

  const isConnected = transportState === 'connected' || transportState === 'ready';
  const isConnecting = transportState === 'connecting';

  return (
    <div className="flex items-center gap-3">
      {/* Start/Stop Button */}
      {!isConnected && !isConnecting && (
        <Button
          onClick={startVoice}
          className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700"
        >
          <Mic className="h-5 w-5 mr-2" />
          Start Voice AI
        </Button>
      )}

      {isConnecting && (
        <Button disabled className="bg-gray-400">
          <Loader2 className="h-5 w-5 mr-2 animate-spin" />
          Connecting...
        </Button>
      )}

      {isConnected && (
        <>
          {/* Microphone Toggle */}
          <PipecatClientMicToggle>
            {({ disabled, isMicEnabled, onClick }) => (
              <Button
                disabled={disabled}
                onClick={onClick}
                className={
                  isMicEnabled
                    ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700'
                    : 'bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700'
                }
              >
                {isMicEnabled ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
                <span className="ml-2">{isMicEnabled ? 'Mute' : 'Unmute'}</span>
              </Button>
            )}
          </PipecatClientMicToggle>

          {/* Stop Button */}
          <Button
            onClick={stopVoice}
            variant="outline"
            className="border-red-500 text-red-500 hover:bg-red-50"
          >
            Stop Voice
          </Button>

          {/* Status Indicator */}
          <div className="flex items-center gap-2 text-sm text-green-600">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            Voice AI Active
          </div>
        </>
      )}
    </div>
  );
}

// Main export component
export default function PipecatVoiceChat({ onTranscript }: { onTranscript?: (text: string) => void }) {
  return (
    <PipecatClientProvider client={pipecatClient}>
      <VoiceControls onTranscript={onTranscript} />
      {/* Audio player for bot responses */}
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}
```

---

### **Fix 3.3: Integrate Voice with Chat Interface**

**File**: `sih25/FRONTEND_REACT/src/components/ChatInterface.tsx`

**Changes**:

1. **Import Pipecat component** (add to imports):
```typescript
import PipecatVoiceChat from './voice/PipecatVoiceChat';
```

2. **Replace voice buttons** (Lines 613-643):

**Remove old code**:
```typescript
{/* Simple Voice Button */}
<Button onClick={toggleSimpleVoice} ... >
  {isListening ? <MicOff /> : <Mic />}
</Button>

{/* Advanced Voice Button (Pipecat) */}
<Button onClick={toggleAdvancedVoice} ... >
  <Zap className="h-5 w-5" />
</Button>
```

**Replace with**:
```typescript
{/* Pipecat Voice Integration */}
<PipecatVoiceChat
  onTranscript={(text) => {
    // When voice produces transcript, send it as message
    setInput(text);
    sendMessage();
  }}
/>
```

3. **Remove old voice functions** (delete Lines 193-304):
- `toggleAdvancedVoice()`
- `toggleSimpleVoice()`

---

### **Fix 3.4: Create Backend Voice Connect Endpoint**

**Problem**: Pipecat needs `/voice/connect` endpoint to establish WebRTC session.

**File**: `sih25/AGENT/main.py`

**Add new endpoint**:

```python
from fastapi import FastAPI, WebSocket
from sih25.VOICE_AI.pipecat_handler import create_voice_session

# Add to existing app
@app.post("/voice/connect")
async def voice_connect(request: dict):
    """
    Pipecat client connects here to establish voice session.
    Returns Daily.co room configuration.
    """
    try:
        session_id = request.get("session_id", f"voice-{datetime.now().timestamp()}")

        # Create Daily.co room for this session
        daily_api_key = os.getenv("DAILY_API_KEY")
        daily_room_url = os.getenv("DAILY_ROOM_URL")

        if not daily_api_key or not daily_room_url:
            raise HTTPException(
                status_code=500,
                detail="Daily.co not configured. Set DAILY_API_KEY and DAILY_ROOM_URL in .env"
            )

        # Return room configuration for Pipecat client
        return {
            "room_url": daily_room_url,
            "token": daily_api_key,  # In production, generate ephemeral tokens
            "session_id": session_id,
            "bot_ready": True
        }

    except Exception as e:
        logger.error(f"Voice connect failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🔗 Phase 4: Frontend Integration

### **Fix 4.1: Route Frontend Through Backend APIs**

**Problem**: React frontend bypasses backend and talks directly to Supabase.

**File**: `sih25/FRONTEND_REACT/src/services/api.ts`

**Current Code (Lines 58-129)**: Direct Supabase access

**Strategy**: Keep Supabase as **fallback**, but prioritize backend APIs.

**Revised Code**:

```typescript
// Backend API Client
const backendClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,  // http://localhost:8000
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Unified API that tries backend first, falls back to Supabase
export const api = {
  // Get profiles - tries MCP API first
  async getProfiles(limit: number = 100): Promise<Profile[]> {
    try {
      // ✅ TRY BACKEND FIRST
      const response = await backendClient.post('/tools/list_profiles', {
        min_lat: -90,
        max_lat: 90,
        min_lon: -180,
        max_lon: 180,
        max_results: limit
      });

      const profiles = response.data.data || [];
      console.log(`✅ Fetched ${profiles.length} profiles from backend`);
      return profiles;

    } catch (backendError) {
      console.warn('⚠️ Backend unavailable, falling back to Supabase');

      // FALLBACK TO SUPABASE
      try {
        const response = await supabaseClient.get('/profiles', {
          headers: { 'Range': `0-${limit - 1}` }
        });
        return response.data || [];
      } catch (supabaseError) {
        console.error('❌ Both backend and Supabase failed');
        return [];
      }
    }
  },

  // Chat - route through AGNO agent
  async sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
    try {
      const response = await backendClient.post('/agent/chat', {
        message: message,
        session_id: sessionId || `session_${Date.now()}`,
        context: { interface: 'react' }
      });

      return {
        response: response.data.response,
        session_id: response.data.session_id,
        suggestions: response.data.follow_up_suggestions || []
      };

    } catch (error) {
      console.error('Chat API error:', error);
      // Fallback to simple response
      return {
        response: 'I apologize, the AI agent is currently unavailable. Please try again later.',
        session_id: sessionId || `session_${Date.now()}`,
        suggestions: []
      };
    }
  },

  // Health check for connection status
  async checkBackendHealth(): Promise<boolean> {
    try {
      const response = await backendClient.get('/health');
      return response.data.status === 'healthy';
    } catch {
      return false;
    }
  }
};

// Keep old exports for backward compatibility
export const supabaseApi = { /* existing code */ };
export const chatApi = { /* existing code */ };
export default api;
```

---

### **Fix 4.2: Update App.tsx to Use Backend**

**File**: `sih25/FRONTEND_REACT/src/App.tsx`

**Current Code (Lines 118-170)**: Direct Supabase access in Dashboard

**Revised Code**:

```typescript
const fetchStats = async () => {
  setConnectionStatus('loading')
  try {
    console.log('🔄 Fetching stats from backend...')

    // ✅ Check backend health first
    const isHealthy = await api.checkBackendHealth()

    if (!isHealthy) {
      console.warn('⚠️ Backend offline, trying Supabase directly')
      // Fallback to Supabase (existing code)
      const profiles = await api.supabase.getProfiles(100)
      // ... existing fallback logic
      return
    }

    // ✅ Fetch from backend (which uses MCP tools)
    const profiles = await api.getProfiles(100)
    console.log(`✅ Fetched ${profiles.length} profiles via backend`)

    if (profiles.length > 0) {
      // Calculate stats from profiles
      const temps = profiles.map((p: any) => p.temperature).filter((t: number) => !isNaN(t))
      const salinities = profiles.map((p: any) => p.salinity).filter((s: number) => !isNaN(s))
      const depths = profiles.map((p: any) => p.depth).filter((d: number) => !isNaN(d))

      setStats({
        totalProfiles: profiles.length,
        avgTemperature: temps.length > 0 ? temps.reduce((a, b) => a + b, 0) / temps.length : 0,
        avgSalinity: salinities.length > 0 ? salinities.reduce((a, b) => a + b, 0) / salinities.length : 0,
        depthRange: {
          min: depths.length > 0 ? Math.min(...depths) : 0,
          max: depths.length > 0 ? Math.max(...depths) : 0
        }
      })
      setConnectionStatus('connected')
    }
  } catch (error) {
    console.error('❌ Failed to fetch stats:', error)
    setConnectionStatus('offline')
    // Show offline message
  }
}
```

---

## ✅ Phase 5: Testing & Validation

### **Test 5.1: Backend Services Health Check**

```bash
# Terminal 1: Start all backend services
cd /Users/prada/Desktop/coding/SIH25
python run_mvp.py

# Wait for all services to start (~30 seconds)
# You should see:
# ✅ MCP Tool Server started on http://localhost:8000
# ✅ AGNO Agent Server started on http://localhost:8001
# ✅ DataOps Server started on http://localhost:8002
# ✅ Frontend Dashboard started on http://localhost:8050
```

**Verify each service**:

```bash
# Terminal 2: Test health endpoints
curl http://localhost:8000/health
# Expected: {"status":"healthy","database":"connected","service":"MCP Tool Server"}

curl http://localhost:8001/health
# Expected: {"status":"healthy","service":"Agent Server"}

curl http://localhost:8002/health
# Expected: {"status":"healthy","service":"DataOps Server"}
```

---

### **Test 5.2: React Frontend Integration**

```bash
# Terminal 3: Start React frontend
cd sih25/FRONTEND_REACT
bun run dev

# Open browser: http://localhost:5173
```

**Expected Behavior**:
1. ✅ Dashboard loads without errors
2. ✅ Connection status shows "Connected to backend API" (green)
3. ✅ Stats show real data from database (not mock data)
4. ✅ No 401 errors in console
5. ✅ Visualizations display real profiles

---

### **Test 5.3: Chat Integration**

**In React Frontend** (http://localhost:5173):

1. Click "AI Chat" tab
2. Type: "Show me profiles near the equator"
3. Click Send

**Expected**:
- ✅ Message sent to AGNO agent at http://localhost:8001/agent/chat
- ✅ Agent uses MCP tools to query database
- ✅ Response includes actual data insights
- ✅ Follow-up suggestions appear

**Check Backend Logs**:
```
[AGNO Agent] Received query: "Show me profiles near the equator"
[MCP Tools] Calling list_profiles with lat -10 to 10
[Database] Found 15 profiles
[AGNO Agent] Returning response with 15 profiles
```

---

### **Test 5.4: Voice AI Integration**

**In React Frontend** (http://localhost:5173):

1. Click "AI Chat" tab
2. Click "Start Voice AI" button
3. Allow microphone access
4. Speak: "What's the temperature in the Pacific Ocean?"

**Expected**:
- ✅ Voice button shows "Voice AI Active" with green indicator
- ✅ Microphone captures audio
- ✅ Transcription appears in chat input
- ✅ Message automatically sent to agent
- ✅ Bot responds with voice (audio plays)

**Check Backend Logs**:
```
[Voice API] Voice connect request received
[Daily.co] Room created: https://pdv.daily.co/prada
[Pipecat] Client connected via WebRTC
[Voice Pipeline] Audio stream active
[AGNO Agent] Processing voice query: "What's the temperature..."
```

---

### **Test 5.5: Data Visualization**

**In Dash Frontend** (http://localhost:8050):

1. Open dashboard
2. Check visualizations

**Expected**:
- ✅ World map shows real float locations (not random)
- ✅ Profile plots show actual depth profiles from database
- ✅ Time series shows real measurement timestamps
- ✅ Hover tooltips display actual profile IDs and values

---

## 📊 Success Metrics

After all fixes, you should have:

| Metric | Before | After |
|--------|--------|-------|
| Frontend-Backend Integration | ❌ Bypassed | ✅ Connected |
| Chat Functionality | ❌ Mock responses | ✅ AI-powered |
| Voice AI | ❌ Subprocess | ✅ WebRTC integrated |
| Data Visualizations | ❌ Fake data | ✅ Real database |
| Supabase Access | ❌ 401 errors | ✅ Working |
| API Response Time | N/A | < 500ms |
| Session Management | ❌ None | ✅ Unified |

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All unit tests pass
- [ ] End-to-end tests pass
- [ ] Backend services start without errors
- [ ] Frontend connects to all backend APIs
- [ ] Voice AI establishes WebRTC connections
- [ ] Supabase RLS policies are production-ready
- [ ] Environment variables secured
- [ ] API rate limits configured
- [ ] Error handling and fallbacks tested
- [ ] Performance profiling complete
- [ ] Documentation updated

---

## 🐛 Troubleshooting

### **Issue: 401 Errors Persist**

**Solution**:
```sql
-- In Supabase SQL Editor, verify policies exist:
SELECT * FROM pg_policies WHERE schemaname = 'public';

-- If no policies, recreate them:
CREATE POLICY "Allow anonymous read profiles" ON profiles FOR SELECT USING (true);
CREATE POLICY "Allow anonymous read observations" ON observations FOR SELECT USING (true);
CREATE POLICY "Allow anonymous read floats" ON floats FOR SELECT USING (true);
```

### **Issue: Voice AI Not Connecting**

**Check**:
1. Daily.co credentials in `.env`:
   ```bash
   echo $DAILY_API_KEY
   echo $DAILY_ROOM_URL
   ```
2. Backend `/voice/connect` endpoint accessible:
   ```bash
   curl http://localhost:8001/voice/connect -X POST -H "Content-Type: application/json" -d '{"session_id":"test"}'
   ```
3. Browser console for WebRTC errors

### **Issue: AGNO Agent Not Responding**

**Check**:
1. Agent service running:
   ```bash
   curl http://localhost:8001/health
   ```
2. GROQ API key valid:
   ```bash
   echo $GROQ_API_KEY
   ```
3. MCP server accessible from agent:
   ```bash
   curl http://localhost:8000/mcp/status
   ```

### **Issue: Visualizations Still Show Mock Data**

**Verify**:
1. Backend returns data:
   ```bash
   curl -X POST http://localhost:8000/tools/list_profiles \
     -H "Content-Type: application/json" \
     -d '{"min_lat":-90,"max_lat":90,"min_lon":-180,"max_lon":180,"max_results":10}'
   ```
2. Frontend calls backend:
   - Open DevTools → Network tab
   - Look for requests to `localhost:8000`
   - Check response data

---

## 📝 Next Steps

After completing all fixes:

1. **Performance Optimization**
   - Add Redis caching for frequent queries
   - Implement request batching
   - Enable HTTP/2

2. **Enhanced Features**
   - Real-time database subscriptions (Supabase Realtime)
   - Voice command shortcuts
   - Export data to CSV/NetCDF

3. **Production Deployment**
   - Dockerize all services
   - Setup CI/CD pipeline
   - Configure monitoring (Sentry, Datadog)
   - Enable SSL/TLS

4. **Documentation**
   - API documentation (OpenAPI/Swagger)
   - User guide for voice commands
   - Developer onboarding guide

---

## 📞 Support

If you encounter issues during implementation:

1. Check logs in respective service directories
2. Review console output in browser DevTools
3. Verify environment variables are loaded correctly
4. Test each service independently before integration

**Estimated Total Implementation Time**: 4-6 hours

**Recommended Approach**: Implement fixes in order (Phase 1 → Phase 5) to minimize breakage.

Good luck! 🚀