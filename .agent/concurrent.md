# Pipeline System Overview (Watcher + UI + Execution)

## 1. System Purpose

This system automates a file processing pipeline:

- Detect `.skp` file changes
- Upload file to remote service
- Poll for processed output
- Extract results into structured folders
- Optionally run Blender processing
- Expose control via UI (FastAPI / Quart)

---

## 2. Core Architecture

```

File System (.skp folder)
↓
File Watcher (watchdog)
↓
Pipeline Manager (routing + control)
↓
Pipeline (per file / per level)
↓
External services (upload API, Blender, etc.)

```

---

## 3. Pipeline Concept

Each file is processed through a **Pipeline instance**.

### Responsibilities:
- Upload file
- Fetch processing token
- Poll for result
- Download ZIP output
- Extract into structured directories

### Key rule:
> One file = one pipeline execution instance

---

## 4. Pipeline Registry

Manages multiple pipelines by “level”.

### Structure:
```

.skp/
v1/
level_a/
level_b/

```

### Behavior:
- Each level gets its own Pipeline instance
- Prevents mixing state across levels
- Enables parallel execution per level (if needed)

---

## 5. Watcher System

Built using `watchdog`.

### Responsibilities:
- Monitor `.skp` directory
- Detect file changes (modified / created / moved)
- Trigger pipeline execution

### Key events handled:
- `on_modified`
- `on_created`
- `on_moved`

### Important:
Use debouncing to avoid duplicate triggers from editors.

---

## 6. Execution Models

### Option A — Threading (Recommended)

```

Watcher → ThreadPool → Pipeline

```

- Simple
- Stable
- Works with blocking code (requests, Blender)
- Best default choice

---

### Option B — Async (Quart + asyncio)

```

Quart API → asyncio → ThreadPool → Pipeline

```

Used for:
- UI responsiveness
- API control
- concurrent job submission

⚠️ Important:
Pipeline itself is still blocking → must run in thread pool.

---

### Option C — Full Async (NOT recommended)

Not suitable because:
- `requests` is blocking
- Blender subprocess is blocking
- file IO is blocking

---

## 7. Concurrency Model

### Safe assumption used:
- No pipeline conflicts
- Only one active mode (watch OR manual OR UI trigger)

### Execution control:
- ThreadPoolExecutor handles concurrency
- Max workers typically = 1 or small number

---

## 8. UI Integration (FastAPI / Quart)

### Responsibilities:
- Start/stop watcher
- Trigger manual pipeline runs
- Switch between modes (watch/manual)
- Display status (future upgrade)

### Example endpoints:

- `POST /run` → run pipeline manually
- `POST /watcher/start` → enable watcher mode
- `POST /watcher/stop` → disable watcher mode

---

## 9. Logging System

### Features:
- Custom log levels (e.g. SUCCESS = 25)
- Pipeline-aware logging (pipeline name included)
- Structured formatting

### Example format:
```

[INFO   ] [upload      ] File uploaded
[SUCCESS] [extract     ] Extraction complete

```

### Pipeline-aware logging:
Each pipeline attaches its identifier to logs:
```

[PIPELINE_A] Uploading file...

```

---

## 10. Blender Integration

### Execution method:
- Subprocess call via `subprocess.Popen`

### Logging:
- stdout captured and forwarded to pipeline logs

### Important constraint:
- Only one Blender process should run at a time (recommended)

---

## 11. Failure Handling

Current approach:
- Minimal retry logic (can be expanded)
- Pipeline fails per-file independently
- Watcher continues running

Future improvements:
- Retry system per stage
- Job timeout handling
- Error state tracking per file

---

## 12. Recommended Improvements (Future)

### High priority:
- Job queue (for safer concurrency control)
- Retry system per pipeline step
- Pipeline status tracking

### Medium priority:
- WebSocket live logs to UI
- Progress percentage per stage
- Cancel running pipelines

### Advanced:
- Distributed pipeline workers
- Blender execution isolation layer
- Persistent job recovery system

---

## 13. Mental Model

```

Watcher / UI
↓
Pipeline Manager
↓
ThreadPoolExecutor
↓
Pipeline Instance
↓
External systems (API, Blender, filesystem)

```

---

## 14. Key Design Rules

- Pipeline = stateless execution unit (per run)
- Watcher = event detector only
- UI = control layer only
- Execution = thread-managed (not async-only)
- Logging = centralized and pipeline-aware

---

## 15. Summary

This system is a hybrid architecture:

- Event-driven (watcher)
- Request-driven (UI)
- Thread-executed (pipeline)
- Optionally async-controlled (Quart layer)

It prioritizes:
- reliability over complexity
- controlled concurrency over full async
- clear separation of concerns over tight coupling

