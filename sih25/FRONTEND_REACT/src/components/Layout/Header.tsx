import React, { useEffect, useState } from 'react'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Waves, Menu, X } from 'lucide-react'
import { motion } from 'framer-motion'

interface HeaderProps {
  onMenuToggle: () => void
  isMenuOpen: boolean
}

export default function Header({ onMenuToggle, isMenuOpen }: HeaderProps) {
  const [dark, setDark] = useState<boolean>(false)

  useEffect(() => {
    try {
      const pref = localStorage.getItem('theme')
      let isDark = false
      if (pref) {
        isDark = pref === 'dark'
      } else {
        // fall back to system preference when no saved theme
        isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
      }
      setDark(isDark)
      const root = document.documentElement
      if (isDark) root.classList.add('dark')
      else root.classList.remove('dark')
      // update theme-color meta for better address bar coloring
      const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
      if (meta) meta.content = isDark ? '#0b141d' : '#ffffff'
    } catch {}
  }, [])

  const toggleDark = () => {
    const next = !dark
    setDark(next)
    const root = document.documentElement
    if (next) {
      root.classList.add('dark')
      try { localStorage.setItem('theme', 'dark') } catch {}
    } else {
      root.classList.remove('dark')
      try { localStorage.setItem('theme', 'light') } catch {}
    }
    // update theme-color meta
    try {
      const meta = document.querySelector('meta[name="theme-color"]') as HTMLMetaElement | null
      if (meta) meta.content = next ? '#0b141d' : '#ffffff'
    } catch {}
  }
  return (
    <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50">
      <div className="px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <motion.div 
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg flex items-center justify-center">
              <Waves className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">FloatChat</h1>
              <p className="text-xs text-gray-600 dark:text-gray-300">ARGO Data Platform</p>
            </div>
          </motion.div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <a href="#dashboard" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors">
              Dashboard
            </a>
            <a href="#chat" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors">
              AI Chat
            </a>
            <a href="#visualization" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors">
              Visualization
            </a>
            <a href="#map" className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors">
              Map
            </a>
          </nav>

          {/* Status & Actions */}
          <div className="flex items-center gap-4">
            <Badge variant="secondary" className="hidden sm:flex">
              <div className="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
              System Online
            </Badge>
            <Button variant="outline" size="sm" className="hidden sm:flex" onClick={toggleDark}>
              {dark ? 'Light Mode' : 'Dark Mode'}
            </Button>

            {/* Mobile menu button */}
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={onMenuToggle}
            >
              {isMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isMenuOpen && (
        <motion.div 
          className="md:hidden border-t border-gray-200 bg-white"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
        >
          <div className="px-4 py-4 space-y-3">
            <a 
              href="#dashboard" 
              className="block text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              onClick={onMenuToggle}
            >
              Dashboard
            </a>
            <a 
              href="#chat" 
              className="block text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              onClick={onMenuToggle}
            >
              AI Chat
            </a>
            <a 
              href="#visualization" 
              className="block text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              onClick={onMenuToggle}
            >
              Visualization
            </a>
            <a 
              href="#map" 
              className="block text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
              onClick={onMenuToggle}
            >
              Map
            </a>
            <div className="pt-3 border-t border-gray-200">
              <Button variant="outline" size="sm" className="w-full" onClick={toggleDark}>
                {dark ? 'Light Mode' : 'Dark Mode'}
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </header>
  )
}
