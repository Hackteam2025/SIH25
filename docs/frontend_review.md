# Frontend Review: Single Points of Failure and Debugging Guide

This document outlines the key single points of failure in the FloatChat frontend and provides a structured guide for debugging integration issues.

### Frontend Architecture Overview

*   **Framework**: The frontend is a Python-based Plotly Dash application.
*   **Core Logic**: `app.py` is the heart of the frontend, defining the UI, layout, and all user interaction logic.
*   **Backend Services**: The frontend is highly dependent on three separate backend microservices:
    1.  **Agent API** (`http://localhost:8001`): Powers the chat and voice AI features.
    2.  **MCP Tool Server** (`http://localhost:8000`): Handles data operations, database resets, and metadata management.
    3.  **DataOps Orchestrator** (`http://localhost:8002`): Manages the processing of large data files (NetCDF).

---

### Key Single Points of Failure

Here are the critical areas where the application is most likely to fail:

#### 1. Hardcoded API URLs

*   **The Problem**: In `app.py`, the URLs for all three backend services are hardcoded as constants (`AGENT_API_URL`, `MCP_API_URL`, `DATAOPS_API_URL`).
*   **Why It Fails**: If any backend service is down, running on a different port, or on another machine, the frontend features that rely on it will break. There's no dynamic way to discover or configure these services.
*   **How to Debug**:
    *   The `start_frontend.py` script includes a basic health check that runs at startup. Pay attention to its output.
    *   Manually verify each service is running by using a tool like `curl` in your terminal. For example, to check the Agent API, run:
        ```bash
        curl http://localhost:8001/health
        ```
    *   If a feature fails, the first step is to confirm the corresponding backend service is running and accessible at its hardcoded address.

#### 2. The Voice AI Integration

*   **The Problem**: The voice feature is entirely dependent on the `/voice/start` and `/voice/stop` endpoints of the **Agent API**.
*   **Why It Fails**: This is a classic single point of failure. If the Agent API's voice handler has a bug, is misconfigured, or the service is down, the entire voice functionality will cease to work. The frontend simply shows a "service unavailable" message without any fallback.
*   **How to Debug**:
    1.  **Browser DevTools**: Open your browser's developer tools (F12), go to the "Network" tab, and click the voice button. Look for the request to `/voice/start`. If it's red or shows an error (like 500 or 404), the problem is with the backend.
    2.  **Agent Logs**: Check the terminal logs for the Agent API service (`sih25/AGENT/api.py`). It will contain detailed error messages.
    3.  **Direct API Test**: Use `curl` to bypass the frontend and test the endpoint directly:
        ```bash
        curl -X POST -H "Content-Type: application/json" -d '{"session_id": "my-test-session"}' http://localhost:8001/voice/start
        ```
        The response from this command will tell you if the backend itself is the source of the issue.

#### 3. Fragile Error Handling

*   **The Problem**: The `try...except` blocks in the frontend code are good for preventing crashes, but they provide generic error messages to the user (e.g., "I'm having trouble connecting...").
*   **Why It Fails (for debugging)**: As a developer, these generic messages hide the root cause. You are forced to dig through logs to understand what really happened (e.g., a timeout, a server error, or a network failure).
*   **How to Debug**: Always keep an eye on the terminal where you launched the frontend (`start_frontend.py`) and, more importantly, the terminals for each of the three backend services. The real, detailed error messages will be there.

#### 4. File Processing Timeouts

*   **The Problem**: The file upload feature has a hardcoded `timeout` (e.g., 60 seconds for profile data).
*   **Why It Fails**: If a large file takes longer than the timeout period to upload and process, the frontend will report a failure, even if the backend is still working correctly.
*   **How to Debug**:
    *   Start by testing with very small files to confirm the pipeline works.
    *   Monitor the logs of the **DataOps** (`sih25/DATAOPS/main.py`) and **MCP** (`sih25/API/main.py`) services for any processing errors.

---

### A Beginner's Debugging Workflow

Here is a simple, structured way to approach debugging this application:

1.  **Start All Services**: Open separate terminals and run the frontend and all three backend services. Make sure none of them crash on startup.
2.  **Use Browser DevTools (F12)**:
    *   **Network Tab**: This is your most important tool. Watch the network requests as you use the app. Red-colored requests indicate an error. Click on them to inspect the response from the server.
    *   **Console Tab**: Check for any errors printed here.
3.  **Check All Logs**: When an error occurs, systematically check the terminal output for the frontend and all three backend services. One of them will almost certainly contain a detailed error message that points to the root cause.
4.  **Isolate the Backend**: If you suspect a backend issue, use `curl` to interact with it directly. This proves whether the problem is in the backend logic or in the frontend's handling of it.
