/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_MCP_API_URL: string
  readonly VITE_VOICE_API_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Leaflet Heat Plugin Types
declare module 'leaflet' {
  namespace L {
    function heatLayer(
      latLngs: Array<[number, number, number?]>,
      options?: any
    ): any;
  }
}

// Global L object
declare const L: any;