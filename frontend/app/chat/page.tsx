"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ThemeToggle } from "@/components/theme-toggle"
import { VoiceRecognition } from "@/components/voice-recognition"
import { TextInputFallback } from "@/components/text-input-fallback"
import { MessageBubble } from "@/components/message-bubble"
import { ProductCard } from "@/components/product-card"
import { LanguageSelector } from "@/components/language-selector"
import { ApiStatus } from "@/components/api-status"
import { ArrowLeft, AlertTriangle, MessageSquare, Volume2, VolumeX } from "lucide-react"
import Link from "next/link"
import { Footer } from "@/components/footer"

interface Message {
  id: string
  type: "user" | "assistant"
  content: string
  timestamp: Date
  language?: string
  products?: any[]
  sentiment?: "positive" | "neutral" | "negative"
  audioFile?: string
}

export default function ChatPage() {
  // Unique session id per chat session for audio retrieval
  const [sessionId] = useState<string>(() => `session_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`)
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || ""
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      type: "assistant",
      content: "Hello! I'm your AI sales assistant. How can I help you today? आप कैसे हैं?",
      timestamp: new Date(),
      sentiment: "positive",
    },
  ])
  const [isListening, setIsListening] = useState(false)
  const [currentLanguage, setCurrentLanguage] = useState("en")
  const [isTyping, setIsTyping] = useState(false)
  const [isOnline, setIsOnline] = useState(true)
  const [isAudioEnabled, setIsAudioEnabled] = useState(true)
  const [isAudioPlaying, setIsAudioPlaying] = useState(false)
  const [currentAudioId, setCurrentAudioId] = useState<string>("")
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // Check online status
  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
    }
    const handleOffline = () => {
      setIsOnline(false)
      if (isListening) {
        setIsListening(false)
      }
    }

    setIsOnline(navigator.onLine)
    window.addEventListener("online", handleOnline)
    window.addEventListener("offline", handleOffline)

    return () => {
      window.removeEventListener("online", handleOnline)
      window.removeEventListener("offline", handleOffline)
    }
  }, [isListening])

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        // Clear source and force reload to reset
        try {
          audioRef.current.src = ""
          audioRef.current.removeAttribute("src")
          audioRef.current.load()
        } catch {}
        audioRef.current = null
      }
    }
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Robust function to stop any playing audio
  const stopAudio = () => {
    console.log("🛑 Stopping audio - Enhanced cleanup")
    if (audioRef.current) {
      try {
        audioRef.current.pause()
        audioRef.current.currentTime = 0
        // Clear the source completely to prevent caching issues
        audioRef.current.src = ""
        audioRef.current.removeAttribute("src")
        // Remove all event listeners to prevent memory leaks
        audioRef.current.onloadstart = null
        audioRef.current.oncanplay = null
        audioRef.current.oncanplaythrough = null
        audioRef.current.onplay = null
        audioRef.current.onended = null
        audioRef.current.onerror = null
        audioRef.current.onabort = null
        audioRef.current.onstalled = null
        // Force reload to clear internal state
        audioRef.current.load()
        audioRef.current = null
      } catch (error) {
        console.error("Error stopping audio:", error)
      }
    }
    setIsAudioPlaying(false)
    setCurrentAudioId("")
  }
  // Enhanced audio play function with cache-busting and session
  const playAudioWithSession = async (sid: string, messageId: string) => {
    console.log(`🎵 === ENHANCED AUDIO PLAYBACK ===`)
    console.log(`Session ID: ${sid}`)
    console.log(`Message ID: ${messageId}`)
    console.log(`Audio enabled: ${isAudioEnabled}`)

    stopAudio()

    if (!isAudioEnabled) {
      console.log("❌ Audio is disabled - skipping playback")
      return
    }
    if (!sid) {
      console.log("❌ No session ID provided")
      return
    }

    try {
      const audio = new Audio()
      const ts = Date.now()
      const url = `${API_BASE_URL}/api/v1/voice-assistant/get-audio/${sid}?t=${ts}&msg=${messageId}`
      audio.src = url
      audio.preload = 'auto'
      audio.volume = 1.0

      const cleanup = () => {
        audio.onloadstart = null
        audio.oncanplay = null
        audio.oncanplaythrough = null
        audio.onplay = null
        audio.onended = null
        audio.onerror = null
        audio.onabort = null
        audio.onstalled = null
      }

      audio.onloadstart = () => {
        if (isAudioEnabled && audioRef.current === audio) {
          setCurrentAudioId(messageId)
          setIsAudioPlaying(true)
        } else {
          audio.pause()
          cleanup()
        }
      }

      audio.oncanplaythrough = () => {
        if (isAudioEnabled && audioRef.current === audio) {
          audio.play().catch(error => {
            console.error("❌ Audio play failed:", error)
            if (audioRef.current === audio) {
              setIsAudioPlaying(false)
              setCurrentAudioId("")
              cleanup()
              audioRef.current = null
            }
          })
        } else {
          audio.pause()
          cleanup()
        }
      }

      audio.onplay = () => {
        if (audioRef.current === audio) {
          setIsAudioPlaying(true)
        }
      }

      audio.onended = () => {
        if (audioRef.current === audio) {
          setIsAudioPlaying(false)
          setCurrentAudioId("")
          cleanup()
          audioRef.current = null
        }
      }

      audio.onerror = () => {
        if (audioRef.current === audio) {
          setIsAudioPlaying(false)
          setCurrentAudioId("")
          cleanup()
          audioRef.current = null
        }
      }

      audio.onabort = () => {
        if (audioRef.current === audio) {
          setIsAudioPlaying(false)
          setCurrentAudioId("")
          cleanup()
        }
      }

      audioRef.current = audio
      audio.load()
    } catch (error) {
      console.error("❌ Error in playAudioWithSession:", error)
      setIsAudioPlaying(false)
      setCurrentAudioId("")
    }
  }

  // Improved audio play function using direct URL from API
  const playAudioFromUrl = async (audioUrl: string, messageId: string) => {
    console.log(`=== AUDIO URL DEBUG ===`)
    console.log(`Audio URL: ${audioUrl}`)
    console.log(`Message ID: ${messageId}`)
    console.log(`Audio enabled: ${isAudioEnabled}`)
    console.log(`Full URL: ${API_BASE_URL}${audioUrl}`)
    
    // Always stop any currently playing audio first
    stopAudio()
    
    // Check if audio is enabled
    if (!isAudioEnabled) {
      console.log("❌ Audio is disabled - not starting playback")
      return
    }
    
    if (!audioUrl) {
      console.log("❌ No audio URL provided")
      return
    }

    try {
      // Create new audio element
      const audio = new Audio()
      console.log("🎵 Created new Audio element")
      
      // Set audio properties - use the provided audio URL
      audio.src = `${API_BASE_URL}${audioUrl}`
      audio.preload = 'auto'
      audio.volume = 1.0
      
      console.log("🎵 Audio src set to URL endpoint, starting load...")
      
      // Set up event handlers with proper cleanup
      const cleanup = () => {
        audio.onloadstart = null
        audio.oncanplay = null
        audio.oncanplaythrough = null
        audio.onplay = null
        audio.onended = null
        audio.onerror = null
        audio.onabort = null
        audio.onstalled = null
      }
      
      audio.onloadstart = () => {
        console.log("📥 Audio loading started")
        // Only update state if audio is still enabled
        if (isAudioEnabled) {
          setCurrentAudioId(messageId)
          setIsAudioPlaying(true)
        } else {
          console.log("❌ Audio disabled during load - stopping")
          audio.pause()
          cleanup()
          return
        }
      }
      
      audio.oncanplaythrough = () => {
        console.log("✅ Audio ready to play through")
        // Double-check audio is still enabled before playing
        if (isAudioEnabled && audioRef.current === audio) {
          audio.play().then(() => {
            console.log("🎵 Audio playback started successfully")
          }).catch(error => {
            console.error("❌ Audio play failed:", error)
            setIsAudioPlaying(false)
            setCurrentAudioId("")
            cleanup()
          })
        } else {
          console.log("❌ Audio disabled or replaced during canplaythrough")
          audio.pause()
          cleanup()
        }
      }

      audio.onplay = () => {
        console.log("▶️ Audio is now playing")
        if (audioRef.current === audio) {
          setIsAudioPlaying(true)
        }
      }

      audio.onended = () => {
        console.log("⏹️ Audio playback ended")
        if (audioRef.current === audio) {
          setIsAudioPlaying(false)
          setCurrentAudioId("")
          cleanup()
          audioRef.current = null
        }
      }

      audio.onerror = (error) => {
        console.error("❌ Audio error:", error)
        console.error("❌ Audio error details:", audio.error)
        if (audioRef.current === audio) {
          setIsAudioPlaying(false)
          setCurrentAudioId("")
          cleanup()
          audioRef.current = null
        }
      }

      audio.onabort = () => {
        console.log("⚠️ Audio loading aborted")
        if (audioRef.current === audio) {
          setIsAudioPlaying(false)
          setCurrentAudioId("")
          cleanup()
        }
      }

      // Store reference and start loading
      audioRef.current = audio
      audio.load()
      console.log("🎵 Audio load() called")

    } catch (error) {
      console.error("❌ Error in playAudioFromUrl:", error)
      setIsAudioPlaying(false)
      setCurrentAudioId("")
    }
  }

  // Improved audio toggle function
  const toggleAudio = () => {
    const newAudioState = !isAudioEnabled
    console.log(`Audio toggling from ${isAudioEnabled} to ${newAudioState}`)
    
    // If disabling audio, stop any currently playing audio immediately
    if (!newAudioState) {
      console.log("🔇 Disabling audio - stopping current playback")
      stopAudio()
    }
    
    setIsAudioEnabled(newAudioState)
    console.log(`Audio ${newAudioState ? 'enabled' : 'disabled'}`)
  }
  const handleSendMessage = async (content: string) => {
    if (!content.trim()) return

    // Prevent duplicate submissions
    if (isTyping) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: content.trim(),
      timestamp: new Date(),
      language: currentLanguage,
    }

    setMessages((prev) => [...prev, userMessage])
    setIsTyping(true)

    // Stop any currently playing audio when sending a new message
    stopAudio()

    try {
      // Call the start-assistant API directly
      const response = await fetch(`${API_BASE_URL}/api/v1/voice-assistant/start-assistant`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          transcript: content.trim(),
          session_id: sessionId
        })
      })

      if (!response.ok) {
        throw new Error(`Server error ${response.status}`)
      }

      const data = await response.json()

      if (!data) {
        throw new Error("Invalid response format")
      }

      const assistantMessageId = (Date.now() + 1).toString()
      const assistantMessage: Message = {
        id: assistantMessageId,
        type: "assistant",
        content: data.text || "Sorry, I couldn't generate a response.",        timestamp: new Date(),
        products: data.products || [],
        sentiment: "positive",
        audioFile: data.audio_file || "",
      }
      
      // Add message first
      setMessages((prev) => [...prev, assistantMessage])
      setIsTyping(false)

      console.log("=== MESSAGE RESPONSE DEBUG ===")
      console.log("API Response data:", data)
      console.log("Audio file from API:", data.audio_file)
      console.log("Audio URL from API:", data.audio_url)
      console.log("Static audio URL from API:", data.static_audio_url)
      console.log("Audio filename from API:", data.audio_filename)
      console.log("Products from API:", data.products)
      if (data.products && Array.isArray(data.products)) {
        console.log("Products array length:", data.products.length)
        data.products.forEach((product: any, index: number) => {
          console.log(`Product ${index}:`, product)
          console.log(`Product ${index} properties:`, Object.keys(product))
        })
      }
      console.log("Current isAudioEnabled:", isAudioEnabled)
      
      // Then handle audio - with a small delay to ensure state is updated
      setTimeout(() => {
        if ((data.audio_file || data.audio_url) && isAudioEnabled) {
          console.log("✅ Starting audio playback with session ID")
          playAudioWithSession(sessionId, assistantMessageId)
        } else {
          console.log("❌ Audio not started")
          console.log(`- Has audio file: ${!!data.audio_file}`)
          console.log(`- Has audio URL: ${!!data.audio_url}`)
          console.log(`- Audio enabled: ${isAudioEnabled}`)
          console.log(`- Audio file value: "${data.audio_file}"`)
          console.log(`- Audio URL value: "${data.audio_url}"`)
        }
      }, 100)

    } catch (error) {
      console.error("Error in chat flow:", error)
      setIsTyping(false)
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
        sentiment: "negative",
      }
      setMessages((prev) => [...prev, errorMessage])
    }
  }

  const handleVoiceResult = (transcript: string) => {
    handleSendMessage(transcript)
  }

  const handleVoiceListeningChange = (listening: boolean) => {
    setIsListening(listening)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-violet-50/30 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950 transition-all duration-700">
      {/* Enhanced Background Pattern */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-10 right-4 sm:top-20 sm:right-20 w-48 h-48 sm:w-72 sm:h-72 bg-gradient-to-br from-blue-400/8 to-violet-600/8 rounded-full blur-3xl animate-float"></div>
        <div className="absolute bottom-10 left-4 sm:bottom-20 sm:left-20 w-48 h-48 sm:w-72 sm:h-72 bg-gradient-to-tr from-cyan-400/8 to-blue-600/8 rounded-full blur-3xl animate-float" style={{animationDelay: '3s'}}></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-64 h-64 sm:w-96 sm:h-96 bg-gradient-to-r from-violet-400/5 to-blue-400/5 rounded-full blur-3xl animate-pulse-slow"></div>
      </div>

      {/* Enhanced Header */}
      <header className="relative border-b border-white/10 dark:border-slate-800/30 glass-strong sticky top-0 z-50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 lg:px-8">
          <div className="flex justify-between items-center h-16 sm:h-20">
            <div className="flex items-center space-x-2 sm:space-x-6 min-w-0 flex-1">
              <Link href="/">
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white transition-all duration-300 hover:bg-white/40 dark:hover:bg-slate-800/40 rounded-xl p-2 sm:p-3 shrink-0"
                >
                  <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
                </Button>
              </Link>
              <div className="flex items-center space-x-2 sm:space-x-4 min-w-0">
                <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-blue-500 via-violet-600 to-cyan-500 rounded-xl sm:rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/20 shrink-0">
                  <MessageSquare className="h-5 w-5 sm:h-6 sm:w-6 text-white" />
                </div>
                <div className="flex flex-col min-w-0">
                  <h1 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white truncate">SalesSpeak Chat</h1>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse shrink-0"></div>
                    <span className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 font-medium truncate">AI Assistant Online</span>
                  </div>
                  <div className="mt-1">
                    <span className="inline-block px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 text-[10px] sm:text-xs font-medium tracking-wide">
                      Trained on Lenden Club data
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-1 sm:space-x-4 shrink-0">
              <div className="hidden sm:block">
                <ApiStatus />
              </div>
              
              {/* Audio Toggle Button */}
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleAudio}
                className={`relative transition-all duration-300 hover:bg-white/40 dark:hover:bg-slate-800/40 rounded-xl p-2 sm:p-3 ${
                  isAudioEnabled 
                    ? 'text-blue-600 dark:text-blue-400' 
                    : 'text-slate-400 dark:text-slate-600'
                }`}
                title={isAudioEnabled ? "Disable audio" : "Enable audio"}
              >
                {isAudioEnabled ? (
                  <Volume2 className="h-4 w-4 sm:h-5 sm:w-5" />
                ) : (
                  <VolumeX className="h-4 w-4 sm:h-5 sm:w-5" />
                )}
                {isAudioPlaying && isAudioEnabled && (
                  <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                )}
              </Button>

              <ThemeToggle />
              <div className="hidden sm:block">
                <LanguageSelector currentLanguage={currentLanguage} onLanguageChange={setCurrentLanguage} />
              </div>
            </div>
          </div>
          
          {/* Mobile-only bottom row for hidden elements */}
          <div className="sm:hidden pb-3 flex items-center justify-between">
            <ApiStatus />
            <LanguageSelector currentLanguage={currentLanguage} onLanguageChange={setCurrentLanguage} />
          </div>
        </div>
      </header>

      <div className="relative flex h-[calc(100vh-4rem)] sm:h-[calc(100vh-5rem)]">
        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col w-full">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-4 sm:space-y-6 scrollbar-thin">
            {/* Offline Warning */}
            {!isOnline && (
              <Alert className="border-yellow-300/50 glass-strong border border-yellow-200/50 dark:border-yellow-600/30 shadow-lg animate-in slide-in-from-top-4 duration-500">
                <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
                <AlertDescription className="text-yellow-800 dark:text-yellow-200">
                  You're currently offline. Voice recognition won't work, but you can still type messages.
                </AlertDescription>
              </Alert>
            )}            {messages.map((message) => (
              <div key={message.id} className="animate-in slide-in-from-bottom-4 duration-500">
                <MessageBubble message={message} />                
                {message.products && message.products.length > 0 && (
                  <div className="mt-4 sm:mt-6">
                    <div className="mb-2 text-sm text-blue-600 dark:text-blue-400 font-medium">
                      Found {message.products.length} products:
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                      {message.products.map((product, index) => {
                        console.log(`Rendering product ${index}:`, product)
                        try {
                          return <ProductCard key={product.id || product.product_id || `product-${index}`} product={product} />
                        } catch (error) {
                          console.error(`Error rendering product ${index}:`, error, product)
                          return (
                            <div key={`error-product-${index}`} className="p-4 border-2 border-red-200 rounded-lg bg-red-50 dark:bg-red-900/20">
                              <p className="text-red-600 dark:text-red-400 text-sm">
                                Error displaying product {index}. Check console for details.
                              </p>
                              <pre className="text-xs mt-2 overflow-auto">{JSON.stringify(product, null, 2)}</pre>
                            </div>
                          )
                        }
                      })}
                    </div>
                  </div>
                )}
                
                {/* Show if no products */}
                {message.type === "assistant" && (!message.products || message.products.length === 0) && (
                  <div className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    No products in this response.
                  </div>
                )}
              </div>
            ))}
            {isTyping && (
              <div className="flex items-center space-x-3 text-slate-500 dark:text-slate-400 animate-in slide-in-from-bottom-4 duration-300">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-violet-500 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-violet-500 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                  <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-violet-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
                </div>
                <span className="text-sm font-medium">Assistant is thinking...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Compact Input Area - Claude-like Design for Sales Assistant */}
          <div className="border-t border-white/20 dark:border-slate-800/50 glass-strong p-3 sm:p-4">
            <div className="max-w-4xl mx-auto">
              {/* Compact Input Row */}
              <div className="flex items-center space-x-3 sm:space-x-4">
                {/* Voice Button */}
                <div className="relative flex-shrink-0">
                  <div className="relative bg-white/20 dark:bg-slate-900/20 backdrop-blur-lg border border-white/30 dark:border-slate-700/30 rounded-full p-2 shadow-lg">
                    <VoiceRecognition
                      isListening={isListening}
                      onListeningChange={handleVoiceListeningChange}
                      onResult={handleVoiceResult}
                      language={currentLanguage}
                      size="sm"
                      isAudioPlaying={isAudioPlaying}
                      onStopAudio={stopAudio}
                    />
                  </div>
                </div>

                {/* Text Input */}
                <div className="flex-1">
                  <TextInputFallback
                    onSend={handleSendMessage}
                    placeholder={isListening ? "🎤 Listening..." : "Ask about pricing, features, or product recommendations..."}
                    disabled={isTyping}
                  />
                </div>
              </div>

              {/* Compact Status Row */}
              <div className="flex items-center justify-between mt-2 px-1">
                <div className="flex items-center space-x-4 text-xs">
                  {/* Voice Status */}
                  {isListening && (
                    <div className="flex items-center space-x-1 text-slate-600 dark:text-slate-300">
                      <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></span>
                      <span>Listening</span>
                    </div>
                  )}

                  {/* Audio Status */}
                  {isAudioPlaying && isAudioEnabled && (
                    <div className="flex items-center space-x-1 text-blue-600 dark:text-blue-400">
                      <Volume2 className="h-3 w-3 animate-pulse" />
                      <span>Playing</span>
                    </div>
                  )}

                  {!isAudioEnabled && (
                    <div className="flex items-center space-x-1 text-slate-500 dark:text-slate-400">
                      <VolumeX className="h-3 w-3" />
                      <span>Audio off</span>
                    </div>
                  )}
                </div>

                {/* Language & Session Info */}
                <div className="flex items-center space-x-2 text-xs text-slate-500 dark:text-slate-400">
                  <span>{currentLanguage === 'hi' ? 'हिंदी/EN' : 'EN'}</span>
                  <span className="text-slate-400">•</span>
                  <span className="font-mono">{sessionId.slice(-6)}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}