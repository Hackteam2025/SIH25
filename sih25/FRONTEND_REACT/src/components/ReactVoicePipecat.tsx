import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Volume2, Loader2, Globe, ChevronDown } from 'lucide-react'
import { toast } from 'react-hot-toast'
import { PipecatClient, RTVIEvent } from '@pipecat-ai/client-js'
import { DailyTransport } from '@pipecat-ai/daily-transport'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface VoiceInterfaceProps {
  onDataReceived?: (data: any, visualization: any) => void
}

interface Language {
  code: string
  name: string
  sttCode: string
  ttsVoice: string
  display: string
}

const SUPPORTED_LANGUAGES: Language[] = [
  { code: 'en', name: 'English', sttCode: 'en-US', ttsVoice: 'default', display: '🇺🇸 English' },
  { code: 'hi', name: 'Hindi', sttCode: 'hi-IN', ttsVoice: 'karun', display: '🇮🇳 हिंदी' },
  { code: 'ta', name: 'Tamil', sttCode: 'ta-IN', ttsVoice: 'meera', display: '🇮🇳 தமிழ்' },
  { code: 'te', name: 'Telugu', sttCode: 'te-IN', ttsVoice: 'priya', display: '🇮🇳 తెలుగు' }
]

export default function ReactVoicePipecat({ onDataReceived }: VoiceInterfaceProps) {
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [response, setResponse] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState<Language>(SUPPORTED_LANGUAGES[0])
  const [showLanguageDropdown, setShowLanguageDropdown] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)

  const rtviClientRef = useRef<PipecatClient | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)

  const initializeAudioVisualizer = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      analyserRef.current.fftSize = 256
    }
  }, [])

  const updateAudioLevel = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)

    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length
    setAudioLevel(average / 255)

    animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
  }, [])

  const connectToPipecat = async () => {
    setIsConnecting(true)

    try {
      // Initialize Pipecat client with Daily transport
      const transport = new DailyTransport()

      const client = new PipecatClient({
        transport,
        enableMic: true,
        enableCam: false
      })

      // Set up event handlers
      client.on(RTVIEvent.BotReady, () => {
        console.log('Bot is ready')
        setIsConnected(true)
        setIsConnecting(false)
        toast.success(`Connected in ${selectedLanguage.name}!`)
        initializeAudioVisualizer()
      })

      client.on(RTVIEvent.UserStartedSpeaking, () => {
        setIsListening(true)
        if (animationFrameRef.current === null) {
          updateAudioLevel()
        }
      })

      client.on(RTVIEvent.UserStoppedSpeaking, () => {
        setIsListening(false)
        if (animationFrameRef.current !== null) {
          cancelAnimationFrame(animationFrameRef.current)
          animationFrameRef.current = null
        }
        setAudioLevel(0)
      })

      client.on(RTVIEvent.UserTranscript, (transcript: any) => {
        setTranscript(transcript.text)
      })

      client.on(RTVIEvent.BotTranscript, (transcript: any) => {
        setResponse(transcript.text)

        // Check if bot response includes ocean data
        if (transcript.metadata?.oceanData && onDataReceived) {
          onDataReceived(
            transcript.metadata.oceanData,
            transcript.metadata.visualizationConfig
          )
        }
      })

      client.on('error', (error: any) => {
        console.error('Pipecat Error:', error)
        toast.error(`Voice error: ${error.message || 'Unknown error'}`)
        disconnect()
      })

      client.on(RTVIEvent.Disconnected, () => {
        setIsConnected(false)
        setIsListening(false)
        console.log('Disconnected from voice service')
      })

      // Connect to the service with configuration
      await client.startBotAndConnect({
        endpoint: `${API_URL}/api/pipecat/connect`,
        config: {
          llm: {
            model: 'groq/llama-3.1-70b-versatile',
            language: selectedLanguage.code,
            systemPrompt: getOceanographicSystemPrompt(selectedLanguage.code)
          },
          stt: {
            provider: 'deepgram',
            language: selectedLanguage.sttCode
          },
          tts: {
            provider: selectedLanguage.code === 'en' ? 'elevenlabs' : 'sarvam',
            voice: selectedLanguage.ttsVoice,
            language: selectedLanguage.code
          }
        }
      })
      rtviClientRef.current = client

    } catch (error) {
      console.error('Connection error:', error)
      toast.error('Failed to connect to voice service')
      setIsConnecting(false)
    }
  }

  const disconnect = async () => {
    if (rtviClientRef.current) {
      try {
        await rtviClientRef.current.disconnect()
        rtviClientRef.current = null
        setIsConnected(false)
        setIsListening(false)
        setTranscript('')
        setResponse('')
        toast.success('Disconnected')

        // Clean up audio context
        if (animationFrameRef.current !== null) {
          cancelAnimationFrame(animationFrameRef.current)
          animationFrameRef.current = null
        }
        if (audioContextRef.current) {
          await audioContextRef.current.close()
          audioContextRef.current = null
        }
      } catch (error) {
        console.error('Disconnect error:', error)
      }
    }
  }

  const toggleConnection = () => {
    if (isConnected) {
      disconnect()
    } else {
      connectToPipecat()
    }
  }

  const changeLanguage = (language: Language) => {
    setSelectedLanguage(language)
    setShowLanguageDropdown(false)

    if (isConnected) {
      // For language change, need to reconnect with new settings
      toast.info(`Please reconnect to switch to ${language.name}`)
      disconnect()
    }
  }

  const getOceanographicSystemPrompt = (langCode: string) => {
    const basePrompt = `You are FloatChat, an expert oceanographic data assistant specializing in ARGO float measurements. You help users discover and understand ocean data through natural conversation.

Your expertise includes:
- ARGO float parameters: TEMP (Temperature), PSAL (Salinity), PRES (Pressure), DOXY (Dissolved Oxygen), CHLA (Chlorophyll-a)
- Ocean regions: Arabian Sea, Bay of Bengal, Indian Ocean, Pacific, Atlantic
- Quality control flags and data interpretation
- Oceanographic phenomena: thermoclines, haloclines, upwelling, eddies, water masses

When users ask about ocean data:
1. Query the ocean database using the MCP tools available
2. Interpret the data scientifically
3. Explain patterns and anomalies
4. Suggest related analyses

Keep responses concise and scientifically accurate.`

    const languageInstructions = {
      en: '',
      hi: '\n\nRespond in Hindi (हिंदी). Keep technical terms in English but explain them in Hindi.',
      ta: '\n\nRespond in Tamil (தமிழ்). Keep technical terms in English but explain them in Tamil.',
      te: '\n\nRespond in Telugu (తెలుగు). Keep technical terms in English but explain them in Telugu.'
    }

    return basePrompt + (languageInstructions[langCode as keyof typeof languageInstructions] || '')
  }

  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [])

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-card text-card-foreground rounded-lg border border-border p-8">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold mb-2">Voice AI Interface</h2>
          <p className="text-muted-foreground">
            Real-time voice interaction with ocean data
          </p>
        </div>

        {/* Language Selector */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <button
              onClick={() => setShowLanguageDropdown(!showLanguageDropdown)}
              className="flex items-center gap-2 px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
            >
              <Globe className="w-4 h-4" />
              <span>{selectedLanguage.display}</span>
              <ChevronDown className="w-4 h-4" />
            </button>

            <AnimatePresence>
              {showLanguageDropdown && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute top-full mt-2 left-0 right-0 bg-card border border-border rounded-lg shadow-lg z-10"
                >
                  {SUPPORTED_LANGUAGES.map((lang) => (
                    <button
                      key={lang.code}
                      onClick={() => changeLanguage(lang)}
                      className="w-full px-4 py-2 text-left hover:bg-secondary transition-colors first:rounded-t-lg last:rounded-b-lg"
                    >
                      {lang.display}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Voice Control Button */}
        <div className="flex justify-center mb-6">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={toggleConnection}
            disabled={isConnecting}
            className={`
              relative w-24 h-24 rounded-full flex items-center justify-center
              transition-all duration-300 shadow-lg
              ${isConnected
                ? 'bg-green-500 hover:bg-green-600'
                : 'bg-blue-500 hover:bg-blue-600'}
              ${isConnecting ? 'opacity-50 cursor-not-allowed' : ''}
            `}
          >
            {isConnecting ? (
              <Loader2 className="w-10 h-10 text-white animate-spin" />
            ) : isConnected ? (
              <motion.div
                animate={isListening ? { scale: [1, 1.2, 1] } : {}}
                transition={isListening ? { repeat: Infinity, duration: 1.5 } : {}}
              >
                <Mic className="w-10 h-10 text-white" />
              </motion.div>
            ) : (
              <MicOff className="w-10 h-10 text-white" />
            )}

            {/* Audio Level Indicator */}
            {isConnected && (
              <motion.div
                className="absolute inset-0 rounded-full border-4"
                style={{
                  borderColor: isListening ? 'rgba(34, 197, 94, 0.5)' : 'transparent',
                  transform: `scale(${1 + audioLevel * 0.5})`
                }}
                transition={{ duration: 0.1 }}
              />
            )}

            {/* Pulse Animation */}
            {isListening && (
              <motion.div
                className="absolute inset-0 rounded-full border-4 border-green-300"
                animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
              />
            )}
          </motion.button>
        </div>

        {/* Status Text */}
        <div className="text-center mb-6">
          <p className="text-sm text-muted-foreground">
            {isConnecting ? 'Connecting...' :
             isConnected ? (isListening ? 'Listening...' : 'Connected - Speak anytime') :
             'Click to connect'}
          </p>
        </div>

        {/* Transcript and Response Display */}
        <AnimatePresence>
          {transcript && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-4"
            >
              <div className="flex items-start gap-2">
                <Volume2 className="w-5 h-5 text-blue-600 mt-1" />
                <div className="flex-1 text-left">
                  <p className="text-sm text-muted-foreground mb-1">You said:</p>
                  <p className="text-foreground">{transcript}</p>
                </div>
              </div>
            </motion.div>
          )}

          {response && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-4"
            >
              <div className="flex items-start gap-2">
                <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                  <span className="text-white font-bold text-sm">AI</span>
                </div>
                <div className="flex-1 text-left">
                  <p className="text-sm text-muted-foreground mb-1">FloatChat:</p>
                  <p className="text-foreground whitespace-pre-wrap">{response}</p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Help Text */}
        <div className="mt-6 text-sm text-muted-foreground text-center">
          <p>Try asking:</p>
          <p className="italic mt-2">
            {selectedLanguage.code === 'en' ?
              '"Show me temperature profiles near the equator"' :
             selectedLanguage.code === 'hi' ?
              '"भूमध्य रेखा के पास तापमान प्रोफाइल दिखाएं"' :
             selectedLanguage.code === 'ta' ?
              '"நடுவரைக்கோட்டின் அருகில் வெப்பநிலை சுயவிவரங்களைக் காட்டு"' :
              '"భూమధ్య రేఖ దగ్గర ఉష్ణోగ్రత ప్రొఫైల్స్ చూపించు"'}
          </p>
        </div>
      </div>
    </div>
  )
}