from typing import List, Dict
import re
import statistics
from datetime import datetime

# Enhanced knowledge base for ARGO ocean data
ARGO_KNOWLEDGE_BASE = [
    {
        "id": "argo_overview",
        "text": "ARGO floats are autonomous profiling floats that collect temperature, salinity, and pressure data in the upper ocean. They typically operate at depths between 0-2000 meters, measuring temperature from -2°C to 40°C and salinity from 20-40 PSU. ARGO floats surface every 10 days to transmit data via satellite.",
        "metadata": {"category": "overview", "priority": "high"}
    },
    {
        "id": "temperature_ranges",
        "text": "Ocean temperature ranges vary by location and depth. Surface temperatures typically range from -2°C in polar regions to 35°C in equatorial regions. Deep ocean temperatures are more stable, usually between 0-4°C. Temperature decreases with depth in most ocean regions.",
        "metadata": {"category": "parameter", "parameter": "temperature", "priority": "high"}
    },
    {
        "id": "salinity_ranges",
        "text": "Ocean salinity typically ranges from 28-40 PSU (Practical Salinity Units). Lower salinity values are found in polar regions and near river mouths due to freshwater input, while higher values occur in subtropical regions where evaporation exceeds precipitation.",
        "metadata": {"category": "parameter", "parameter": "salinity", "priority": "high"}
    },
    {
        "id": "depth_profiles",
        "text": "ARGO floats provide vertical profiles of temperature and salinity. The mixed layer (surface to ~100m) shows strong seasonal variations, while the deep ocean (below 1000m) is more stable. The thermocline region (100-1000m) shows the strongest temperature gradients.",
        "metadata": {"category": "methodology", "priority": "high"}
    },
    {
        "id": "ocean_regions",
        "text": "Major ocean regions include: Atlantic Ocean (temperature 2-28°C, salinity 33-37 PSU), Pacific Ocean (similar ranges), Indian Ocean (warmer surface waters), Southern Ocean (cold temperatures around 0-10°C), Arctic Ocean (very cold, low salinity).",
        "metadata": {"category": "geography", "priority": "medium"}
    },
    {
        "id": "seasonal_patterns",
        "text": "Ocean temperatures show strong seasonal cycles, especially in the mixed layer. Northern hemisphere oceans are warmest in summer (July-August), southern hemisphere in winter (January-February). Deep ocean temperatures show minimal seasonal variation.",
        "metadata": {"category": "temporal", "priority": "medium"}
    },
    {
        "id": "climate_patterns",
        "text": "El Niño events cause warmer temperatures in the eastern Pacific, La Niña causes cooler conditions. The Atlantic Meridional Overturning Circulation affects North Atlantic temperatures. Climate change is causing ocean warming at all depths.",
        "metadata": {"category": "climate", "priority": "medium"}
    }
]

# Initialize with ARGO knowledge base
def initialize_argo_knowledge():
    """Initialize the RAG system with ARGO-specific knowledge."""
    global _index
    if not _index:
        index_metadata(ARGO_KNOWLEDGE_BASE)

# Lightweight in-memory RAG store to avoid external dependencies during dev.
_index: List[Dict] = []  # each item: {id: str, text: str, metadata?: dict}

def index_metadata(docs: List[Dict]):
    """Upsert docs into an in-memory list by id.

    docs: list of {id, text, metadata?}
    """
    global _index
    existing = {str(d.get("id")): i for i, d in enumerate(_index)}
    for d in docs:
        doc_id = str(d.get("id"))
        if not doc_id:
            # skip invalid docs
            continue
        payload = {
            "id": doc_id,
            "text": d.get("text", ""),
            "metadata": d.get("metadata", {}),
        }
        if doc_id in existing:
            _index[existing[doc_id]] = payload
        else:
            _index.append(payload)

def retrieve(query: str, k: int = 5) -> List[Dict]:
    """Enhanced retrieval with ARGO-specific scoring."""
    q = (query or "").lower().strip()
    if not _index:
        # Initialize with ARGO knowledge if empty
        initialize_argo_knowledge()
        if not _index:
            return []

    if not q:
        return _index[:k]

    scored = []
    for d in _index:
        text = d.get("text", "").lower()
        score = 0.0
        metadata = d.get("metadata", {})

        # Keyword matching
        query_words = set(q.split())
        text_words = set(text.split())
        keyword_matches = len(query_words.intersection(text_words))
        score += keyword_matches * 10

        # Exact phrase matching
        if q in text:
            score += 20

        # ARGO-specific terms boost
        argo_terms = ['argo', 'float', 'temperature', 'salinity', 'depth', 'ocean', 'profile', 'psu', 'degc']
        for term in argo_terms:
            if term in q and term in text:
                score += 15

        # Parameter-specific queries
        if 'temperature' in q and metadata.get('parameter') == 'temperature':
            score += 25
        if 'salinity' in q and metadata.get('parameter') == 'salinity':
            score += 25

        # Category priority boost
        priority = metadata.get('priority', 'low')
        if priority == 'high':
            score += 10
        elif priority == 'medium':
            score += 5

        # Length normalization (prefer informative responses)
        text_length = len(text)
        score += min(text_length, 500) / 500.0 * 5

        scored.append((score, d))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:k]]

def summarize(query: str, contexts: List[Dict]) -> str:
    """Enhanced summarization with ARGO-specific insights."""
    if not contexts:
        return "I don't have specific information about that query in my knowledge base."

    # Check if this is an ARGO data question
    query_lower = query.lower()

    # Extract key terms for better response
    has_temperature = 'temperature' in query_lower or 'temp' in query_lower or '°c' in query_lower
    has_salinity = 'salinity' in query_lower or 'salt' in query_lower or 'psu' in query_lower
    has_depth = 'depth' in query_lower or 'm' in query_lower
    has_location = any(term in query_lower for term in ['lat', 'lon', 'equator', 'pacific', 'atlantic', 'indian', 'arctic'])

    # Generate contextual response
    if has_temperature and has_salinity and has_depth:
        return f"Based on ARGO float data, I can provide comprehensive analysis of temperature, salinity, and depth profiles. {contexts[0].get('text', '')}"
    elif has_temperature:
        return f"Temperature analysis from ARGO data: {contexts[0].get('text', '')}"
    elif has_salinity:
        return f"Salinity information from ARGO observations: {contexts[0].get('text', '')}"
    elif has_location:
        return f"Regional ocean data analysis: {contexts[0].get('text', '')}"

    # Default contextual response
    primary_context = contexts[0]
    text = primary_context.get("text", "").strip().replace("\n", " ")

    # Add ARGO context if relevant
    if any(term in query_lower for term in ['argo', 'float', 'ocean']):
        return f"From ARGO float data analysis: {text}"
    else:
        return text

def get_argo_contextual_suggestions(query: str) -> List[str]:
    """Generate contextual query suggestions based on ARGO data."""
    suggestions = []
    query_lower = query.lower()

    if 'temperature' in query_lower:
        suggestions.extend([
            "Show temperature profiles at different depths",
            "Compare temperature patterns across ocean basins",
            "Analyze seasonal temperature variations"
        ])

    if 'salinity' in query_lower:
        suggestions.extend([
            "Examine salinity distribution in major ocean currents",
            "Compare salinity between hemispheres",
            "Analyze freshwater influence on coastal salinity"
        ])

    if any(term in query_lower for term in ['equator', 'tropical']):
        suggestions.extend([
            "Compare equatorial vs polar temperature patterns",
            "Analyze thermocline structure in tropical regions",
            "Study seasonal cycles in equatorial regions"
        ])

    if 'deep' in query_lower or 'depth' in query_lower:
        suggestions.extend([
            "Analyze deep ocean temperature stability",
            "Compare surface vs deep ocean salinity",
            "Study depth-dependent ocean circulation patterns"
        ])

    return suggestions[:4]  # Return top 4 suggestions

# Initialize ARGO knowledge base on module load
initialize_argo_knowledge()
