import React, { forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/utils';

interface OceanInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: 'default' | 'floating' | 'minimal';
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const OceanInput = forwardRef<HTMLInputElement, OceanInputProps>(({
  variant = 'default',
  label,
  error,
  leftIcon,
  rightIcon,
  className,
  ...props
}, ref) => {
  const [isFocused, setIsFocused] = React.useState(false);
  const [hasValue, setHasValue] = React.useState(false);

  React.useEffect(() => {
    setHasValue(Boolean(props.value || props.defaultValue));
  }, [props.value, props.defaultValue]);

  const baseClasses = cn(
    "w-full transition-all duration-300",
    "focus:outline-none",
    "text-ocean-blue placeholder-ocean-blue/50"
  );

  const variantClasses = {
    default: cn(
      "glass-input rounded-current px-4 py-2",
      "border border-white/10",
      "focus:border-seafoam-green focus:ring-2 focus:ring-seafoam-green/20"
    ),
    floating: cn(
      "glass-surface rounded-wave px-4 pt-6 pb-2",
      "border border-white/20",
      "focus:border-seafoam-green focus:ring-2 focus:ring-seafoam-green/20"
    ),
    minimal: cn(
      "bg-transparent border-0 border-b border-white/20 rounded-none px-0 py-2",
      "focus:border-seafoam-green"
    )
  };

  return (
    <div className="relative">
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-ocean-blue/70">
            {leftIcon}
          </div>
        )}

        <input
          ref={ref}
          className={cn(
            baseClasses,
            variantClasses[variant],
            leftIcon && "pl-10",
            rightIcon && "pr-10",
            error && "border-coral-pink focus:border-coral-pink focus:ring-coral-pink/20",
            className
          )}
          onFocus={(e) => {
            setIsFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setIsFocused(false);
            props.onBlur?.(e);
          }}
          onChange={(e) => {
            setHasValue(Boolean(e.target.value));
            props.onChange?.(e);
          }}
          {...props}
        />

        {rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-ocean-blue/70">
            {rightIcon}
          </div>
        )}

        {/* Floating Label */}
        {label && variant === 'floating' && (
          <motion.label
            className={cn(
              "absolute left-4 transition-all duration-200 pointer-events-none",
              "text-ocean-blue/70",
              (isFocused || hasValue)
                ? "top-2 text-xs text-seafoam-green"
                : "top-1/2 -translate-y-1/2 text-base"
            )}
            animate={{
              y: (isFocused || hasValue) ? 0 : 0,
              scale: (isFocused || hasValue) ? 0.85 : 1,
            }}
          >
            {label}
          </motion.label>
        )}
      </div>

      {/* Regular Label */}
      {label && variant !== 'floating' && (
        <label className="block text-sm font-medium text-ocean-blue mb-2">
          {label}
        </label>
      )}

      {/* Error Message */}
      {error && (
        <motion.p
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-2 text-sm text-coral-pink"
        >
          {error}
        </motion.p>
      )}
    </div>
  );
});

OceanInput.displayName = 'OceanInput';