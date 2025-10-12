import React, { useState } from 'react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import HelpModal from '../HelpModal'
import {
  BarChart3,
  MessageSquare,
  Map,
  Settings,
  HelpCircle,
  Download,
  RefreshCw,
  Upload,
  Mic
} from 'lucide-react'
import { motion } from 'framer-motion'

interface SidebarProps {
  activeTab: string
  onTabChange: (tab: string) => void
  isCollapsed: boolean
  onToggle: () => void
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const navigationItems = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: BarChart3,
    description: 'Overview and statistics'
  },
  {
    id: 'chat',
    label: 'AI Chat',
    icon: MessageSquare,
    description: 'Ask questions about data',
    badge: 'AI'
  },
  {
    id: 'map',
    label: 'Map View',
    icon: Map,
    description: 'Geographic visualization'
  },
  {
    id: 'dataops',
    label: 'DataOps Upload',
    icon: Upload,
    description: 'Upload and process NetCDF files',
    badge: 'Pipeline'
  }
]

const quickActions = [
  {
    id: 'export',
    label: 'Export Data',
    icon: Download,
    action: async () => {
      try {
        const res = await fetch(`${API_URL}/data/export/csv`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        const ts = new Date().toISOString().replace(/[:.]/g, '-')
        a.download = `floatchat_export_${ts}.csv`
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      } catch (e) {
        console.error('Export failed', e)
        alert('Export failed. Please try again.')
      }
    }
  },
  {
    id: 'export-json',
    label: 'Export JSON',
    icon: Download,
    action: async () => {
      try {
        const res = await fetch(`${API_URL}/data/export/json`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        const ts = new Date().toISOString().replace(/[:.]/g, '-')
        a.download = `floatchat_export_${ts}.json`
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      } catch (e) {
        console.error('Export JSON failed', e)
        alert('Export JSON failed. Please try again.')
      }
    }
  },
  {
    id: 'export-ascii',
    label: 'Export ASCII',
    icon: Download,
    action: async () => {
      try {
        const res = await fetch(`${API_URL}/data/export/ascii`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        const ts = new Date().toISOString().replace(/[:.]/g, '-')
        a.download = `floatchat_export_${ts}.txt`
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      } catch (e) {
        console.error('Export ASCII failed', e)
        alert('Export ASCII failed. Please try again.')
      }
    }
  },
  {
    id: 'refresh',
    label: 'Refresh',
    icon: RefreshCw,
    action: () => window.location.reload()
  }
]

export default function Sidebar({ activeTab, onTabChange, isCollapsed, onToggle }: SidebarProps) {
  const [showHelp, setShowHelp] = useState(false)

  return (
    <>
      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
    <motion.aside 
      className={`bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
      initial={{ width: 256 }}
      animate={{ width: isCollapsed ? 64 : 256 }}
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between">
            {!isCollapsed && (
              <h2 className="text-lg font-semibold text-foreground">Navigation</h2>
            )}
            <Button
              variant="ghost"
              size="icon"
              onClick={onToggle}
              className="ml-auto"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2">
          {navigationItems.map((item) => {
            const Icon = item.icon
            const isActive = activeTab === item.id
            
            return (
              <motion.div
                key={item.id}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <Button
                  variant={isActive ? "default" : "ghost"}
                  className={`w-full justify-start h-auto p-3 ${
                    isCollapsed ? 'px-2' : 'px-3'
                  }`}
                  onClick={() => onTabChange(item.id)}
                >
                  <div className="flex items-center gap-3 w-full">
                    <Icon className={`h-5 w-5 ${isCollapsed ? 'mx-auto' : ''}`} />
                    {!isCollapsed && (
                      <div className="flex-1 text-left">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{item.label}</span>
                          {item.badge && (
                            <Badge variant="secondary" className="text-xs">
                              {item.badge}
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {item.description}
                        </p>
                      </div>
                    )}
                  </div>
                </Button>
              </motion.div>
            )
          })}
        </nav>

        {/* Quick Actions */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800 space-y-2">
          {!isCollapsed && (
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Quick Actions</p>
          )}
          {quickActions.map((action) => {
            const Icon = action.icon
            return (
              <Button
                key={action.id}
                variant="outline"
                size="sm"
                className={`w-full ${isCollapsed ? 'px-2' : 'px-3'}`}
                onClick={action.action}
              >
                <Icon className={`h-4 w-4 ${isCollapsed ? 'mx-auto' : 'mr-2'}`} />
                {!isCollapsed && action.label}
              </Button>
            )
          })}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <button
            onClick={() => setShowHelp(true)}
            className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors w-full text-left p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <HelpCircle className="h-4 w-4" />
            {!isCollapsed && (
              <span>Need help? Check our docs</span>
            )}
          </button>
        </div>
      </div>
    </motion.aside>
    </>
  )
}
