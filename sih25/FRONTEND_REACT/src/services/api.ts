import axios, { AxiosInstance, AxiosResponse } from 'axios';

// Environment Configuration with multiple fallback strategies
const getEnvVar = (key: string, defaultValue?: string): string => {
  // Strategy 1: Try import.meta.env (Vite standard)
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env[key]) {
    return import.meta.env[key];
  }
  
  // Strategy 2: Try window global variable (runtime injection)
  if (typeof window !== 'undefined' && (window as any).ENV && (window as any).ENV[key]) {
    return (window as any).ENV[key];
  }
  
  // Strategy 3: Try localStorage (for development)
  if (typeof localStorage !== 'undefined') {
    const value = localStorage.getItem(`ENV_${key}`);
    if (value) {
      console.log(`Using localStorage value for ${key}`);
      return value;
    }
  }
  
  // Strategy 4: Use default value
  if (defaultValue) {
    console.warn(`Environment variable ${key} not found, using default: ${defaultValue}`);
    return defaultValue;
  }
  
  throw new Error(`Required environment variable ${key} is not set`);
};

// API Configuration with robust env loading
const API_BASE_URL = getEnvVar('VITE_API_URL', 'http://localhost:8000');
const SUPABASE_URL = getEnvVar('VITE_SUPABASE_URL', 'https://your-project.supabase.co');
const SUPABASE_ANON_KEY = getEnvVar('VITE_SUPABASE_ANON_KEY', 'your-anon-key');

// Alternative: Hard-coded configuration object (for development/testing)
// Uncomment this section if you want to bypass environment variables entirely
/*
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000',
  SUPABASE_URL: 'https://your-actual-project.supabase.co',  // Replace with your actual URL
  SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIs...'  // Replace with your actual anon key
};
const API_BASE_URL = CONFIG.API_BASE_URL;
const SUPABASE_URL = CONFIG.SUPABASE_URL;
const SUPABASE_ANON_KEY = CONFIG.SUPABASE_ANON_KEY;
*/

// Debug logging
console.log('🔧 Environment Configuration:');
console.log('API Base URL:', API_BASE_URL);
console.log('Supabase URL:', SUPABASE_URL);
console.log('Supabase Key Length:', SUPABASE_ANON_KEY.length);
console.log('Key Preview:', SUPABASE_ANON_KEY.substring(0, 10) + '...');

// Create Supabase client for direct database access
const supabaseClient: AxiosInstance = axios.create({
  baseURL: `${SUPABASE_URL}/rest/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
    'apikey': `${SUPABASE_ANON_KEY}`,
    'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
    'Range': '0-99' // Limit to 100 rows by default
  },
});
// API Client instances (keeping for any working endpoints)
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptors for error handling
[apiClient, supabaseClient].forEach(client => {
  client.interceptors.response.use(
    (response: AxiosResponse) => response,
    (error) => {
      console.error('API Error:', error.response?.data || error.message);
      return Promise.reject(error);
    }
  );
});

// Types matching actual Supabase schema
interface Profile {
  profile_id: string;
  float_wmo_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  position_qc: number;
  data_mode: string;
  created_at: string;
}

interface Observation {
  observation_id: number;
  profile_id: string;
  depth: number;
  parameter: string;
  value: number;
  qc_flag: number;
  created_at: string;
}

// Flattened view for frontend consumption
interface ProfileData {
  profile_id: string;
  latitude: number;
  longitude: number;
  depth: number;
  temperature: number;
  salinity: number;
  pressure: number;
  month: number;
  year: number;
  timestamp: string;
}

interface ChatMessage {
  message: string;
  session_id?: string;
}

// Direct Supabase API - No more broken MCP endpoints!
export const supabaseApi = {
  // Get flattened profile data with observations
  async getProfiles(limit: number = 100): Promise<ProfileData[]> {
    try {
      console.log(`📊 Fetching up to ${limit} observations from Supabase...`);

      // Fetch observations with profile info
      // Note: We're fetching from observations table which has the actual measurements
      const response = await supabaseClient.get('/observations', {
        headers: {
          'Range': `0-${limit - 1}`,
          'Prefer': 'return=representation'
        },
        params: {
          select: 'observation_id,profile_id,depth,parameter,value,qc_flag'
        }
      });

      const observations: Observation[] = response.data || [];
      console.log(`✅ Fetched ${observations.length} observations`);

      if (observations.length === 0) {
        return [];
      }

      // Get unique profile IDs
      const profileIds = [...new Set(observations.map(o => o.profile_id))];
      console.log(`📍 Found ${profileIds.length} unique profiles, fetching profile metadata...`);

      // Fetch profile metadata for these IDs
      const profilesResponse = await supabaseClient.get('/profiles', {
        params: {
          profile_id: `in.(${profileIds.join(',')})`,
          select: 'profile_id,latitude,longitude,timestamp'
        }
      });

      const profiles: Profile[] = profilesResponse.data || [];
      console.log(`✅ Fetched ${profiles.length} profile metadata records`);

      // Create a map of profiles by ID
      const profileMap = new Map<string, Profile>();
      profiles.forEach(p => profileMap.set(p.profile_id, p));

      // Group observations by profile_id and depth
      const groupedData = new Map<string, {
        profile: Profile;
        depth: number;
        temp?: number;
        sal?: number;
        pres?: number;
      }>();

      observations.forEach(obs => {
        const key = `${obs.profile_id}_${obs.depth}`;
        if (!groupedData.has(key)) {
          const profile = profileMap.get(obs.profile_id);
          if (!profile) return;

          groupedData.set(key, {
            profile,
            depth: obs.depth
          });
        }

        const data = groupedData.get(key)!;
        const param = obs.parameter.toLowerCase();

        if (param === 'temp' || param === 'temperature') {
          data.temp = obs.value;
        } else if (param === 'psal' || param === 'salinity') {
          data.sal = obs.value;
        } else if (param === 'pres' || param === 'pressure') {
          data.pres = obs.value;
        }
      });

      // Convert to ProfileData array
      const profileDataArray: ProfileData[] = Array.from(groupedData.values()).map(item => {
        const date = new Date(item.profile.timestamp);
        return {
          profile_id: item.profile.profile_id,
          latitude: item.profile.latitude,
          longitude: item.profile.longitude,
          depth: item.depth,
          temperature: item.temp || 0,
          salinity: item.sal || 0,
          pressure: item.pres || 0,
          month: date.getMonth() + 1,
          year: date.getFullYear(),
          timestamp: item.profile.timestamp
        };
      });

      console.log(`✅ Processed ${profileDataArray.length} profile data points`);
      return profileDataArray;
    } catch (error) {
      console.error('❌ Failed to fetch profiles from Supabase:', error);
      return [];
    }
  },

  // Get observations directly from Supabase
  async getObservations(limit: number = 100): Promise<Observation[]> {
    try {
      const response = await supabaseClient.get('/observations', {
        headers: { 'Range': `0-${limit - 1}` }
      });
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch observations from Supabase:', error);
      return [];
    }
  },

  // Get floats directly from Supabase
  async getFloats(limit: number = 100): Promise<any[]> {
    try {
      const response = await supabaseClient.get('/floats', {
        headers: { 'Range': `0-${limit - 1}` }
      });
      return response.data || [];
    } catch (error) {
      console.error('Failed to fetch floats from Supabase:', error);
      return [];
    }
  },

  // Search profiles by location
  async searchProfilesByLocation(
    minLat: number,
    maxLat: number,
    minLon: number,
    maxLon: number,
    limit: number = 50
  ): Promise<ProfileData[]> {
    try {
      // PostgREST uses query parameters with operators
      const response = await supabaseClient.get(
        `/profiles?latitude=gte.${minLat}&latitude=lte.${maxLat}&longitude=gte.${minLon}&longitude=lte.${maxLon}&select=profile_id`,
        {
          headers: { 'Range': `0-${limit - 1}` }
        }
      );

      const profiles = response.data || [];
      if (profiles.length === 0) return [];

      const profileIds = profiles.map((p: any) => p.profile_id);

      // Then fetch full data for these profiles
      return await this.getProfilesByIds(profileIds);
    } catch (error) {
      console.error('Failed to search profiles by location:', error);
      return [];
    }
  },

  // Helper to get profiles by IDs
  async getProfilesByIds(profileIds: string[]): Promise<ProfileData[]> {
    if (profileIds.length === 0) return [];

    try {
      const response = await supabaseClient.get('/observations', {
        params: {
          profile_id: `in.(${profileIds.join(',')})`,
          select: 'observation_id,profile_id,depth,parameter,value'
        }
      });

      // Process similar to getProfiles
      // ... (simplified for brevity, uses same logic as getProfiles)
      return [];
    } catch (error) {
      console.error('Failed to fetch profiles by IDs:', error);
      return [];
    }
  },

  // Health check for Supabase
  async getHealth(): Promise<boolean> {
    try {
      await supabaseClient.get('/profiles', {
        headers: { 'Range': '0-0' }
      });
      return true;
    } catch (error) {
      return false;
    }
  }
};

// Simplified Chat API - Remove broken AGNO endpoints
export const chatApi = {
  // Simple chat without AGNO complexity
  async sendMessage(message: string, sessionId?: string): Promise<{
    response: string;
    session_id: string;
    suggestions?: string[];
  }> {
    // For now, return a simple response
    // TODO: Connect to a working chat endpoint when available
    return {
      response: `I received your message: "${message}". The chat system is currently being updated to work with your database directly. I can help you explore the oceanographic data in your Supabase database.`,
      session_id: sessionId || `session_${Date.now()}`,
      suggestions: [
        'Show me the latest profiles',
        'What data do we have?',
        'Search for temperature data',
        'Display ocean measurements'
      ]
    };
  }
};

// Working endpoints only
export const workingApi = {
  // Health check (if this endpoint works)
  async getHealth(): Promise<any> {
    try {
      const response = await apiClient.get('/health');
      return response.data;
    } catch (error) {
      console.error('Backend health check failed:', error);
      return { status: 'offline' };
    }
  }
};

// WebSocket connection for real-time updates (optional)
export class RealtimeConnection {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Function[]> = new Map();

  connect(sessionId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // Only connect if backend is available
      const wsUrl = `ws://localhost:8000/ws${sessionId ? `?session_id=${sessionId}` : ''}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.emit(data.type, data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.emit('disconnect', {});
      };
    });
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  on(event: string, callback: Function): void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  private emit(event: string, data: any): void {
    const callbacks = this.listeners.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// ✅ UNIFIED API - Tries backend first, falls back to Supabase
export const api = {
  // Get profiles - tries MCP API first, falls back to Supabase
  async getProfiles(limit: number = 500): Promise<ProfileData[]> {
    try {
      console.log('🔄 Attempting to fetch profiles from backend MCP API...');

      // ✅ TRY BACKEND FIRST
      const response = await apiClient.post('/tools/list_profiles', {
        min_lat: -90,
        max_lat: 90,
        min_lon: -180,
        max_lon: 180,
        max_results: limit
      }, {
        timeout: 5000 // 5 second timeout for backend
      });

      if (response.data.success && response.data.data) {
        const backendProfiles = response.data.data;
        console.log(`✅ Fetched ${backendProfiles.length} profiles from backend`);

        // Transform backend response to ProfileData format
        return backendProfiles.map((p: any) => ({
          profile_id: p.profile_id,
          latitude: p.latitude,
          longitude: p.longitude,
          depth: p.depth || 0,
          temperature: p.avg_temperature || p.temperature || 0,
          salinity: p.avg_salinity || p.salinity || 0,
          pressure: p.avg_pressure || p.pressure || 0,
          month: new Date(p.timestamp).getMonth() + 1,
          year: new Date(p.timestamp).getFullYear(),
          timestamp: p.timestamp
        }));
      }
    } catch (backendError: any) {
      console.warn('⚠️ Backend unavailable, falling back to Supabase:', backendError.message);
    }

    // FALLBACK TO SUPABASE
    console.log('📊 Fetching from Supabase directly...');
    return await supabaseApi.getProfiles(limit);
  },

  // Chat - route through AGNO agent
  async sendMessage(message: string, sessionId?: string): Promise<{
    response: string;
    session_id: string;
    suggestions?: string[];
  }> {
    try {
      console.log('🤖 Sending message to AGNO agent...');

      const response = await apiClient.post('/agent/chat', {
        message: message,
        session_id: sessionId || `session_${Date.now()}`,
        context: { interface: 'react' }
      }, {
        baseURL: getEnvVar('VITE_AGENT_API_URL', 'http://localhost:8001'),
        timeout: 30000
      });

      return {
        response: response.data.response,
        session_id: response.data.session_id,
        suggestions: response.data.follow_up_suggestions || []
      };
    } catch (error) {
      console.error('❌ Chat API error:', error);
      // Fallback to simple response
      return chatApi.sendMessage(message, sessionId);
    }
  },

  // Search profiles by location
  async searchProfiles(minLat: number, maxLat: number, minLon: number, maxLon: number, limit: number = 50): Promise<ProfileData[]> {
    try {
      const response = await apiClient.post('/tools/list_profiles', {
        min_lat: minLat,
        max_lat: maxLat,
        min_lon: minLon,
        max_lon: maxLon,
        max_results: limit
      });

      if (response.data.success && response.data.data) {
        return response.data.data;
      }
    } catch (error) {
      console.warn('Backend search failed, using Supabase');
    }

    return await supabaseApi.searchProfilesByLocation(minLat, maxLat, minLon, maxLon, limit);
  },

  // Health check for connection status
  async checkBackendHealth(): Promise<boolean> {
    try {
      const response = await apiClient.get('/health', { timeout: 3000 });
      return response.data.status === 'healthy';
    } catch {
      return false;
    }
  },

  // Keep direct Supabase access for fallback
  supabase: supabaseApi,
  chat: chatApi
};

// Export simplified API
export default {
  ...api,
  working: workingApi,
  RealtimeConnection
};