import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface FloatingCardProps {
  children: React.ReactNode;
  className?: string;
  intensity?: 'subtle' | 'moderate' | 'strong';
  glowColor?: 'seafoam' | 'coral' | 'pearl';
  hoverable?: boolean;
}

export const FloatingCard: React.FC<FloatingCardProps> = ({
  children,
  className,
  intensity = 'moderate',
  glowColor = 'seafoam',
  hoverable = true
}) => {
  const intensityMap = {
    subtle: { y: [-2, 2], duration: 4 },
    moderate: { y: [-5, 5], duration: 3 },
    strong: { y: [-8, 8], duration: 2 }
  };

  const glowMap = {
    seafoam: 'shadow-[0_0_20px_rgba(78,205,196,0.3)]',
    coral: 'shadow-[0_0_20px_rgba(255,107,107,0.3)]',
    pearl: 'shadow-[0_0_20px_rgba(255,248,220,0.3)]'
  };

  const hoverGlowMap = {
    seafoam: 'hover:shadow-[0_0_30px_rgba(78,205,196,0.5)]',
    coral: 'hover:shadow-[0_0_30px_rgba(255,107,107,0.5)]',
    pearl: 'hover:shadow-[0_0_30px_rgba(255,248,220,0.5)]'
  };

  return (
    <motion.div
      animate={{
        y: intensityMap[intensity].y
      }}
      transition={{
        duration: intensityMap[intensity].duration,
        repeat: Infinity,
        repeatType: "reverse",
        ease: "easeInOut"
      }}
      whileHover={hoverable ? { scale: 1.02, y: -2 } : undefined}
      className={cn(
        "glass-surface rounded-wave p-6",
        "border border-white/20",
        "backdrop-filter backdrop-blur-xl",
        "transition-all duration-300",
        glowMap[glowColor],
        hoverable && [
          "hover:border-white/30",
          hoverGlowMap[glowColor],
          "cursor-pointer"
        ],
        className
      )}
    >
      {/* Highlight border */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent" />

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>

      {/* Ripple effect on hover */}
      {hoverable && (
        <div className="absolute inset-0 overflow-hidden rounded-wave">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent transform -translate-x-full hover:translate-x-full transition-transform duration-700" />
        </div>
      )}
    </motion.div>
  );
};