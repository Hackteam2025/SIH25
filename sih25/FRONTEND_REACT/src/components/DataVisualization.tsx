import React, { useState, useEffect, useMemo, memo } from 'react'

import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Badge } from './ui/Badge'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import {
  BarChart3,
  MapPin,
  Thermometer,
  Waves,
  Download,
  Filter,
  Search,
  RefreshCw
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  LineChart,
  Line
} from 'recharts'
import api from '../services/api'

interface Profile {
  profile_id: string
  latitude: number
  longitude: number
  depth: number
  temperature: number
  salinity: number
  pressure: number
  month: number
  year: number
  timestamp: string
}

function DataVisualization() {
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [filteredProfiles, setFilteredProfiles] = useState<Profile[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedDepth, setSelectedDepth] = useState<number | null>(null)
  const [tempBinWidth, setTempBinWidth] = useState<number>(1)
  const [salBinWidth, setSalBinWidth] = useState<number>(0.5)
  const [maWindow, setMaWindow] = useState<number>(3)

  const [stats, setStats] = useState({
    total: 0,
    avgTemp: 0,
    avgSalinity: 0,
    depthRange: { min: 0, max: 0 }
  })

  const [chartLoading, setChartLoading] = useState({
    depth: true,
    scatter: true,
    tempHist: true,
    salHist: true,
    tempTime: true,
    salTime: true
  })

  const fetchProfiles = async () => {
    console.log('🔄 Starting to fetch profiles directly from Supabase...')
    try {
      const startTime = performance.now()

      // Use direct Supabase API - fetch up to 500 observations
      const profilesData = await api.supabase.getProfiles(500)
      const endTime = performance.now()

      console.log(`✅ Fetched ${profilesData.length} profiles from Supabase in ${(endTime - startTime).toFixed(2)}ms`)

      setProfiles(profilesData)

      // Calculate stats from actual data, filtering out zeros
      if (profilesData.length > 0) {
        const temps = profilesData.map(p => p.temperature).filter(t => !isNaN(t) && t !== 0)
        const salinities = profilesData.map(p => p.salinity).filter(s => !isNaN(s) && s !== 0)
        const depths = profilesData.map(p => p.depth).filter(d => !isNaN(d) && d !== 0)

        setStats({
          total: profilesData.length,
          avgTemp: temps.length > 0 ? temps.reduce((a, b) => a + b, 0) / temps.length : 0,
          avgSalinity: salinities.length > 0 ? salinities.reduce((a, b) => a + b, 0) / salinities.length : 0,
          depthRange: {
            min: depths.length > 0 ? Math.min(...depths) : 0,
            max: depths.length > 0 ? Math.max(...depths) : 0
          }
        })
      }

      // Immediate chart loading
      setChartLoading({
        depth: false,
        scatter: false,
        tempHist: false,
        salHist: false,
        tempTime: false,
        salTime: false
      })
    } catch (error) {
      console.error('❌ Failed to fetch profiles from Supabase:', error)
      setProfiles([])
    } finally {
      setLoading(false)
    }
  }

  const filterProfiles = () => {
    let filtered = profiles

    if (searchTerm) {
      filtered = filtered.filter(p =>
        p.profile_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.latitude != null && p.latitude.toString().includes(searchTerm)) ||
        (p.longitude != null && p.longitude.toString().includes(searchTerm))
      )
    }

    if (selectedDepth !== null) {
      filtered = filtered.filter(p => p.depth === selectedDepth)
    }

    setFilteredProfiles(filtered)
  }

  const exportData = async (format: 'csv' | 'ascii') => {
    try {
      const response = await fetch(`${API_URL}/data/export/${format}`)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `floatchat-export.${format === 'csv' ? 'csv' : 'txt'}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Export failed:', error)
    }
  }

  const depthDistribution = useMemo(() => {
    const acc: Record<number, number> = {}
    for (const profile of filteredProfiles) {
      const depth = profile.depth
      acc[depth] = (acc[depth] || 0) + 1
    }
    return acc
  }, [filteredProfiles])

  const depthData = useMemo(() => {
    return Object.entries(depthDistribution).map(([depth, count]) => ({
      depth: parseInt(depth),
      count
    })).sort((a, b) => a.depth - b.depth)
  }, [depthDistribution])

  const tempSalinityData = useMemo(() => {
    return filteredProfiles.map(profile => ({
      temperature: profile.temperature,
      salinity: profile.salinity,
      depth: profile.depth
    }))
  }, [filteredProfiles])

  // Temperature histogram with adjustable bin width
  const tempBins = useMemo(() => {
    const bins: Record<number, number> = {}
    const w = Math.max(0.1, tempBinWidth)
    for (const p of filteredProfiles) {
      if (p.temperature != null && !isNaN(p.temperature)) {
        const bin = Math.floor(p.temperature / w) * w
        bins[bin] = (bins[bin] || 0) + 1
      }
    }
    return Object.entries(bins)
      .map(([t, c]) => ({ temp: Number(t), count: c as number }))
      .sort((a, b) => a.temp - b.temp)
  }, [filteredProfiles, tempBinWidth])

  // Salinity histogram with adjustable bin width
  const salBins = useMemo(() => {
    const bins: Record<number, number> = {}
    const w = Math.max(0.1, salBinWidth)
    for (const p of filteredProfiles) {
      if (p.salinity != null && !isNaN(p.salinity)) {
        const bin = Math.floor(p.salinity / w) * w
        bins[bin] = (bins[bin] || 0) + 1
      }
    }
    return Object.entries(bins)
      .map(([s, c]) => ({ sal: Number(s), count: c as number }))
      .sort((a, b) => a.sal - b.sal)
  }, [filteredProfiles, salBinWidth])

  // Monthly temperature time series with configurable moving average
  const timeSeriesTemp = useMemo(() => {
    const groups: Record<string, { sum: number; n: number }> = {}
    for (const p of filteredProfiles) {
      if (p.temperature != null && !isNaN(p.temperature) && p.year != null && p.month != null) {
        const ym = `${p.year}-${String(p.month).padStart(2, '0')}`
        if (!groups[ym]) groups[ym] = { sum: 0, n: 0 }
        groups[ym].sum += p.temperature
        groups[ym].n += 1
      }
    }
    const series = Object.entries(groups)
      .map(([ym, v]) => ({ ym, avg: v.sum / v.n }))
      .sort((a, b) => a.ym.localeCompare(b.ym))
    const w = Math.max(1, Math.floor(maWindow))
    const half = Math.floor((w - 1) / 2)
    const out = series.map((row, i) => {
      const start = Math.max(0, i - half)
      const end = Math.min(series.length - 1, i + half)
      const slice = series.slice(start, end + 1)
      const ma = slice.reduce((acc, r) => acc + r.avg, 0) / slice.length
      return { ...row, ma }
    })
    return out
  }, [filteredProfiles, maWindow])

  // Monthly salinity time series with matching MA window
  const timeSeriesSal = useMemo(() => {
    const groups: Record<string, { sum: number; n: number }> = {}
    for (const p of filteredProfiles) {
      if (p.salinity != null && !isNaN(p.salinity) && p.year != null && p.month != null) {
        const ym = `${p.year}-${String(p.month).padStart(2, '0')}`
        if (!groups[ym]) groups[ym] = { sum: 0, n: 0 }
        groups[ym].sum += p.salinity
        groups[ym].n += 1
      }
    }
    const series = Object.entries(groups)
      .map(([ym, v]) => ({ ym, avg: v.sum / v.n }))
      .sort((a, b) => a.ym.localeCompare(b.ym))
    const w = Math.max(1, Math.floor(maWindow))
    const half = Math.floor((w - 1) / 2)
    const out = series.map((row, i) => {
      const start = Math.max(0, i - half)
      const end = Math.min(series.length - 1, i + half)
      const slice = series.slice(start, end + 1)
      const ma = slice.reduce((acc, r) => acc + r.avg, 0) / slice.length
      return { ...row, ma }
    })
    return out
  }, [filteredProfiles, maWindow])

  // Export helpers
  const exportCSV = (filename: string, rows: Record<string, any>[]) => {
    if (!rows || !rows.length) return
    const headers = Object.keys(rows[0])
    const lines = [headers.join(',')]
    for (const r of rows) {
      lines.push(headers.map(h => JSON.stringify(r[h] ?? '')).join(','))
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const exportPNG = async (containerId: string, fileName: string) => {
    const el = document.getElementById(containerId)
    if (!el) return
    const svg = el.querySelector('svg') as SVGSVGElement | null
    if (!svg) return
    const svgData = new XMLSerializer().serializeToString(svg)
    const img = new Image()
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(svgBlob)
    img.onload = () => {
      const canvas = document.createElement('canvas') as HTMLCanvasElement
      canvas.width = svg.clientWidth || 1000
      canvas.height = svg.clientHeight || 600
      const ctx = canvas.getContext('2d')!
      ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--background') || '#0b141d'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0)
      URL.revokeObjectURL(url)
      canvas.toBlob((blob) => {
        if (!blob) return
        const pngUrl = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = pngUrl
        a.download = fileName
        a.click()
        URL.revokeObjectURL(pngUrl)
      })
    }
    img.src = url
  }

  useEffect(() => {
    console.log('🚀 DataVisualization component mounted')
    fetchProfiles()
  }, [])

  // Add dependency tracking for filter changes
  useEffect(() => {
    if (profiles.length > 0) {
      filterProfiles()
    }
  }, [searchTerm, selectedDepth, profiles])

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="h-6 bg-gray-200 rounded animate-pulse"></div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
              <div className="h-10 bg-gray-200 rounded animate-pulse"></div>
            </div>
          </CardContent>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i}>
              <CardHeader>
                <div className="h-6 bg-gray-200 rounded animate-pulse w-3/4"></div>
              </CardHeader>
              <CardContent>
                <div className="h-80 bg-gray-200 rounded animate-pulse"></div>
              </CardContent>
            </Card>
          ))}
        </div>

        <Card>
          <CardHeader>
            <div className="h-6 bg-gray-200 rounded animate-pulse"></div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-4 bg-gray-200 rounded animate-pulse"></div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Data Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4 flex-wrap">
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                <Input
                  placeholder="Search by ID, lat, lon..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="min-w-[150px]">
              <label className="text-sm font-medium mb-2 block">Depth Filter</label>
              <select
                value={selectedDepth || ''}
                onChange={(e) => setSelectedDepth(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full h-10 px-3 py-2 border border-input bg-background rounded-md text-sm"
              >
                <option value="">All Depths</option>
                {[5, 10, 20, 50, 100, 200, 500].map(depth => (
                  <option key={depth} value={depth}>{depth}m</option>
                ))}
              </select>
            </div>
            
            <div className="flex items-end gap-2">
              <Button onClick={() => window.open(`${API_URL}/data/export/csv`, '_blank')}>Download CSV</Button>
              <Button onClick={() => window.open(`${API_URL}/data/export/json`, '_blank')}>Download JSON</Button>
              <Button onClick={() => window.open(`${API_URL}/data/export/netcdf`, '_blank')}>Download NetCDF</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Chart Controls */}
      <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
            <BarChart3 className="h-5 w-5" />
            Chart Controls
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-blue-800 dark:text-blue-200 block">Temperature bin width (°C)</label>
              <Input 
                type="number" 
                step="0.1" 
                value={tempBinWidth} 
                onChange={(e) => setTempBinWidth(parseFloat(e.target.value) || 1)} 
                className="border-blue-300 focus:border-blue-500 focus:ring-blue-500/20"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-blue-800 dark:text-blue-200 block">Salinity bin width (PSU)</label>
              <Input 
                type="number" 
                step="0.1" 
                value={salBinWidth} 
                onChange={(e) => setSalBinWidth(parseFloat(e.target.value) || 0.5)} 
                className="border-blue-300 focus:border-blue-500 focus:ring-blue-500/20"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-semibold text-blue-800 dark:text-blue-200 block">Moving average window</label>
              <Input 
                type="number" 
                min={1} 
                step={1} 
                value={maWindow} 
                onChange={(e) => setMaWindow(parseInt(e.target.value) || 3)} 
                className="border-blue-300 focus:border-blue-500 focus:ring-blue-500/20"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-blue-500 bg-gradient-to-br from-white to-blue-50/30 dark:from-gray-900 dark:to-blue-950/30">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                Depth Distribution
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => exportPNG('chart-depth', 'depth_distribution.png')} className="hover:bg-blue-50 hover:border-blue-300">
                  PNG
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCSV('depth_distribution.csv', depthData)} className="hover:bg-blue-50 hover:border-blue-300">
                  CSV
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div id="chart-depth" className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            {chartLoading.depth ? (
              <div className="flex items-center justify-center h-[320px]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading depth chart...</span>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={depthData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="depth" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            )}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-green-500 bg-gradient-to-br from-white to-green-50/30 dark:from-gray-900 dark:to-green-950/30">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-green-900 dark:text-green-100">
                <svg className="h-5 w-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="3" />
                  <circle cx="12" cy="5" r="1" />
                  <circle cx="12" cy="19" r="1" />
                  <circle cx="5" cy="12" r="1" />
                  <circle cx="19" cy="12" r="1" />
                </svg>
                Temperature vs Salinity
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => exportPNG('chart-scatter', 'temp_vs_salinity.png')} className="hover:bg-green-50 hover:border-green-300">
                  PNG
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCSV('temp_vs_salinity.csv', tempSalinityData)} className="hover:bg-green-50 hover:border-green-300">
                  CSV
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div id="chart-scatter" className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            {chartLoading.scatter ? (
              <div className="flex items-center justify-center h-[320px]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading scatter chart...</span>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <ScatterChart data={tempSalinityData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="temperature" name="Temperature (°C)" />
                  <YAxis dataKey="salinity" name="Salinity (PSU)" />
                  <Tooltip />
                  <Scatter dataKey="salinity" fill="#10b981" />
                </ScatterChart>
              </ResponsiveContainer>
            )}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-red-500 bg-gradient-to-br from-white to-red-50/30 dark:from-gray-900 dark:to-red-950/30">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-red-900 dark:text-red-100">
                <Thermometer className="h-5 w-5 text-red-600" />
                Temperature Histogram ({tempBinWidth}°C bins)
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => exportPNG('chart-temp-hist', 'temperature_histogram.png')} className="hover:bg-red-50 hover:border-red-300">
                  PNG
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCSV('temperature_histogram.csv', tempBins)} className="hover:bg-red-50 hover:border-red-300">
                  CSV
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div id="chart-temp-hist" className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            {chartLoading.tempHist ? (
              <div className="flex items-center justify-center h-[320px]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading temperature histogram...</span>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={tempBins}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="temp"
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Temperature (°C)', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle' } }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fef2f2',
                      border: '1px solid #fecaca',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                  <Bar dataKey="count" fill="url(#redGradient)" radius={[4, 4, 0, 0]} />
                  <defs>
                    <linearGradient id="redGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ef4444" />
                      <stop offset="100%" stopColor="#dc2626" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            )}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-cyan-500 bg-gradient-to-br from-white to-cyan-50/30 dark:from-gray-900 dark:to-cyan-950/30">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-cyan-900 dark:text-cyan-100">
                <Waves className="h-5 w-5 text-cyan-600" />
                Salinity Histogram ({salBinWidth} PSU bins)
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => exportPNG('chart-sal-hist', 'salinity_histogram.png')} className="hover:bg-cyan-50 hover:border-cyan-300">
                  PNG
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCSV('salinity_histogram.csv', salBins)} className="hover:bg-cyan-50 hover:border-cyan-300">
                  CSV
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div id="chart-sal-hist" className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            {chartLoading.salHist ? (
              <div className="flex items-center justify-center h-[320px]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading salinity histogram...</span>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={salBins}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="sal"
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Salinity (PSU)', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle' } }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Count', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ecfeff',
                      border: '1px solid #a5f3fc',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                  <Bar dataKey="count" fill="url(#cyanGradient)" radius={[4, 4, 0, 0]} />
                  <defs>
                    <linearGradient id="cyanGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#06b6d4" />
                      <stop offset="100%" stopColor="#0891b2" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            )}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-orange-500 bg-gradient-to-br from-white to-orange-50/30 dark:from-gray-900 dark:to-orange-950/30">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-orange-900 dark:text-orange-100">
                <svg className="h-5 w-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Monthly Temperature (avg & MA={maWindow})
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => exportPNG('chart-temp-ma', 'temperature_timeseries.png')} className="hover:bg-orange-50 hover:border-orange-300">
                  PNG
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCSV('temperature_timeseries.csv', timeSeriesTemp)} className="hover:bg-orange-50 hover:border-orange-300">
                  CSV
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div id="chart-temp-ma" className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            {chartLoading.tempTime ? (
              <div className="flex items-center justify-center h-[320px]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading temperature timeseries...</span>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={timeSeriesTemp}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="ym"
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Month/Year', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle' } }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Temperature (°C)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#fff7ed',
                      border: '1px solid #fed7aa',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                  <Line type="monotone" dataKey="avg" stroke="#f97316" strokeWidth={3} dot={false} name="Average" />
                  <Line type="monotone" dataKey="ma" stroke="#ea580c" strokeWidth={2} dot={false} strokeDasharray="5 5" name="Moving Average" />
                </LineChart>
              </ResponsiveContainer>
            )}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-purple-500 bg-gradient-to-br from-white to-purple-50/30 dark:from-gray-900 dark:to-purple-950/30">
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-purple-900 dark:text-purple-100">
                <svg className="h-5 w-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                Monthly Salinity (avg & MA={maWindow})
              </CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => exportPNG('chart-sal-ma', 'salinity_timeseries.png')} className="hover:bg-purple-50 hover:border-purple-300">
                  PNG
                </Button>
                <Button variant="outline" size="sm" onClick={() => exportCSV('salinity_timeseries.csv', timeSeriesSal)} className="hover:bg-purple-50 hover:border-purple-300">
                  CSV
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            <div id="chart-sal-ma" className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            {chartLoading.salTime ? (
              <div className="flex items-center justify-center h-[320px]">
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  <span className="text-sm">Loading salinity timeseries...</span>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={timeSeriesSal}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis
                    dataKey="ym"
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Month/Year', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle' } }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    label={{ value: 'Salinity (PSU)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle' } }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#faf5ff',
                      border: '1px solid #e9d5ff',
                      borderRadius: '8px',
                      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    }}
                  />
                  <Line type="monotone" dataKey="avg" stroke="#a855f7" strokeWidth={3} dot={false} name="Average" />
                  <Line type="monotone" dataKey="ma" stroke="#9333ea" strokeWidth={2} dot={false} strokeDasharray="5 5" name="Moving Average" />
                </LineChart>
              </ResponsiveContainer>
            )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Data Table */}
      <Card>
        <CardHeader>
          <CardTitle>Profile Data ({filteredProfiles.length} profiles)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-2">ID</th>
                  <th className="text-left p-2">Latitude</th>
                  <th className="text-left p-2">Longitude</th>
                  <th className="text-left p-2">Depth</th>
                  <th className="text-left p-2">Temperature</th>
                  <th className="text-left p-2">Salinity</th>
                </tr>
              </thead>
              <tbody>
                {filteredProfiles.slice(0, 20).map((profile, index) => (
                  <tr key={`${profile.profile_id}-${index}`} className="border-b hover:bg-muted">
                    <td className="p-2">{profile.profile_id}</td>
                    <td className="p-2">{profile.latitude != null ? profile.latitude.toFixed(3) : 'N/A'}</td>
                    <td className="p-2">{profile.longitude != null ? profile.longitude.toFixed(3) : 'N/A'}</td>
                    <td className="p-2">
                      <Badge variant="outline">{profile.depth != null ? `${profile.depth}m` : 'N/A'}</Badge>
                    </td>
                    <td className="p-2">{profile.temperature != null ? `${profile.temperature.toFixed(2)}°C` : 'N/A'}</td>
                    <td className="p-2">{profile.salinity != null ? `${profile.salinity.toFixed(2)} PSU` : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredProfiles.length > 20 && (
              <p className="text-sm text-gray-500 mt-2">
                Showing first 20 of {filteredProfiles.length} profiles
              </p>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default memo(DataVisualization)
