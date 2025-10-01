import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils';

interface BubbleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'coral' | 'seafoam';
  size?: 'sm' | 'md' | 'lg';
  isActive?: boolean;
  children: React.ReactNode;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  showRipple?: boolean;
}

export const BubbleButton: React.FC<BubbleButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isActive = false,
  children,
  leftIcon,
  rightIcon,
  showRipple = true,
  className,
  onClick,
  ...props
}) => {
  const [ripples, setRipples] = useState<{ x: number; y: number; id: number }[]>([]);

  const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (showRipple) {
      const button = e.currentTarget;
      const rect = button.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      const newRipple = {
        x,
        y,
        id: Date.now()
      };

      setRipples(prev => [...prev, newRipple]);

      // Remove ripple after animation
      setTimeout(() => {
        setRipples(prev => prev.filter(ripple => ripple.id !== newRipple.id));
      }, 600);
    }

    onClick?.(e);
  };

  const baseClasses = cn(
    "relative inline-flex items-center justify-center",
    "font-medium rounded-bubble transition-all duration-300",
    "focus:outline-none focus:ring-2 focus:ring-seafoam-green/50",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    "overflow-hidden group",
    "backdrop-filter backdrop-blur-lg"
  );

  const variantClasses = {
    primary: cn(
      "bg-gradient-to-r from-ocean-blue to-ocean-surface",
      "text-white border border-ocean-surface/30",
      "hover:from-ocean-surface hover:to-seafoam-green",
      "shadow-[0_4px_20px_rgba(0,116,217,0.3)]",
      "hover:shadow-[0_6px_25px_rgba(78,205,196,0.4)]",
      isActive && "from-seafoam-green to-ocean-surface shadow-[0_6px_25px_rgba(78,205,196,0.6)]"
    ),
    secondary: cn(
      "glass-surface text-ocean-blue border border-white/20",
      "hover:border-white/30 hover:bg-white/20",
      "backdrop-blur-xl",
      isActive && "bg-white/25 border-white/40"
    ),
    coral: cn(
      "bg-gradient-to-r from-coral-pink to-coral-orange",
      "text-white border border-coral-pink/30",
      "hover:from-coral-orange hover:to-coral-pink",
      "shadow-[0_4px_20px_rgba(255,107,107,0.3)]",
      "hover:shadow-[0_6px_25px_rgba(255,107,107,0.5)]",
      isActive && "shadow-[0_6px_25px_rgba(255,107,107,0.7)]"
    ),
    seafoam: cn(
      "bg-gradient-to-r from-seafoam-green to-bubble-white",
      "text-ocean-deep border border-seafoam-green/30",
      "hover:from-bubble-white hover:to-seafoam-green",
      "shadow-[0_4px_20px_rgba(78,205,196,0.3)]",
      "hover:shadow-[0_6px_25px_rgba(78,205,196,0.5)]",
      isActive && "shadow-[0_6px_25px_rgba(78,205,196,0.7)]"
    )
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-sm gap-1.5 min-w-[60px] h-8",
    md: "px-4 py-2 text-base gap-2 min-w-[80px] h-10",
    lg: "px-6 py-3 text-lg gap-2.5 min-w-[100px] h-12"
  };

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={cn(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      onClick={handleClick}
      {...props}
    >
      {/* Background shimmer effect */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent transform -translate-x-full group-hover:translate-x-full transition-transform duration-700" />

      {/* Content */}
      <span className="relative flex items-center gap-2 z-10">
        {leftIcon}
        {children}
        {rightIcon}
      </span>

      {/* Ripple effects */}
      <AnimatePresence>
        {ripples.map((ripple) => (
          <motion.div
            key={ripple.id}
            className="absolute rounded-full bg-white/30 pointer-events-none"
            style={{
              left: ripple.x - 25,
              top: ripple.y - 25,
              width: 50,
              height: 50
            }}
            initial={{ scale: 0, opacity: 1 }}
            animate={{ scale: 2, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        ))}
      </AnimatePresence>

      {/* Active state glow */}
      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-bubble"
          animate={{
            boxShadow: [
              "0 0 20px rgba(78, 205, 196, 0.5)",
              "0 0 30px rgba(78, 205, 196, 0.8)",
              "0 0 20px rgba(78, 205, 196, 0.5)"
            ]
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
      )}
    </motion.button>
  );
};