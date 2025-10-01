import React, { useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'

// Persist dark mode preference
const applyTheme = () => {
  try {
    const pref = localStorage.getItem('theme')
    if (pref === 'dark') document.body.classList.add('dark')
    if (pref === 'light') document.body.classList.remove('dark')
  } catch {}
}

applyTheme()

const root = createRoot(document.getElementById('root') as HTMLElement)
root.render(<App />)
