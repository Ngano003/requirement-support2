# Requirements Review AI - Web App Implementation Plan (v3.2)

## Phase 3: Web App Development (Streamlit)

### 1. Architecture & Tech Stack
- **App**: `streamlit`
- **Graph Viz**: `streamlit-agraph` (interactive) or `pyvis` (static HTML embedding). *Decision: Use `streamlit-agraph` for click events.*
- **Log Streaming**: Python `logging` + Streamlit textual output widget.
- **Config**: `pydantic-settings` or simple `yaml` loader.

### 2. Directory Structure (Updated)
```
workspace/
  ├── app.py                  # Main UI
  ├── config.yaml             # Default config
  ├── src/
  │   ├── analyzer.py         # Core Analysis
  │   ├── history_manager.py  # [NEW] Manages result versions 
  │   ├── log_handler.py      # [NEW] Stream logs to UI
  │   ├── extractors/
  │       ├── text_splitter.py # [NEW] Overlap logic
  │       └── ...
  └── projects/
      └── {project_name}/
            ├── config.yaml   # Project specific config
            ├── inputs/       # Source docs
            └── reports/      # History storage
                └── {timestamp}/
                    ├── graph.json
                    └── report.md
```

### 3. Detailed Implementation Steps

#### Step 1: Base Application & Project/History Management
- Create `HistoryManager` class to handle timestamped folders.
- Implement sidebar for Project selection and History browsing.

#### Step 2: Input & Extraction with Overlap
- Implement `TextSplitter` with `chunk_size` and `overlap`.
- Implement `All-or-Nothing` error handling logic in the extraction loop.

#### Step 3: Analysis Pipeline & Real-time Logging
- Setup a custom `logging.Handler` that queues messages to display in Streamlit.
- Integrate existing `analyzer.py` logic.

#### Step 4: Visualization & Interaction
- Implement Graph Filtering (slider to hide low-degree nodes).
- Implement Evidence Tracing: Ensure JSON outcome includes source snippets, and display them on edge click.

#### Step 5: Docker Packaging
- Finalize `Dockerfile` for easy deployment.

## Next Step
Start with **Step 1: Base Application**.
