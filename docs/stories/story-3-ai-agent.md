# Story: AI Agent Setup with AGNO Framework

<!-- Source: Brownfield PRD + Architecture documents -->
<!-- Context: Brownfield enhancement - AGNO AI Agent for conversational interface -->

## Status: Draft

## Story

As a **conversation interface developer**,
I want **an AGNO-based AI Agent that provides natural language access to oceanographic data**,
so that **users can ask questions like "Show me salinity profiles near the equator" and get scientifically accurate responses**.

## Context Source

- Source Document: docs/prd.md + docs/architecture.md
- Enhancement Type: Conversational AI interface
- Existing System Impact: Uses MCP Tool Server for database access

## Acceptance Criteria

1. **New functionality works as specified**:
   - AI Agent accepts natural language queries about oceanographic data
   - Agent translates user questions into appropriate MCP tool calls
   - Responses include both text explanations and data for visualization
   - Conversation context maintained across multiple exchanges

2. **Integration with MCP Tool Server**:
   - Agent exclusively uses predefined MCP tools (no direct database access)
   - All queries respect ARGO protocols through server-side validation
   - Tool responses are interpreted and explained in user-friendly language

3. **Scientific accuracy maintained**:
   - Agent provides scientific context for all data interpretations
   - Data provenance clearly communicated to users
   - Quality control information included in responses
   - Agent refuses to display bad data (QC flag 4) without explicit warnings

4. **Performance and user experience**:
   - Average conversation length > 5 exchanges (per PRD success metric)
   - Query success rate > 90% for valid natural language inputs
   - Time to first insight < 30 seconds for new users

## Dev Technical Guidance

### Existing System Context

**MCP Tool Integration:**
- Agent will call tools from MCP Tool Server (Story 2)
- Available tools: `list_profiles`, `get_profile_details`, `search_floats_near`, etc.
- All database access mediated through these secure tools

**AGNO Framework Requirements (from PRD Section 8.3):**
- State management for conversation context
- Memory system for user preferences and session history
- Tool execution with error handling
- Streaming responses for real-time interaction

**Scientific Domain Knowledge:**
- Grounded in ARGO documentation and protocols
- Understanding of oceanographic parameters (temperature, salinity, BGC)
- Knowledge of data quality concepts and spatial/temporal analysis

### Integration Approach

**Agent Architecture:**
```python
# Core agent structure
class FloatChatAgent:
    def __init__(self, mcp_server_url: str):
        self.tools = MCPToolClient(mcp_server_url)
        self.memory = ConversationMemory()
        self.context = ScientificContext()

    async def process_query(self, user_message: str) -> AgentResponse:
        # 1. Parse natural language intent
        # 2. Select appropriate tools
        # 3. Execute tool calls with context
        # 4. Interpret results scientifically
        # 5. Generate user-friendly response
```

**Natural Language Processing:**
- Intent recognition for spatial queries ("near the equator")
- Temporal parsing ("in March 2023", "last winter")
- Parameter identification ("temperature", "salinity profiles")
- Quality control preferences ("high quality data only")

**Response Generation:**
- Scientific explanations with appropriate detail level
- Data summaries suitable for visualization
- Follow-up question suggestions
- Error explanations in user-friendly terms

### Technical Constraints

- **No Direct Database Access**: All data through MCP Tool Server
- **Scientific Accuracy**: Must maintain ARGO protocol compliance
- **Conversation Memory**: Support multi-turn conversations with context
- **Error Handling**: Graceful degradation when tools fail
- **Streaming**: Support real-time response generation

### Missing Information

❗ **User Input Needed:**
1. **AGNO Setup**: Do you have AGNO framework already installed/configured?
2. **LLM Provider**: Which LLM should the agent use (OpenAI, Claude, local model)?
3. **Voice Integration**: Should this story include Pipecat voice setup or separate?
4. **Conversation Storage**: Where should conversation history be persisted?

## Tasks / Subtasks

- [ ] **Task 1: Set up AGNO framework environment**
  - [ ] Install AGNO framework in existing uv environment
  - [ ] Create `sih25/AGENT/` directory structure
  - [ ] Configure AGNO with oceanographic domain knowledge
  - [ ] Set up LLM provider integration (API keys, model selection)

- [ ] **Task 2: Implement MCP Tool Client**
  - [ ] Create `sih25/AGENT/mcp_client.py` for tool server communication
  - [ ] Implement async tool calling with error handling
  - [ ] Add tool discovery and capability mapping
  - [ ] Test connectivity with MCP Tool Server from Story 2

- [ ] **Task 3: Build natural language processing pipeline**
  - [ ] Create intent recognition for oceanographic queries
  - [ ] Implement spatial/temporal parsing ("equatorial region", "winter 2023")
  - [ ] Add parameter extraction ("temperature profiles", "BGC data")
  - [ ] Build query validation before tool execution

- [ ] **Task 4: Implement conversation management**
  - [ ] Add conversation memory for multi-turn dialogues
  - [ ] Implement context tracking (previous queries, user preferences)
  - [ ] Create follow-up question generation
  - [ ] Add session management for multiple users

- [ ] **Task 5: Develop scientific response generation**
  - [ ] Create response templates for different query types
  - [ ] Add scientific context and data interpretation
  - [ ] Implement data provenance communication
  - [ ] Add visualization data preparation for frontend

- [ ] **Task 6: Integration testing with existing components**
  - [ ] Test agent queries against MCP Tool Server
  - [ ] Verify scientific accuracy of generated responses
  - [ ] Test conversation flow with realistic user scenarios
  - [ ] Validate performance meets PRD requirements

## Risk Assessment

### Implementation Risks

- **Primary Risk**: Agent generates scientifically inaccurate interpretations
- **Mitigation**: Comprehensive testing with domain experts and validation against known data
- **Verification**: Scientific accuracy validation suite

- **Secondary Risk**: Natural language parsing fails for domain-specific terms
- **Mitigation**: Extensive training data and fallback to clarifying questions
- **Verification**: Query success rate testing with varied inputs

### Rollback Plan

- Disable agent endpoints, fall back to direct tool server access
- Conversation interface becomes simple tool execution interface
- No impact on MCP Tool Server or database layers

### Safety Checks

- [ ] Agent cannot bypass MCP tool validation
- [ ] Scientific accuracy verified with test queries
- [ ] Error messages provide constructive guidance
- [ ] Conversation memory doesn't leak between sessions

## Definition of Done

- [ ] AGNO agent successfully processes natural language oceanographic queries
- [ ] Agent integrates seamlessly with MCP Tool Server
- [ ] Conversation context maintained across multiple exchanges
- [ ] Scientific accuracy verified for various query types
- [ ] Performance meets user experience requirements from PRD
- [ ] Error handling provides helpful feedback to users
- [ ] Response format compatible with visualization dashboard needs