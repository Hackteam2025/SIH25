import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card'
import { Button } from './ui/Button'
import { Badge } from './ui/Badge'
import { X, Book, MessageCircle, Map, BarChart3, Database, Search, Download, Lightbulb, ExternalLink } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface HelpModalProps {
  isOpen: boolean
  onClose: () => void
}

const helpSections = [
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: Lightbulb,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 dark:bg-blue-950/20',
    content: [
      {
        title: 'Welcome to FloatChat',
        description: 'FloatChat is an AI-powered platform for exploring ARGO float ocean data. Navigate between different views using the sidebar.',
        tips: [
          'Start with the Dashboard for an overview of available data',
          'Use AI Chat for natural language queries about ocean data',
          'Explore the Map View for geographic visualization',
          'Check out Analytics for detailed charts and statistics'
        ]
      }
    ]
  },
  {
    id: 'ai-chat',
    title: 'AI Chat Assistant',
    icon: MessageCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50 dark:bg-green-950/20',
    content: [
      {
        title: 'Natural Language Queries',
        description: 'Ask questions about ARGO float data in plain English. The AI will analyze the data and provide insights.',
        tips: [
          'Try: "Show me temperature patterns near the equator"',
          'Ask: "What\'s the salinity distribution in May 2025?"',
          'Query: "Find data from latitude -10 to 10"',
          'Use: "Analyze depth profiles below 1000m"'
        ]
      },
      {
        title: 'Suggested Queries',
        description: 'Click on suggested queries when the chat is empty to get started quickly.',
        tips: [
          'Queries are optimized for the available data',
          'Results include statistical summaries and citations',
          'Responses stream in real-time for better experience'
        ]
      }
    ]
  },
  {
    id: 'map-view',
    title: 'Interactive Map',
    icon: Map,
    color: 'text-red-600',
    bgColor: 'bg-red-50 dark:bg-red-950/20',
    content: [
      {
        title: 'Map Navigation',
        description: 'Explore ARGO float locations on an interactive world map with clustering and filtering.',
        tips: [
          'Zoom and pan to explore different regions',
          'Click on markers to see profile details',
          'Use the side panel to filter by depth and temperature',
          'Toggle the heatmap for temperature/salinity visualization'
        ]
      },
      {
        title: 'Heatmap Features',
        description: 'Visualize temperature and salinity patterns with customizable heatmaps.',
        tips: [
          'Switch between Temperature and Salinity heatmaps',
          'Adjust radius, blur, and intensity for better visualization',
          'Use "Explain View" to get AI analysis of the current map area',
          'Heatmaps update automatically when you change parameters'
        ]
      }
    ]
  },
  {
    id: 'analytics',
    title: 'Data Analytics',
    icon: BarChart3,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50 dark:bg-purple-950/20',
    content: [
      {
        title: 'Interactive Charts',
        description: 'Explore data through various chart types with export capabilities.',
        tips: [
          'Adjust bin widths for histograms using the controls',
          'Export charts as PNG images or CSV data',
          'Use moving averages to smooth time series data',
          'Hover over charts for detailed information'
        ]
      },
      {
        title: 'Available Charts',
        description: 'Six different chart types provide comprehensive data analysis.',
        tips: [
          'Depth Distribution: See how measurements are distributed by depth',
          'Temperature vs Salinity: Explore the relationship between these variables',
          'Histograms: Analyze the distribution of temperature and salinity values',
          'Time Series: Track monthly patterns with moving averages'
        ]
      }
    ]
  },
  {
    id: 'data-entry',
    title: 'Data Entry',
    icon: Database,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50 dark:bg-orange-950/20',
    content: [
      {
        title: 'Insert New Profiles',
        description: 'Add new ARGO float profile data to the database (Development mode only).',
        tips: [
          'All required fields must be filled with valid values',
          'Latitude: -90 to 90 degrees',
          'Longitude: -180 to 180 degrees',
          'Temperature: -5°C to 50°C (realistic ocean temperatures)',
          'Salinity: 0 to 50 PSU (practical salinity units)'
        ]
      },
      {
        title: 'Validation & Feedback',
        description: 'The form provides real-time validation and clear feedback.',
        tips: [
          'Error messages appear immediately for invalid inputs',
          'Success confirmation shows the inserted profile details',
          'Use the Reset button to clear all form data',
          'Form is organized by sections for easy data entry'
        ]
      }
    ]
  }
]

const quickLinks = [
  {
    title: 'ARGO Float Program',
    url: 'https://argo.ucsd.edu/',
    description: 'Learn about the global ARGO float network'
  },
  {
    title: 'Ocean Data Standards',
    url: 'https://www.nodc.noaa.gov/',
    description: 'NOAA National Centers for Environmental Information'
  },
  {
    title: 'API Documentation',
    url: '/api/docs',
    description: 'Technical API reference and endpoints'
  }
]

export default function HelpModal({ isOpen, onClose }: HelpModalProps) {
  const [activeSection, setActiveSection] = useState('getting-started')

  if (!isOpen) return null

  const currentSection = helpSections.find(s => s.id === activeSection)

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Book className="h-6 w-6" />
                <div>
                  <h2 className="text-xl font-bold">FloatChat Help Center</h2>
                  <p className="text-blue-100 text-sm">Everything you need to know about using FloatChat</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-white hover:bg-white/20"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
          </div>

          <div className="flex h-[calc(90vh-120px)]">
            {/* Sidebar */}
            <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 overflow-y-auto">
              <div className="p-4 space-y-2">
                {helpSections.map((section) => {
                  const Icon = section.icon
                  return (
                    <button
                      key={section.id}
                      onClick={() => setActiveSection(section.id)}
                      className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${
                        activeSection === section.id
                          ? 'bg-white dark:bg-gray-700 shadow-sm border border-gray-200 dark:border-gray-600'
                          : 'hover:bg-white/50 dark:hover:bg-gray-700/50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className={`h-5 w-5 ${section.color}`} />
                        <span className="font-medium text-gray-800 dark:text-gray-200">
                          {section.title}
                        </span>
                      </div>
                    </button>
                  )
                })}
              </div>

              {/* Quick Links */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
                  External Resources
                </h3>
                <div className="space-y-2">
                  {quickLinks.map((link, index) => (
                    <a
                      key={index}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block p-2 rounded-lg hover:bg-white/50 dark:hover:bg-gray-700/50 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <ExternalLink className="h-3 w-3 text-gray-500" />
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                          {link.title}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {link.description}
                      </p>
                    </a>
                  ))}
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto">
              {currentSection && (
                <div className="p-6">
                  <div className={`p-4 rounded-lg ${currentSection.bgColor} mb-6`}>
                    <div className="flex items-center gap-3 mb-2">
                      <currentSection.icon className={`h-6 w-6 ${currentSection.color}`} />
                      <h3 className="text-xl font-bold text-gray-800 dark:text-gray-200">
                        {currentSection.title}
                      </h3>
                    </div>
                  </div>

                  <div className="space-y-6">
                    {currentSection.content.map((item, index) => (
                      <Card key={index} className="shadow-sm">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-lg text-gray-800 dark:text-gray-200">
                            {item.title}
                          </CardTitle>
                          <p className="text-gray-600 dark:text-gray-400 text-sm">
                            {item.description}
                          </p>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            {item.tips.map((tip, tipIndex) => (
                              <div key={tipIndex} className="flex items-start gap-3 p-2 rounded-lg bg-gray-50 dark:bg-gray-800">
                                <div className="w-2 h-2 rounded-full bg-blue-500 mt-2 flex-shrink-0" />
                                <span className="text-sm text-gray-700 dark:text-gray-300">
                                  {tip}
                                </span>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
