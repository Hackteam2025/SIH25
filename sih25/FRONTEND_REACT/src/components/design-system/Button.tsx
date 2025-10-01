import React from 'react';
import { motion } from 'framer-motion';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/utils';

interface OceanButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'coral' | 'seafoam';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  children: React.ReactNode;
}

export const OceanButton: React.FC<OceanButtonProps> = ({
  variant = 'primary',
  size = 'md',
  isLoading = false,
  leftIcon,
  rightIcon,
  children,
  className,
  disabled,
  ...props
}) => {
  const baseClasses = cn(
    "relative inline-flex items-center justify-center",
    "font-medium rounded-wave transition-all duration-200",
    "focus:outline-none focus:ring-2 focus:ring-seafoam-green/50",
    "disabled:opacity-50 disabled:cursor-not-allowed",
    "overflow-hidden group"
  );

  const variantClasses = {
    primary: cn(
      "bg-gradient-to-r from-ocean-blue to-ocean-surface",
      "text-white border border-ocean-surface/30",
      "hover:from-ocean-surface hover:to-seafoam-green",
      "shadow-[0_4px_20px_rgba(0,116,217,0.3)]",
      "hover:shadow-[0_6px_25px_rgba(78,205,196,0.4)]"
    ),
    secondary: cn(
      "glass-surface text-ocean-blue border border-white/20",
      "hover:border-white/30 hover:bg-white/20",
      "backdrop-blur-xl"
    ),
    ghost: cn(
      "text-ocean-blue hover:bg-white/10",
      "border border-transparent hover:border-white/20"
    ),
    coral: cn(
      "bg-gradient-to-r from-coral-pink to-coral-orange",
      "text-white border border-coral-pink/30",
      "hover:from-coral-orange hover:to-coral-pink",
      "shadow-[0_4px_20px_rgba(255,107,107,0.3)]"
    ),
    seafoam: cn(
      "bg-gradient-to-r from-seafoam-green to-bubble-white",
      "text-ocean-deep border border-seafoam-green/30",
      "hover:from-bubble-white hover:to-seafoam-green",
      "shadow-[0_4px_20px_rgba(78,205,196,0.3)]"
    )
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-sm gap-1.5",
    md: "px-4 py-2 text-base gap-2",
    lg: "px-6 py-3 text-lg gap-2.5",
    xl: "px-8 py-4 text-xl gap-3"
  };

  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={cn(
        baseClasses,
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled || isLoading}
      {...props}
    >
      {/* Ripple Effect */}
      <div className="absolute inset-0 overflow-hidden rounded-wave">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent transform -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
      </div>

      {/* Content */}
      <span className="relative flex items-center gap-2">
        {isLoading ? (
          <Loader2 className="animate-spin" size={16} />
        ) : (
          leftIcon
        )}
        {children}
        {!isLoading && rightIcon}
      </span>
    </motion.button>
  );
};