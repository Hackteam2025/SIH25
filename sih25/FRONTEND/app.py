"""
FloatChat Frontend - Simplified Integration with Existing Services

This module implements a Plotly Dash frontend that connects directly to:
- sih25/AGENT/api.py (Agent API with integrated voice capabilities)
- sih25/API/main.py (MCP Tool Server for data retrieval)
- sih25/DATAOPS/main_orchestrator.py (Data processing)
"""

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
from datetime import datetime
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Dash app
app = dash.Dash(__name__)
app.title = "FloatChat - Oceanographic Data Explorer"

# Configuration for existing services
AGENT_API_URL = "http://localhost:8001"  # Agent with voice integration
MCP_API_URL = "http://localhost:8000"    # MCP Tool Server
DATAOPS_API_URL = "http://localhost:8002" # DataOps orchestrator

# Custom CSS styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }

            .main-container {
                min-height: 100vh;
                padding: 20px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
            }

            .header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 20px;
                border-radius: 15px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
            }

            .header h1 {
                margin: 0;
                font-size: 28px;
                font-weight: 600;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            }

            .reset-btn {
                background-color: darkred !important;
                color: white !important;
                border: none !important;
                border-radius: 8px !important;
                padding: 12px 24px !important;
                font-weight: bold !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 4px 15px rgba(139, 0, 0, 0.3) !important;
            }

            .reset-btn:hover {
                background-color: #8B0000 !important;
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(139, 0, 0, 0.4) !important;
            }

            .main-content {
                display: grid;
                grid-template-columns: 1fr 1.5fr;
                gap: 20px;
                min-height: calc(100vh - 200px);
            }

            .chat-panel {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.18);
                display: flex;
                flex-direction: column;
            }

            .viz-panel {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                padding: 25px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.18);
                overflow-y: auto;
            }

            .chat-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
                padding-bottom: 15px;
                border-bottom: 2px solid rgba(102, 126, 234, 0.2);
            }

            .chat-title {
                font-size: 20px;
                font-weight: 600;
                color: #1e3c72;
                margin: 0;
            }

            .voice-toggle {
                width: 55px;
                height: 55px;
                border-radius: 50%;
                border: none;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                font-size: 22px;
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
                position: relative;
            }

            .voice-toggle:hover {
                transform: scale(1.05);
                box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5);
            }

            .voice-toggle.active {
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
                animation: pulseVoice 1.5s infinite;
                box-shadow: 0 6px 25px rgba(255, 107, 107, 0.5);
            }

            .voice-toggle.active::after {
                content: "";
                position: absolute;
                top: -5px;
                left: -5px;
                right: -5px;
                bottom: -5px;
                border-radius: 50%;
                border: 2px solid rgba(255, 107, 107, 0.6);
                animation: pulseRing 1.5s infinite;
            }

            @keyframes pulseVoice {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }

            @keyframes pulseRing {
                0% { transform: scale(1); opacity: 1; }
                100% { transform: scale(1.3); opacity: 0; }
            }

            .chat-display {
                flex: 1;
                overflow-y: auto;
                margin-bottom: 20px;
                padding: 20px;
                border: 1px solid rgba(102, 126, 234, 0.2);
                border-radius: 12px;
                background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
                min-height: 400px;
                max-height: 500px;
            }

            .message {
                margin-bottom: 15px;
                padding: 15px;
                border-radius: 15px;
                max-width: 85%;
                word-wrap: break-word;
                animation: slideIn 0.3s ease-out;
            }

            @keyframes slideIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }

            .user-message {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                margin-left: auto;
                text-align: right;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }

            .agent-message {
                background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
                color: #374151;
                border: 1px solid rgba(102, 126, 234, 0.2);
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.1);
            }

            .voice-message {
                border-left: 4px solid #ff6b6b;
                background: linear-gradient(135deg, #fff5f5 0%, #fef2f2 100%);
            }

            .chat-input-area {
                display: flex;
                gap: 12px;
                align-items: center;
                padding: 15px;
                background: rgba(255, 255, 255, 0.7);
                border-radius: 12px;
                backdrop-filter: blur(10px);
            }

            .chat-input {
                flex: 1;
                padding: 15px 20px;
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 25px;
                outline: none;
                transition: all 0.3s ease;
                font-size: 14px;
                background: rgba(255, 255, 255, 0.9);
            }

            .chat-input:focus {
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
                background: rgba(255, 255, 255, 1);
            }

            .send-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 25px;
                padding: 15px 28px;
                cursor: pointer;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }

            .send-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }

            .status-indicator {
                margin-top: 10px;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 500;
            }

            .loading-indicator {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                color: #667eea;
                font-style: italic;
            }

            .spinner {
                width: 16px;
                height: 16px;
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-top: 2px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .viz-grid {
                display: grid;
                grid-template-columns: 1fr;
                gap: 20px;
            }

            .admin-panel {
                margin-top: 20px;
                background: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }

            .admin-summary {
                padding: 15px 20px;
                background: rgba(248, 250, 252, 0.8);
                border-radius: 15px 15px 0 0;
                border-bottom: 1px solid rgba(102, 126, 234, 0.2);
                font-weight: 600;
                color: #374151;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .admin-summary:hover {
                background: rgba(241, 245, 249, 0.9);
            }

            .admin-content {
                padding: 20px;
            }

            .upload-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }

            .upload-section {
                background: rgba(248, 250, 252, 0.7);
                border-radius: 12px;
                padding: 20px;
                border: 2px solid rgba(102, 126, 234, 0.2);
            }

            .upload-section h4 {
                margin: 0 0 15px 0;
                color: #1e3c72;
                font-size: 16px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .upload-section p {
                margin: 0 0 15px 0;
                font-size: 14px;
                color: #6b7280;
                line-height: 1.4;
            }

            .profile-section {
                border-color: rgba(34, 197, 94, 0.3);
                background: rgba(240, 253, 244, 0.7);
            }

            .metadata-section {
                border-color: rgba(147, 51, 234, 0.3);
                background: rgba(250, 245, 255, 0.7);
            }

            .profile-section h4 {
                color: #16a34a;
            }

            .metadata-section h4 {
                color: #7c3aed;
            }

            @media (max-width: 768px) {
                .main-content {
                    grid-template-columns: 1fr;
                    gap: 15px;
                }

                .chat-panel, .viz-panel {
                    min-height: 350px;
                }
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            {%app_entry%}
        </div>
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

def create_world_map():
    """Create interactive world map with ARGO float locations"""
    import numpy as np

    fig = go.Figure()

    try:
        # ✅ Fetch real data from MCP API
        response = requests.post(
            f"{MCP_API_URL}/tools/list_profiles",
            json={
                "min_lat": -90,
                "max_lat": 90,
                "min_lon": -180,
                "max_lon": 180,
                "max_results": 100
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            # Check if we got successful response with data
            if data.get("success") and data.get("data"):
                profiles = data["data"]

                lats = [p["latitude"] for p in profiles]
                lons = [p["longitude"] for p in profiles]
                float_ids = [p["profile_id"] for p in profiles]
                # Get average temperature from observations
                temps = [p.get("avg_temperature", 15.0) if p.get("avg_temperature") else 15.0 for p in profiles]
            else:
                logger.warning(f"MCP API returned empty data, using sample")
                return create_sample_map()
        else:
            logger.warning(f"MCP API returned {response.status_code}, using sample data")
            return create_sample_map()

    except Exception as e:
        logger.error(f"Failed to fetch profiles: {e}")
        return create_sample_map()

    # Limit arrays to same length
    min_len = min(len(lats), len(lons), len(float_ids), len(temps))
    lats, lons, float_ids, temps = lats[:min_len], lons[:min_len], float_ids[:min_len], temps[:min_len]

    fig.add_trace(go.Scattergeo(
        lat=lats,
        lon=lons,
        mode='markers',
        marker=dict(
            size=12,
            color=temps,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="Surface Temp (°C)", x=1.02),
            line=dict(width=1, color='white')
        ),
        text=[f"{fid}<br>Temp: {temp:.1f}°C" for fid, temp in zip(float_ids, temps)],
        hovertemplate='<b>%{text}</b><br>Lat: %{lat:.2f}<br>Lon: %{lon:.2f}<extra></extra>',
        name="ARGO Floats"
    ))

    fig.update_layout(
        title={
            'text': f"🌍 Real-Time ARGO Float Network ({len(lats)} floats)",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#1e3c72'}
        },
        geo=dict(
            projection_type='natural earth',
            showland=True,
            landcolor='lightgray',
            showocean=True,
            oceancolor='lightblue',
            showlakes=True,
            lakecolor='lightblue',
            showcoastlines=True,
            coastlinecolor="RebeccaPurple"
        ),
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_profile_plot():
    """Create temperature-salinity depth profile"""
    import numpy as np

    depths = np.arange(0, 2000, 25)
    temperatures = 25 * np.exp(-depths/1000) + 2 + np.random.normal(0, 0.3, len(depths))
    salinities = 34 + 1.5 * np.exp(-depths/800) + np.random.normal(0, 0.1, len(depths))

    fig = go.Figure()

    # Temperature profile
    fig.add_trace(go.Scatter(
        x=temperatures,
        y=depths,
        mode='lines+markers',
        name='Temperature',
        line=dict(color='#ff6b6b', width=3),
        marker=dict(size=6, color='#ff6b6b'),
        hovertemplate='Depth: %{y}m<br>Temperature: %{x:.2f}°C<extra></extra>'
    ))

    # Salinity profile (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=salinities,
        y=depths,
        mode='lines+markers',
        name='Salinity',
        line=dict(color='#4ecdc4', width=3),
        marker=dict(size=6, color='#4ecdc4'),
        xaxis='x2',
        hovertemplate='Depth: %{y}m<br>Salinity: %{x:.2f} PSU<extra></extra>'
    ))

    fig.update_layout(
        title={
            'text': "🌡️ Ocean Depth Profiles",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#1e3c72'}
        },
        xaxis=dict(title="Temperature (°C)", side="bottom", color='#ff6b6b'),
        xaxis2=dict(title="Salinity (PSU)", side="top", overlaying="x", color='#4ecdc4'),
        yaxis=dict(title="Depth (m)", autorange='reversed'),
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(x=0.7, y=0.9)
    )

    return fig

def create_timeseries_plot():
    """Create time series of oceanographic parameters"""
    import pandas as pd
    import numpy as np

    dates = pd.date_range('2023-01-01', periods=90, freq='D')
    sst = 26 + 3 * np.sin(2 * np.pi * np.arange(90) / 365) + np.random.normal(0, 0.5, 90)
    chlorophyll = 0.5 + 0.3 * np.sin(2 * np.pi * np.arange(90) / 365 + np.pi/4) + np.random.normal(0, 0.05, 90)

    fig = go.Figure()

    # SST time series
    fig.add_trace(go.Scatter(
        x=dates,
        y=sst,
        mode='lines+markers',
        name='Sea Surface Temperature',
        line=dict(color='#ff6b6b', width=2),
        marker=dict(size=4),
        yaxis='y',
        hovertemplate='Date: %{x}<br>SST: %{y:.2f}°C<extra></extra>'
    ))

    # Chlorophyll time series (secondary y-axis)
    fig.add_trace(go.Scatter(
        x=dates,
        y=chlorophyll,
        mode='lines+markers',
        name='Chlorophyll-a',
        line=dict(color='#4ecdc4', width=2),
        marker=dict(size=4),
        yaxis='y2',
        hovertemplate='Date: %{x}<br>Chl-a: %{y:.3f} mg/m³<extra></extra>'
    ))

    fig.update_layout(
        title={
            'text': "📈 Oceanographic Time Series",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16, 'color': '#1e3c72'}
        },
        xaxis=dict(title="Date"),
        yaxis=dict(title="SST (°C)", side="left", color='#ff6b6b'),
        yaxis2=dict(title="Chlorophyll-a (mg/m³)", side="right", overlaying="y", color='#4ecdc4'),
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(x=0.02, y=0.98)
    )

    return fig

# App layout
app.layout = html.Div([
    # Stores for state management
    dcc.Store(id="conversation-history", data=[]),
    dcc.Store(id="voice-session-state", data={"active": False, "session_id": None}),
    dcc.Store(id="user-session", data={"session_id": str(uuid.uuid4())}),

    # Header
    html.Div([
        html.H1("🌊 FloatChat - Oceanographic Data Explorer"),
        html.Button(
            "RESET DATABASE",
            id="reset-btn",
            className="reset-btn",
            n_clicks=0
        )
    ], className="header"),

    # Main content
    html.Div([
        # Left panel: Chat interface
        html.Div([
            # Chat header with voice toggle
            html.Div([
                html.H3("🤖 AI Oceanographer", className="chat-title"),
                html.Button(
                    "🎤",
                    id="voice-toggle-btn",
                    className="voice-toggle",
                    n_clicks=0,
                    title="Toggle Voice Mode (Integrated AGNO Voice AI)"
                )
            ], className="chat-header"),

            # Chat display area
            html.Div(
                id="chat-display",
                children=[
                    html.Div("Welcome to FloatChat! 🌊", className="message agent-message"),
                    html.Div("I'm your AI oceanographer with integrated voice capabilities. Ask me about ARGO float data, ocean measurements, or request visualizations!", className="message agent-message")
                ],
                className="chat-display"
            ),

            # Chat input area
            html.Div([
                dcc.Input(
                    id="chat-input",
                    type="text",
                    placeholder="Ask about oceanographic data, float locations, temperature profiles...",
                    className="chat-input",
                    n_submit=0,
                    value=""
                ),
                html.Button(
                    "Send 🚀",
                    id="send-btn",
                    className="send-btn",
                    n_clicks=0
                )
            ], className="chat-input-area"),

            # Status indicators
            html.Div(id="status-display", className="status-indicator")

        ], className="chat-panel"),

        # Right panel: Visualizations
        html.Div([
            html.H3("📊 Interactive Oceanographic Visualizations",
                   style={"margin-bottom": "20px", "color": "#1e3c72", "text-align": "center"}),

            html.Div([
                # Interactive world map
                dcc.Graph(
                    id="map-plot",
                    figure=create_world_map(),
                    style={"height": "450px", "margin-bottom": "20px"}
                ),

                # Profile plots
                dcc.Graph(
                    id="profile-plot",
                    figure=create_profile_plot(),
                    style={"height": "350px", "margin-bottom": "20px"}
                ),

                # Time series
                dcc.Graph(
                    id="timeseries-plot",
                    figure=create_timeseries_plot(),
                    style={"height": "350px"}
                )
            ], className="viz-grid")

        ], className="viz-panel")

    ], className="main-content"),

    # Admin panel
    html.Details([
        html.Summary("🔧 Data Administration & File Processing", className="admin-summary"),
        html.Div([
            # Upload grid with vertical split
            html.Div([
                # Left side: Profile Data Upload
                html.Div([
                    html.H4([
                        "🌊 Profile Data Upload",
                        html.Span(" (NetCDF)", style={"font-size": "12px", "color": "#6b7280"})
                    ]),
                    html.P("Upload NetCDF files containing ARGO profile data for database storage and analysis."),
                    dcc.Upload(
                        id="profile-file-upload",
                        children=html.Div([
                            "🗂️ Drop NetCDF Files or ",
                            html.A("Click to Select", style={"color": "#16a34a", "font-weight": "bold"})
                        ]),
                        style={
                            "width": "100%",
                            "height": "80px",
                            "lineHeight": "80px",
                            "borderWidth": "2px",
                            "borderStyle": "dashed",
                            "borderColor": "rgba(34, 197, 94, 0.4)",
                            "borderRadius": "8px",
                            "textAlign": "center",
                            "margin": "10px 0",
                            "background": "rgba(240, 253, 244, 0.8)",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease"
                        },
                        multiple=True
                    ),
                    html.Button(
                        "🚀 Process Profile Data",
                        id="process-profile-btn",
                        style={
                            "background": "linear-gradient(135deg, #16a34a 0%, #22c55e 100%)",
                            "color": "white",
                            "border": "none",
                            "padding": "10px 20px",
                            "border-radius": "6px",
                            "cursor": "pointer",
                            "font-weight": "600",
                            "width": "100%",
                            "box-shadow": "0 4px 15px rgba(34, 197, 94, 0.3)"
                        },
                        n_clicks=0
                    ),
                    html.Div(id="profile-processing-status", style={"margin-top": "10px"})
                ], className="upload-section profile-section"),

                # Right side: Metadata Upload
                html.Div([
                    html.H4([
                        "🔍 Metadata Upload",
                        html.Span(" (JSON/CSV)", style={"font-size": "12px", "color": "#6b7280"})
                    ]),
                    html.P("Upload metadata files for semantic search and AI-powered discovery via vector embeddings."),
                    dcc.Upload(
                        id="metadata-file-upload",
                        children=html.Div([
                            "📋 Drop Metadata Files or ",
                            html.A("Click to Select", style={"color": "#7c3aed", "font-weight": "bold"})
                        ]),
                        style={
                            "width": "100%",
                            "height": "80px",
                            "lineHeight": "80px",
                            "borderWidth": "2px",
                            "borderStyle": "dashed",
                            "borderColor": "rgba(147, 51, 234, 0.4)",
                            "borderRadius": "8px",
                            "textAlign": "center",
                            "margin": "10px 0",
                            "background": "rgba(250, 245, 255, 0.8)",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease"
                        },
                        multiple=True
                    ),
                    html.Button(
                        "🧠 Process Metadata",
                        id="process-metadata-btn",
                        style={
                            "background": "linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)",
                            "color": "white",
                            "border": "none",
                            "padding": "10px 20px",
                            "border-radius": "6px",
                            "cursor": "pointer",
                            "font-weight": "600",
                            "width": "100%",
                            "box-shadow": "0 4px 15px rgba(147, 51, 234, 0.3)"
                        },
                        n_clicks=0
                    ),
                    html.Button(
                        "✨ Create Sample Data",
                        id="create-sample-btn",
                        style={
                            "background": "linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)",
                            "color": "white",
                            "border": "none",
                            "padding": "8px 16px",
                            "border-radius": "6px",
                            "cursor": "pointer",
                            "font-weight": "500",
                            "width": "100%",
                            "margin-top": "8px",
                            "font-size": "14px",
                            "box-shadow": "0 2px 10px rgba(245, 158, 11, 0.3)"
                        },
                        n_clicks=0,
                        title="Generate sample metadata for testing vector search"
                    ),
                    html.Div(id="metadata-processing-status", style={"margin-top": "10px"})
                ], className="upload-section metadata-section"),

            ], className="upload-grid"),

            # Statistics and status
            html.Div([
                html.Div(id="system-status-display", style={"margin-top": "15px"}),
                html.Button(
                    "📊 Show Vector DB Stats",
                    id="show-stats-btn",
                    style={
                        "background": "linear-gradient(135deg, #6b7280 0%, #9ca3af 100%)",
                        "color": "white",
                        "border": "none",
                        "padding": "8px 16px",
                        "border-radius": "6px",
                        "cursor": "pointer",
                        "font-weight": "500",
                        "margin-top": "10px",
                        "box-shadow": "0 2px 10px rgba(107, 114, 128, 0.3)"
                    },
                    n_clicks=0
                )
            ])
        ], className="admin-content")
    ], className="admin-panel"),

    # Interval for status updates
    dcc.Interval(
        id="status-interval",
        interval=3000,  # Update every 3 seconds
        n_intervals=0
    )
])

# Voice toggle callback - connects to existing AGNO voice system
@app.callback(
    [Output("voice-toggle-btn", "className"),
     Output("status-display", "children"),
     Output("voice-session-state", "data")],
    [Input("voice-toggle-btn", "n_clicks")],
    [State("voice-session-state", "data"),
     State("user-session", "data")]
)
def toggle_voice_mode(n_clicks, voice_state, user_session):
    if n_clicks == 0:
        return "voice-toggle", "", {"active": False, "session_id": None}

    session_id = user_session["session_id"]
    current_active = voice_state.get("active", False)

    if not current_active:
        # Start voice session with existing AGNO voice handler
        try:
            response = requests.post(
                f"{AGENT_API_URL}/voice/start",
                json={"session_id": session_id},
                timeout=5
            )

            if response.status_code == 200:
                status_msg = html.Div([
                    html.Span("🔴 ", style={"color": "#ff6b6b"}),
                    "Voice AI Active - AGNO listening... Speak naturally!"
                ], style={"color": "#ff6b6b", "font-weight": "bold", "background": "rgba(255, 107, 107, 0.1)", "padding": "8px", "border-radius": "6px"})

                return "voice-toggle active", status_msg, {"active": True, "session_id": session_id}
            else:
                status_msg = html.Div([
                    html.Span("⚠️ ", style={"color": "#f59e0b"}),
                    "Voice service unavailable - using text mode"
                ], style={"color": "#f59e0b", "background": "rgba(245, 158, 11, 0.1)", "padding": "8px", "border-radius": "6px"})

                return "voice-toggle", status_msg, {"active": False, "session_id": None}

        except requests.exceptions.RequestException:
            status_msg = html.Div([
                html.Span("⚠️ ", style={"color": "#f59e0b"}),
                "Voice service offline - using text mode"
            ], style={"color": "#f59e0b", "background": "rgba(245, 158, 11, 0.1)", "padding": "8px", "border-radius": "6px"})

            return "voice-toggle", status_msg, {"active": False, "session_id": None}
    else:
        # Stop voice session
        try:
            requests.post(
                f"{AGENT_API_URL}/voice/stop",
                json={"session_id": session_id},
                timeout=5
            )
        except:
            pass

        status_msg = html.Div([
            html.Span("⚫ ", style={"color": "#6b7280"}),
            "Voice mode inactive - using text input"
        ], style={"color": "#6b7280", "background": "rgba(107, 114, 128, 0.1)", "padding": "8px", "border-radius": "6px"})

        return "voice-toggle", status_msg, {"active": False, "session_id": None}

# Chat functionality - connects to existing Agent API
@app.callback(
    [Output("chat-display", "children"),
     Output("chat-input", "value"),
     Output("conversation-history", "data")],
    [Input("send-btn", "n_clicks"),
     Input("chat-input", "n_submit")],
    [State("chat-input", "value"),
     State("conversation-history", "data"),
     State("chat-display", "children"),
     State("user-session", "data")]
)
def handle_chat_message(send_clicks, input_submit, message, conversation_history, current_display, user_session):
    if not message or message.strip() == "":
        return no_update, no_update, no_update

    session_id = user_session["session_id"]

    # Add user message
    user_message = html.Div(message, className="message user-message")

    # Show loading indicator
    loading_message = html.Div([
        html.Div(className="spinner"),
        " Consulting AGNO AI Oceanographer..."
    ], className="message agent-message loading-indicator")

    # Update display with user message and loading
    temp_display = current_display + [user_message, loading_message]

    try:
        # Call existing Agent API
        response = requests.post(
            f"{AGENT_API_URL}/agent/chat",
            json={
                "message": message,
                "session_id": session_id,
                "context": {"interface": "dashboard"}
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            ai_response = result.get("response", "I apologize, but I couldn't process your request.")

            # Check if this was a voice-processed message
            is_voice = result.get("metadata", {}).get("voice_processed", False)
            message_class = "message agent-message voice-message" if is_voice else "message agent-message"

            # Add scientific insights if available
            insights = result.get("scientific_insights", [])
            if insights:
                ai_response += "\n\n🔬 Scientific Context:\n" + "\n".join([f"• {insight}" for insight in insights])

            # Add follow-up suggestions
            suggestions = result.get("follow_up_suggestions", [])
            if suggestions:
                ai_response += "\n\n💡 You might also ask:\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])

        else:
            ai_response = "I'm having trouble connecting to my AI systems. Please try again in a moment."
            message_class = "message agent-message"

    except requests.exceptions.RequestException:
        ai_response = "🤖 I'm currently offline, but I can still help with basic oceanographic questions! Try asking about ARGO floats, temperature profiles, or ocean regions."
        message_class = "message agent-message"

    agent_message = html.Div(ai_response, className=message_class)

    # Update conversation history
    conversation_history.append({
        "user": message,
        "agent": ai_response,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    })

    # Final display update
    updated_display = current_display + [user_message, agent_message]

    return updated_display, "", conversation_history

# Reset database callback
@app.callback(
    Output("reset-btn", "n_clicks"),
    [Input("reset-btn", "n_clicks")]
)
def handle_reset(n_clicks):
    if n_clicks > 0:
        try:
            # Call existing database reset endpoint
            response = requests.post(f"{MCP_API_URL}/admin/reset", timeout=10)
            logger.info(f"Database reset attempted: {response.status_code}")
        except:
            logger.warning("Database reset failed - service unavailable")
    return 0

# File processing - connects to existing DataOps orchestrator for profiles
@app.callback(
    Output("profile-processing-status", "children"),
    [Input("process-profile-btn", "n_clicks")],
    [State("profile-file-upload", "contents"),
     State("profile-file-upload", "filename")]
)
def handle_profile_processing(process_clicks, file_contents, filenames):
    if process_clicks > 0 and file_contents:
        try:
            # Create a dictionary of filename: content
            files_to_process = {name: content for name, content in zip(filenames, file_contents)}

            # Process NetCDF files using existing DataOps orchestrator
            response = requests.post(
                f"{DATAOPS_API_URL}/process",
                json={"files": files_to_process},
                timeout=60  # Increased timeout for file processing
            )

            if response.status_code == 200:
                return html.Div([
                    "✅ Profile data processed successfully! Data is now available for analysis.",
                ], style={"color": "#10b981", "font-weight": "bold", "font-size": "14px"})
            else:
                error_detail = response.json().get("detail", "Unknown error")
                return html.Div([
                    f"⚠️ Profile processing failed: {error_detail}",
                ], style={"color": "#f59e0b", "font-weight": "bold", "font-size": "14px"})

        except requests.exceptions.RequestException:
            return html.Div([
                "📡 DataOps service is starting up or unavailable. Please try again in a moment.",
            ], style={"color": "#6b7280", "font-weight": "bold", "font-size": "14px"})

    return html.Div("Ready to process NetCDF profile files",
                   style={"color": "#6b7280", "font-size": "14px"})


# Metadata processing - connects to new vector database system
@app.callback(
    Output("metadata-processing-status", "children"),
    [Input("process-metadata-btn", "n_clicks")],
    [State("metadata-file-upload", "contents"),
     State("metadata-file-upload", "filename")]
)
def handle_metadata_processing(process_clicks, file_contents, filenames):
    if process_clicks > 0 and file_contents and filenames:
        try:
            # Process metadata files using new vector database system
            # For demo, simulate file processing (in real implementation, would save and process files)
            response = requests.post(
                f"{MCP_API_URL}/metadata/upload",
                json={
                    "file_path": "/tmp/metadata_file",
                    "filename": filenames[0] if filenames else "metadata.json"
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return html.Div([
                    f"✅ Metadata processed! {data.get('processed_count', 0)} entries added to vector database.",
                    html.Br(),
                    html.Small(f"File: {data.get('file_info', {}).get('filename', 'N/A')}",
                              style={"color": "#6b7280"})
                ], style={"color": "#7c3aed", "font-weight": "bold", "font-size": "14px"})
            else:
                return html.Div([
                    "⚠️ Metadata processing failed. Please check file format (JSON/CSV supported).",
                ], style={"color": "#f59e0b", "font-weight": "bold", "font-size": "14px"})

        except requests.exceptions.RequestException:
            return html.Div([
                "📡 Vector database service is starting up. Please try again in a moment.",
            ], style={"color": "#6b7280", "font-weight": "bold", "font-size": "14px"})

    return html.Div("Ready to process metadata files (JSON, CSV, JSONL)",
                   style={"color": "#6b7280", "font-size": "14px"})


# Create sample metadata for testing
@app.callback(
    Output("metadata-processing-status", "children", allow_duplicate=True),
    [Input("create-sample-btn", "n_clicks")],
    prevent_initial_call=True
)
def create_sample_metadata(n_clicks):
    if n_clicks > 0:
        try:
            # Create sample metadata using the API
            response = requests.post(
                f"{MCP_API_URL}/metadata/create_sample",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return html.Div([
                    f"✨ Created {data.get('profiles_created', 0)} sample metadata entries!",
                    html.Br(),
                    html.Small("Sample data includes Indian Ocean profiles with various parameters.",
                              style={"color": "#6b7280"})
                ], style={"color": "#f59e0b", "font-weight": "bold", "font-size": "14px"})
            else:
                return html.Div([
                    "⚠️ Failed to create sample data. Vector database may not be available.",
                ], style={"color": "#dc2626", "font-weight": "bold", "font-size": "14px"})

        except requests.exceptions.RequestException:
            return html.Div([
                "📡 Vector database service unavailable. Please try again later.",
            ], style={"color": "#6b7280", "font-weight": "bold", "font-size": "14px"})

    return no_update


# Show vector database statistics
@app.callback(
    Output("system-status-display", "children"),
    [Input("show-stats-btn", "n_clicks")]
)
def show_vector_stats(n_clicks):
    if n_clicks > 0:
        try:
            # Get vector database statistics
            response = requests.get(f"{MCP_API_URL}/metadata/stats", timeout=10)

            if response.status_code == 200:
                stats = response.json()

                status_color = "#10b981" if stats.get("status") == "active" else "#f59e0b"

                return html.Div([
                    html.H5("📊 Vector Database Statistics", style={"margin": "10px 0 5px 0", "color": "#374151"}),
                    html.Div([
                        html.Strong("Status: "),
                        html.Span(stats.get("status", "unknown").title(),
                                 style={"color": status_color, "font-weight": "bold"})
                    ], style={"margin": "5px 0"}),
                    html.Div([
                        html.Strong("Total Embeddings: "),
                        html.Span(str(stats.get("total_embeddings", 0)),
                                 style={"color": "#6b7280"})
                    ], style={"margin": "5px 0"}),
                    html.Div([
                        html.Strong("Embedding Model: "),
                        html.Span(stats.get("embedding_model", "unknown"),
                                 style={"color": "#6b7280"})
                    ], style={"margin": "5px 0"}),
                    html.Div([
                        html.Strong("Last Updated: "),
                        html.Span(stats.get("last_updated", "unknown")[:19] if stats.get("last_updated") else "unknown",
                                 style={"color": "#6b7280", "font-size": "12px"})
                    ], style={"margin": "5px 0"})
                ], style={
                    "background": "rgba(243, 244, 246, 0.8)",
                    "border-radius": "8px",
                    "padding": "15px",
                    "margin": "10px 0",
                    "border-left": f"4px solid {status_color}"
                })
            else:
                return html.Div([
                    "⚠️ Unable to retrieve vector database statistics.",
                ], style={"color": "#f59e0b", "font-weight": "bold", "margin": "10px 0"})

        except requests.exceptions.RequestException:
            return html.Div([
                "📡 Vector database service unavailable.",
            ], style={"color": "#6b7280", "font-weight": "bold", "margin": "10px 0"})

    return ""


if __name__ == "__main__":
    logger.info("Starting FloatChat Frontend...")
    logger.info(f"Agent API: {AGENT_API_URL}")
    logger.info(f"MCP API: {MCP_API_URL}")
    logger.info(f"DataOps API: {DATAOPS_API_URL}")

    app.run(debug=True, host="0.0.0.0", port=8050)