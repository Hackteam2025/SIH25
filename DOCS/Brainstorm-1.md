<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Brainstorming session 1 : data and some core information


---
Problem Statement ID
25040
Problem Statement Title
FloatChat - AI-Powered Conversational Interface for ARGO Ocean Data Discovery and Visualization
Description
Background

Oceanographic data is vast, complex, and heterogeneous – ranging from satellite observations to in-situ measurements like CTD casts, Argo floats, and BGC sensors. The Argo program, which deploys autonomous profiling floats across the world’s oceans, generates an extensive dataset in NetCDF format containing temperature, salinity, and other essential ocean variables. Accessing, querying, and visualizing this data requires domain knowledge, technical skills, and familiarity with complex formats and tools. With the rise of AI and Large Language Models (LLMs), especially when combined with modern structured databases and interactive dashboards, it is now feasible to create intuitive, accessible systems that democratize access to ocean data.

Description

The current problem statement proposes the development of an AI-powered conversational system for ARGO float data that enables users to query, explore, and visualize oceanographic information using natural language.

The current system shall:
− Ingest ARGO NetCDF files and convert them into structured formats (like SQL/Parquet).
− Use a vector database (like FAISS/Chroma) to store metadata and summaries for retrieval.
− Leverage Retrieval-Augmented Generation (RAG) pipelines powered by multimodal LLMs (such as GPT, QWEN, LLaMA, or Mistral) to interpret user queries and map them to database queries (SQL). (Use Model Context Protocol (MCP))
− Enable interactive dashboards (via Streamlit or Dash) for visualization of ARGO profiles, such as mapped trajectories, depth-time plots, and profile comparisons, etc.
− Provide a chatbot-style interface where users can ask questions like:
  • Show me salinity profiles near the equator in March 2023
  • Compare BGC parameters in the Arabian Sea for the last 6 months
  • What are the nearest ARGO floats to this location?

This tool will bridge the gap between domain experts, decision-makers, and raw data by allowing non-technical users to extract meaningful insights effortlessly.

Expected Solution

− End-to-end pipeline to process ARGO NetCDF data and store it in a relational (PostgreSQL) and vector database (FAISS/Chroma).
− Backend LLM system that translates natural language into database queries and generates responses using RAG.
− Frontend dashboard with geospatial visualizations (using Plotly, Leaflet, or Cesium) and tabular summaries to ASCII, NetCDF.
− Chat interface that understands user intent and guides them through data discovery.
− Demonstrate a working Proof-of-Concept (PoC) with Indian Ocean ARGO data and future extensibility to in-situ observations (BGC, glider, buoys, etc.), and satellite datasets.

Acronyms

NetCDF: Network Common Data Format
CTD: Conductivity Temperature and Depth
BGC: Bio-Geo-Chemical Floats
Organization
Ministry of Earth Sciences (MoES)
Department
Indian National Centre for Ocean Information Services (INCOIS)
Category
Software
Theme
Miscellaneous
Youtube LinkDataset Link
• Argo Global Data Repository: ftp.ifremer.fr/ifremer/argo • Indian Argo Project: [https://incois.gov.in/OON/index.jsp](https://incois.gov.in/OON/index.jsp)
Contact info

for this we have to perform some data ops and have some preprocessing.
the thing is idk anything about how to perform data ops.
i have to make this for a hackathon named smart india hac. (sih)
i thought to use voice ai via pipecat and agent core will be based on AGNO due to its agent os. also, for storing out the information (as since the ARGO dataset has this structure, see this chat : ''' man okey, so
i'll use the mcp of supabase which will help us to bypass the sql generation and will retrieve the data using mcp (correct me if im wrong via web searching)
see this : ARGO Data Structure Validation
Yes, ARGO data IS 2-phased:
ARGO provides float metadata, detailed trajectory data, profile data [Langwatch](https://langwatch.ai/blog/best-ai-agent-frameworks-in-2025-comparing-langgraph-dspy-crewai-agno-and-more)[Turing](https://www.turing.com/resources/ai-agent-frameworks) and profile, trajectory, meta and technical data files [Comparing CrewAI, LangGraph,Agno, and Autogen](https://www.linkedin.com/pulse/comparing-crewai-langgraph-autogen-which-ai-framework-kooshki-wym9f) separately.
Structure:
Metadata files: Float info, deployment details, technical specs
Profile files: Actual measurements (temperature, salinity, pressure)
Trajectory files: Float movement paths
Individual profiles organized by ocean and subdivided into years and months [A Detailed Comparison of Top 6 AI Agent Frameworks in 2025](https://www.turing.com/resources/ai-agent-frameworks) - perfect for your ChromaDB metadata indexing approach.
---
'''
we thought to use chroma db, postgres sql via supabase for db querying with the help of supabase mcp server which our AGNO agent will has the access to.

but i need some help of you, i want to make this project to : in realtime ingest the user's uploaded data and preprocess it and then stores into the sql database.

guide me on how to approach this problem. we have initially separated out the different components like related to core llm agent, data ops, and voice ai pipeline.

infact, the llm agent has the mcp servers attached (usuallly like supabase mcp server, our custom tools which provides data intelligence like related to preprocessing, and data vizualization currently)

i need a short poa on how to tackle this. very consise i dont wanna be hallucinated.

from the doc, act as an analyst and lmk what should i be doing the next?

Here’s a concise, low‑risk plan of action to stand up real‑time ingestion, SQL‑backed retrieval, and an MCP‑powered agent for FloatChat; using Supabase’s MCP server lets the agent call named/parameterized queries so it doesn’t have to generate raw SQL, but those queries/procedures still need to be defined server‑side.

### Assumptions

- Target stack: Python (FastAPI, xarray/NetCDF4, pandas/pyarrow), PostgreSQL (+PostGIS), object storage (Supabase Storage/S3), Chroma (vector DB), Streamlit/Dash for viz, AGNO agent with MCP tools, voice via Pipecat.
- Scope: PoC on Indian Ocean subset + user file uploads; prioritize ingestion reliability and query safety.


### Immediate next steps

- Create a single repo with three services: ingest-api, worker, app (chat+viz).
- Provision Postgres (enable PostGIS), object storage bucket, and Chroma; set env/secrets and CI templates.
- Define 6 MCP tools (read-only, parameterized) that wrap prepared SQL/functions; whitelist only these in the agent.


### Data model (pragmatic PoC)

- floats(id, wmo_id, platform_type, last_cycle_time, last_lat, last_lon, region).
- profiles(id, float_id, cycle_number, t_obs, lat, lon, depth_min, depth_max, has_bgc, qc_summary, parquet_url).
- profile_stats(profile_id, temp_min,max,mean; sal_min,max,mean; n_levels; flags).
- embeddings(doc_id=profile_id, vector, metadata: {region, time, params, wmo_id}).


### Ingestion flow (real‑time upload)

- ingest-api: POST /upload accepts NetCDF; stores raw to object storage; enqueues job (Redis/NATS).
- worker: uses xarray to read NetCDF, extracts core metadata (lat, lon, time, cycle, WMO, QC), computes stats, writes full vertical arrays to Parquet, upserts floats/profiles/profile_stats, creates a concise text summary, embeds it, and upserts to Chroma.
- Idempotency: hash(raw_uri) to skip duplicates; transaction wrap for SQL writes; DLQ on parse failures.


### Batch seed (optional for demo)

- One script to download a small Indian Ocean slice (last 6–12 months), run the same worker pipeline, and prefill Postgres/Chroma to ensure the chat has something to query on day 1.


### MCP tool surface (no raw SQL from LLM)

- list_profiles(region, t_start, t_end, has_bgc, limit, offset).
- get_profile(profile_id).
- search_floats_near(lon, lat, radius_km, t_start, t_end).
- profile_section(profile_id, var, depth_min, depth_max) → returns Parquet URL and selective rows.
- compare_param(region, t_start, t_end, var) → returns grouped stats.
- recent_trajectories(region, days) → returns geojson line segments.


### Agent orchestration

- System prompt: “Use only approved tools; never generate SQL. Prefer ‘list → narrow → fetch’ pattern. If tool returns zero, ask for narrower time/region.”
- RAG: embed profile summaries + a short “data dictionary” of variables/QC flags for grounding; retrieval before tool selection for better disambiguation.


### Dashboard + chat

- Streamlit or Dash app with two panes: Chat (agent) and Viz.
- Viz primitives: map (Leaflet/Plotly) for trajectories; profile plot (depth vs variable); time–depth heatmap for a float; comparison panel for region stats.
- The app subscribes to chat tool results and renders appropriate plots based on payload type (profiles list, geojson, stats).


### Voice pipeline

- Pipe chat turn text ↔ TTS/ASR via Pipecat; keep the same agent core; add short “voice summaries” of results and verbal prompts to refine filters (time/region/param).


### Reliability/guardrails

- Strict schema validation on upload; reject files missing lat/lon/time/pressure arrays.
- Parameter bounds for MCP tools (time windows, radius caps, row limits); return paginated results.
- Fallback answers: if no data, propose nearest time window or adjacent region with data.


### What to build first (48–72 hrs)

1) Provision DB/storage/vector and commit minimal schema \& migrations.
2) Implement worker on 1–2 sample NetCDFs → Parquet in storage, SQL rows upserted, embeddings created.
3) Wrap 3 MCP tools (list_profiles, get_profile, search_floats_near) with prepared queries; integrate into agent.
4) Minimal Streamlit: map + single profile plot wired to tool outputs; add Chat textbox.
5) Upload endpoint + queue; verify E2E on a new user upload.

### Demo acceptance (PoC)

- “Show salinity profiles near the equator in March 2023” returns a list + map pins; selecting a profile plots salinity vs depth.
- “Compare BGC chlorophyll in Arabian Sea last 6 months” returns stats and a time series/box plot.
- “Nearest floats to 64.2E, 12.1N?” returns top 5 with distances and latest times.


### Notes on “bypass SQL generation”

- Correct framing: the agent does not author ad‑hoc SQL; it calls safe, parameterized tools that execute vetted SQL/SPA or stored procedures. Keep tool args typed, validated, and range‑limited.

If helpful, next deliverable can be a skeleton repo (folders, env templates, migrations, worker stub, first three MCP tools, and a minimal Streamlit app) to accelerate the first demo.

---

# part 1:

man but tell me do you mean, should i perform data schema exploration first then go for doing preprocessing, i could'nt understand your wordings, lmk what you meant because suppose even if we have to make an inintial step then what i thought is that to create an apache airflow or dagster based workflow which ingests the data preprocesses it -> moves to next stage for visualization.
we can also have those parts as individually present in the our mcp server :: like 1. preprocess 2. viz 3.sql supabase one 4 \& 5 you told but i forgot which one tho.

part2 :
good i would like to add another layer on it : data validation ; i thought to use pydantic for it and im impressed by plotly dash. i'll use it. meanwhile for rag : i was thinking to go with naive approach currently. should i be needing a prd or epics at current moment from the doc?

Short answer: Yes—profile and fix the data contract first, then run preprocessing; wire that order into the DAG so validation can fail fast before expensive transforms and viz steps. A simple “ingest → schema/profile → validate → preprocess/clean → persist/query → viz” pipeline is a sound baseline to start with.[^2_1][^2_2]

### Recommended order

- Do schema exploration/profiling first to establish column names, types, nullability, and required fields; this lets validation catch contract drift before feature engineering.[^2_2][^2_1]
- Run formal validation (fail-fast) immediately after profiling, then proceed to cleaning, enrichment, and transformations only on validated batches.[^2_1][^2_2]
- Persist outputs and serve to downstream analytics/RAG components, keeping visualization as a consumer of the validated, transformed layer.[^2_2][^2_1]


### Airflow/Dagster DAG sketch

- Tasks: ingest → schema_profile → validate → preprocess_clean → load_to_warehouse (Supabase/Postgres) → build_embeddings (optional) → viz_service (Dash) → monitoring/alerts.[^2_1][^2_2]
- Keep “schema_profile + validate” upstream; if validation fails, short-circuit the DAG and alert, avoiding wasted compute in preprocess/viz.[^2_2][^2_1]


### MCP tool endpoints (modular services)

- preprocess: batch cleaning/standardization with idempotent reruns.[^2_1][^2_2]
- viz: Plotly Dash service that reads curated tables/views only.[^2_2][^2_1]
- sql_supabase: thin SQL/CRUD/RPC layer for Supabase Postgres; for arbitrary SQL prefer direct Postgres drivers or RPC as the Python client isn’t a general “execute SQL” shell.[^2_3][^2_4]
- rag_index: chunk + embed + upsert vectors (pgvector via Supabase vecs).[^2_5][^2_6]
- rag_query: top‑K retrieval + prompt assembly + generation; start with a naïve baseline.[^2_7][^2_5]


### Data validation layer

- Pydantic is great for row-wise/record contracts (types, ranges, formats) inside Python steps; pair it with table/column-level checks (e.g., Great Expectations) for schema, distributions, and integrity.[^2_1][^2_2]
- Don’t rely on schema-only checks—add semantic expectations (value ranges, regex patterns, cross-field rules) and log/monitor validation outcomes for drift.[^2_2][^2_1]


### Naive RAG baseline (good for now)

- Pipeline: chunk documents → embed chunks → store in vector DB (pgvector/vecs) → at query time embed question → retrieve top‑K → stuff into the prompt → generate.[^2_5][^2_7]
- Use Supabase vecs to manage pgvector collections from Python; it’s a straightforward way to stand up a baseline without extra infra.[^2_6][^2_5]
- Treat naïve RAG as a baseline; later iterate with re-ranking, query rewriting, or hybrid retrieval once metrics justify it.[^2_8][^2_5]


### Supabase notes for the “sql” piece

- The official Python client supports PostgREST-style queries and RPC, not arbitrary “execute SQL”; for raw SQL use a Postgres driver (or RPC when possible).[^2_4][^2_3]
- If adding vectors, pgvector + vecs API provides create/upsert/query over collections directly from Python.[^2_6][^2_4]


### Do a PRD or epics right now?

- If this is a small, focused slice (ingest→validate→preprocess→viz with a naïve RAG add‑on), a single brownfield epic or even one story is sufficient to move fast.[^2_9]
- If scope spans multiple coordinated features (validation framework, pipeline orchestration, RAG store, Dash app, monitoring), draft a short PRD and split into epics for clean sequencing and handoffs; use the brownfield PRD if integrating into an existing system.[^2_9]
- Rule of thumb in this method: quick enhancement → use the “create brownfield epic/story” flow; major multi-part enhancement → create PRD, then architecture, then stories.[^2_9]

<div style="text-align: center">⁂</div>

[^2_1]: https://docs.greatexpectations.io/docs/reference/learn/data_quality_use_cases/schema

[^2_2]: https://www.oreilly.com/library/view/building-machine-learning/9781492053187/ch04.html

[^2_3]: https://github.com/supabase/supabase-py/issues/417

[^2_4]: https://supabase.com/docs/reference/python/introduction

[^2_5]: https://wandb.ai/site/articles/rag-techniques/

[^2_6]: https://supabase.com/docs/guides/ai/vecs-python-client

[^2_7]: https://arxiv.org/abs/2312.10997

[^2_8]: https://redis.io/blog/10-techniques-to-improve-rag-accuracy/


---

# aha, man now i understood : we are just going to stop till build embeddings in the dag sketch workflow. WHICH CAN TRIGGER IF WE DONT HAVE ANY EXISTING VECTORSTORE DATA OR THE SUPABASE DB IS EMPTY in EITHER OF THE CASES. thus being intelligent and we will have a RESET method, which will clear out the DB and VECTOR STORE data.

this will be the final flow of application.
the application starts. it shows up a simple interface having  2 columns. on the left side we can have the interactive dashboard visualizaitons possible through DASH by plotly.
and on the right side, a chat layout where you can start the conversation. just as similar to chatgpt layout, including a placeholder on the bottom of the screen, with a small button for voice mode.
when we click that button, it will transform into an interactive mode with no any other core architecture issues because it will use pipecat and we can think of this as abstracting the agent from the end user. like pre and post-pending the stt and tts layers only.
the main llm will be an ai agent made possible by AGNO having memory and tools attached as form of mcp server.
well i was starting out from scratch and have 10 days to implement this. the faster it it, the better.
also adding context about the data :
Argo
[](https://argo.ucsd.edu/)
[Home](https://argo.ucsd.edu/)
[About](https://argo.ucsd.edu/about/)
[Organization](https://argo.ucsd.edu/organization/)
[Data](https://argo.ucsd.edu/data/)
[Technology](https://argo.ucsd.edu/how-do-floats-work/)
[Science](https://argo.ucsd.edu/science/)
[Outreach](https://argo.ucsd.edu/outreach/)
[OneArgo](https://argo.ucsd.edu/oneargo/)
[](https://argo.ucsd.edu/data/how-to-use-argo-files/#)
How to use Argo profile files
[Home](https://argo.ucsd.edu/) [Argo data](https://argo.ucsd.edu/data/) [How to use Argo profile files](https://argo.ucsd.edu/data/how-to-use-argo-files/)
Quick start guide on how to use the Argo profile files
Most users are interested in getting the vertical profile data from Argo floats.  Vertical profile data are stored in Argo profile files.  There is one profile file for every cycle.  This quick start guide is designed to help you get started using Argo netCDF files available at the Argo GDACs ([click here](https://argo.ucsd.edu/data/data-from-gdacs/) to learn how to get data from the GDACs).  To learn about other ways of accessing Argo data, visit the Argo [data products page](https://argo.ucsd.edu/data/argo-data-products/), the [data visualizations page](https://argo.ucsd.edu/data/data-visualizations/) or the [software tools page](https://argo.ucsd.edu/data/argo-software-tools/). This guide will cover four main topics:
Real time and delayed mode files
Core and BGC files
How to choose the correct variables to use for each parameter
How to use quality control flags and errors
Real time profile files
Real time profile files are where Argo data are first made publicly available at the GDACs. Real time files on the GDACs all contain an “R” before the WMO number (e.g. R5900400_001.nc, BR5904179_001.nc). These real time profile files are available within 12 – 24 hours of the float completing its profile.
In the real time profile files, data measured by the float are recorded in the variables <PARAM>.  For the list of Argo <PARAM>s, please refer to Reference Table 3 in the [Argo Users Manual](https://doi.org/10.13155/29825).  For example, the basic vertical temperature and salinity data are stored in the <PARAM> = PRES, TEMP, PSAL.
Each <PARAM> has an associated variable called <PARAM>_QC which records the quality control flags.  In the real time profile files, the quality control flags are set by a number of automatic tests which aim to detect gross errors.
Each <PARAM> also has another associated variable called <PARAM>_ADJUSTED.  If scientific calibration is applied to the measured parameters in real time, the real time adjusted values will be recorded in <PARAM>_ADJUSTED.
If real time adjusted values are available, the variable DATA_MODE will record ‘A’. If real time adjusted values are not available, the variable DATA_MODE will record ‘R’.
In general these data should be consistent with ocean climatologies. Monthly climatology tests are performed, along with visual comparisons for profiles that fail the tests.  However, for scientific applications that are sensitive to small pressure and salinity biases (e.g. calculations of global ocean heat content or mixed layer depth), it is not recommended to use “R” files.
To learn more about real time quality control tests, see the[ ADMT documentation page](http://www.argodatamgt.org/Documentation) for core Argo and BGC-Argo quality control documentation.
Delayed mode files
Delayed mode profile files are the same as the real time profile files, except their file names on the GDACs all contain a “D” before the WMO number (e.g. D5900400_001.nc, BD5904179_001.nc). These profile files contain delayed mode adjusted data, which are recorded in the variable <PARAM>_ADJUSTED. The variable DATA_MODE will record ‘D’. Two other variables are also filled in delayed mode, which are <PARAM>_ADJUSTED_QC and <PARAM>_ADJUSTED_ERROR, which record the delayed mode quality control flags and the delayed mode adjustment uncertainty.
Core Argo delayed mode files are available 1 – 2 years after a profile is taken; sometimes earlier. These have been subjected to detailed scrutiny by oceanographic experts and the adjusted salinity has been estimated by comparison with high quality ship-based CTD data and Argo climatologies using the process described by [Wong et al, 2003](http://dx.doi.org/10.1175/1520-0426(2003)020%3C0308:DMCOAC%3E2.0.CO;2); [Böhme and Send, 2005](http://dx.doi.org/10.1016/j.dsr2.2004.12.014); [Owens and Wong, 2009](http://dx.doi.org/10.1016/j.dsr.2008.09.008); [Cabanes et al, 2016](http://dx.doi.org/10.1016/j.dsr.2016.05.007).
For BGC parameters, delayed mode files can be available within 5 – 6 cycles after deployment.  This is because the BGC sensors often return data that are out of calibration, but early adjustment methodologies exist that can significantly improve their accuracy.  Additional delayed mode quality control occurs when a longer record of float data is available.
To learn more about delayed mode quality control, read the papers on the methods linked above or see the[ ADMT documentation page](http://www.argodatamgt.org/Documentation) for core Argo and BGC-Argo quality control documentation.
Core and BGC files
For core floats, the profile files (R…nc, D…nc) contain data from the CTD.
For BGC floats, there are core profile files which contain data from the CTD and b-profile files (BR….nc, BD….nc) which contain all the BGC parameters, including intermediate ones, and just PRES from the CTD.  In addition, there are [synthetic profile files](http://www.argodatamgt.org/Data-Mgt-Team/News/BGC-Argo-synthetic-profiles-distributed-on-GDAC) (SR…nc, SD…nc) which are generated by the GDACs to align CTD and BGC parameters obtained with different vertical sampling schemes, and make them available in one file.
How to choose the correct variables to use for each parameter
For each parameter, there are two variables associated with it:  a raw version and an adjusted version.  The raw version can be found in the “PARAM” variable (e.g. TEMP, PRES, DOXY) and the adjusted version can be found in the “PARAM_ADJUSTED” variable (e.g. TEMP_ADJUSTED, PRES_ADJUSTED, DOXY_ADJUSTED).
Core files
Look at the ‘DATA_MODE’ variable.
If DATA_MODE(i) is ‘R’, there is no adjusted data.  Use PARAM(i) only.
If DATA_MODE(i) is ‘D’ or ‘A’, there is adjusted data.  Use PARAM_ADJUSTED(i) only.
BGC files
The ‘DATA_MODE’ variable is not enough in BGC files because the various BGC parameters can be adjusted at different times. Instead, look at the ‘PARAMETER_DATA_MODE’ variable to see which parameter has adjusted values available.
If PARAMETER_DATA_MODE(i,j) is ‘R’, there is no adjusted data in the ith profile for the jth parameter.  Use PARAM(i,j) only.
If PARAMETER_DATA_MODE(i,j) is ‘D’ or ‘A’, there is adjusted data in the ith profile for the jth parameter.  Use PARAM_ADJUSTED(i,j) only.
How to use quality control flags and errors
The Argo profile files provide both quality control (QC) flags and errors to help users decide if they want to use the data or not.  There are flags for both the raw and adjusted data.  The QC flags are as follows:
QC flag
Meaning
Real time comment
Delayed mode comment
0
No QC performed
No QC performed
No QC performed
1
Good data
All real time QC tests passed
The adjusted value is statistically consistent and a statistical error estimate is supplied.
2
Probably good data
Probably good
3
Bad data that are potentially correctable
Test 15 or Test 16 or Test 17 failed and all other real-time QC tests passed. These data are not to be used without scientific correction. A flag ‘3’ may be assigned by an operator during additional visual QC for bad data that may be corrected in delayed mode.
An adjustment has been applied, but the value may still be bad.
4
Bad data
Data have failed one or more of the real-time QC tests, excluding Test 16. A flag ‘4’ may be assigned by an operator during additional visual QC for bad data that are not correctable.
Bad data.  Not adjustable.
5
Value changed
Value changed
Value changed
6
Not currently used
Not currently used
Not currently used
7
Not currently used
Not currently used
Not currently used
8
Estimated
Estimated value (interpolated, extrapolated or other estimation).
Estimated value (interpolated, extrapolated or other estimation).
9
Missing value
Missing value
Missing value
Many positions for under ice profiles are estimated, leading to JULD_QC and POSITION_QC flags of ‘8’.
Uncertaintly of the adjustments are provided, and are recorded in the <PARAM>_ADJUSTED_ERROR variables.  See the [Data FAQ](https://argo.ucsd.edu/data/data-faq/) page for more information on this error.
So, to get the cleanest and best possible data set, it is advised to use only delayed mode data with a QC flag of 1 and reasonably small errors. If that isn’t important to your study, you can relax the data state, QC flags and error requirements as necessary.
 
 
[](https://argo.sioword.ucsd.edu/wp-content/uploads/sites/361/2020/01/Argo_wld.gif)
Contact
Argo Program Office
e-mail: [argo@ucsd.edu](mailto:argo@ucsd.edu)
Argo Support Centre e-mail: [support@argo.net](mailto:support@argo.net)
Stay connected:
[Argo email lists](https://argo.ucsd.edu/stay-connected/)
[OneArgo Data Bytes](https://argo.ucsd.edu/oneargo-data-bytes/)
[Additional Links](https://argo.ucsd.edu/links)
[Global Argo Centers and Programs](https://argo.ucsd.edu/links/#GDAC)
[Argo Regional Centers](https://argo.ucsd.edu/links/#ARC)
[National Programs and Float Sites](https://argo.ucsd.edu/links/#National)
[Argo Data Access and QC Tools](https://argo.ucsd.edu/links/#TOOLS)
[International Programs related to Argo](https://argo.ucsd.edu/links/#INTL)
[Scripps Institution of Oceanography,](https://scripps.ucsd.edu/) [UC San Diego](https://ucsd.edu/) | [Log In](https://argo.ucsd.edu/wp-admin)
---

Yes—locking scope to build an intelligent embeddings DAG that auto-runs when the vector store or Supabase DB is empty, plus a simple two‑pane UI (Dash visualizations left, chat + optional voice right) with a RESET that clears DB/vector data, is a solid final flow for 10 days and sets up a clean foundation for RAG + voice across Argo data via an AGNO agent using MCP tools and memory.[1][2][3][4][5][6]

Below is a concise, implementation-ready plan: triggers, components, and a day‑by‑day schedule tailored to Argo ingestion, Supabase vectorization, Dash UI, Pipecat voice, and an AGNO agent with MCP tools.[2][3][4][5][6][1]

### Final flow

- On startup, run a “store health” check; if either Supabase tables are empty or no vectors exist, kick off the embeddings DAG; otherwise, proceed to serve UI and agent endpoints.[4][1]
- Provide a single-click **RESET** that drops or truncates relevant Supabase tables and clears the vector index; expose it as an MCP tool so it’s invokable in a controlled way by the agent with human-in-the-loop.[5][1]
- UI: left column shows Plotly Dash interactive charts; right column is a chat layout with a message list, input at bottom, and a small “voice” toggle to switch to Pipecat real‑time mode (STT→agent→TTS) while abstracting the LLM agent behind audio layers.[3][7][4]
- Agent: use **AGNO** for a stateful agent with memory and a pluggable knowledge backend; attach tool calls via MCP servers (e.g., reset, Argo queries, admin ops) so the agent can call them when useful with explicit user confirmation.[8][6][9][5]


### Data and embeddings

- Source: Argo netCDF profile files; prefer delayed mode profiles (“D”) and adjusted variables (<PARAM>_ADJUSTED) with QC flag 1 to build clean embeddings; fall back to “A” or “R” cautiously when delayed mode is unavailable, following official guidance.[10][2]
- Variable selection: for core profiles, use DATA_MODE “D/A” → <PARAM>_ADJUSTED, and “R” → <PARAM>; for BGC profiles use PARAMETER_DATA_MODE per-parameter to decide adjusted vs raw; keep QC filters in place to exclude poor-quality data.[2]
- Pipeline: 1) discover/download profiles; 2) extract metadata + chosen variables (e.g., PRES_ADJUSTED, TEMP_ADJUSTED, PSAL_ADJUSTED) with QC==1; 3) normalize/serialize to text chunks with provenance; 4) embed and upsert to Supabase/pgvector via LangChain’s Supabase vector store integration.[1][2]


### UI layout

- Implement a simple Dash app with two columns using standard Div layout and Dash components; left hosts Plotly graphs from curated Argo slices, right hosts a scrollable chat panel with a bottom text input and a mic button to activate voice mode.[11][4]
- Use callbacks for user interactions and periodic refresh for dashboard tiles if desired; keep styling minimal at first to hit the 10‑day target.[4]


### Voice mode (Pipecat)

- Add a “voice” toggle that swaps the right pane into a Pipecat session: inbound audio → STT → agent → TTS to the browser, wired via your chosen RTC transport; Pipecat’s real‑time graph abstracts the low‑latency audio path and lets the same agent logic run under voice without core changes.[12][7][3]
- Keep STT/TTS as pluggable nodes so latency/quality can be tuned later; Pipecat’s modular design fits this short‑sprint approach well.[7][3]


### Agent layer (AGNO + MCP)

- Build the main LLM as an AGNO agent with memory and a vector-backed knowledge module; configure knowledge retrieval over pgvector or Supabase vector store for grounded responses.[6][9][1]
- Add MCP servers/tools for: reset_store(), argo_profile_fetch(), and admin/status operations so the agent can discover and call tools with explicit UI confirmation per MCP best practices and security guidance.[5][8]


### RESET and idempotency

- Implement **RESET** as: 1) MCP tool that truncates Supabase tables and clears vectors; 2) a visible admin action in the UI requiring explicit human approval before execution, aligned with MCP’s human‑in‑the‑loop safety recommendations.[1][5]
- On next startup (or immediately), the embeddings DAG sees empty state and rebuilds vectors end‑to‑end, ensuring clean idempotency.[1]


### 10‑day build plan

- Day 1: Scaffold Dash two‑pane shell and basic callbacks; set up chat UI layout and placeholder charts; confirm local run.[11][4]
- Day 2: Add Supabase client, schema, and LangChain Supabase vector store wiring; test basic insert/query round‑trip with fake data.[1]
- Day 3: Argo ingestion prototype—download a small set of core profiles; parse DATA_MODE and QC, extract adjusted variables; serialize chunks with source metadata.[10][2]
- Day 4: Embeddings DAG v1—chunks → embed → upsert to Supabase; implement “store health” startup check and conditional DAG trigger if empty.[1]
- Day 5: RAG query path in agent—wire AGNO agent with memory + vector retrieval for grounding; stub MCP tools list and one no‑op tool.[9][6][5]
- Day 6: Dash charts fed by Argo slices (temperature/salinity profiles) with filters; ensure QC/adjusted rules persist to visualization layer.[2][4]
- Day 7: Pipecat integration v1—voice toggle in UI, connect to Pipecat session, ensure STT→agent→TTS loop works with trivial prompts.[3][7]
- Day 8: MCP tooling—implement reset_store() tool with human confirmation; add argo_profile_fetch() tool for targeted retrieval ops.[5]
- Day 9: Hardening pass—error states, logging, and guardrails on QC/data modes; verify vector rebuild path and idempotency.[2][1]
- Day 10: Polish \& demo—tighten UI, add minimal docs, run end‑to‑end with empty store → embeddings DAG → dashboard + chat/voice.[3][4]


### Minimal tech stitching

- Vector store: use LangChain’s Supabase integration with pgvector for embeddings upsert/query to reduce glue code and ship faster in 10 days.[1]
- UI shell: Dash default layout and callbacks for two columns and chat input is straightforward and reliable for quick delivery.[4][11]
- Voice path: Pipecat handles real‑time STT/TTS and model streaming, keeping the agent logic cleanly abstracted behind the audio graph.[7][3]
- Agent: AGNO provides declarative composition of model, memory, tools, and knowledge; add MCP tooling for reset/admin safely with confirmation.[6][9][5]


### Argo data handling rules to bake in

- Prefer delayed mode “D” files and use <PARAM>_ADJUSTED with QC==1 when available; otherwise, consider “A” or raw “R” carefully and record provenance and flags.[2]
- For BGC profiles, decide per-parameter via PARAMETER_DATA_MODE and use *_ADJUSTED where available, applying QC thresholds consistently.[2]
- Document these rules in code comments and data docs so future extensions remain scientifically consistent.[2]


### What you’ll have at the end

- A clean two‑pane app with interactive Dash visuals and a chat UI plus a voice toggle running Pipecat to talk to the same agent logic, backed by a robust RAG pipeline over Argo with a **RESET** and auto‑rebuild on empty stores—simple, reliable, and ready to scale after the sprint.[6][3][4][5][1][2]

Notes on assumptions made: the plan assumes Supabase with pgvector, LangChain’s Supabase integration, AGNO for the agent runtime, MCP tools for reset/admin, and Pipecat for voice, which collectively minimize glue code and maximize sprint speed given the 10‑day constraint.[3][5][6][1]

---

# actually see your idea is great but for the reset switch, it doens't makes sense to the chatbot itself tho. wdy think? i thought to include it in the ui itself, in the top right section in the darker red shade with white text, 3px rounded corner.

i'll recommend you to gather as much as information possible before starting out this session. have a detailed deterministic knowledge and come up with context complete final document which will represent our PRD.
