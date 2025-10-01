/**
 * Voice Service Integration with Pipecat Pipeline
 * Connects the ocean-themed frontend with your existing voice AI backend
 */

export interface VoiceSession {
  session_id: string;
  language: string;
  status: 'connected' | 'disconnected' | 'error';
}

export interface VoiceMessage {
  transcript: string;
  confidence: number;
  language: string;
  timestamp: Date;
}

export class PipecatVoiceService {
  private baseUrl: string;
  private sessionId: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
  }

  async startSession(language: string = 'en-US'): Promise<VoiceSession> {
    const response = await fetch(`${this.baseUrl}/voice/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language })
    });

    if (!response.ok) {
      throw new Error(`Failed to start voice session: ${response.statusText}`);
    }

    const session = await response.json();
    this.sessionId = session.session_id;
    return session;
  }

  async stopSession(): Promise<void> {
    if (!this.sessionId) return;

    await fetch(`${this.baseUrl}/voice/stop`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: this.sessionId })
    });

    this.sessionId = null;
  }

  async processAudio(audioBlob: Blob): Promise<VoiceMessage> {
    if (!this.sessionId) {
      throw new Error('No active voice session');
    }

    const formData = new FormData();
    formData.append('audio', audioBlob);
    formData.append('session_id', this.sessionId);

    const response = await fetch(`${this.baseUrl}/voice/process`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      throw new Error(`Voice processing failed: ${response.statusText}`);
    }

    return await response.json();
  }
}
