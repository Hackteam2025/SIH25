# SMART INDIA HACKATHON 2025

---

### **TITLE PAGE**

-   **Problem Statement ID:** 25040
-   **Problem Statement Title:** FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization
-   **Organization:** Ministry of Earth Sciences (MoES)
-   **Department:** Indian National Centre for Ocean Information Services (INCOIS)
-   **Theme:** Miscellaneous
-   **PS Category:** Software
-   **Team ID:** (Enter Team ID)
-   **Team Name:** (Enter Team Name)

---

### **PROPOSED SOLUTION**

**Idea: FloatChat - A Conversational AI for Ocean Data Exploration**

-   **Detailed Explanation:** FloatChat is an AI-powered web platform that transforms the exploration of complex ARGO oceanographic data into an intuitive conversation. Users can ask questions in natural language (e.g., *"Show me salinity profiles near the equator in March 2023"*) and receive immediate, interactive visualizations and scientifically accurate answers.
-   **How it Addresses the Problem:** It removes the significant technical barrier of using ARGO data. It automates the entire workflow of data ingestion, validation, querying, and visualization, which is currently a manual, code-intensive process. This democratizes data access for non-programmers, bridging the gap between raw data and expert insights.
-   **Innovation and Uniqueness:**
    -   **Conversational Interface for Scientific Data:** Moves beyond traditional dashboards to a more intuitive, question-based exploration model.
    -   **Scientifically-Grounded AI:** The AI is sandboxed and uses a secure, human-vetted toolset (MCP Server) that enforces ARGO data quality protocols, ensuring reliability and accuracy.
    -   **Retrieval-Augmented Generation (RAG):** Utilizes a vector database (ChromaDB) to understand the *context* of user queries, not just keywords, leading to more relevant discoveries.

---

### **TECHNICAL APPROACH**

-   **Technologies to be Used:**
    -   **Frontend:** Plotly Dash
    -   **Backend:** Python, FastAPI
    -   **AI Framework:** AGNO/MCP (for tool-augmented agent using RAG)
    -   **Data Pipeline:** Pandas, Xarray
    -   **Databases:** PostgreSQL (for structured data), ChromaDB (for vector embeddings)
    -   **Voice I/O:** Pipecat

-   **Methodology and Process (Flow Chart):**
    ```mermaid
    graph TD
        subgraph "User Interface"
            UI_Chat["Chat & Viz UI"]
        end
        subgraph "Backend"
            AI_AGENT[AI AGENT]
            API_MCP[MCP Tool Server]
        end
        subgraph "Data Layer"
            DATAOPS_PIPELINE[DATAOPS Pipeline]
            DATA_LOADER[DATA LOADER]
            DATABASE[(PostgreSQL)]
            VECTOR_DB[(ChromaDB)]
        end

        USER[User] -- Asks Question --> UI_Chat
        UI_Chat -- Sends Query --> AI_AGENT
        AI_AGENT -- Calls Secure Tools --> API_MCP
        API_MCP -- Queries --> DATABASE & VECTOR_DB
        API_MCP -- Returns Data --> AI_AGENT
        AI_AGENT -- Generates Response & Viz --> UI_Chat

        %% Data Ingestion Flow (Offline)
        NetCDF_File -- Uploaded to --> DATAOPS_PIPELINE
        DATAOPS_PIPELINE -- Creates Clean Files --> DATA_LOADER
        DATA_LOADER -- Populates --> DATABASE & VECTOR_DB
    ```

---

### **FEASIBILITY AND VIABILITY**

-   **Analysis of Feasibility:**
    -   The project is highly feasible by integrating existing, robust open-source technologies (Python, FastAPI, Plotly, ChromaDB).
    -   The architecture is modular, allowing for parallel development and incremental implementation, as proven by the 5-story development plan.
    -   The brownfield approach leverages an existing `DATAOPS` pipeline, reducing initial development time.

-   **Potential Challenges and Risks:**
    -   **Risk:** AI generating scientifically inaccurate interpretations.
    -   **Strategy:** A sandboxed AI that can *only* use secure, human-vetted tools from an MCP server. All tools have built-in validation that enforces ARGO data quality protocols.
    -   **Risk:** Complex natural language queries failing.
    -   **Strategy:** A hybrid search approach combining structured SQL queries with semantic vector search (RAG) to better understand user intent.
    -   **Risk:** Handling large query results causing performance issues.
    -   **Strategy:** Implementing server-side data summarization and pagination within the API tools.

---

### **IMPACT AND BENEFITS**

-   **Potential Impact on Target Audience:**
    -   **Oceanographic Researchers:** Drastically reduces time spent on manual data preparation and plotting, accelerating the pace of discovery.
    -   **Policy Makers & Govt. Officials (MoES/INCOIS):** Provides direct, timely access to ocean data insights for informed decision-making on environmental and climate policy.
    -   **Students & Educators:** Lowers the barrier to entry for exploring real-world scientific datasets, serving as a powerful educational tool.

-   **Benefits of the Solution:**
    -   **Social:** Democratizes access to publicly funded scientific data, fostering citizen science and greater public engagement with oceanography.
    -   **Economic:** Accelerates research and development in climate modeling, fisheries management, and maritime operations.
    -   **Environmental:** Enables faster and more intuitive monitoring of ocean health, climate change indicators, and marine ecosystems.

---

### **RESEARCH AND REFERENCES**

-   **Official Dataset Links:**
    -   **Argo Global Data Repository:** `ftp.ifremer.fr/ifremer/argo`
    -   **Indian Argo Project:** `https://incois.gov.in/OON/index.jsp`

-   **Internal Project Documentation (Source of Truth):**
    -   `docs/prd.md`: Product Requirements Document for FloatChat.
    -   `docs/architecture.md`: Detailed System Architecture and design principles.
    -   `docs/stories/*.md`: User stories detailing the implementation of each core component.

-   **Core Technologies & Protocols:**
    -   **ARGO Data Management:** [Official ARGO User's Manual](https://archimer.ifremer.fr/doc/00187/29825/)
    -   **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com/)
    -   **Plotly Dash:** [dash.plotly.com](https://dash.plotly.com/)
    -   **ChromaDB:** [www.trychroma.com](https://www.trychroma.com/)
