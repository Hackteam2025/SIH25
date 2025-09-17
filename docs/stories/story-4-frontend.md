# Story: Frontend Dashboard with Plotly Dash

<!-- Source: Brownfield PRD + Architecture documents -->
<!-- Context: Brownfield enhancement - Interactive visualization dashboard -->

## Status: Draft

## Story

As a **user interacting with oceanographic data**,
I want **an intuitive dashboard with chat interface and interactive visualizations**,
so that **I can explore ARGO data through conversation and see results as maps and plots**.

## Context Source

- Source Document: docs/prd.md + docs/architecture.md
- Enhancement Type: Web-based user interface with chat and visualization
- Existing System Impact: Integrates with AI Agent and MCP Tool Server

## Acceptance Criteria

1. **New functionality works as specified**:
   - Two-column Plotly Dash interface (chat + visualizations)
   - Interactive maps showing float trajectories and measurement locations
   - Dynamic depth-profile plots for temperature, salinity, BGC parameters
   - Real-time chat interface with AI Agent integration
   - Data Admin UI for file upload and processing triggers

2. **Integration with AI system**:
   - Chat messages sent to AI Agent and responses displayed in real-time
   - Agent responses trigger appropriate visualizations automatically
   - Visualization data requested from MCP Tool Server REST endpoints
   - Loading states and error handling for async operations

3. **Visualization requirements (from PRD FR-VI)**:
   - Interactive maps with float locations and trajectories
   - Depth profile plots with proper scientific labeling and units
   - Time-series visualizations for temporal analysis
   - Data quality indicators visible in all plots
   - Export capability for visualizations as PNG files

4. **User experience requirements**:
   - Time to first insight < 30 seconds for new users (PRD success metric)
   - Responsive design that works on desktop browsers
   - RESET button (dark red, white text, 3px rounded) for clearing database

## Dev Technical Guidance

### Existing System Context

**Integration Points:**
- AI Agent API for chat functionality (Story 3)
- MCP Tool Server REST endpoints for visualization data (Story 2)
- DATAOPS file upload triggering through orchestrator API

**Technology Alignment:**
- Python 3.11 with existing uv environment
- Plotly Dash for interactive web dashboard
- Integration with async FastAPI backend services

**Required UI Components (from PRD FR-DS-07, Section 5.2):**
- File upload interface in Data Admin section
- Chat interface with text input and message history
- Interactive maps using Plotly geo components
- Scientific plotting with proper axis labels and units
- Processing status indicators and error displays

### Integration Approach

**Dashboard Layout:**
```python
# Two-column layout structure
app.layout = html.Div([
    # Header with RESET button
    html.Div([
        html.H1("FloatChat - Oceanographic Data Explorer"),
        html.Button("RESET", id="reset-btn",
                   style={'background': 'darkred', 'color': 'white', 'border-radius': '3px'})
    ]),

    # Main content: two columns
    html.Div([
        # Left column: Chat interface
        html.Div([
            dcc.Store(id="conversation-history"),
            html.Div(id="chat-display"),
            dcc.Input(id="chat-input", type="text", placeholder="Ask about ocean data..."),
            html.Button("Send", id="send-btn")
        ], className="chat-column"),

        # Right column: Visualizations
        html.Div([
            dcc.Graph(id="map-plot"),
            dcc.Graph(id="profile-plot"),
            dcc.Graph(id="timeseries-plot")
        ], className="viz-column")
    ], className="main-content"),

    # Admin panel (collapsible)
    html.Details([
        html.Summary("Data Administration"),
        dcc.Upload(id="file-upload"),
        html.Button("Process Data", id="process-btn"),
        html.Div(id="processing-status")
    ])
])
```

**Callback Architecture:**
- Chat input → AI Agent API → Response display + Visualization update
- File upload → DATAOPS trigger → Processing status updates
- Map interactions → Profile plot updates
- RESET button → Database clearing confirmation dialog

### Technical Constraints

- **Real-time Updates**: Use Dash callbacks with intervals for processing status
- **Scientific Accuracy**: All plots must include proper units and quality indicators
- **Performance**: Visualizations must render within reasonable time for demo
- **Error Handling**: Graceful failures when backend services unavailable
- **Responsive Design**: Must work on various screen sizes

### Missing Information

❗ **User Input Needed:**
1. **Styling Preferences**: Do you want specific colors/themes for the oceanographic dashboard?
2. **Map Tiles**: Should maps use OpenStreetMap, satellite imagery, or oceanographic base maps?
3. **Voice Integration**: Should this story include Pipecat voice interface setup?
4. **Authentication**: Is user login required or open access during development?

## Tasks / Subtasks

- [ ] **Task 1: Set up Plotly Dash application structure**
  - [ ] Create `sih25/FRONTEND/` directory with Dash application
  - [ ] Implement basic two-column layout with chat and visualization areas
  - [ ] Add responsive CSS styling for desktop browsers
  - [ ] Configure Dash server to integrate with existing uv environment

- [ ] **Task 2: Implement chat interface**
  - [ ] Create chat input component with message history display
  - [ ] Add real-time messaging with loading indicators
  - [ ] Implement conversation history storage (client-side or session-based)
  - [ ] Add error handling for AI Agent connectivity issues

- [ ] **Task 3: Build interactive map visualization**
  - [ ] Implement Plotly geo map with float location markers
  - [ ] Add float trajectory plotting with temporal progression
  - [ ] Include clickable markers that trigger profile detail requests
  - [ ] Add geographic region selection tools

- [ ] **Task 4: Create scientific plot components**
  - [ ] Implement depth profile plots for temperature/salinity/BGC parameters
  - [ ] Add proper scientific axis labeling (units, quality indicators)
  - [ ] Create time-series visualization for temporal analysis
  - [ ] Include data quality color coding and legends

- [ ] **Task 5: Add data administration interface**
  - [ ] Implement file upload component for NetCDF files
  - [ ] Add processing trigger with status monitoring
  - [ ] Create RESET button with confirmation dialog (dark red styling)
  - [ ] Include processing logs and error display

- [ ] **Task 6: Integrate with backend services**
  - [ ] Connect chat interface to AI Agent API endpoints
  - [ ] Integrate visualization requests with MCP Tool Server REST API
  - [ ] Add file upload integration with DATAOPS orchestrator
  - [ ] Test full workflow: upload → process → chat → visualize

## Risk Assessment

### Implementation Risks

- **Primary Risk**: Complex Dash callbacks cause performance issues or blocking
- **Mitigation**: Use background callbacks and proper async patterns
- **Verification**: Load testing with multiple concurrent users

- **Secondary Risk**: Scientific plots lack proper context or mislead users
- **Mitigation**: Include comprehensive legends, units, and quality indicators
- **Verification**: Domain expert review of generated visualizations

### Rollback Plan

- Serve static HTML dashboard if Dash server fails
- Chat interface can fall back to simple API testing interface
- Visualizations can be pre-generated images if interactive plots fail

### Safety Checks

- [ ] All scientific plots include proper units and quality information
- [ ] Chat interface cannot send malformed requests to AI Agent
- [ ] File upload validates file types and sizes before processing
- [ ] RESET functionality requires explicit confirmation

## Definition of Done

- [ ] Two-column dashboard displays with chat and visualization areas
- [ ] Chat interface successfully communicates with AI Agent
- [ ] Interactive maps display float locations and trajectories correctly
- [ ] Scientific plots show temperature/salinity profiles with proper labeling
- [ ] Data administration interface allows file upload and processing
- [ ] RESET button clears database with proper confirmation
- [ ] All components handle errors gracefully and provide user feedback
- [ ] Dashboard meets performance requirements for hackathon demo