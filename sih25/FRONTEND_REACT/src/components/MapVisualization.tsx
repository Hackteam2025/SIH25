import React, { useEffect, useRef, useState } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "./ui/Card";
import { MapPin, Eye, Settings, Info, X, Filter, BarChart3, HelpCircle } from "lucide-react";
import Modal from "./components";
import HelpModal from "./HelpModal";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { Input } from "./ui/Input";
import * as L from "leaflet";
import { motion, AnimatePresence } from "framer-motion";

// Dummy data and functions for demonstration
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
function getDepthStats() {
  return [];
}
function getDepthColor(depth: number) {
  return "#ccc";
}

// Map style configurations
const mapStyles = {
  openstreetmap: {
    name: 'StreetMap',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
    icon: '🗺️'
  },
  satellite: {
    name: 'Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 17,
    icon: '🛰️'
  },
  terrain: {
    name: 'Terrain',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap contributors',
    maxZoom: 17,
    icon: '🏔️'
  },
  dark: {
    name: 'Dark Mode',
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 19,
    icon: '🌙'
  },
  ocean: {
    name: 'Ocean Focus',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
    attribution: '&copy; Esri &mdash; Sources: GEBCO, NOAA, CHS, OSU, UNH, CSUMB, National Geographic, DeLorme, NAVTEQ, and Esri',
    maxZoom: 13,
    icon: '🌊'
  }
}

const MapVisualization: React.FC = () => {
  const [filter, setFilter] = useState<{
    depth: number | null;
    temperature: number | null;
    salinityMin: number | null;
    salinityMax: number | null;
    monthMin: number | null;
    monthMax: number | null;
    yearMin: number | null;
    yearMax: number | null;
  }>({ depth: null, temperature: null, salinityMin: null, salinityMax: null, monthMin: null, monthMax: null, yearMin: null, yearMax: null });
  const [selectedProfile, setSelectedProfile] = useState<any>(null);
  const [profiles, setProfiles] = useState<any[]>([]);
  const [explain, setExplain] = useState<{ summary: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [showHelp, setShowHelp] = useState(false)
  
  // Map refs
  const mapRef = useRef<HTMLDivElement | null>(null);
  const leafletRef = useRef<L.Map | null>(null)
  const markersRef = useRef<L.Marker[]>([])
  const clusterRef = useRef<any>(null)
  
  // Heatmap state
  // Heatmap removed
  
  // Map style state
  const [currentMapStyle, setCurrentMapStyle] = useState('openstreetmap')
  const [currentTileLayer, setCurrentTileLayer] = useState<L.TileLayer | null>(null)

  // Initialize map once
  useEffect(() => {
    if (leafletRef.current || !mapRef.current) return
    const map = L.map(mapRef.current).setView([20, 0], 2)

    console.log('Initializing map...')

    // Add initial tile layer
    const initialStyle = mapStyles[currentMapStyle as keyof typeof mapStyles]
    const tileLayer = L.tileLayer(initialStyle.url, {
      maxZoom: initialStyle.maxZoom,
      attribution: initialStyle.attribution
    }).addTo(map)

    setCurrentTileLayer(tileLayer)
    leafletRef.current = map

    // init cluster group (provided by plugin loaded in index.html)
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const cluster = (L as any).markerClusterGroup ? (L as any).markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 80,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: true,
        zoomToBoundsOnClick: true
      }) : null

      if (cluster) {
        clusterRef.current = cluster
        map.addLayer(cluster)
        console.log('Marker clustering enabled')
      } else {
        console.log('Marker clustering not available - markers will be added individually')
      }
    } catch (error) {
      console.warn('Failed to initialize marker clustering:', error)
    }
    return () => {
      map.remove()
      leafletRef.current = null
    }
  }, [])

  // Load filter settings from URL search params on mount (heatmap removed)
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      const getNum = (key: string): number | null => {
        const v = params.get(key)
        if (v === null || v === '') return null
        const n = Number(v)
        return isNaN(n) ? null : n
      }
      const initialFilter = {
        depth: getNum('depth'),
        temperature: getNum('temperature'),
        salinityMin: getNum('sal_min'),
        salinityMax: getNum('sal_max'),
        monthMin: getNum('month_min'),
        monthMax: getNum('month_max'),
        yearMin: getNum('year_min'),
        yearMax: getNum('year_max'),
      }
      setFilter((prev) => ({ ...prev, ...initialFilter }))
      // heatmap params removed
    } catch (e) {
      // ignore URL parse errors
    }
    // run only once
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Persist filter settings to URL (heatmap removed)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const setOrDel = (k: string, v: number | string | null | undefined) => {
      if (v === null || v === undefined || v === '') params.delete(k)
      else params.set(k, String(v))
    }
    // depth filter not used in map view anymore
    setOrDel('temperature', filter.temperature)
    setOrDel('sal_min', filter.salinityMin)
    setOrDel('sal_max', filter.salinityMax)
    setOrDel('month_min', filter.monthMin)
    setOrDel('month_max', filter.monthMax)
    setOrDel('year_min', filter.yearMin)
    setOrDel('year_max', filter.yearMax)
    // heatmap params removed
    const newUrl = `${window.location.pathname}?${params.toString()}`
    window.history.replaceState(null, '', newUrl)
  }, [filter])

  // Function to change map style
  const changeMapStyle = (styleKey: string) => {
    const map = leafletRef.current
    if (!map || !currentTileLayer) return
    
    const newStyle = mapStyles[styleKey as keyof typeof mapStyles]
    if (!newStyle) return
    
    // Remove current tile layer
    map.removeLayer(currentTileLayer)
    
    // Add new tile layer
    const newTileLayer = L.tileLayer(newStyle.url, {
      maxZoom: newStyle.maxZoom,
      attribution: newStyle.attribution
    }).addTo(map)
    
    setCurrentTileLayer(newTileLayer)
    setCurrentMapStyle(styleKey)
  }

  // Add debounce for fetch calls
  const debounceTimerRef = useRef<number | null>(null)

  // Add data caching
  const cacheRef = useRef<Map<string, any[]>>(new Map())

  // Build API query based on map bounds and filters
  const fetchProfiles = async () => {
    const map = leafletRef.current
    if (!map) return
    setLoading(true)
    const b = map.getBounds()

    console.log('Map bounds:', {
      south: b.getSouth(),
      north: b.getNorth(),
      west: b.getWest(),
      east: b.getEast()
    })

    // Create cache key based on bounds and filters
    const cacheKey = [
      b.getSouth().toFixed(3), b.getWest().toFixed(3), b.getNorth().toFixed(3), b.getEast().toFixed(3),
      filter.temperature ?? 'any',
      filter.salinityMin ?? 'any', filter.salinityMax ?? 'any',
      filter.monthMin ?? 'any', filter.monthMax ?? 'any',
      filter.yearMin ?? 'any', filter.yearMax ?? 'any',
    ].join(',')

    // Check cache first
    if (cacheRef.current.has(cacheKey)) {
      console.log('Loading from cache')
      setProfiles(cacheRef.current.get(cacheKey)!)
      setLoading(false)
      return
    }

    const params = new URLSearchParams()
    // Reduce default limit for better performance
    params.set('limit', '500')

    // Validate and clamp coordinates to valid ranges
    const south = Math.max(-90, Math.min(90, b.getSouth()))
    const north = Math.max(-90, Math.min(90, b.getNorth()))
    const west = Math.max(-180, Math.min(180, b.getWest()))
    const east = Math.max(-180, Math.min(180, b.getEast()))

    console.log('Original bounds:', {
      south: b.getSouth(),
      north: b.getNorth(),
      west: b.getWest(),
      east: b.getEast()
    })

    console.log('Clamped bounds:', {
      south, north, west, east
    })

    params.set('min_lat', String(south))
    params.set('max_lat', String(north))
    params.set('min_lon', String(west))
    params.set('max_lon', String(east))
    // depth filter removed from map query
    if (filter.temperature != null) {
      // allow small range around temperature to catch floats
      const t = filter.temperature
      params.set('temp_min', String(t - 0.5))
      params.set('temp_max', String(t + 0.5))
    }
    if (filter.salinityMin != null) params.set('salinity_min', String(filter.salinityMin))
    if (filter.salinityMax != null) params.set('salinity_max', String(filter.salinityMax))
    if (filter.monthMin != null) params.set('month_min', String(filter.monthMin))
    if (filter.monthMax != null) params.set('month_max', String(filter.monthMax))
    if (filter.yearMin != null) params.set('year_min', String(filter.yearMin))
    if (filter.yearMax != null) params.set('year_max', String(filter.yearMax))

    const url = `${API_URL}/data/profiles?${params.toString()}`
    console.log('Fetching profiles from:', url)

    try {
      const res = await fetch(url)
      console.log('API Response status:', res.status)
      const json = await res.json()
      console.log('API Response:', json)

      const profilesData = json.results || []
      setProfiles(profilesData)
      console.log(`Loaded ${profilesData.length} profiles from API`)

      // Cache the results
      cacheRef.current.set(cacheKey, profilesData)

      // If no results from bounds query, try loading all profiles as fallback (but with smaller limit)
      if (!profilesData || profilesData.length === 0) {
        console.log('No results from bounds query, trying fallback...')
        const fallbackUrl = `${API_URL}/data/profiles?limit=200` // Smaller fallback limit
        console.log('Fallback URL:', fallbackUrl)

        try {
          const fallbackRes = await fetch(fallbackUrl)
          const fallbackJson = await fallbackRes.json()
          console.log('Fallback API Response:', fallbackJson)
          const fallbackData = fallbackJson.results || []
          setProfiles(fallbackData)
          console.log(`Loaded ${fallbackData.length} profiles from fallback`)

          // Cache fallback results too
          cacheRef.current.set('fallback', fallbackData)
        } catch (fallbackError) {
          console.error('Fallback API also failed:', fallbackError)
        }
      }
    } catch (e) {
      console.error('Failed to load profiles', e)

      // Try to use cached data as fallback
      const fallbackData = cacheRef.current.get('fallback')
      if (fallbackData) {
        console.log('Using cached fallback data')
        setProfiles(fallbackData)
      }
    } finally {
      setLoading(false)
    }
  }

  // Debounced version of fetchProfiles for map move events
  const debouncedFetchProfiles = () => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }
    debounceTimerRef.current = setTimeout(() => {
      fetchProfiles()
    }, 500) // Wait 500ms after map stops moving
  }

  // Initial fetch and on map moveend
  useEffect(() => {
    const map = leafletRef.current
    if (!map) return

    // Load data immediately on first load
    fetchProfiles()

    // Use debounced fetch for map move events
    const handler = () => { debouncedFetchProfiles() }
    map.on('moveend', handler)

    return () => {
      map.off('moveend', handler)
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leafletRef.current])

  // Render markers when profiles change
  useEffect(() => {
    const map = leafletRef.current
    if (!map) return

    console.log(`Rendering ${profiles.length} profiles on map`)

    // Clear previous markers
    if (clusterRef.current) {
      clusterRef.current.clearLayers()
    }
    markersRef.current.forEach(m => m.remove())
    markersRef.current = []

    // Apply optional filters
    const filtered = profiles.filter(p => {
      const byTemp = filter.temperature == null || Math.round(p.temperature) === Math.round(filter.temperature)
      const bySalMin = filter.salinityMin == null || Number(p.salinity) >= filter.salinityMin
      const bySalMax = filter.salinityMax == null || Number(p.salinity) <= filter.salinityMax
      const byMonthMin = filter.monthMin == null || Number(p.month) >= filter.monthMin
      const byMonthMax = filter.monthMax == null || Number(p.month) <= filter.monthMax
      const byYearMin = filter.yearMin == null || Number(p.year) >= filter.yearMin
      const byYearMax = filter.yearMax == null || Number(p.year) <= filter.yearMax
      return byTemp && bySalMin && bySalMax && byMonthMin && byMonthMax && byYearMin && byYearMax
    })

    console.log(`After filtering: ${filtered.length} profiles`)

    // Add markers
    let markersCreated = 0
    filtered.slice(0, 2000).forEach((p: any) => {
      if (typeof p.latitude !== 'number' || typeof p.longitude !== 'number') {
        console.log(`Skipping profile ${p.id}: invalid coordinates`)
        return
      }
      if (isNaN(p.latitude) || isNaN(p.longitude)) {
        console.log(`Skipping profile ${p.id}: NaN coordinates`)
        return
      }

      console.log(`Creating marker at: ${p.latitude}, ${p.longitude} for profile ${p.id}`)
      markersCreated++

      const marker = L.marker([p.latitude, p.longitude], {
        title: `Profile ${p.id}`
      })

      marker.bindPopup(`
        <div class="p-3">
          <h3 class="font-semibold text-lg mb-2">Profile ${p.id}</h3>
          <div class="space-y-1 text-sm">
            <p><strong>Location:</strong> ${p.latitude.toFixed(4)}°, ${p.longitude.toFixed(4)}°</p>
            <p><strong>Depth:</strong> ${p.depth} m</p>
            <p><strong>Temperature:</strong> ${Number(p.temperature).toFixed(2)} °C</p>
            <p><strong>Salinity:</strong> ${Number(p.salinity).toFixed(2)} PSU</p>
            <p><strong>Date:</strong> ${p.month}/${p.year}</p>
          </div>
        </div>
      `)

      markersRef.current.push(marker)

      // Ensure marker is visible by adding it to the map directly first
      marker.addTo(map)

      // Also add to cluster if available
      if (clusterRef.current) {
        clusterRef.current.addLayer(marker)
      }
    })

    console.log(`Successfully created ${markersCreated} markers`)

    if (filtered.length) {
      const first = filtered[0]
      map.setView([first.latitude, first.longitude], 3)
    }

    // Add a test marker to verify map is working
    if (markersCreated === 0 && profiles.length > 0) {
      console.log('No markers created from API data, adding test marker')
      const testMarker = L.marker([0, 0], {
        title: 'Test Marker'
      }).bindPopup('<div>Test marker at equator</div>')
      testMarker.addTo(map)
    }
    // Heatmap removed
  }, [profiles, filter])

  const explainView = async () => {
    const map = leafletRef.current
    if (!map) return
    const b = map.getBounds()

    // Validate and clamp coordinates to valid ranges
    const south = Math.max(-90, Math.min(90, b.getSouth()))
    const north = Math.max(-90, Math.min(90, b.getNorth()))
    const west = Math.max(-180, Math.min(180, b.getWest()))
    const east = Math.max(-180, Math.min(180, b.getEast()))

    const params = new URLSearchParams()
    params.set('min_lat', String(south))
    params.set('max_lat', String(north))
    params.set('min_lon', String(west))
    params.set('max_lon', String(east))
    // depth filter removed from explain view
    if (filter.temperature != null) {
      const t = filter.temperature
      params.set('temp_min', String(t - 0.5))
      params.set('temp_max', String(t + 0.5))
    }
    try {
      const res = await fetch(`${API_URL}/data/explain?${params.toString()}`)
      const json = await res.json()
      setExplain({ summary: json.summary || 'No summary available.' })
    } catch (e) {
      setExplain({ summary: 'Failed to fetch explanation.' })
    }
  }

  return (
    <>
      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
      <div className="h-full flex flex-col bg-gradient-to-br from-green-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-green-950 rounded-xl shadow-2xl overflow-hidden">
      {/* Enhanced Header */}
      <div className="bg-gradient-to-r from-green-600 to-blue-600 text-white p-6 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm"
            >
              <MapPin className="h-5 w-5" />
            </motion.div>
            <div>
              <h2 className="text-xl font-bold">ARGO Float Locations</h2>
              <p className="text-green-100 text-sm">Interactive ocean data mapping</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge className="bg-white/20 text-white border-white/30">
              <BarChart3 className="h-3 w-3 mr-1" />
              {profiles.length} profiles
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHelp(true)}
              className="text-white hover:bg-white/20"
            >
              <HelpCircle className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowControls(!showControls)}
              className="text-white hover:bg-white/20"
            >
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Map Container */}
        <div className="flex-1 relative">
          <div ref={mapRef} className="w-full h-full" />
          
          {/* Loading Overlay */}
          {loading && (
            <div className="absolute inset-0 bg-black/20 flex items-center justify-center backdrop-blur-sm">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow-lg">
                <div className="flex items-center gap-3">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  >
                    <MapPin className="h-5 w-5 text-green-600" />
                  </motion.div>
                  <span className="text-sm font-medium">Loading profiles...</span>
                </div>
              </div>
            </div>
          )}

      {/* Heatmap legend removed */}

          {/* Floating Controls (heatmap toggle removed) */}
          <div className="absolute top-4 left-4 flex flex-col gap-2">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                variant="outline"
                size="sm"
                onClick={explainView}
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-lg border-0"
              >
                <Eye className="h-4 w-4 mr-2" />
                Explain View
              </Button>
            </motion.div>

            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <Button
                variant="outline"
                size="sm"
                onClick={fetchProfiles}
                className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-lg border-0"
              >
                <MapPin className="h-4 w-4 mr-2" />
                Load Data
              </Button>
            </motion.div>
          </div>

          {/* Floating Map Style Selector */}
          <div className="absolute top-4 right-4">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
              <div className="bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm shadow-lg rounded-lg border-0 p-2">
                <div className="flex items-center gap-1">
                  <span className="text-xs font-medium text-gray-600 dark:text-gray-400 px-2">
                    {mapStyles[currentMapStyle as keyof typeof mapStyles]?.icon}
                  </span>
                  <select
                    value={currentMapStyle}
                    onChange={(e) => changeMapStyle(e.target.value)}
                    className="text-xs bg-transparent border-none outline-none text-gray-700 dark:text-gray-300 cursor-pointer"
                  >
                    {Object.entries(mapStyles).map(([key, style]) => (
                      <option key={key} value={key}>
                        {style.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </motion.div>
          </div>
        </div>

        {/* Enhanced Side Panel */}
        <AnimatePresence>
          {showControls && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm border-l border-gray-200 dark:border-gray-700 overflow-y-auto"
            >
              <div className="p-6 space-y-6">
                {/* Map Style Selector */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <MapPin className="h-5 w-5 text-indigo-600" />
                    Map Style
                  </h3>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(mapStyles).map(([key, style]) => (
                      <button
                        key={key}
                        onClick={() => changeMapStyle(key)}
                        className={`p-3 rounded-lg border transition-all duration-200 text-left ${
                          currentMapStyle === key
                            ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/20 text-indigo-700 dark:text-indigo-300'
                            : 'border-gray-200 dark:border-gray-600 hover:border-indigo-300 dark:hover:border-indigo-500 hover:bg-gray-50 dark:hover:bg-gray-700'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-lg">{style.icon}</span>
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                            {style.name}
                          </span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Heatmap controls removed */}

                {/* Depth Legend */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <Info className="h-5 w-5 text-blue-600" />
                    Depth Legend
                  </h3>
                  <div className="grid grid-cols-1 gap-2">
                    {[
                      { color: 'bg-green-500', label: '≤ 10m', range: 'Surface' },
                      { color: 'bg-blue-500', label: '11-50m', range: 'Shallow' },
                      { color: 'bg-yellow-500', label: '51-100m', range: 'Medium' },
                      { color: 'bg-orange-500', label: '101-200m', range: 'Deep' },
                      { color: 'bg-red-500', label: '> 200m', range: 'Very Deep' }
                    ].map((item, index) => (
                      <div key={index} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
                        <div className={`w-4 h-4 rounded-full ${item.color} shadow-sm`}></div>
                        <div className="flex-1">
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.label}</span>
                          <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">({item.range})</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Filters */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <Filter className="h-5 w-5 text-purple-600" />
                    Filters
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                        Temperature (°C)
                      </label>
                      <Input
                        type="number"
                        value={filter.temperature || ""}
                        onChange={(e) => setFilter({
                          ...filter,
                          temperature: e.target.value ? parseFloat(e.target.value) : null,
                        })}
                        placeholder="Enter temperature in Celsius"
                        className="w-full"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                          Salinity min (PSU)
                        </label>
                        <Input
                          type="number"
                          step={0.1}
                          value={filter.salinityMin ?? ""}
                          onChange={(e) => setFilter({
                            ...filter,
                            salinityMin: e.target.value !== '' ? parseFloat(e.target.value) : null,
                          })}
                          placeholder="e.g. 33.0"
                          className="w-full"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                          Salinity max (PSU)
                        </label>
                        <Input
                          type="number"
                          step={0.1}
                          value={filter.salinityMax ?? ""}
                          onChange={(e) => setFilter({
                            ...filter,
                            salinityMax: e.target.value !== '' ? parseFloat(e.target.value) : null,
                          })}
                          placeholder="e.g. 37.5"
                          className="w-full"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                          Month range (min)
                        </label>
                        <Input
                          type="number"
                          min={1}
                          max={12}
                          value={filter.monthMin ?? ""}
                          onChange={(e) => setFilter({
                            ...filter,
                            monthMin: e.target.value !== '' ? parseInt(e.target.value) : null,
                          })}
                          placeholder="1-12"
                          className="w-full"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                          Month range (max)
                        </label>
                        <Input
                          type="number"
                          min={1}
                          max={12}
                          value={filter.monthMax ?? ""}
                          onChange={(e) => setFilter({
                            ...filter,
                            monthMax: e.target.value !== '' ? parseInt(e.target.value) : null,
                          })}
                          placeholder="1-12"
                          className="w-full"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                          Year range (min)
                        </label>
                        <Input
                          type="number"
                          value={filter.yearMin ?? ""}
                          onChange={(e) => setFilter({
                            ...filter,
                            yearMin: e.target.value !== '' ? parseInt(e.target.value) : null,
                          })}
                          placeholder="e.g. 2024"
                          className="w-full"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 block">
                          Year range (max)
                        </label>
                        <Input
                          type="number"
                          value={filter.yearMax ?? ""}
                          onChange={(e) => setFilter({
                            ...filter,
                            yearMax: e.target.value !== '' ? parseInt(e.target.value) : null,
                          })}
                          placeholder="e.g. 2025"
                          className="w-full"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Explain Results */}
                <AnimatePresence>
                  {explain && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="space-y-4"
                    >
                      <div className="flex items-center justify-between">
                        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                          <Eye className="h-5 w-5 text-indigo-600" />
                          View Analysis
                        </h3>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExplain(null)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className="p-4 bg-indigo-50 dark:bg-indigo-950/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
                        <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
                          {explain.summary}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Selected Profile Details Modal */}
      {selectedProfile && (
        <Modal onClose={() => setSelectedProfile(null)}>
          <div className="p-6">
            <h2 className="text-lg font-semibold mb-4 text-gray-800 dark:text-gray-200">Profile Details</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">Profile ID</p>
                <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">{selectedProfile.id}</p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">Location</p>
                <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                  {selectedProfile.latitude.toFixed(3)}, {selectedProfile.longitude.toFixed(3)}
                </p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">Depth</p>
                <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">{selectedProfile.depth}m</p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">Temperature</p>
                <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                  {selectedProfile.temperature.toFixed(2)}°C
                </p>
              </div>
              <div className="p-3 bg-gray-50 dark:bg-gray-700 rounded-lg col-span-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">Salinity</p>
                <p className="text-lg font-semibold text-gray-800 dark:text-gray-200">
                  {selectedProfile.salinity.toFixed(2)} PSU
                </p>
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <Button
                variant="outline"
                onClick={() => setSelectedProfile(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
    </>
  );
};

export default MapVisualization;
