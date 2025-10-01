import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface OceanCardProps {
  children: React.ReactNode;
  variant?: 'default' | 'floating' | 'minimal' | 'elevated';
  className?: string;
  hoverable?: boolean;
  glowColor?: 'seafoam' | 'coral' | 'ocean' | 'pearl';
}

export const OceanCard: React.FC<OceanCardProps> = ({
  children,
  variant = 'default',
  className,
  hoverable = false,
  glowColor = 'seafoam'
}) => {
  const baseClasses = cn(
    "backdrop-filter backdrop-blur-xl",
    "transition-all duration-300",
    "border border-white/20",
    "overflow-hidden"
  );

  const variantClasses = {
    default: cn(
      "glass-surface rounded-wave p-6",
      "shadow-[0_8px_32px_rgba(0,31,63,0.25)]"
    ),
    floating: cn(
      "glass-moderate rounded-wave p-6",
      "shadow-[0_12px_48px_rgba(0,31,63,0.35)]",
      "animate-float-gentle"
    ),
    minimal: cn(
      "glass-subtle rounded-current p-4",
      "shadow-[0_4px_16px_rgba(0,31,63,0.15)]"
    ),
    elevated: cn(
      "glass-strong rounded-wave p-8",
      "shadow-[0_16px_64px_rgba(0,31,63,0.45)]"
    )
  };

  const glowMap = {
    seafoam: 'hover:shadow-[0_0_30px_rgba(78,205,196,0.4)]',
    coral: 'hover:shadow-[0_0_30px_rgba(255,107,107,0.4)]',
    ocean: 'hover:shadow-[0_0_30px_rgba(0,116,217,0.4)]',
    pearl: 'hover:shadow-[0_0_30px_rgba(255,248,220,0.4)]'
  };

  return (
    <motion.div
      whileHover={hoverable ? {
        scale: 1.02,
        y: -2
      } : undefined}
      className={cn(
        baseClasses,
        variantClasses[variant],
        hoverable && [
          "cursor-pointer",
          "hover:border-white/30",
          glowMap[glowColor]
        ],
        className
      )}
    >
      {/* Top highlight */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-white/30 to-transparent" />

      {/* Content */}
      <div className="relative z-10">
        {children}
      </div>

      {/* Ripple effect for hoverable cards */}
      {hoverable && (
        <div className="absolute inset-0 overflow-hidden rounded-wave">
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent transform -translate-x-full hover:translate-x-full transition-transform duration-700" />
        </div>
      )}
    </motion.div>
  );
};