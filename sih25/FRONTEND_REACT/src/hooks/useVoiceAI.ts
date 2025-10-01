import { useState, useEffect, useRef, useCallback } from 'react';
import { voiceApi } from '../services/api';

interface VoiceState {
  isActive: boolean;
  isListening: boolean;
  isProcessing: boolean;
  currentLanguage: string;
  sessionId: string | null;
  transcript: string;
  lastResponse: string;
  error: string | null;
  isConnected: boolean;
  confidence: number;
  detectedLanguage?: string;
}

interface UseVoiceAIOptions {
  defaultLanguage?: string;
  autoStart?: boolean;
  onTranscript?: (transcript: string, language?: string) => void;
  onResponse?: (response: string, data?: any) => void;
  onError?: (error: string) => void;
  onLanguageDetected?: (language: string) => void;
  intelligentLanguageSwitching?: boolean; // Enable intelligent language detection
}

export const useVoiceAI = (options: UseVoiceAIOptions = {}) => {
  const {
    defaultLanguage = 'en-US',
    autoStart = false,
    onTranscript,
    onResponse,
    onError,
    onLanguageDetected,
    intelligentLanguageSwitching = true
  } = options;

  const [state, setState] = useState<VoiceState>({
    isActive: false,
    isListening: false,
    isProcessing: false,
    currentLanguage: defaultLanguage,
    sessionId: null,
    transcript: '',
    lastResponse: '',
    error: null,
    isConnected: false,
    confidence: 0
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const connectionCheckRef = useRef<NodeJS.Timeout | null>(null);

  // Check connection status periodically
  const checkConnection = useCallback(async () => {
    try {
      const status = await voiceApi.getConnectionStatus();
      setState(prev => ({
        ...prev,
        isConnected: status.connected
      }));
    } catch (error) {
      setState(prev => ({
        ...prev,
        isConnected: false
      }));
    }
  }, []);

  // Initialize voice session with intelligent language handling
  const startSession = useCallback(async (language?: string) => {
    try {
      setState(prev => ({ ...prev, isProcessing: true, error: null }));

      const targetLanguage = language || state.currentLanguage;
      const result = await voiceApi.startVoiceSession(targetLanguage);

      setState(prev => ({
        ...prev,
        isActive: true,
        sessionId: result.session_id,
        isProcessing: false,
        currentLanguage: targetLanguage,
        isConnected: true
      }));

      // Start connection monitoring
      if (connectionCheckRef.current) {
        clearInterval(connectionCheckRef.current);
      }
      connectionCheckRef.current = setInterval(checkConnection, 5000);

      return result.session_id;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to start voice session';
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: errorMessage,
        isConnected: false
      }));
      onError?.(errorMessage);
      throw error;
    }
  }, [state.currentLanguage, onError, checkConnection]);

  // Stop voice session
  const stopSession = useCallback(async () => {
    try {
      if (state.sessionId) {
        await voiceApi.stopVoiceSession(state.sessionId);
      }

      // Stop any ongoing recording
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }

      // Close media stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }

      // Clear connection monitoring
      if (connectionCheckRef.current) {
        clearInterval(connectionCheckRef.current);
        connectionCheckRef.current = null;
      }

      setState(prev => ({
        ...prev,
        isActive: false,
        isListening: false,
        isProcessing: false,
        sessionId: null,
        transcript: '',
        error: null,
        isConnected: false,
        confidence: 0
      }));
    } catch (error: any) {
      console.error('Error stopping voice session:', error);
    }
  }, [state.sessionId]);

  // Toggle voice activation
  const toggle = useCallback(async () => {
    if (state.isActive) {
      await stopSession();
    } else {
      await startSession();
    }
  }, [state.isActive, startSession, stopSession]);

  // Start listening for voice input
  const startListening = useCallback(async () => {
    if (!state.isActive || state.isListening || !state.isConnected) return;

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000 // Optimal for speech recognition
        }
      });

      streamRef.current = stream;

      // Set up MediaRecorder with optimal settings for voice
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await processAudioBlob(audioBlob);
      };

      // Start recording
      mediaRecorder.start();

      setState(prev => ({
        ...prev,
        isListening: true,
        error: null
      }));

    } catch (error: any) {
      const errorMessage = 'Microphone access denied or not available';
      setState(prev => ({
        ...prev,
        error: errorMessage
      }));
      onError?.(errorMessage);
    }
  }, [state.isActive, state.isListening, state.isConnected]);

  // Stop listening
  const stopListening = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }

    setState(prev => ({
      ...prev,
      isListening: false
    }));
  }, []);

  // Process audio blob with intelligent language handling
  const processAudioBlob = useCallback(async (audioBlob: Blob) => {
    if (!state.sessionId || !state.isConnected) return;

    try {
      setState(prev => ({ ...prev, isProcessing: true }));

      // Convert blob to base64
      const audioData = await blobToBase64(audioBlob);

      const result = await voiceApi.processVoice({
        audio_data: audioData,
        language: state.currentLanguage,
        session_id: state.sessionId
      });

      if (result.success) {
        const transcript = result.transcript || '';
        const response = result.response || '';
        const detectedLang = result.detected_language;

        // Intelligent language switching logic
        if (intelligentLanguageSwitching && detectedLang && detectedLang !== state.currentLanguage) {
          console.log(`Language detected: ${detectedLang}, switching from ${state.currentLanguage}`);

          // Update current language to match detected language
          setState(prev => ({
            ...prev,
            currentLanguage: detectedLang,
            detectedLanguage: detectedLang
          }));

          // Notify about language change
          onLanguageDetected?.(detectedLang);

          // Update the session language for future responses
          try {
            await voiceApi.changeLanguage(state.sessionId, detectedLang);
          } catch (langError) {
            console.warn('Failed to change session language:', langError);
          }
        }

        setState(prev => ({
          ...prev,
          transcript,
          lastResponse: response,
          isProcessing: false,
          confidence: 0.8 // Mock confidence score, replace with actual from API
        }));

        if (transcript) {
          onTranscript?.(transcript, detectedLang);
        }

        if (response) {
          onResponse?.(response, result.data_results);
        }
      } else {
        throw new Error('Voice processing failed');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Voice processing failed';
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: errorMessage
      }));
      onError?.(errorMessage);
    }
  }, [state.sessionId, state.currentLanguage, state.isConnected, intelligentLanguageSwitching, onTranscript, onResponse, onError, onLanguageDetected]);

  // Change language manually
  const changeLanguage = useCallback(async (language: string) => {
    try {
      if (state.sessionId && state.isConnected) {
        await voiceApi.changeLanguage(state.sessionId, language);
      }

      setState(prev => ({
        ...prev,
        currentLanguage: language
      }));
    } catch (error: any) {
      const errorMessage = 'Failed to change language';
      setState(prev => ({
        ...prev,
        error: errorMessage
      }));
      onError?.(errorMessage);
    }
  }, [state.sessionId, state.isConnected, onError]);

  // Process text input (for testing without voice)
  const processText = useCallback(async (text: string) => {
    if (!state.sessionId || !state.isConnected) return;

    try {
      setState(prev => ({ ...prev, isProcessing: true }));

      const result = await voiceApi.processVoice({
        text,
        language: state.currentLanguage,
        session_id: state.sessionId
      });

      if (result.success) {
        setState(prev => ({
          ...prev,
          transcript: text,
          lastResponse: result.response || '',
          isProcessing: false
        }));

        if (result.response) {
          onResponse?.(result.response, result.data_results);
        }
      }
    } catch (error: any) {
      const errorMessage = 'Text processing failed';
      setState(prev => ({
        ...prev,
        isProcessing: false,
        error: errorMessage
      }));
      onError?.(errorMessage);
    }
  }, [state.sessionId, state.currentLanguage, state.isConnected, onResponse, onError]);

  // Auto-start if enabled
  useEffect(() => {
    if (autoStart && !state.isActive) {
      startSession();
    }
  }, [autoStart, state.isActive, startSession]);

  // Initial connection check
  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopSession();
      if (connectionCheckRef.current) {
        clearInterval(connectionCheckRef.current);
      }
    };
  }, []);

  return {
    ...state,
    startSession,
    stopSession,
    toggle,
    startListening,
    stopListening,
    changeLanguage,
    processText,
    checkConnection
  };
};

// Utility function
const blobToBase64 = (blob: Blob): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(',')[1]); // Remove data:audio/webm;base64, prefix
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
};