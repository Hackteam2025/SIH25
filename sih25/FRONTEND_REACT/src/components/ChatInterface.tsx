import React, { useState, useRef, useEffect } from 'react'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Badge } from './ui/Badge'
import HelpModal from './HelpModal'
import { Send, Bot, User, Loader2, Sparkles, MessageCircle, Trash2, Copy, HelpCircle, Mic, MicOff, Zap, Database, BarChart3 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import api from '../services/api'

interface Message {
  id: string
  content: string
  sender: 'user' | 'bot'
  timestamp: Date
  isLoading?: boolean
  toolCalls?: Array<{
    tool_name: string
    parameters: any
    result: any
  }>
  scientificInsights?: string[]
  followUpSuggestions?: string[]
  visualizationData?: {
    type: 'map' | 'chart' | 'table'
    data: any
    metadata: any
  }
}

interface ChatResponse {
  answer: string
  suggestions: string[]
  data_insights: {
    total_profiles?: number
    temperature?: {
      min: number
      max: number
      avg: number
      median: number
    }
    salinity?: {
      min: number
      max: number
      avg: number
      median: number
    }
    depth?: {
      min: number
      max: number
      avg: number
    }
    region?: string
  }
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const suggestedQueries = [
  "Show me temperature patterns near the equator",
  "What's the salinity distribution in the Pacific?",
  "Analyze temperature data for May 2025",
  "Compare temperature vs salinity correlation",
  "Find deep ocean profiles below 1000m",
  "Show me data from the Southern Ocean",
  "Analyze seasonal temperature variations",
  "Compare Atlantic vs Pacific salinity"
]

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [sessionId, setSessionId] = useState<string>('')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [dataInsights, setDataInsights] = useState<any>({})
  const [isListening, setIsListening] = useState(false)
  const [isAdvancedVoice, setIsAdvancedVoice] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Initialize simple chat session on component mount
  useEffect(() => {
    initializeSession()
  }, [])

  const initializeSession = async () => {
    // Simple session initialization without broken AGNO endpoints
    const sessionId = `session_${Date.now()}`
    setSessionId(sessionId)

    // Add welcome message
    const welcomeMessage: Message = {
      id: 'welcome',
      content: `Hello! I'm your oceanographic data assistant. I can help you explore your Supabase database containing ARGO float data. What would you like to discover today?`,
      sender: 'bot',
      timestamp: new Date(),
      followUpSuggestions: [
        "Show me the latest profiles in the database",
        "What oceanographic data do we have?",
        "Search for temperature measurements",
        "Display recent float observations"
      ]
    }
    setMessages([welcomeMessage])
    setSuggestions(welcomeMessage.followUpSuggestions || [])
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const clearChat = () => {
    setMessages([])
  }

  const copyMessage = (content: string) => {
    navigator.clipboard.writeText(content)
  }

  const handleSuggestedQuery = (query: string) => {
    setInput(query)
    inputRef.current?.focus()
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.trim(),
      sender: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    const currentInput = input.trim()
    setInput('')
    setIsLoading(true)
    setIsTyping(true)
    setSuggestions([])
    setDataInsights({})

    try {
      // Use simplified chat API instead of broken AGNO agent
      const chatResponse = await api.chat.sendMessage(currentInput, sessionId)

      setIsTyping(false)

      // Create simple bot message
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: chatResponse.response,
        sender: 'bot',
        timestamp: new Date(),
        followUpSuggestions: chatResponse.suggestions
      }

      setMessages(prev => [...prev, botMessage])

      // Set suggestions from chat response
      setSuggestions(chatResponse.suggestions || [])

    } catch (error) {
      console.error('Chat error:', error)
      setIsTyping(false)

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'I apologize, but I encountered an issue processing your request. The chat system is currently simplified while we work on improvements.',
        sender: 'bot',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    }

    setIsLoading(false)
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const toggleAdvancedVoice = async () => {
    if (isAdvancedVoice) {
      // Stop the voice pipeline
      try {
        const response = await fetch(`${API_URL}/voice/stop`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })

        if (response.ok) {
          setIsAdvancedVoice(false)
          setIsListening(false)
          alert('🔇 Advanced Voice Mode Stopped\n\nThe Pipecat voice AI pipeline has been stopped.')
        } else {
          console.error('Failed to stop voice pipeline')
          alert('Failed to stop voice pipeline. Check console for details.')
        }
      } catch (error) {
        console.error('Error stopping voice pipeline:', error)
        alert('Error stopping voice pipeline. Check console for details.')
      }
      return
    }

    try {
      // First check if voice pipeline is configured
      const configResponse = await fetch(`${API_URL}/voice/config`)
      if (!configResponse.ok) {
        throw new Error('Voice service not available')
      }

      const configData = await configResponse.json()

      if (!configData.supported) {
        alert(`🚫 Voice AI Configuration Issues\n\nMissing dependencies:\n${configData.missing_dependencies.join('\n')}\n\nRecommended setup:\n${configData.recommended_setup.join('\n')}`)
        return
      }

      // Check current status
      const statusResponse = await fetch(`${API_URL}/voice/status`)
      const statusData = await statusResponse.json()

      if (statusData.running) {
        // Already running, just connect to it
        setIsAdvancedVoice(true)
        alert('🎤 Advanced Voice Mode (Active)\n\nConnected to running Pipecat voice AI pipeline.\n\nYou can now speak naturally about ocean data.')
      } else {
        // Start the voice pipeline
        const startResponse = await fetch(`${API_URL}/voice/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: `chat-session-${Date.now()}`,
            advanced_mode: true
          })
        })

        if (startResponse.ok) {
          const startData = await startResponse.json()
          setIsAdvancedVoice(true)
          alert(`🎤 Advanced Voice Mode Started\n\nPipecat voice AI pipeline is now running!\n\nSession: ${startData.session_id}\nStarted: ${new Date(startData.started_at).toLocaleTimeString()}\n\nYou can now speak naturally about ocean data.`)
        } else {
          const errorData = await startResponse.json()
          throw new Error(errorData.detail || 'Failed to start voice pipeline')
        }
      }
    } catch (error) {
      console.error('Voice pipeline error:', error)
      alert(`❌ Advanced Voice Mode Error\n\n${error.message}\n\nFalling back to simple browser voice recognition.`)
      toggleSimpleVoice()
    }
  }

  const toggleSimpleVoice = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      alert('Speech recognition not supported in this browser')
      return
    }

    if (isListening) {
      setIsListening(false)
      return
    }

    const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition
    const recognition = new SpeechRecognition()

    recognition.continuous = false
    recognition.interimResults = false
    recognition.lang = 'en-US'

    recognition.onstart = () => {
      setIsListening(true)
    }

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript
      setInput(transcript)
      setIsListening(false)
    }

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error)
      setIsListening(false)
    }

    recognition.onend = () => {
      setIsListening(false)
    }

    recognition.start()
  }

  return (
    <>
      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
      <div className="h-full flex flex-col bg-gradient-to-br from-blue-50 via-white to-indigo-50 dark:from-gray-900 dark:via-gray-800 dark:to-blue-950 rounded-xl shadow-2xl overflow-hidden">
      {/* Enhanced Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm"
            >
              <Sparkles className="h-5 w-5" />
            </motion.div>
            <div>
              <h2 className="text-xl font-bold">FloatChat Assistant</h2>
              <p className="text-blue-100 text-sm">AI-powered ocean data analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-white/20 text-white border-white/30">
              <MessageCircle className="h-3 w-3 mr-1" />
              AI Powered
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHelp(true)}
              className="text-white hover:bg-white/20"
            >
              <HelpCircle className="h-4 w-4" />
            </Button>
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearChat}
                className="text-white hover:bg-white/20"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-[400px] bg-white/50 dark:bg-gray-800/50">
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-12"
          >
            <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <Bot className="h-8 w-8 text-white" />
            </div>
            <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
              Welcome to FloatChat!
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
              Ask me anything about ARGO float ocean data. I can help you analyze temperature, salinity, and depth patterns.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
              {suggestedQueries.map((query, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => handleSuggestedQuery(query)}
                  className="p-3 text-left bg-white dark:bg-gray-700 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-500"
                >
                  <span className="text-sm text-gray-700 dark:text-gray-300">{query}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className={`flex gap-4 ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex gap-4 max-w-[85%] ${message.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                <motion.div 
                  className={`w-10 h-10 rounded-full flex items-center justify-center shadow-lg ${
                    message.sender === 'user' 
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white' 
                      : 'bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 dark:from-gray-600 dark:to-gray-700 dark:text-gray-200'
                  }`}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {message.sender === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                </motion.div>
                <div className={`relative group ${
                  message.sender === 'user' ? 'text-right' : 'text-left'
                }`}>
                  <div className={`rounded-2xl px-6 py-4 shadow-lg backdrop-blur-sm ${
                    message.sender === 'user'
                      ? 'bg-gradient-to-r from-blue-500 to-blue-600 text-white'
                      : 'bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-600'
                  }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>

                    {/* Tool Calls Display */}
                    {message.toolCalls && message.toolCalls.length > 0 && message.sender === 'bot' && (
                      <div className="mt-3 space-y-2">
                        <h5 className="text-xs font-semibold text-gray-600 dark:text-gray-400 flex items-center gap-2">
                          <Database className="h-3 w-3" />
                          Tools Used
                        </h5>
                        {message.toolCalls.map((tool, index) => (
                          <div key={index} className="bg-gray-50 dark:bg-gray-600 rounded-lg p-2 text-xs">
                            <div className="font-medium text-blue-600 dark:text-blue-400">
                              {tool.tool_name}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Scientific Insights */}
                    {message.scientificInsights && message.scientificInsights.length > 0 && message.sender === 'bot' && (
                      <div className="mt-3">
                        <h5 className="text-xs font-semibold text-green-600 dark:text-green-400 flex items-center gap-2 mb-2">
                          <Sparkles className="h-3 w-3" />
                          Scientific Insights
                        </h5>
                        <ul className="space-y-1">
                          {message.scientificInsights.map((insight, index) => (
                            <li key={index} className="text-xs text-green-700 dark:text-green-300 bg-green-50 dark:bg-green-900/20 rounded px-2 py-1">
                              • {insight}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Visualization Data Indicator */}
                    {message.visualizationData && message.sender === 'bot' && (
                      <div className="mt-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg p-2">
                        <h5 className="text-xs font-semibold text-purple-600 dark:text-purple-400 flex items-center gap-2">
                          <BarChart3 className="h-3 w-3" />
                          Data Available for Visualization
                        </h5>
                        <div className="text-xs text-purple-700 dark:text-purple-300 mt-1">
                          Type: {message.visualizationData.type}
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-2">
                      <p className={`text-xs ${
                        message.sender === 'user' ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'
                      }`}>
                        {message.timestamp.toLocaleTimeString()}
                      </p>
                      {message.sender === 'bot' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyMessage(message.content)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0"
                        >
                          <Copy className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {(isLoading || isTyping) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-4 justify-start"
          >
            <div className="w-10 h-10 rounded-full bg-gradient-to-r from-gray-100 to-gray-200 dark:from-gray-600 dark:to-gray-700 text-gray-700 dark:text-gray-200 flex items-center justify-center shadow-lg">
              <Bot className="h-5 w-5" />
            </div>
            <div className="bg-white dark:bg-gray-700 rounded-2xl px-6 py-4 flex items-center gap-3 shadow-lg border border-gray-200 dark:border-gray-600">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              >
                <Loader2 className="h-4 w-4 text-blue-500" />
              </motion.div>
              <span className="text-sm text-gray-600 dark:text-gray-300">
                {isTyping ? 'Thinking...' : 'Generating response...'}
              </span>
            </div>
          </motion.div>
        )}
        
        {/* Data Insights Panel */}
        {dataInsights && Object.keys(dataInsights).length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/50 dark:to-indigo-950/50 rounded-xl p-4 border border-blue-200 dark:border-blue-800"
          >
            <h4 className="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-3 flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              Data Insights
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {dataInsights.total_profiles && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Total Profiles</p>
                  <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{dataInsights.total_profiles}</p>
                </div>
              )}
              {dataInsights.temperature && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Temperature</p>
                  <p className="text-sm font-semibold text-orange-600 dark:text-orange-400">
                    {dataInsights.temperature.avg}°C avg
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {dataInsights.temperature.min}-{dataInsights.temperature.max}°C
                  </p>
                </div>
              )}
              {dataInsights.salinity && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Salinity</p>
                  <p className="text-sm font-semibold text-cyan-600 dark:text-cyan-400">
                    {dataInsights.salinity.avg} PSU avg
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {dataInsights.salinity.min}-{dataInsights.salinity.max} PSU
                  </p>
                </div>
              )}
              {dataInsights.depth && (
                <div className="bg-white dark:bg-gray-800 rounded-lg p-3 shadow-sm">
                  <p className="text-xs text-gray-500 dark:text-gray-400">Depth Range</p>
                  <p className="text-sm font-semibold text-green-600 dark:text-green-400">
                    {dataInsights.depth.min}-{dataInsights.depth.max}m
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Avg: {dataInsights.depth.avg}m
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* Contextual Suggestions */}
        {suggestions.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-950/50 dark:to-emerald-950/50 rounded-xl p-4 border border-green-200 dark:border-green-800"
          >
            <h4 className="text-sm font-semibold text-green-800 dark:text-green-200 mb-3 flex items-center gap-2">
              <MessageCircle className="h-4 w-4" />
              Suggested Follow-up Queries
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {suggestions.map((suggestion, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => handleSuggestedQuery(suggestion)}
                  className="text-left p-3 bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-all duration-200 border border-green-200 dark:border-green-800 hover:border-green-300 dark:hover:border-green-600 hover:bg-green-50 dark:hover:bg-green-900/30"
                >
                  <span className="text-sm text-green-700 dark:text-green-300">{suggestion}</span>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </div>
      
      {/* Enhanced Input Area with Voice */}
      <div className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-6">
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about ARGO float data... (e.g., 'equator', 'May 2025', 'lat -10 to 10')"
              disabled={isLoading}
              className="w-full px-4 py-3 text-sm border-2 border-gray-200 dark:border-gray-600 rounded-xl focus:border-blue-500 focus:ring-4 focus:ring-blue-500/20 transition-all duration-200 bg-gray-50 dark:bg-gray-700"
            />
          </div>

          {/* Simple Voice Button */}
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              onClick={toggleSimpleVoice}
              disabled={isLoading || isAdvancedVoice}
              className={`h-12 w-12 rounded-xl shadow-lg disabled:opacity-50 disabled:cursor-not-allowed ${
                isListening && !isAdvancedVoice
                  ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700'
                  : 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700'
              }`}
              title="Simple Voice Recognition"
            >
              {isListening && !isAdvancedVoice ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
            </Button>
          </motion.div>

          {/* Advanced Voice Button (Pipecat) */}
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              onClick={toggleAdvancedVoice}
              disabled={isLoading}
              className={`h-12 w-12 rounded-xl shadow-lg disabled:opacity-50 disabled:cursor-not-allowed ${
                isAdvancedVoice
                  ? 'bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700'
                  : 'bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-600 hover:to-indigo-700'
              }`}
              title="Advanced Voice AI (Pipecat Pipeline)"
            >
              <Zap className="h-5 w-5" />
            </Button>
          </motion.div>

          {/* Send Button */}
          <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
            <Button
              onClick={sendMessage}
              disabled={!input.trim() || isLoading}
              className="h-12 w-12 rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="h-5 w-5" />
            </Button>
          </motion.div>
        </div>

        <div className="flex items-center justify-between mt-3">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Press Enter to send • 🎤 Simple voice • ⚡ Advanced AI voice
          </p>

          {(isListening || isAdvancedVoice) && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="flex items-center gap-2 text-xs"
            >
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span className="text-red-600 dark:text-red-400 font-medium">
                {isAdvancedVoice ? 'Advanced Voice Active' : 'Listening...'}
              </span>
            </motion.div>
          )}
        </div>
      </div>
    </div>
    </>
  )
}
