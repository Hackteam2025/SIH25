import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface OceanLoaderProps {
  variant?: 'waves' | 'bubbles' | 'current' | 'pulse';
  size?: 'sm' | 'md' | 'lg';
  color?: 'seafoam' | 'coral' | 'ocean';
  className?: string;
}

export const OceanLoader: React.FC<OceanLoaderProps> = ({
  variant = 'waves',
  size = 'md',
  color = 'seafoam',
  className
}) => {
  const colorMap = {
    seafoam: 'bg-seafoam-green',
    coral: 'bg-coral-pink',
    ocean: 'bg-ocean-surface'
  };

  const sizeMap = {
    sm: { container: 'w-8 h-8', wave: 'h-3' },
    md: { container: 'w-12 h-12', wave: 'h-4' },
    lg: { container: 'w-16 h-16', wave: 'h-6' }
  };

  const WaveLoader = () => (
    <div className={cn("flex items-end justify-center gap-1", sizeMap[size].container, className)}>
      {[0, 1, 2, 3].map((i) => (
        <motion.div
          key={i}
          className={cn("w-1 rounded-full", sizeMap[size].wave, colorMap[color])}
          animate={{
            scaleY: [0.4, 1, 0.4],
            opacity: [0.6, 1, 0.6]
          }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.15,
            ease: "easeInOut"
          }}
        />
      ))}
    </div>
  );

  const BubbleLoader = () => (
    <div className={cn("relative", sizeMap[size].container, className)}>
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className={cn("absolute rounded-full", colorMap[color])}
          style={{
            width: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
            height: size === 'sm' ? '8px' : size === 'md' ? '12px' : '16px',
            left: '50%',
            top: '50%'
          }}
          animate={{
            scale: [0, 1, 0],
            opacity: [0, 1, 0],
            x: [0, Math.cos(i * 2.1) * 20, 0],
            y: [0, Math.sin(i * 2.1) * 20, 0]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            delay: i * 0.4,
            ease: "easeInOut"
          }}
        />
      ))}
    </div>
  );

  const CurrentLoader = () => (
    <div className={cn("relative overflow-hidden", sizeMap[size].container, className)}>
      <motion.div
        className={cn("absolute inset-0 rounded-full opacity-20", colorMap[color])}
      />
      <motion.div
        className={cn("absolute top-1/2 left-0 h-0.5 rounded-full", colorMap[color])}
        style={{ width: '100%' }}
        animate={{
          x: ['-100%', '100%'],
          scaleX: [0.3, 1, 0.3]
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
    </div>
  );

  const PulseLoader = () => (
    <div className={cn("relative", sizeMap[size].container, className)}>
      <motion.div
        className={cn("absolute inset-0 rounded-full", colorMap[color])}
        animate={{
          scale: [0.8, 1.2, 0.8],
          opacity: [1, 0.3, 1]
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
      <motion.div
        className={cn("absolute inset-2 rounded-full", colorMap[color])}
        animate={{
          scale: [1.2, 0.8, 1.2],
          opacity: [0.3, 1, 0.3]
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut"
        }}
      />
    </div>
  );

  const loaderMap = {
    waves: WaveLoader,
    bubbles: BubbleLoader,
    current: CurrentLoader,
    pulse: PulseLoader
  };

  const LoaderComponent = loaderMap[variant];

  return <LoaderComponent />;
};