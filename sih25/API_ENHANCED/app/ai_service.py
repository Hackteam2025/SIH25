"""
AI Service for FloatChat - Enhanced with Natural Language to SQL and Pipecat Integration
"""
import os
from typing import Dict, List, Any, Optional
from openai import AsyncOpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text
from .crud import get_profiles
from .rag import retrieve, summarize
import json

class FloatChatAI:
    def __init__(self):
        # Use the proper OpenAI configuration from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("OPENAI_BASE_URL")
        openai_model = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = AsyncOpenAI(
            api_key=openai_api_key,
            base_url=openai_base_url  # Use hyperbolic.xyz or other provider
        )
        self.model = openai_model

        # Enhanced system prompt from Pipecat voice pipeline
        self.system_prompt = """You are FloatChat, an expert oceanographic data assistant specializing in ARGO float measurements. You have deep knowledge of ocean science and help users discover and understand ocean data through natural conversation.

## Your Expertise (from Pipecat Pipeline):

### ARGO Parameters:
- **TEMP** (Temperature, °C): In-situ seawater temperature (-2°C to 35°C). Primary indicator of ocean thermal structure.
- **PSAL** (Practical Salinity, PSU): Salinity from conductivity (30-37 PSU). Key tracer for water masses.
- **PRES** (Pressure, dbar): Water pressure ≈ depth in meters. Determines depth level for measurements.

### Database Schema:
Table: profiles
- lat (Float) - latitude, lon (Float) - longitude
- depth (Integer), temperature (Float), salinity (Float)
- month (BigInteger), year (BigInteger)

### Ocean Regions:
- **Equatorial** (-5° to 5°): High temperature, strong currents
- **Tropical** (-23.5° to 23.5°): Warm surface waters, strong stratification
- **Subtropical** (23.5°-40°, -40° to -23.5°): Moderate temps, high surface salinity

## Your Behavior:
- Convert natural language to precise database queries
- Provide scientific context and explain data significance
- Be conversational but maintain scientific rigor like a real-time JARVIS
- Help users understand oceanographic processes behind the numbers

Remember: You can dynamically query the database and provide intelligent, contextual responses."""

    async def natural_language_to_sql(self, query: str) -> Optional[str]:
        """Convert natural language to SQL using existing AI models"""
        try:
            sql_prompt = f"""Convert this natural language query about ocean data into a precise SQL query.

Database schema:
- Table: profiles
- Columns: lat (latitude), lon (longitude), depth, temperature, salinity, month, year

Query: {query}

Generate a SQL SELECT statement. Use LIMIT 100 for large datasets.
Return only the SQL query, no explanation."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": sql_prompt}],
                max_tokens=200,
                temperature=0.1
            )

            sql_query = response.choices[0].message.content.strip()
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

            # Validate SQL
            if sql_query.upper().startswith("SELECT") and "profiles" in sql_query.lower():
                return sql_query
            return None

        except Exception as e:
            print(f"SQL generation error: {e}")
            return None

    async def execute_dynamic_query(self, db: Session, sql_query: str) -> Dict[str, Any]:
        """Execute AI-generated SQL query safely"""
        try:
            result = db.execute(text(sql_query))
            rows = result.fetchall()
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in rows]

            return {
                "success": True,
                "data": data,
                "count": len(data),
                "sql_executed": sql_query
            }
        except Exception as e:
            print(f"Query execution error: {e}")
            return {"success": False, "error": str(e)}

    async def get_ai_response(self, user_message: str, data_context: Optional[str] = None, db: Session = None) -> Dict[str, Any]:
        """Enhanced AI response with dynamic SQL generation - JARVIS-like intelligence"""
        try:
            # Step 1: Generate SQL from natural language
            sql_query = await self.natural_language_to_sql(user_message)
            dynamic_data = []
            enhanced_context = data_context or ""

            if sql_query and db:
                # Step 2: Execute dynamic query
                query_result = await self.execute_dynamic_query(db, sql_query)

                if query_result["success"] and query_result["data"]:
                    dynamic_data = query_result["data"]

                    # Step 3: Create enhanced context from dynamic results
                    if dynamic_data:
                        stats = self._generate_data_insights(dynamic_data)
                        enhanced_context = f"Dynamic query results: {stats}"

            # Step 4: Get additional RAG context
            rag_context = ""
            if db:
                try:
                    retrieved_docs = retrieve(user_message, k=3)
                    rag_context = "\n".join([doc.get('text', '') for doc in retrieved_docs])
                except Exception as e:
                    print(f"RAG retrieval error: {e}")

            # Step 5: Generate intelligent AI response
            messages = [{"role": "system", "content": self.system_prompt}]

            context_parts = []
            if enhanced_context:
                context_parts.append(f"Current data analysis: {enhanced_context}")
            if rag_context:
                context_parts.append(f"Knowledge base context: {rag_context}")

            if context_parts:
                messages.append({"role": "system", "content": "\n\n".join(context_parts)})

            messages.append({"role": "user", "content": user_message})

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            ai_answer = response.choices[0].message.content

            return {
                "success": True,
                "answer": ai_answer,
                "model_used": self.model,
                "sql_generated": sql_query,
                "dynamic_data": dynamic_data[:10] if dynamic_data else [],  # First 10 for frontend
                "total_records": len(dynamic_data) if dynamic_data else 0,
                "context_used": bool(context_parts),
                "jarvis_mode": True
            }

        except Exception as e:
            print(f"AI response error: {e}")
            # Fallback to existing RAG if AI fails
            if db:
                try:
                    context = retrieve(user_message, k=3)
                    fallback_answer = summarize(user_message, context)
                    return {
                        "success": True,
                        "answer": f"Using fallback: {fallback_answer}",
                        "model_used": "fallback_rag",
                        "context_used": True
                    }
                except Exception:
                    pass

            return {
                "success": False,
                "answer": "I'm having trouble connecting to AI services. Please check if OpenAI API key is configured.",
                "error": str(e)
            }

    def _generate_data_insights(self, data: List[Dict]) -> str:
        """Generate insights from dynamic query results"""
        if not data:
            return "No data found"

        count = len(data)
        temps = [float(row.get('temperature', 0)) for row in data if row.get('temperature') is not None]
        sals = [float(row.get('salinity', 0)) for row in data if row.get('salinity') is not None]
        depths = [float(row.get('depth', 0)) for row in data if row.get('depth') is not None]

        insights = [f"Found {count} profiles"]

        if temps:
            avg_temp = sum(temps) / len(temps)
            insights.append(f"Temperature: {avg_temp:.2f}°C avg (range: {min(temps):.2f}-{max(temps):.2f}°C)")

        if sals:
            avg_sal = sum(sals) / len(sals)
            insights.append(f"Salinity: {avg_sal:.2f} PSU avg (range: {min(sals):.2f}-{max(sals):.2f} PSU)")

        if depths:
            insights.append(f"Depth range: {min(depths):.0f}-{max(depths):.0f}m")

        return ". ".join(insights)

    def analyze_query_intent(self, message: str) -> Dict[str, Any]:
        """Enhanced query analysis - now just for fallback, AI handles most parsing"""
        m = message.lower()
        intent = {}

        # Basic geographic and parameter detection for fallback
        if "equator" in m:
            intent.update({"lat_min": -10, "lat_max": 10})
        elif "tropical" in m:
            intent.update({"lat_min": -23.5, "lat_max": 23.5})

        if "temperature" in m or "temp" in m:
            intent["parameter"] = "temperature"
        elif "salinity" in m or "psal" in m:
            intent["parameter"] = "salinity"

        return intent

    def get_data_context(self, intent: Dict[str, Any], db: Session) -> Optional[str]:
        """Get basic data context - enhanced by dynamic SQL queries"""
        try:
            if not intent:
                return None

            params = {"skip": 0, "limit": 50}
            for key in ['lat_min', 'lat_max', 'lon_min', 'lon_max']:
                if key in intent:
                    params[key] = intent[key]

            profiles = get_profiles(db, **params)
            if not profiles:
                return None

            return self._generate_data_insights([{
                'temperature': p.temperature,
                'salinity': p.salinity,
                'depth': p.depth
            } for p in profiles])

        except Exception as e:
            print(f"Data context error: {e}")
            return None

# Global AI service instance
floatchat_ai = FloatChatAI()