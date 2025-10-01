# Voice AI Connection Fix

## Issue
The Pipecat React client was trying to connect to the wrong endpoint and the response format didn't match what Pipecat expects.

## Problems Found

1. **Wrong import names** (FIXED ✅)
   - Was: `RTVIClient`
   - Should be: `PipecatClient`

2. **Wrong connection method** (FIXED ✅)
   - Was: `client.connect({ baseUrl, endpoints })`
   - Should be: `client.startBotAndConnect({ endpoint })`

3. **Wrong response format** (FIXED ✅)
   - Was: `{ url, token, session_id, bot_ready }`
   - Should be: `{ url, token }` (Daily transport expects only these two fields)

## Changes Made

### Frontend (`PipecatVoiceChat.tsx`)

```typescript
// Correct imports
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import {
  PipecatClientProvider,
  usePipecatClient,
  // ... other hooks
} from '@pipecat-ai/client-react';

// Correct connection
const startVoice = async () => {
  const BACKEND_URL = import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8001';

  await client.startBotAndConnect({
    endpoint: `${BACKEND_URL}/voice/connect`
  });
};
```

### Backend (`api.py`)

```python
@router.post("/connect")
async def voice_connect(request: dict = None):
    # ... create room and start bot ...

    # Return ONLY url and token (Daily transport format)
    return {
        "url": room_url,
        "token": token
    }
```

## Testing

1. Make sure backend is running:
   ```bash
   python run_mvp.py
   ```

2. Make sure frontend is running:
   ```bash
   cd sih25/FRONTEND_REACT
   bun run dev
   ```

3. Open browser: `http://localhost:5173`

4. Go to "AI Chat" tab

5. Click "Start Voice AI"

6. Expected flow:
   - Client calls `POST http://localhost:8001/voice/connect`
   - Backend creates Daily room and returns `{ url, token }`
   - Bot subprocess starts
   - Client joins Daily room
   - Voice AI ready! 🎤

## Verification

Check browser console for:
```
🎤 Starting voice AI connection...
[Pipecat Client] Fetching from http://localhost:8001/voice/connect
[Pipecat Client] Received response...
✅ Voice AI connected
```

If you see errors, check:
1. Is `VITE_AGENT_API_URL=http://localhost:8001` set in `.env`?
2. Is Agent server running on port 8001?
3. Are Daily.co credentials configured?

---

**Status**: ✅ FIXED
**Files Modified**:
- `sih25/FRONTEND_REACT/src/components/voice/PipecatVoiceChat.tsx`
- `sih25/VOICE_AI/api.py`
