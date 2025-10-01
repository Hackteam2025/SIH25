import React, { useCallback, useState, useEffect } from 'react';
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js';
import { DailyTransport } from '@pipecat-ai/daily-transport';
import {
  PipecatClientProvider,
  PipecatClientAudio,
  usePipecatClient,
  useRTVIClientEvent,
  usePipecatClientTransportState
} from '@pipecat-ai/client-react';
import { Mic, MicOff, Loader2, Volume2, Phone, PhoneOff } from 'lucide-react';

// Initialize Pipecat client with Daily transport and extensive logging
const pipecatClient = new PipecatClient({
  transport: new DailyTransport(),
  enableMic: true,
  enableCam: false,
  callbacks: {
    onConnected: () => console.log('🎉 [Pipecat] User connected to Daily room'),
    onDisconnected: () => console.log('👋 [Pipecat] User disconnected from Daily room'),
    onTransportStateChanged: (state: string) => console.log('🔄 [Pipecat] Transport state:', state),
    onBotConnected: () => console.log('🤖 [Pipecat] Bot connected to room'),
    onBotDisconnected: () => console.log('🤖 [Pipecat] Bot disconnected from room'),
    onBotReady: () => console.log('✅ [Pipecat] Bot is ready for conversation!'),
  }
});

interface VoiceControlsProps {
  onTranscript?: (text: string, isFinal: boolean) => void;
  onBotResponse?: (text: string) => void;
}

// Inner component that uses hooks
function VoiceControls({ onTranscript, onBotResponse }: VoiceControlsProps) {
  const client = usePipecatClient();
  const transportState = usePipecatClientTransportState();
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [currentLanguage, setCurrentLanguage] = useState<'en' | 'hi'>('en');
  const [isProcessing, setIsProcessing] = useState(false);

  // Listen for ALL RTVI events for comprehensive debugging
  useEffect(() => {
    const events = [
      RTVIEvent.Connected,
      RTVIEvent.Disconnected,
      RTVIEvent.TransportStateChanged,
      RTVIEvent.BotReady,
      RTVIEvent.BotStartedSpeaking,
      RTVIEvent.BotStoppedSpeaking,
      RTVIEvent.UserStartedSpeaking,
      RTVIEvent.UserStoppedSpeaking,
      RTVIEvent.UserTranscript,
      RTVIEvent.BotTranscript,
      RTVIEvent.Metrics,
      RTVIEvent.Error,
    ];

    const handlers = events.map(event => {
      const handler = (data: any) => {
        console.log(`📡 [RTVI Event] ${event}:`, data);
      };
      client.on(event, handler);
      return { event, handler };
    });

    return () => {
      handlers.forEach(({ event, handler }) => {
        client.off(event, handler);
      });
    };
  }, [client]);

  // Listen for user transcript (what user said)
  useRTVIClientEvent(
    RTVIEvent.UserTranscript,
    useCallback((transcript: any) => {
      console.log('👤 [User Transcript]:', transcript);
      if (onTranscript) {
        onTranscript(transcript.text, transcript.final);
      }
    }, [onTranscript])
  );

  // Listen for bot transcript (what bot is saying)
  useRTVIClientEvent(
    RTVIEvent.BotTranscript,
    useCallback((transcript: any) => {
      console.log('🤖 [Bot Transcript]:', transcript);
      if (onBotResponse) {
        onBotResponse(transcript.text);
      }
    }, [onBotResponse])
  );

  // Listen for user speaking events
  useRTVIClientEvent(
    RTVIEvent.UserStartedSpeaking,
    useCallback(() => {
      console.log('🎤 [User] Started speaking');
    }, [])
  );

  useRTVIClientEvent(
    RTVIEvent.UserStoppedSpeaking,
    useCallback(() => {
      console.log('🎤 [User] Stopped speaking');
    }, [])
  );

  // Listen for bot started/stopped speaking
  useRTVIClientEvent(
    RTVIEvent.BotStartedSpeaking,
    useCallback(() => {
      console.log('🤖 [Bot] Started speaking');
      setIsProcessing(true);
    }, [])
  );

  useRTVIClientEvent(
    RTVIEvent.BotStoppedSpeaking,
    useCallback(() => {
      console.log('🤖 [Bot] Stopped speaking');
      setIsProcessing(false);
    }, [])
  );

  // Listen for errors
  useRTVIClientEvent(
    RTVIEvent.Error,
    useCallback((error: any) => {
      console.error('❌ [Pipecat Error]:', error);
    }, [])
  );

  const startVoice = async () => {
    try {
      console.log('🎤 [Voice AI] Starting connection...');
      const BACKEND_URL = import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8001';
      console.log('🌐 [Voice AI] Backend URL:', BACKEND_URL);

      // Use startBotAndConnect with the endpoint URL
      console.log('📞 [Voice AI] Calling /voice/connect...');
      const response = await client.startBotAndConnect({
        endpoint: `${BACKEND_URL}/voice/connect`
      });

      console.log('✅ [Voice AI] Connected successfully!', response);
    } catch (error) {
      console.error('❌ [Voice AI] Connection failed:', error);
    }
  };

  const stopVoice = async () => {
    try {
      console.log('🔇 [Voice AI] Stopping...');
      await client.disconnect();
      console.log('✅ [Voice AI] Disconnected successfully');
    } catch (error) {
      console.error('❌ [Voice AI] Disconnect failed:', error);
    }
  };

  const toggleMic = async () => {
    try {
      if (isMicEnabled) {
        await client.enableMic(false);
        setIsMicEnabled(false);
      } else {
        await client.enableMic(true);
        setIsMicEnabled(true);
      }
    } catch (error) {
      console.error('Failed to toggle mic:', error);
    }
  };

  const switchLanguage = async () => {
    const newLang = currentLanguage === 'en' ? 'hi' : 'en';
    setCurrentLanguage(newLang);
    // You can send language preference to bot if needed
    console.log(`🌐 Switched language to: ${newLang === 'hi' ? 'Hindi' : 'English'}`);
  };

  const isConnected = transportState === 'connected' || transportState === 'ready';
  const isConnecting = transportState === 'authenticating' || transportState === 'connecting';

  return (
    <div className="flex flex-col gap-4 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-gray-800 dark:to-gray-900 rounded-lg border border-blue-200 dark:border-gray-700">
      {/* Status Display */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${
            isConnected ? 'bg-green-500 animate-pulse' :
            isConnecting ? 'bg-yellow-500 animate-pulse' :
            'bg-gray-400'
          }`}></div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isConnected ? 'Voice AI Active' :
             isConnecting ? 'Connecting...' :
             'Voice AI Offline'}
          </span>
        </div>

        {isConnected && (
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <span className={`px-2 py-1 rounded-full ${
              currentLanguage === 'hi'
                ? 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300'
                : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
            }`}>
              {currentLanguage === 'hi' ? '🇮🇳 हिंदी' : '🇬🇧 English'}
            </span>
          </div>
        )}
      </div>

      {/* Control Buttons */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Connect/Disconnect Button */}
        {!isConnected && !isConnecting && (
          <button
            onClick={startVoice}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 text-white rounded-lg font-medium transition-all shadow-md hover:shadow-lg"
          >
            <Phone className="h-5 w-5" />
            Start Voice AI
          </button>
        )}

        {isConnecting && (
          <button
            disabled
            className="flex items-center gap-2 px-4 py-2 bg-gray-400 text-white rounded-lg font-medium cursor-not-allowed"
          >
            <Loader2 className="h-5 w-5 animate-spin" />
            Connecting...
          </button>
        )}

        {isConnected && (
          <>
            {/* Microphone Toggle */}
            <button
              onClick={toggleMic}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all shadow-md hover:shadow-lg ${
                isMicEnabled
                  ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white'
                  : 'bg-gradient-to-r from-gray-500 to-gray-600 hover:from-gray-600 hover:to-gray-700 text-white'
              }`}
            >
              {isMicEnabled ? (
                <>
                  <Mic className="h-5 w-5" />
                  Mute
                </>
              ) : (
                <>
                  <MicOff className="h-5 w-5" />
                  Unmute
                </>
              )}
            </button>

            {/* Language Toggle */}
            <button
              onClick={switchLanguage}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white rounded-lg font-medium transition-all shadow-md hover:shadow-lg"
            >
              <span className="text-sm">
                {currentLanguage === 'hi' ? 'Switch to English' : 'हिंदी में बदलें'}
              </span>
            </button>

            {/* Disconnect Button */}
            <button
              onClick={stopVoice}
              className="flex items-center gap-2 px-4 py-2 border-2 border-red-500 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg font-medium transition-all"
            >
              <PhoneOff className="h-5 w-5" />
              Stop Voice
            </button>
          </>
        )}
      </div>

      {/* Processing Indicator */}
      {isProcessing && (
        <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
          <Volume2 className="h-4 w-4 animate-pulse" />
          <span>Bot is speaking...</span>
        </div>
      )}

      {/* Instructions */}
      {!isConnected && (
        <div className="text-xs text-gray-600 dark:text-gray-400 mt-2">
          <p>💡 Click "Start Voice AI" to begin voice conversation</p>
          <p>🎤 Supports both English and Hindi</p>
          <p>🌊 Ask questions about ocean data and ARGO floats</p>
        </div>
      )}
    </div>
  );
}

// Main export component with provider
export default function PipecatVoiceChat({
  onTranscript,
  onBotResponse
}: VoiceControlsProps) {
  return (
    <PipecatClientProvider client={pipecatClient}>
      <VoiceControls
        onTranscript={onTranscript}
        onBotResponse={onBotResponse}
      />
      {/* Audio player for bot responses */}
      <PipecatClientAudio />
    </PipecatClientProvider>
  );
}
