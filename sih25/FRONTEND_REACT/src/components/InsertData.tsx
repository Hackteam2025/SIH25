import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Badge } from './ui/Badge'
import HelpModal from './HelpModal'
import { Database, Plus, RotateCcw, CheckCircle, AlertCircle, Upload, MapPin, Thermometer, Waves, Calendar, Hash, HelpCircle, Edit, Trash2, Search } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type FormState = {
  float_id: string
  latitude: string
  longitude: string
  depth: string
  temperature: string
  salinity: string
  month: string
  year: string
  date: string
}

const initialState: FormState = {
  float_id: 'dev-float',
  latitude: '',
  longitude: '',
  depth: '',
  temperature: '',
  salinity: '',
  month: '',
  year: '',
  date: ''
}

export default function InsertData() {
  const [form, setForm] = useState<FormState>(initialState)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const [showSuccess, setShowSuccess] = useState(false)
  const [showHelp, setShowHelp] = useState(false)
  const [profileId, setProfileId] = useState<string>('')
  const [loadedProfileId, setLoadedProfileId] = useState<number | null>(null)

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setForm(prev => ({ ...prev, [name]: value }))
    // Clear validation error when user starts typing
    if (validationErrors[name]) {
      setValidationErrors(prev => ({ ...prev, [name]: '' }))
    }
  }
  const loadProfile = async () => {
    setError(null)
    setResult(null)
    if (!profileId) {
      setError('Enter a Profile ID to load')
      return
    }
    try {
      setLoading(true)
      const res = await fetch(`${API_URL}/data/profile/${profileId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const p = await res.json()
      setLoadedProfileId(p.id)
      // Populate form
      setForm({
        float_id: p.float_id ?? 'dev-float',
        latitude: String(p.latitude ?? ''),
        longitude: String(p.longitude ?? ''),
        depth: String(p.depth ?? ''),
        temperature: String(p.temperature ?? ''),
        salinity: String(p.salinity ?? ''),
        month: String(p.month ?? ''),
        year: String(p.year ?? ''),
        date: p.date ? String(p.date).slice(0,10) : ''
      })
    } catch (e: any) {
      setError(e?.message || 'Failed to load profile')
    } finally {
      setLoading(false)
    }
  }

  const updateProfile = async () => {
    setError(null)
    setResult(null)
    if (!loadedProfileId) {
      setError('Load a profile first to update')
      return
    }
    // Simple reuse of validation
    if (!validateForm()) return
    try {
      setLoading(true)
      const payload = {
        float_id: form.float_id || 'dev-float',
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        depth: Number(form.depth),
        temperature: Number(form.temperature),
        salinity: Number(form.salinity),
        month: Number(form.month),
        year: Number(form.year),
        date: form.date || null,
      }
      const res = await fetch(`${API_URL}/data/profile/${loadedProfileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setResult(json)
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 3000)
    } catch (e: any) {
      setError(e?.message || 'Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  const deleteProfile = async () => {
    setError(null)
    setResult(null)
    if (!loadedProfileId && !profileId) {
      setError('Enter or load a Profile ID to delete')
      return
    }
    const id = loadedProfileId ?? Number(profileId)
    if (!id || isNaN(id)) {
      setError('Invalid Profile ID')
      return
    }
    if (!confirm(`Delete profile ${id}? This cannot be undone.`)) return
    try {
      setLoading(true)
      const res = await fetch(`${API_URL}/data/profile/${id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setResult(json)
      // Clear form
      resetForm()
      setProfileId('')
      setLoadedProfileId(null)
      setShowSuccess(true)
      setTimeout(() => setShowSuccess(false), 3000)
    } catch (e: any) {
      setError(e?.message || 'Failed to delete profile')
    } finally {
      setLoading(false)
    }
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}
    
    if (!form.latitude) errors.latitude = 'Latitude is required'
    else if (Math.abs(Number(form.latitude)) > 90) errors.latitude = 'Latitude must be between -90 and 90'
    
    if (!form.longitude) errors.longitude = 'Longitude is required'
    else if (Math.abs(Number(form.longitude)) > 180) errors.longitude = 'Longitude must be between -180 and 180'
    
    if (!form.depth) errors.depth = 'Depth is required'
    else if (Number(form.depth) < 0) errors.depth = 'Depth must be positive'
    
    if (!form.temperature) errors.temperature = 'Temperature is required'
    else if (Number(form.temperature) < -5 || Number(form.temperature) > 50) errors.temperature = 'Temperature should be between -5°C and 50°C'
    
    if (!form.salinity) errors.salinity = 'Salinity is required'
    else if (Number(form.salinity) < 0 || Number(form.salinity) > 50) errors.salinity = 'Salinity should be between 0 and 50 PSU'
    
    if (!form.month) errors.month = 'Month is required'
    else if (Number(form.month) < 1 || Number(form.month) > 12) errors.month = 'Month must be between 1 and 12'
    
    if (!form.year) errors.year = 'Year is required'
    else if (Number(form.year) < 1900 || Number(form.year) > 2100) errors.year = 'Year must be between 1900 and 2100'

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setShowSuccess(false)
    
    try {
      const payload = {
        float_id: form.float_id || 'dev-float',
        latitude: Number(form.latitude),
        longitude: Number(form.longitude),
        depth: Number(form.depth),
        temperature: Number(form.temperature),
        salinity: Number(form.salinity),
        month: Number(form.month),
        year: Number(form.year),
        date: form.date || null
      }
      
      const res = await fetch(`${API_URL}/data/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setResult(json)
      setShowSuccess(true)
      
      // Auto-hide success message after 3 seconds
      setTimeout(() => setShowSuccess(false), 3000)
    } catch (e: any) {
      setError(e?.message || 'Failed to insert profile')
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setForm(initialState)
    setValidationErrors({})
    setError(null)
    setResult(null)
    setShowSuccess(false)
  }

  return (
    <>
      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
      <div className="h-full flex flex-col bg-gradient-to-br from-purple-50 via-white to-pink-50 dark:from-gray-900 dark:via-gray-800 dark:to-purple-950 rounded-xl shadow-2xl overflow-hidden">
      {/* Enhanced Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white p-6 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
              className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm"
            >
              <Database className="h-5 w-5" />
            </motion.div>
            <div>
              <h2 className="text-xl font-bold">Insert ARGO Profile</h2>
              <p className="text-purple-100 text-sm">Add new ocean data to the database</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className="bg-white/20 text-white border-white/30">
              <Upload className="h-3 w-3 mr-1" />
              Development Mode
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowHelp(true)}
              className="text-white hover:bg-white/20"
            >
              <HelpCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Success Message */}
      <AnimatePresence>
        {showSuccess && (
          <motion.div
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -50 }}
            className="bg-green-500 text-white p-4 text-center"
          >
            <div className="flex items-center justify-center gap-2">
              <CheckCircle className="h-5 w-5" />
              <span className="font-medium">Profile inserted successfully!</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-purple-500 bg-gradient-to-br from-white to-purple-50/30 dark:from-gray-900 dark:to-purple-950/30">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-purple-900 dark:text-purple-100">
                <Plus className="h-5 w-5 text-purple-600" />
                Profile Data Entry
              </CardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Enter ARGO float profile data. All fields marked with * are required.
              </p>
            </CardHeader>
            <CardContent className="pt-0">
              {/* Load / Update / Delete Controls */}
              <div className="mb-6 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">Profile ID</label>
                    <div className="flex gap-2">
                      <Input
                        value={profileId}
                        onChange={(e) => setProfileId(e.target.value)}
                        placeholder="Enter ID to load"
                        className="flex-1"
                      />
                      <Button type="button" variant="outline" onClick={loadProfile} className="flex items-center gap-2">
                        <Search className="h-4 w-4" /> Load
                      </Button>
                    </div>
                    {loadedProfileId && (
                      <p className="text-xs text-gray-500 mt-1">Loaded profile ID: {loadedProfileId}</p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" onClick={updateProfile} className="flex-1 flex items-center justify-center gap-2">
                      <Edit className="h-4 w-4" /> Update
                    </Button>
                    <Button type="button" variant="outline" onClick={deleteProfile} className="flex-1 flex items-center justify-center gap-2">
                      <Trash2 className="h-4 w-4" /> Delete
                    </Button>
                  </div>
                </div>
              </div>
              <form onSubmit={submit} className="space-y-6">
                {/* Float ID Section */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <Hash className="h-4 w-4 text-purple-600" />
                    Float Identification
                  </h3>
                  <div className="grid grid-cols-1 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Float ID
                      </label>
                      <Input
                        name="float_id"
                        value={form.float_id}
                        onChange={onChange}
                        placeholder="e.g., dev-float-001"
                        className="w-full"
                      />
                    </div>
                  </div>
                </div>

                {/* Location Section */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-blue-600" />
                    Geographic Location
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Latitude * <span className="text-xs text-gray-500">(-90 to 90)</span>
                      </label>
                      <Input
                        name="latitude"
                        type="number"
                        step="0.0001"
                        value={form.latitude}
                        onChange={onChange}
                        placeholder="e.g., 25.7617"
                        className={`w-full ${validationErrors.latitude ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.latitude && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.latitude}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Longitude * <span className="text-xs text-gray-500">(-180 to 180)</span>
                      </label>
                      <Input
                        name="longitude"
                        type="number"
                        step="0.0001"
                        value={form.longitude}
                        onChange={onChange}
                        placeholder="e.g., -80.1918"
                        className={`w-full ${validationErrors.longitude ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.longitude && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.longitude}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Measurements Section */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <Thermometer className="h-4 w-4 text-red-600" />
                    Ocean Measurements
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Depth (m) * <span className="text-xs text-gray-500">(≥ 0)</span>
                      </label>
                      <Input
                        name="depth"
                        type="number"
                        step="1"
                        value={form.depth}
                        onChange={onChange}
                        placeholder="e.g., 150"
                        className={`w-full ${validationErrors.depth ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.depth && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.depth}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Temperature (°C) * <span className="text-xs text-gray-500">(-5 to 50)</span>
                      </label>
                      <Input
                        name="temperature"
                        type="number"
                        step="0.01"
                        value={form.temperature}
                        onChange={onChange}
                        placeholder="e.g., 24.5"
                        className={`w-full ${validationErrors.temperature ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.temperature && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.temperature}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block flex items-center gap-1">
                        <Waves className="h-3 w-3" />
                        Salinity (PSU) * <span className="text-xs text-gray-500">(0 to 50)</span>
                      </label>
                      <Input
                        name="salinity"
                        type="number"
                        step="0.01"
                        value={form.salinity}
                        onChange={onChange}
                        placeholder="e.g., 35.2"
                        className={`w-full ${validationErrors.salinity ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.salinity && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.salinity}</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Time Section */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-green-600" />
                    Time Information
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Month * <span className="text-xs text-gray-500">(1-12)</span>
                      </label>
                      <Input
                        name="month"
                        type="number"
                        min="1"
                        max="12"
                        value={form.month}
                        onChange={onChange}
                        placeholder="e.g., 6"
                        className={`w-full ${validationErrors.month ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.month && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.month}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Year * <span className="text-xs text-gray-500">(1900-2100)</span>
                      </label>
                      <Input
                        name="year"
                        type="number"
                        min="1900"
                        max="2100"
                        value={form.year}
                        onChange={onChange}
                        placeholder="e.g., 2025"
                        className={`w-full ${validationErrors.year ? 'border-red-500' : ''}`}
                      />
                      {validationErrors.year && (
                        <p className="text-red-500 text-xs mt-1">{validationErrors.year}</p>
                      )}
                    </div>
                    <div>
                      <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                        Specific Date <span className="text-xs text-gray-500">(optional)</span>
                      </label>
                      <Input
                        name="date"
                        type="date"
                        value={form.date}
                        onChange={onChange}
                        className="w-full"
                      />
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-4 pt-6 border-t border-gray-200 dark:border-gray-700">
                  <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} className="flex-1">
                    <Button
                      type="submit"
                      disabled={loading}
                      className="w-full bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg disabled:opacity-50"
                    >
                      {loading ? (
                        <div className="flex items-center gap-2">
                          <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                          >
                            <Upload className="h-4 w-4" />
                          </motion.div>
                          Inserting...
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Plus className="h-4 w-4" />
                          Insert Profile
                        </div>
                      )}
                    </Button>
                  </motion.div>
                  <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={resetForm}
                      className="flex items-center gap-2 hover:bg-gray-50 dark:hover:bg-gray-800"
                    >
                      <RotateCcw className="h-4 w-4" />
                      Reset
                    </Button>
                  </motion.div>
                </div>
              </form>
            </CardContent>
          </Card>
        </motion.div>

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mt-6"
            >
              <Card className="border-l-4 border-l-red-500 bg-red-50 dark:bg-red-950/20">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                    <AlertCircle className="h-5 w-5" />
                    <span className="font-medium">Error</span>
                  </div>
                  <p className="text-red-600 dark:text-red-300 mt-1">{error}</p>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Success Result */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mt-6"
            >
              <Card className="border-l-4 border-l-green-500 bg-green-50 dark:bg-green-950/20">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-green-700 dark:text-green-400">
                    <CheckCircle className="h-5 w-5" />
                    Profile Inserted Successfully
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400">Profile ID</p>
                      <p className="font-semibold text-gray-800 dark:text-gray-200">{result.id}</p>
                    </div>
                    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400">Float ID</p>
                      <p className="font-semibold text-gray-800 dark:text-gray-200">{result.float_id}</p>
                    </div>
                    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400">Location</p>
                      <p className="font-semibold text-gray-800 dark:text-gray-200">
                        {result.latitude?.toFixed(3)}, {result.longitude?.toFixed(3)}
                      </p>
                    </div>
                    <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400">Depth</p>
                      <p className="font-semibold text-gray-800 dark:text-gray-200">{result.depth}m</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
    </>
  )
}
