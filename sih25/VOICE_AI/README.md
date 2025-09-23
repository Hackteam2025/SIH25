# AGNO Voice AI Integration

This directory contains the voice AI integration for the AGNO oceanographic assistant, enabling natural language voice queries about float data.

## Architecture

The voice pipeline follows this flow:
```
User Voice Input → Silero VAD → STT → AGNO Agent → Voice Processor → TTS → Audio Output
```

### Key Components

- **AGNO Voice Handler** (`agno_voice_handler.py`): Main integration layer between Pipecat and AGNO agent
- **Voice Pipeline** (`oceanographic_voice_pipeline.py`): Complete pipeline implementation
- **Voice Processor**: Cleans and optimizes AGNO responses for voice output
- **Configuration** (`config.py`): Environment and service configuration management

## Features

- 🎤 **Voice Input**: Real-time speech recognition with Silero VAD
- 🤖 **AGNO Integration**: Seamless integration with existing AGNO agent
- 🔊 **Voice Output**: Natural TTS with response optimization
- 📝 **Session Logging**: Optional transcript logging for analysis
- ⚡ **Interruption Support**: Users can interrupt the bot mid-sentence
- 🌊 **Domain Optimization**: Responses optimized for oceanographic terminology

## Configuration

### Required Environment Variables

```bash
# MCP Server (for AGNO agent)
MCP_SERVER_URL=http://localhost:8000

# Speech-to-Text (choose one)
DEEPGRAM_API_KEY=your_deepgram_key
SONIOX_API_KEY=your_soniox_key

# Text-to-Speech (choose one)
DEEPGRAM_API_KEY=your_deepgram_key  # Can use same key for STT/TTS
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# Optional: Daily.co WebRTC (for web deployment)
DAILY_API_KEY=your_daily_key
```

### Service Providers

**STT Options:**
- **Deepgram**: Fast, accurate, good for real-time
- **Soniox**: High accuracy, especially for technical terms

**TTS Options:**
- **Deepgram**: Fast, reliable, good baseline
- **ElevenLabs**: Higher quality, more natural voices

## Quick Start

1. **Install Dependencies**:
   ```bash
   uv add "pipecat-ai[openai,deepgram]"
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Test Installation**:
   ```bash
   python test_voice_ai.py
   ```

4. **Run Voice Pipeline**:
   ```bash
   python oceanographic_voice_pipeline.py
   ```

## Usage Examples

### Voice Queries

- *"Show me temperature profiles near the equator"*
- *"What's the salinity data for the Mediterranean Sea?"*
- *"Find floats that measured BGC parameters last year"*
- *"Get me the latest data from float number 1234"*

### Response Optimization

The voice processor automatically:
- Removes technical thinking tags
- Simplifies complex data references
- Adds natural conversation context
- Optimizes length for voice output

## Integration with Existing Components

### AGNO Agent Integration
```python
from agno_voice_handler import AGNOVoiceHandler

handler = AGNOVoiceHandler(mcp_server_url="http://localhost:8000")
await handler.initialize_agent()
response = await handler.process_user_input("Show me temperature data")
```

### Voice Response Processing
```python
from agno_voice_handler import AGNOVoiceProcessor

processor = AGNOVoiceProcessor()
voice_response = processor.clean_for_voice(agno_response)
final_response = processor.add_voice_friendly_context(voice_response)
```

## Testing

Run the test suite to verify all components:

```bash
python test_voice_ai.py
```

Tests include:
- Dependency verification
- Configuration validation
- AGNO handler functionality
- Voice response processing
- Interactive demo mode

## Deployment Options

### Local Development
- Uses local microphone/speakers
- Perfect for testing and development

### Web Deployment (Future)
- Daily.co WebRTC integration
- Scalable for multiple users
- Web-based interface

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure AGNO agent directory is in Python path
2. **Audio Issues**: Check microphone permissions and audio drivers
3. **API Errors**: Verify API keys and network connectivity
4. **MCP Connection**: Ensure MCP Tool Server is running

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Web interface integration
- [ ] Multiple language support
- [ ] Voice biometrics for user identification
- [ ] Real-time visualization sync
- [ ] Advanced interruption handling
- [ ] Custom wake word detection