import React, { useState, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Button } from './ui/Button'
import { Badge } from './ui/Badge'
import HelpModal from './HelpModal'
import {
  Upload,
  CheckCircle,
  AlertCircle,
  XCircle,
  FileText,
  Loader2,
  Trash2,
  Database,
  HelpCircle,
  BarChart3,
  Clock,
  FileCheck,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

const DATAOPS_API_URL = import.meta.env.VITE_DATAOPS_API_URL || 'http://localhost:8002'

type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'completed_with_errors'

interface JobStatusData {
  job_id: string
  status: JobStatus
  progress: number
  message: string
  files_processed: number
  files_total: number
  created_at: string
  updated_at: string
  results?: any
  errors?: string[]
}

export default function DataOpsUpload() {
  const [files, setFiles] = useState<File[]>([])
  const [uploading, setUploading] = useState(false)
  const [currentJob, setCurrentJob] = useState<JobStatusData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showHelp, setShowHelp] = useState(false)
  const [recentJobs, setRecentJobs] = useState<JobStatusData[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Poll for job status updates
  useEffect(() => {
    if (currentJob && ['queued', 'processing'].includes(currentJob.status)) {
      pollingIntervalRef.current = setInterval(() => {
        fetchJobStatus(currentJob.job_id)
      }, 2000) // Poll every 2 seconds

      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
        }
      }
    }
  }, [currentJob])

  // Fetch recent jobs on mount
  useEffect(() => {
    fetchRecentJobs()
  }, [])

  const fetchJobStatus = async (jobId: string) => {
    try {
      const res = await fetch(`${DATAOPS_API_URL}/jobs/${jobId}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data: JobStatusData = await res.json()
      setCurrentJob(data)

      // Stop polling if job is complete
      if (!['queued', 'processing'].includes(data.status)) {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
        // Refresh recent jobs
        fetchRecentJobs()
      }
    } catch (e: any) {
      console.error('Failed to fetch job status:', e)
    }
  }

  const fetchRecentJobs = async () => {
    try {
      const res = await fetch(`${DATAOPS_API_URL}/jobs?limit=5`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setRecentJobs(data.jobs || [])
    } catch (e: any) {
      console.error('Failed to fetch recent jobs:', e)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      const ncFiles = selectedFiles.filter(f => f.name.endsWith('.nc'))

      if (ncFiles.length !== selectedFiles.length) {
        setError('Only .nc (NetCDF) files are supported')
        setTimeout(() => setError(null), 3000)
      }

      setFiles(prev => [...prev, ...ncFiles])
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (files.length === 0) {
      setError('Please select at least one file')
      return
    }

    setUploading(true)
    setError(null)
    setCurrentJob(null)

    try {
      const formData = new FormData()
      files.forEach(file => {
        formData.append('files', file)
      })

      const res = await fetch(`${DATAOPS_API_URL}/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.detail || `HTTP ${res.status}`)
      }

      const data = await res.json()

      // Clear files after successful upload
      setFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

      // Start tracking the job
      fetchJobStatus(data.job_id)
    } catch (e: any) {
      setError(e?.message || 'Failed to upload files')
    } finally {
      setUploading(false)
    }
  }

  const getStatusColor = (status: JobStatus) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'processing':
      case 'queued':
        return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'completed_with_errors':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getStatusIcon = (status: JobStatus) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5" />
      case 'processing':
        return <Loader2 className="h-5 w-5 animate-spin" />
      case 'queued':
        return <Clock className="h-5 w-5" />
      case 'failed':
        return <XCircle className="h-5 w-5" />
      case 'completed_with_errors':
        return <AlertCircle className="h-5 w-5" />
      default:
        return <FileText className="h-5 w-5" />
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <>
      <HelpModal isOpen={showHelp} onClose={() => setShowHelp(false)} />
      <div className="h-full flex flex-col bg-gradient-to-br from-blue-50 via-white to-cyan-50 dark:from-gray-900 dark:via-gray-800 dark:to-blue-950 rounded-xl shadow-2xl overflow-hidden">
        {/* Enhanced Header */}
        <div className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white p-6 shadow-lg">
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
                <h2 className="text-xl font-bold">DataOps Upload</h2>
                <p className="text-blue-100 text-sm">Upload and process UFDR NetCDF files</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-white/20 text-white border-white/30">
                <Upload className="h-3 w-3 mr-1" />
                Pipeline Ready
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

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Upload Section */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Card className="shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 border-l-blue-500">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2 text-blue-900 dark:text-blue-100">
                  <Upload className="h-5 w-5 text-blue-600" />
                  Upload Files
                </CardTitle>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Select NetCDF (.nc) files to upload and process through the DataOps pipeline
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* File Input */}
                <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-8 text-center hover:border-blue-500 transition-colors">
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept=".nc"
                    onChange={handleFileChange}
                    className="hidden"
                    id="file-upload"
                  />
                  <label
                    htmlFor="file-upload"
                    className="cursor-pointer flex flex-col items-center gap-2"
                  >
                    <Upload className="h-12 w-12 text-gray-400" />
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Click to upload or drag and drop
                    </span>
                    <span className="text-xs text-gray-500">NetCDF (.nc) files only</span>
                  </label>
                </div>

                {/* Selected Files List */}
                {files.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                      Selected Files ({files.length})
                    </h4>
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {files.map((file, index) => (
                        <motion.div
                          key={index}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
                        >
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <FileText className="h-4 w-4 text-blue-600 flex-shrink-0" />
                            <span className="text-sm text-gray-700 dark:text-gray-300 truncate">
                              {file.name}
                            </span>
                            <span className="text-xs text-gray-500 flex-shrink-0">
                              ({(file.size / 1024 / 1024).toFixed(2)} MB)
                            </span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(index)}
                            className="flex-shrink-0"
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Upload Button */}
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button
                    onClick={handleUpload}
                    disabled={files.length === 0 || uploading}
                    className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white shadow-lg disabled:opacity-50"
                  >
                    {uploading ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Uploading...
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Upload className="h-4 w-4" />
                        Upload and Process
                      </div>
                    )}
                  </Button>
                </motion.div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
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

          {/* Current Job Status */}
          <AnimatePresence>
            {currentJob && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <Card className={`border-l-4 ${getStatusColor(currentJob.status)}`}>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2">
                      {getStatusIcon(currentJob.status)}
                      Processing Status
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="font-medium">{currentJob.message}</span>
                        <span className="text-gray-500">{currentJob.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <motion.div
                          className="bg-blue-600 h-2 rounded-full"
                          initial={{ width: 0 }}
                          animate={{ width: `${currentJob.progress}%` }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                        <p className="text-gray-600 dark:text-gray-400">Status</p>
                        <p className="font-semibold text-gray-800 dark:text-gray-200 capitalize">
                          {currentJob.status.replace('_', ' ')}
                        </p>
                      </div>
                      <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                        <p className="text-gray-600 dark:text-gray-400">Files</p>
                        <p className="font-semibold text-gray-800 dark:text-gray-200">
                          {currentJob.files_processed} / {currentJob.files_total}
                        </p>
                      </div>
                      <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                        <p className="text-gray-600 dark:text-gray-400">Job ID</p>
                        <p className="font-semibold text-gray-800 dark:text-gray-200 text-xs truncate">
                          {currentJob.job_id.split('-')[0]}...
                        </p>
                      </div>
                      <div className="p-3 bg-white dark:bg-gray-800 rounded-lg">
                        <p className="text-gray-600 dark:text-gray-400">Updated</p>
                        <p className="font-semibold text-gray-800 dark:text-gray-200 text-xs">
                          {new Date(currentJob.updated_at).toLocaleTimeString()}
                        </p>
                      </div>
                    </div>

                    {currentJob.errors && currentJob.errors.length > 0 && (
                      <div className="p-3 bg-red-50 dark:bg-red-950/20 rounded-lg">
                        <p className="text-sm font-medium text-red-700 dark:text-red-400 mb-2">
                          Errors:
                        </p>
                        <ul className="text-sm text-red-600 dark:text-red-300 space-y-1">
                          {currentJob.errors.map((err, idx) => (
                            <li key={idx}>• {err}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {currentJob.results && currentJob.status === 'completed' && (
                      <div className="p-3 bg-green-50 dark:bg-green-950/20 rounded-lg">
                        <p className="text-sm font-medium text-green-700 dark:text-green-400 mb-2">
                          Pipeline Results:
                        </p>
                        <div className="text-sm text-green-600 dark:text-green-300">
                          <p>✓ Files processed: {currentJob.results.summary?.successful || 0}</p>
                          {currentJob.results.summary?.failed > 0 && (
                            <p>✗ Files failed: {currentJob.results.summary?.failed}</p>
                          )}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Recent Jobs */}
          {recentJobs.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Card className="shadow-lg">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="h-5 w-5 text-blue-600" />
                    Recent Jobs
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {recentJobs.map((job) => (
                      <div
                        key={job.job_id}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors cursor-pointer"
                        onClick={() => setCurrentJob(job)}
                      >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          {getStatusIcon(job.status)}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                              {job.files_total} file(s) • {job.message}
                            </p>
                            <p className="text-xs text-gray-500">
                              {formatDate(job.created_at)}
                            </p>
                          </div>
                        </div>
                        <Badge className={getStatusColor(job.status)}>
                          {job.status.replace('_', ' ')}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </div>
      </div>
    </>
  )
}
