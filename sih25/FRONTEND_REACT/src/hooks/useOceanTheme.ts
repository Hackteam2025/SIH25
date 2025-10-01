import { useState, useEffect, useCallback } from 'react';

interface OceanThemeConfig {
  intensity: 'calm' | 'moderate' | 'stormy';
  showBubbles: boolean;
  glowColor: 'seafoam' | 'coral' | 'ocean' | 'pearl';
  animationSpeed: number;
  enableAnimations: boolean;
}

interface UseOceanThemeReturn extends OceanThemeConfig {
  updateTheme: (config: Partial<OceanThemeConfig>) => void;
  resetTheme: () => void;
  presets: Record<string, OceanThemeConfig>;
  applyPreset: (presetName: string) => void;
}

const DEFAULT_THEME: OceanThemeConfig = {
  intensity: 'moderate',
  showBubbles: true,
  glowColor: 'seafoam',
  animationSpeed: 1,
  enableAnimations: true
};

const THEME_PRESETS: Record<string, OceanThemeConfig> = {
  calm: {
    intensity: 'calm',
    showBubbles: true,
    glowColor: 'pearl',
    animationSpeed: 0.7,
    enableAnimations: true
  },
  energetic: {
    intensity: 'stormy',
    showBubbles: true,
    glowColor: 'coral',
    animationSpeed: 1.5,
    enableAnimations: true
  },
  minimal: {
    intensity: 'calm',
    showBubbles: false,
    glowColor: 'ocean',
    animationSpeed: 0.5,
    enableAnimations: false
  },
  vibrant: {
    intensity: 'moderate',
    showBubbles: true,
    glowColor: 'seafoam',
    animationSpeed: 1.2,
    enableAnimations: true
  }
};

export const useOceanTheme = (): UseOceanThemeReturn => {
  const [theme, setTheme] = useState<OceanThemeConfig>(() => {
    // Load from localStorage if available
    const saved = localStorage.getItem('ocean-theme');
    if (saved) {
      try {
        return { ...DEFAULT_THEME, ...JSON.parse(saved) };
      } catch {
        return DEFAULT_THEME;
      }
    }
    return DEFAULT_THEME;
  });

  // Save to localStorage whenever theme changes
  useEffect(() => {
    localStorage.setItem('ocean-theme', JSON.stringify(theme));
  }, [theme]);

  // Apply CSS custom properties for theme
  useEffect(() => {
    const root = document.documentElement;

    // Set animation speeds
    root.style.setProperty('--animation-speed', theme.animationSpeed.toString());

    // Set animation state
    if (!theme.enableAnimations) {
      root.style.setProperty('--animation-play-state', 'paused');
    } else {
      root.style.setProperty('--animation-play-state', 'running');
    }

    // Set glow colors based on selection
    const glowColors = {
      seafoam: 'rgba(78, 205, 196, 0.3)',
      coral: 'rgba(255, 107, 107, 0.3)',
      ocean: 'rgba(0, 116, 217, 0.3)',
      pearl: 'rgba(255, 248, 220, 0.3)'
    };

    root.style.setProperty('--active-glow-color', glowColors[theme.glowColor]);

  }, [theme]);

  const updateTheme = useCallback((config: Partial<OceanThemeConfig>) => {
    setTheme(prev => ({ ...prev, ...config }));
  }, []);

  const resetTheme = useCallback(() => {
    setTheme(DEFAULT_THEME);
  }, []);

  const applyPreset = useCallback((presetName: string) => {
    const preset = THEME_PRESETS[presetName];
    if (preset) {
      setTheme(preset);
    }
  }, []);

  return {
    ...theme,
    updateTheme,
    resetTheme,
    presets: THEME_PRESETS,
    applyPreset
  };
};