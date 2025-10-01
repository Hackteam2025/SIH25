import React from 'react';
import { motion } from 'framer-motion';
import { Mic, Volume2, Wifi, WifiOff, Languages } from 'lucide-react';
import { FloatingCard } from '../ocean/FloatingCard';
import { OceanLoader } from '../ocean/OceanLoader';

interface VoiceStatusProps {
  isActive: boolean;
  isListening: boolean;
  isProcessing: boolean;
  currentLanguage: string;
  isConnected: boolean;
  transcript?: string;
  confidence?: number;
}

export const VoiceStatus: React.FC<VoiceStatusProps> = ({
  isActive,
  isListening,
  isProcessing,
  currentLanguage,
  isConnected,
  transcript,
  confidence = 0
}) => {
  const getStatusIcon = () => {
    if (isProcessing) return <OceanLoader variant="pulse" size="sm" color="coral" />;
    if (isListening) return <Mic className="w-4 h-4 text-coral-pink animate-pulse" />;
    if (isActive) return <Volume2 className="w-4 h-4 text-seafoam-green" />;
    return <Mic className="w-4 h-4 text-ocean-blue/50" />;
  };

  const getStatusText = () => {
    if (!isConnected) return 'Voice AI Disconnected';
    if (isProcessing) return 'Processing your voice...';
    if (isListening) return 'Listening for your input...';
    if (isActive) return 'Voice AI Ready';
    return 'Voice AI Inactive';
  };

  const getStatusColor = () => {
    if (!isConnected) return 'border-gray-400';
    if (isProcessing) return 'border-coral-orange';
    if (isListening) return 'border-coral-pink';
    if (isActive) return 'border-seafoam-green';
    return 'border-ocean-blue/30';
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed top-20 right-4 z-40"
    >
      <FloatingCard
        className={`min-w-[300px] border-2 ${getStatusColor()}`}
        intensity="moderate"
        glowColor={isListening ? 'coral' : 'seafoam'}
      >
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            {getStatusIcon()}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-medium text-ocean-blue text-sm">
                {getStatusText()}
              </h4>
              {!isConnected && <WifiOff className="w-3 h-3 text-red-500" />}
              {isConnected && <Wifi className="w-3 h-3 text-seafoam-green" />}
            </div>

            <div className="flex items-center gap-2 text-xs text-ocean-blue/70 mb-2">
              <Languages className="w-3 h-3" />
              <span>{currentLanguage}</span>
            </div>

            {/* Live Transcript */}
            {transcript && (
              <div className="bg-white/5 rounded-wave p-2 mb-2">
                <p className="text-xs text-ocean-blue/70 mb-1">Transcript:</p>
                <p className="text-sm text-ocean-blue break-words">{transcript}</p>

                {confidence > 0 && (
                  <div className="mt-2 flex items-center gap-2">
                    <div className="flex-1 bg-white/20 rounded-full h-1">
                      <motion.div
                        className="bg-seafoam-green h-1 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${confidence * 100}%` }}
                        transition={{ duration: 0.3 }}
                      />
                    </div>
                    <span className="text-xs text-ocean-blue/70">{Math.round(confidence * 100)}%</span>
                  </div>
                )}
              </div>
            )}

            {/* Processing Animation */}
            {isProcessing && (
              <div className="flex items-center gap-2 text-xs text-ocean-blue/70">
                <div className="flex gap-1">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <motion.div
                      key={i}
                      className="w-1 h-1 bg-coral-orange rounded-full"
                      animate={{
                        scale: [1, 1.5, 1],
                        opacity: [0.5, 1, 0.5]
                      }}
                      transition={{
                        duration: 0.8,
                        repeat: Infinity,
                        delay: i * 0.2
                      }}
                    />
                  ))}
                </div>
                <span>Analyzing speech...</span>
              </div>
            )}
          </div>
        </div>
      </FloatingCard>
    </motion.div>
  );
};