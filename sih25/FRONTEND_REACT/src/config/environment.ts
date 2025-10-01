/**
 * Environment Configuration File
 * 
 * Alternative methods to load environment variables for React/Vite apps
 * Use this if you're having issues with .env file loading
 */

export interface AppConfig {
  apiBaseUrl: string;
  supabaseUrl: string;
  supabaseAnonKey: string;
  isDevelopment: boolean;
}

// Method 1: Runtime Configuration Function
export const loadConfig = (): AppConfig => {
  // Check multiple sources for environment variables
  const getEnvVar = (key: string, fallback?: string): string => {
    // Try import.meta.env first (Vite standard)
    if (import.meta.env?.[key]) {
      return import.meta.env[key];
    }
    
    // Try window.ENV (runtime injection)
    if ((window as any).ENV?.[key]) {
      return (window as any).ENV[key];
    }
    
    // Try localStorage (manual override)
    const localValue = localStorage.getItem(`CONFIG_${key}`);
    if (localValue) {
      return localValue;
    }
    
    // Use fallback
    if (fallback) {
      return fallback;
    }
    
    throw new Error(`Environment variable ${key} is required but not set`);
  };

  return {
    apiBaseUrl: getEnvVar('VITE_API_URL', 'http://localhost:8000'),
    supabaseUrl: getEnvVar('VITE_SUPABASE_URL', 'https://your-project.supabase.co'),
    supabaseAnonKey: getEnvVar('VITE_SUPABASE_ANON_KEY', 'your-anon-key'),
    isDevelopment: getEnvVar('NODE_ENV', 'development') === 'development'
  };
};

// Method 2: Static Configuration (for when .env completely fails)
// Uncomment and modify these values as needed:
/*
export const STATIC_CONFIG: AppConfig = {
  apiBaseUrl: 'http://localhost:8000',
  supabaseUrl: 'https://xyzproject.supabase.co',
  supabaseAnonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
  isDevelopment: true
};
*/

// // Method 3: Environment-specific configs
// const DEVELOPMENT_CONFIG: Partial<AppConfig> = {
//   apiBaseUrl: 'http://localhost:8000',
//   supabaseUrl: 'https://dev-project.supabase.co',
//   // Add your dev Supabase key here
// };

// const PRODUCTION_CONFIG: Partial<AppConfig> = {
//   apiBaseUrl: 'https://api.yourapp.com',
//   supabaseUrl: 'https://prod-project.supabase.co',
//   // Add your prod Supabase key here
// };

// export const getEnvironmentConfig = (): Partial<AppConfig> => {
//   const isDev = window.location.hostname === 'localhost' || 
//                 window.location.hostname === '127.0.0.1';
  
//   return isDev ? DEVELOPMENT_CONFIG : PRODUCTION_CONFIG;
// };

// Method 4: Manual Configuration Override
// Use this in browser console to set values manually:
// localStorage.setItem('CONFIG_VITE_SUPABASE_ANON_KEY', 'your-actual-key');
// localStorage.setItem('CONFIG_VITE_SUPABASE_URL', 'https://your-project.supabase.co');

export const setConfigManually = (config: Partial<AppConfig>): void => {
  if (config.supabaseUrl) {
    localStorage.setItem('CONFIG_VITE_SUPABASE_URL', config.supabaseUrl);
  }
  if (config.supabaseAnonKey) {
    localStorage.setItem('CONFIG_VITE_SUPABASE_ANON_KEY', config.supabaseAnonKey);
  }
  if (config.apiBaseUrl) {
    localStorage.setItem('CONFIG_VITE_API_URL', config.apiBaseUrl);
  }
  
  console.log('Configuration saved to localStorage. Reload the page to apply changes.');
};

// Export the main config function
export default loadConfig;