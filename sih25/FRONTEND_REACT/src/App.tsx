import React, { useState, useEffect } from 'react'
import { Toaster, toast } from 'react-hot-toast'
import Header from './components/Layout/Header'
import Sidebar from './components/Layout/Sidebar'
import ChatInterface from './components/ChatInterface'
import DataVisualization from './components/DataVisualization'
import MapVisualization from './components/MapVisualization'
import InsertData from './components/InsertData'
import ReactVoicePipecat from './components/ReactVoicePipecat'
import { motion, AnimatePresence } from 'framer-motion'
import api from './services/api'

type Tab = 'dashboard' | 'chat' | 'map' | 'insert' | 'voice'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Simulate initial loading
    const timer = setTimeout(() => {
      setIsLoading(false)
    }, 1000)
    return () => clearTimeout(timer)
  }, [])

  // Dynamic page title for basic SEO/UX
  useEffect(() => {
    const titles: Record<Tab, string> = {
      dashboard: 'Dashboard',
      chat: 'AI Chat',
      map: 'Map View',
      insert: 'Insert Data',
      voice: 'Voice AI'
    }
    document.title = `FloatChat – ${titles[activeTab]}`
  }, [activeTab])

  const renderContent = () => {
    switch (activeTab) {
      case 'chat':
        return <ChatInterface />
      case 'map':
        return <MapVisualization />
      case 'insert':
        return <InsertData />
      case 'voice':
        return <ReactVoicePipecat />
      case 'dashboard':
      default:
        return <Dashboard />
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold mb-2">FloatChat</h2>
          <p className="text-muted-foreground">Loading ARGO Data Platform...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <Toaster position="top-right" />
      
      <Header 
        onMenuToggle={() => setIsMenuOpen(!isMenuOpen)}
        isMenuOpen={isMenuOpen}
      />
      
      <div className="flex">
        <Sidebar
          activeTab={activeTab}
          onTabChange={(tab) => setActiveTab(tab as Tab)}
          isCollapsed={isSidebarCollapsed}
          onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />
        
        <main className="flex-1 p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              {renderContent()}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

function Dashboard() {
  const [stats, setStats] = useState({
    totalProfiles: 0,
    avgTemperature: 0,
    avgSalinity: 0,
    depthRange: { min: 0, max: 0 }
  })
  const [connectionStatus, setConnectionStatus] = useState<'loading' | 'connected' | 'offline'>('loading')

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    setConnectionStatus('loading')
    try {
      // Use direct Supabase connection instead of broken MCP
      console.log('🔄 Fetching stats directly from Supabase...')

      // First check if Supabase is healthy
      const isHealthy = await api.supabase.getHealth()
      if (!isHealthy) {
        throw new Error('Supabase connection failed')
      }

      // Get some sample data directly from Supabase
      const profiles = await api.supabase.getProfiles(500)
      console.log(`✅ Fetched ${profiles.length} profiles from Supabase`)

      if (profiles.length > 0) {
        const temps = profiles.map((p) => p.temperature).filter((t) => !isNaN(t) && t !== 0)
        const salinities = profiles.map((p) => p.salinity).filter((s) => !isNaN(s) && s !== 0)
        const depths = profiles.map((p) => p.depth).filter((d) => !isNaN(d) && d !== 0)

        setStats({
          totalProfiles: profiles.length,
          avgTemperature: temps.length > 0 ? temps.reduce((a: number, b: number) => a + b, 0) / temps.length : 0,
          avgSalinity: salinities.length > 0 ? salinities.reduce((a: number, b: number) => a + b, 0) / salinities.length : 0,
          depthRange: {
            min: depths.length > 0 ? Math.min(...depths) : 0,
            max: depths.length > 0 ? Math.max(...depths) : 0
          }
        })
        setConnectionStatus('connected')
      } else {
        // Show placeholder data when no profiles returned
        setStats({
          totalProfiles: 0,
          avgTemperature: 0,
          avgSalinity: 0,
          depthRange: { min: 0, max: 0 }
        })
        setConnectionStatus('offline')
      }
    } catch (error) {
      console.error('❌ Failed to fetch stats from Supabase:', error)
      // Show mock data when API fails
      setStats({
        totalProfiles: 406, // We know this from database
        avgTemperature: 12.5,
        avgSalinity: 35.2,
        depthRange: { min: 100, max: 2000 }
      })
      setConnectionStatus('offline')
    }
  }

  const reindex = async () => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const id = toast.loading('Re-indexing metadata...')
    try {
      const res = await fetch(`${API_URL}/admin/reindex`, {
        method: 'POST'
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      toast.success(`Indexed ${json.indexed ?? 0} docs`, { id })
    } catch (e: any) {
      toast.error(`Re-index failed: ${e?.message || 'Unknown error'}`, { id })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">FloatChat Dashboard</h1>
        <p className="text-muted-foreground">AI-powered ARGO float ocean data discovery and analysis</p>

        {/* Connection Status */}
        <div
          className={
            `flex items-center mt-4 p-3 rounded-lg border transition-colors ` +
            (connectionStatus === 'connected'
              ? 'bg-emerald-100 border-emerald-200 text-emerald-900 dark:bg-emerald-900/30 dark:border-emerald-800 dark:text-emerald-200'
              : connectionStatus === 'loading'
              ? 'bg-amber-100 border-amber-200 text-amber-900 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-200'
              : 'bg-rose-100 border-rose-200 text-rose-900 dark:bg-rose-900/30 dark:border-rose-800 dark:text-rose-200')
          }
        >
          <div
            className={
              `w-3 h-3 rounded-full mr-3 ` +
              (connectionStatus === 'connected'
                ? 'bg-emerald-500'
                : connectionStatus === 'loading'
                ? 'bg-amber-500'
                : 'bg-rose-500')
            }
          />
          <span className="text-sm">
            {connectionStatus === 'connected' ? 'Connected to backend API' :
             connectionStatus === 'loading' ? 'Connecting to backend...' :
             'Using offline mode - showing sample data'}
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-card text-card-foreground rounded-lg border border-border p-6"
        >
          <div className="flex items-center">
            <div className="p-2 bg-primary/10 text-primary rounded-lg">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-muted-foreground">Total Profiles</p>
              <p className="text-2xl font-bold">{stats.totalProfiles.toLocaleString()}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-card text-card-foreground rounded-lg border border-border p-6"
        >
          <div className="flex items-center">
            <div className="p-2 bg-red-500/10 text-red-500 rounded-lg">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-muted-foreground">Avg Temperature</p>
              <p className="text-2xl font-bold">{stats.avgTemperature.toFixed(1)}°C</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-card text-card-foreground rounded-lg border border-border p-6"
        >
          <div className="flex items-center">
            <div className="p-2 bg-green-500/10 text-green-500 rounded-lg">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-muted-foreground">Avg Salinity</p>
              <p className="text-2xl font-bold">{stats.avgSalinity.toFixed(2)} PSU</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-card text-card-foreground rounded-lg border border-border p-6"
        >
          <div className="flex items-center">
            <div className="p-2 bg-purple-500/10 text-purple-500 rounded-lg">
              <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-muted-foreground">Depth Range</p>
              <p className="text-2xl font-bold">{stats.depthRange.min}-{stats.depthRange.max}m</p>
            </div>
          </div>
        </motion.div>
      </div>


      {/* Analytics Section (merged from Visualization) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="bg-card text-card-foreground rounded-lg border border-border p-6"
      >
        <h2 className="text-lg font-semibold mb-4">Analytics</h2>
        <p className="text-sm text-muted-foreground mb-4">Interactive charts and insights derived from current dataset.</p>
        <div className="w-full">
          <DataVisualization />
        </div>
      </motion.div>
    </div>
  )
}

export default App