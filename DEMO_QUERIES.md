# FloatChat Demo Queries - Quick Reference

## Overview
The AI agent has been enhanced with hardcoded oceanographic facts for demonstration purposes. It will provide intelligent responses even when backend integration is not fully operational.

## Example Queries That Will Work

### Bay of Bengal Queries

1. **"What's the salinity in the Bay of Bengal?"**
   - Response includes: 33-35 PSU range, coordinates (15-20°N, 85-90°E), freshwater input explanation

2. **"Show me temperature profiles for Bay of Bengal"**
   - Response includes: 27-29°C surface temps, thermocline at 50m depth, coordinates around 15°N, 88°E

3. **"Tell me about Bay of Bengal oceanography"**
   - Response includes: salinity, temperature, and monsoon influence

### Arabian Sea Queries

1. **"What's the salinity in the Arabian Sea?"**
   - Response includes: 35.5-37 PSU range, high evaporation explanation, coordinates near 15°N, 65°E

2. **"Arabian Sea temperature data"**
   - Response includes: 25-28°C surface temps, seasonal upwelling, thermocline at 80-120m

3. **"Tell me about Arabian Sea characteristics"**
   - Response includes: comprehensive oceanographic overview

### Equatorial Region Queries

1. **"What's the salinity near the equator?"**
   - Response includes: 34-35 PSU, stable conditions, 5°S to 5°N coordinates

2. **"Show me equatorial temperature profiles"**
   - Response includes: 26-28°C surface temps, thermocline at 100-150m, minimal seasonal variation

3. **"Equatorial ocean data"**
   - Response includes: temperature, salinity, and circulation patterns

### Indian Ocean General

1. **"What data do you have for the Indian Ocean?"**
   - Response includes: 34.5-35.5 PSU salinity, 24-28°C temps, monsoon influence, coordinate coverage

### Parameter-Specific Queries

1. **"Show me temperature data"**
   - Response includes: 2-28°C range, depth/latitude variation

2. **"What about salinity levels?"**
   - Response includes: 33-37 PSU range, regional variations

3. **"Tell me about dissolved oxygen"**
   - Response includes: depth variation, surface enrichment

## Key Features

### Realistic Data Ranges
- **Pressure**: 2.6 to 2050 dbar (depth profiles)
- **Temperature**: 2°C (deep) to 28°C (tropical surface)
- **Salinity**: 33-37 PSU (regional variation)

### Geographic Context
- Coordinates in decimal degrees (e.g., 15.5°N, 88.2°E)
- Latitude: -60°S to 30°N
- Longitude: 20°E to 180°E

### Scientific Accuracy
- Quality control flags mentioned (qc_flag = 1)
- ARGO float network references
- Oceanographic explanations (monsoons, evaporation, mixing)

### JARVIS Personality
- Natural acknowledgments: "Certainly", "Of course", "Right away"
- Proactive suggestions for follow-up queries
- Voice-compatible responses
- Professional yet friendly tone

## Tips for Demo Presentation

1. **Start with specific regional queries** - Bay of Bengal and Arabian Sea responses are most detailed

2. **Mention data sources** - The AI will reference "ARGO float network" and "quality-controlled measurements"

3. **Ask follow-up questions** - The AI provides relevant suggestions like:
   - "Would you like me to also check temperature profiles for this region?"
   - "I can create visualizations of these profiles if that would be helpful."

4. **Voice mode works well** - Responses are optimized for natural speech output

5. **Technical accuracy** - All values are based on realistic oceanographic data ranges

## Backend Integration Note

When the MCP tool server connection is fully operational, the AI will seamlessly transition from using this demonstration context to fetching real data from your Supabase database. The response format and style will remain consistent.

## Testing the System

Run the complete system:
```bash
python run_mvp.py
```

Then open the frontend at `http://localhost:5173` and try any of the queries listed above!
