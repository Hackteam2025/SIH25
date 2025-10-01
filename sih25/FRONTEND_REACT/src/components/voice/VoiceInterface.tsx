import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, Volume2, VolumeX, Settings, Languages, Wifi, WifiOff } from 'lucide-react';
import { FloatingCard } from '../ocean/FloatingCard';
import { OceanButton } from '../design-system/Button';
import { OceanLoader } from '../ocean/OceanLoader';

interface VoiceInterfaceProps {
  isActive: boolean;
  onToggle: () => void;
  onLanguageChange: (language: string) => void;
  currentLanguage: string;
  isListening?: boolean;
  isProcessing?: boolean;
  transcript?: string;
  isConnected?: boolean;
  confidence?: number;
}

const SUPPORTED_LANGUAGES = [
  { code: 'en-US', name: 'English', flag: '🇺🇸', nativeName: 'English' },
  { code: 'hi-IN', name: 'हिंदी', flag: '🇮🇳', nativeName: 'Hindi' },
  { code: 'bn-IN', name: 'বাংলা', flag: '🇮🇳', nativeName: 'Bengali' },
  { code: 'te-IN', name: 'తెలుగు', flag: '🇮🇳', nativeName: 'Telugu' },
  { code: 'mr-IN', name: 'मराठी', flag: '🇮🇳', nativeName: 'Marathi' },
  { code: 'ta-IN', name: 'தமிழ்', flag: '🇮🇳', nativeName: 'Tamil' },
  { code: 'gu-IN', name: 'ગુજરાતી', flag: '🇮🇳', nativeName: 'Gujarati' },
  { code: 'kn-IN', name: 'ಕನ್ನಡ', flag: '🇮🇳', nativeName: 'Kannada' },
  { code: 'ml-IN', name: 'മലയാളം', flag: '🇮🇳', nativeName: 'Malayalam' },
  { code: 'or-IN', name: 'ଓଡ଼ିଆ', flag: '🇮🇳', nativeName: 'Odia' },
  { code: 'pa-IN', name: 'ਪੰਜਾਬੀ', flag: '🇮🇳', nativeName: 'Punjabi' },
  { code: 'as-IN', name: 'অসমীয়া', flag: '🇮🇳', nativeName: 'Assamese' }
];

export const VoiceInterface: React.FC<VoiceInterfaceProps> = ({
  isActive,
  onToggle,
  onLanguageChange,
  currentLanguage,
  isListening = false,
  isProcessing = false,
  transcript = '',
  isConnected = true,
  confidence = 0
}) => {
  const [showControls, setShowControls] = useState(false);
  const [showLanguageSelect, setShowLanguageSelect] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isAudioEnabled, setIsAudioEnabled] = useState(true);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);

  // Audio level visualization
  useEffect(() => {
    if (isActive && isListening) {
      startAudioVisualization();
    } else {
      stopAudioVisualization();
    }

    return () => stopAudioVisualization();
  }, [isActive, isListening]);

  const startAudioVisualization = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();

      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      analyserRef.current.fftSize = 256;
      const bufferLength = analyserRef.current.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const updateAudioLevel = () => {
        if (analyserRef.current && isListening) {
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((acc, val) => acc + val, 0) / dataArray.length;
          setAudioLevel(average / 255);
          requestAnimationFrame(updateAudioLevel);
        }
      };

      updateAudioLevel();
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  };

  const stopAudioVisualization = () => {
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setAudioLevel(0);
  };

  const currentLang = SUPPORTED_LANGUAGES.find(lang => lang.code === currentLanguage) || SUPPORTED_LANGUAGES[0];

  const getStatusColor = () => {
    if (!isConnected) return 'bg-gray-400';
    if (isProcessing) return 'bg-coral-orange';
    if (isListening) return 'bg-coral-pink';
    if (isActive) return 'bg-seafoam-green';
    return 'bg-ocean-blue/50';
  };

  const getStatusText = () => {
    if (!isConnected) return 'Disconnected';
    if (isProcessing) return 'Processing...';
    if (isListening) return 'Listening...';
    if (isActive) return 'Ready';
    return 'Inactive';
  };

  return (
    <div className="relative">
      {/* Main Voice Button - VoiceUIKit inspired design */}
      <motion.div
        className="relative"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <motion.button
          onClick={() => {
            onToggle();
            setShowControls(true);
          }}
          className={`relative p-4 rounded-bubble transition-all duration-300 ${
            isActive
              ? 'bg-gradient-to-r from-coral-pink to-coral-orange shadow-[0_0_30px_rgba(255,107,107,0.6)]'
              : 'glass-surface hover:bg-white/20'
          }`}
          animate={{
            scale: isListening ? [1, 1.1, 1] : 1,
          }}
          transition={{
            duration: 0.8,
            repeat: isListening ? Infinity : 0,
            ease: "easeInOut"
          }}
        >
          {isActive ? (
            <MicOff className="w-6 h-6 text-white" />
          ) : (
            <Mic className="w-6 h-6 text-ocean-blue" />
          )}

          {/* Audio Level Visualization - VoiceUIKit style */}
          {isListening && (
            <div className="absolute inset-0 rounded-bubble overflow-hidden">
              <motion.div
                className="absolute bottom-0 left-0 right-0 bg-white/20"
                initial={{ height: '0%' }}
                animate={{ height: `${audioLevel * 100}%` }}
                transition={{ duration: 0.1 }}
              />

              {/* Ripple effect */}
              <motion.div
                className="absolute inset-0 border-2 border-white/30 rounded-bubble"
                animate={{
                  scale: [1, 1.5],
                  opacity: [0.8, 0]
                }}
                transition={{
                  duration: 1.5,
                  repeat: Infinity,
                  ease: "easeOut"
                }}
              />
            </div>
          )}
        </motion.button>

        {/* Status Indicator */}
        <div className="absolute -top-1 -right-1">
          <div className={`w-4 h-4 rounded-full ${getStatusColor()} animate-pulse`}>
            {!isConnected && <WifiOff className="w-3 h-3 text-white absolute inset-0.5" />}
          </div>
        </div>

        {/* Connection Status */}
        {!isConnected && (
          <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2">
            <div className="bg-red-500 text-white text-xs px-2 py-1 rounded-wave">
              Offline
            </div>
          </div>
        )}
      </motion.div>

      {/* Voice Controls Panel - VoiceUIKit inspired */}
      <AnimatePresence>
        {showControls && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8, y: 20 }}
            className="absolute top-full mt-4 right-0 z-50"
          >
            <FloatingCard className="w-80 p-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${getStatusColor()} animate-pulse`} />
                  <span className="font-medium text-ocean-blue">{getStatusText()}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setIsAudioEnabled(!isAudioEnabled)}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                  >
                    {isAudioEnabled ? (
                      <Volume2 className="w-4 h-4 text-ocean-blue" />
                    ) : (
                      <VolumeX className="w-4 h-4 text-ocean-blue/50" />
                    )}
                  </button>

                  <button
                    onClick={() => setShowControls(false)}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                  >
                    ×
                  </button>
                </div>
              </div>

              {/* Current Language */}
              <div className="mb-4">
                <button
                  onClick={() => setShowLanguageSelect(!showLanguageSelect)}
                  className="w-full flex items-center gap-3 p-3 bg-white/5 rounded-wave hover:bg-white/10 transition-colors"
                >
                  <span className="text-2xl">{currentLang.flag}</span>
                  <div className="flex-1 text-left">
                    <p className="text-sm font-medium text-ocean-blue">{currentLang.nativeName}</p>
                    <p className="text-xs text-ocean-blue/70">{currentLang.name}</p>
                  </div>
                  <Languages className="w-4 h-4 text-ocean-blue/70" />
                </button>
              </div>

              {/* Language Selector */}
              <AnimatePresence>
                {showLanguageSelect && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="mb-4 overflow-hidden"
                  >
                    <div className="max-h-40 overflow-y-auto space-y-1 custom-scrollbar">
                      {SUPPORTED_LANGUAGES.map((lang) => (
                        <button
                          key={lang.code}
                          onClick={() => {
                            onLanguageChange(lang.code);
                            setShowLanguageSelect(false);
                          }}
                          className={`w-full flex items-center gap-3 p-2 rounded hover:bg-white/10 transition-colors ${
                            lang.code === currentLanguage ? 'bg-white/20' : ''
                          }`}
                        >
                          <span className="text-lg">{lang.flag}</span>
                          <div className="flex-1 text-left">
                            <p className="text-sm text-ocean-blue">{lang.nativeName}</p>
                            <p className="text-xs text-ocean-blue/70">{lang.name}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Live Transcript */}
              {transcript && (
                <div className="mb-4">
                  <p className="text-xs text-ocean-blue/70 mb-2">Live Transcript:</p>
                  <div className="p-3 bg-white/5 rounded-wave min-h-[60px]">
                    <p className="text-sm text-ocean-blue">{transcript}</p>
                    {confidence > 0 && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-xs text-ocean-blue/70">Confidence:</span>
                        <div className="flex-1 bg-white/10 rounded-full h-1">
                          <div
                            className="bg-seafoam-green h-1 rounded-full transition-all duration-300"
                            style={{ width: `${confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-ocean-blue/70">{Math.round(confidence * 100)}%</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Audio Levels */}
              {isListening && (
                <div className="mb-4">
                  <p className="text-xs text-ocean-blue/70 mb-2">Audio Level:</p>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: 10 }).map((_, i) => (
                      <div
                        key={i}
                        className={`w-1 h-4 rounded-full transition-colors duration-100 ${
                          audioLevel * 10 > i ? 'bg-seafoam-green' : 'bg-white/20'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Processing Indicator */}
              {isProcessing && (
                <div className="mb-4 flex items-center gap-3">
                  <OceanLoader variant="waves" size="sm" color="coral" />
                  <span className="text-sm text-ocean-blue">Processing your request...</span>
                </div>
              )}

              {/* Quick Actions */}
              <div className="flex gap-2">
                <OceanButton
                  size="sm"
                  variant="secondary"
                  onClick={() => {/* Test voice */}}
                  className="flex-1"
                  disabled={!isConnected}
                >
                  Test Voice
                </OceanButton>

                <OceanButton
                  size="sm"
                  variant="ghost"
                  onClick={() => {/* Settings */}}
                  leftIcon={<Settings className="w-4 h-4" />}
                >
                  Settings
                </OceanButton>
              </div>

              {/* Connection Info */}
              <div className="mt-3 pt-3 border-t border-white/10 text-center">
                <div className="flex items-center justify-center gap-2 text-xs text-ocean-blue/70">
                  {isConnected ? (
                    <>
                      <Wifi className="w-3 h-3" />
                      <span>Connected to Pipecat Voice AI</span>
                    </>
                  ) : (
                    <>
                      <WifiOff className="w-3 h-3" />
                      <span>Connection lost - Reconnecting...</span>
                    </>
                  )}
                </div>
              </div>
            </FloatingCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};