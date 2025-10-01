import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Menu, X, Mic, Settings, Activity } from 'lucide-react';
import { WaveBackground } from '../ocean/WaveBackground';
import { FloatingCard } from '../ocean/FloatingCard';
import { OceanButton } from '../design-system/Button';
import { cn } from '../../lib/utils';

interface OceanLayoutProps {
  children: React.ReactNode;
  showVoiceButton?: boolean;
  isVoiceActive?: boolean;
  onVoiceToggle?: () => void;
}

export const OceanLayout: React.FC<OceanLayoutProps> = ({
  children,
  showVoiceButton = true,
  isVoiceActive = false,
  onVoiceToggle
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Animated Ocean Background */}
      <WaveBackground intensity="moderate" showBubbles />

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 p-4">
        <FloatingCard className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 hover:bg-white/10 rounded-current transition-colors"
            >
              <Menu className="w-5 h-5 text-ocean-blue" />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-ocean-sunset rounded-bubble flex items-center justify-center">
                <span className="text-white font-bold text-sm">FC</span>
              </div>
              <div>
                <h1 className="ocean-heading text-lg font-bold">FloatChat</h1>
                <p className="text-xs text-ocean-blue/70">Ocean Data Explorer</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1 bg-white/10 rounded-wave">
              <Activity className="w-4 h-4 text-seafoam-green" />
              <span className="text-sm text-ocean-blue">Live Data</span>
            </div>

            {showVoiceButton && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={onVoiceToggle}
                className={cn(
                  "p-3 rounded-bubble transition-all duration-300",
                  isVoiceActive
                    ? "bg-coral-pink shadow-[0_0_20px_rgba(255,107,107,0.5)]"
                    : "glass-surface hover:bg-white/20"
                )}
              >
                <Mic className={cn(
                  "w-5 h-5",
                  isVoiceActive ? "text-white" : "text-ocean-blue"
                )} />
              </motion.button>
            )}

            <button className="p-2 hover:bg-white/10 rounded-current transition-colors">
              <Settings className="w-5 h-5 text-ocean-blue" />
            </button>
          </div>
        </FloatingCard>
      </header>

      {/* Sidebar */}
      <AnimatePresence>
        {isSidebarOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsSidebarOpen(false)}
              className="fixed inset-0 bg-abyss-black/50 z-40"
            />

            {/* Sidebar */}
            <motion.div
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "spring", damping: 25, stiffness: 200 }}
              className="fixed left-4 top-4 bottom-4 w-80 z-50"
            >
              <FloatingCard className="h-full flex flex-col">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="ocean-heading text-xl font-bold">Navigation</h2>
                  <button
                    onClick={() => setIsSidebarOpen(false)}
                    className="p-2 hover:bg-white/10 rounded-current transition-colors"
                  >
                    <X className="w-5 h-5 text-ocean-blue" />
                  </button>
                </div>

                <nav className="flex-1 space-y-2">
                  {[
                    { label: "Chat Interface", href: "/chat", icon: "💬" },
                    { label: "Data Visualization", href: "/viz", icon: "📊" },
                    { label: "Map Explorer", href: "/map", icon: "🗺️" },
                    { label: "Upload Data", href: "/upload", icon: "📁" },
                    { label: "Voice AI", href: "/voice", icon: "🎤" },
                    { label: "Settings", href: "/settings", icon: "⚙️" }
                  ].map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      className="flex items-center gap-3 p-3 hover:bg-white/10 rounded-wave transition-colors group"
                    >
                      <span className="text-xl">{item.icon}</span>
                      <span className="ocean-body group-hover:text-seafoam-green transition-colors">
                        {item.label}
                      </span>
                    </a>
                  ))}
                </nav>

                {/* Footer Info */}
                <div className="mt-auto pt-4 border-t border-white/10">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-2 mb-2">
                      <div className="w-2 h-2 bg-seafoam-green rounded-full animate-pulse" />
                      <span className="text-sm text-ocean-blue">Connected to ARGO</span>
                    </div>
                    <p className="text-xs text-ocean-blue/70">
                      SIH 2025 • Team COMET
                    </p>
                  </div>
                </div>
              </FloatingCard>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="pt-24 pb-8 px-4 relative z-10">
        {children}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-4 left-4 right-4 z-50">
        <FloatingCard className="text-center py-3" intensity="subtle">
          <p className="text-sm text-ocean-blue/70">
            Powered by ARGO Global Ocean Data • SIH 2025 • Team COMET
          </p>
        </FloatingCard>
      </footer>
    </div>
  );
};