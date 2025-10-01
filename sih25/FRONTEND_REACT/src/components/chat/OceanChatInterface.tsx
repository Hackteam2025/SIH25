import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Mic, MicOff, Volume2, VolumeX } from 'lucide-react';
import { FloatingCard } from '../ocean/FloatingCard';
import { OceanButton } from '../design-system/Button';
import { OceanLoader } from '../ocean/OceanLoader';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isVoice?: boolean;
  audioUrl?: string;
}

interface OceanChatInterfaceProps {
  onSendMessage: (message: string) => void;
  onVoiceToggle: () => void;
  isVoiceActive: boolean;
  isLoading?: boolean;
  messages?: ChatMessage[];
}

export const OceanChatInterface: React.FC<OceanChatInterfaceProps> = ({
  onSendMessage,
  onVoiceToggle,
  isVoiceActive,
  isLoading = false,
  messages = []
}) => {
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Initialize with welcome message if no messages
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
    if (messages.length > 0) return messages;
    return [
      {
        id: '1',
        type: 'assistant',
        content: "Hello! I'm FloatChat, your oceanographic data assistant. I can help you explore ARGO float measurements from around the world's oceans. What would you like to discover today?",
        timestamp: new Date()
      }
    ];
  });

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages, isTyping]);

  useEffect(() => {
    if (messages.length > 0) {
      setChatMessages(messages);
    }
  }, [messages]);

  const handleSendMessage = () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setChatMessages(prev => [...prev, userMessage]);
    onSendMessage(inputValue);
    setInputValue('');
    setIsTyping(true);

    // Simulate response (replace with actual backend integration)
    setTimeout(() => {
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: "I'm processing your request about ocean data. Let me search through the ARGO database for relevant information...",
        timestamp: new Date()
      };
      setChatMessages(prev => [...prev, assistantMessage]);
      setIsTyping(false);
    }, 1500);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[70vh] max-w-4xl mx-auto">
      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-4 pr-2 custom-scrollbar">
        <AnimatePresence initial={false}>
          {chatMessages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.3 }}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] ${
                  message.type === 'user'
                    ? 'bg-gradient-to-r from-coral-pink to-coral-orange text-white'
                    : 'glass-surface text-ocean-blue'
                } rounded-wave p-4 shadow-lg`}
              >
                {message.type === 'assistant' && (
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-6 h-6 bg-gradient-ocean-sunset rounded-bubble flex items-center justify-center">
                      <span className="text-white text-xs font-bold">FC</span>
                    </div>
                    <span className="text-sm font-medium">FloatChat</span>
                    {message.isVoice && (
                      <Volume2 className="w-4 h-4 text-seafoam-green" />
                    )}
                  </div>
                )}

                <p className="whitespace-pre-wrap leading-relaxed">
                  {message.content}
                </p>

                <div className="flex items-center justify-between mt-2 pt-2 border-t border-white/10">
                  <span className="text-xs opacity-70">
                    {message.timestamp.toLocaleTimeString()}
                  </span>

                  {message.audioUrl && (
                    <button className="text-xs hover:text-seafoam-green transition-colors">
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Typing Indicator */}
        {isTyping && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex justify-start"
          >
            <div className="glass-surface rounded-wave p-4 max-w-[80%]">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-6 h-6 bg-gradient-ocean-sunset rounded-bubble flex items-center justify-center">
                  <span className="text-white text-xs font-bold">FC</span>
                </div>
                <span className="text-sm font-medium text-ocean-blue">FloatChat</span>
              </div>

              <div className="flex items-center gap-3">
                <OceanLoader variant="waves" size="sm" color="seafoam" />
                <span className="text-sm text-ocean-blue/70">Thinking...</span>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <FloatingCard className="flex items-end gap-3 p-4" intensity="subtle">
        <div className="flex-1">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about ocean temperature, salinity, ARGO floats, or anything ocean-related..."
            className="w-full bg-transparent text-ocean-blue placeholder-ocean-blue/50 resize-none focus:outline-none"
            rows={inputValue.split('\n').length}
            maxLength={1000}
            disabled={isLoading}
          />

          <div className="flex items-center justify-between mt-2">
            <span className="text-xs text-ocean-blue/50">
              {inputValue.length}/1000 characters
            </span>

            <div className="flex items-center gap-2">
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onVoiceToggle}
                className={`p-2 rounded-current transition-all duration-300 ${
                  isVoiceActive
                    ? 'bg-coral-pink text-white shadow-[0_0_15px_rgba(255,107,107,0.5)]'
                    : 'text-ocean-blue hover:bg-white/10'
                }`}
                disabled={isLoading}
              >
                {isVoiceActive ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </motion.button>

              <OceanButton
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                isLoading={isLoading}
                size="sm"
                variant="primary"
                rightIcon={<Send className="w-4 h-4" />}
              >
                Send
              </OceanButton>
            </div>
          </div>
        </div>
      </FloatingCard>

      {/* Quick Actions */}
      <div className="flex gap-2 mt-3 flex-wrap justify-center">
        {[
          "Show me ocean temperature data",
          "What's the latest from ARGO floats?",
          "Analyze salinity patterns",
          "Find data near coordinates"
        ].map((suggestion, index) => (
          <motion.button
            key={index}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => setInputValue(suggestion)}
            className="px-3 py-1 text-sm glass-surface hover:glass-moderate rounded-wave text-ocean-blue/80 hover:text-ocean-blue transition-all duration-200"
            disabled={isLoading}
          >
            {suggestion}
          </motion.button>
        ))}
      </div>
    </div>
  );
};