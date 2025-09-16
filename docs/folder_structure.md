sih25/
├── DATAOPS/                    # ✅ Current - Keep as-is
│   ├── main_orchestrator.py
│   ├── step3_schema_explorer.py
│   ├── step4_data_validator.py
│   ├── step5_data_preprocessor.py
│   └── step6_data_exporter_parquet.py
├── api/                        # 🆕 Add - FastAPI backend
│   ├── __init__.py
│   ├── main.py
│   ├── routers/
│   └── models/
├── database/                   # 🆕 Add - DB models & migrations
│   ├── __init__.py
│   ├── models.py
│   ├── supabase_client.py
│   └── migrations/
├── vector_store/               # 🆕 Add - ChromaDB integration
│   ├── __init__.py
│   ├── embeddings.py
│   └── retrieval.py
├── llm/                        # 🆕 Add - MCP & LLM integration
│   ├── __init__.py
│   ├── mcp_server.py
│   └── agents.py
├── ui/                         # 🆕 Add - Dashboard & chat UI
│   ├── __init__.py
│   ├── dashboard.py
│   ├── chat_interface.py
│   └── components/
├── voice/                      # 🆕 Add - Pipecat integration
│   ├── __init__.py
│   └── voice_processor.py
├── utils/                      # 🆕 Add - Shared utilities
│   ├── __init__.py
│   ├── config.py
│   └── helpers.py
└── docs/                       # ✅ Current - Keep & expand
    ├── prd.md
    └── PPLX/