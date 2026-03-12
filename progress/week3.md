# Week 3 Progress – Event Buffer, KPI Calculation & Main Service Integration

> Reporting period: Full implementation built on top of Week 2

---

## 1. Project Background

The project is the Graph Digital Twin Platform, implementing an Event Knowledge Graph pipeline for industrial digital twins. The physical system (mt-ems-pl) publishes `component_event` via MQTT with fields: `time`, `component_id`, `part_id`, `activity` (e.g. LOAD, PROCESS, UNLOAD, TRANSFER, PASS, BLOCK, FAIL, FINISH, SCRAP).

**This week's goals:**
1. Event buffering (resolve MQTT out-of-order delivery)
2. Map physical event format to Neo4j graph database
3. Real-time KPI calculation (Throughput, WIP, Flow Time, Utilization)
4. Main service integration: MQTT → buffer → Neo4j + KPI printing
5. Replay mode for offline testing

---

## 2. New / Modified Files

### 2.1 New Files

| File | Purpose |
|------|---------|
| `event_buffer.py` | Event buffer to handle short-term MQTT out-of-order delivery |
| `kpi_calculator.py` | KPI engine (Throughput, WIP, Flow Time, Utilization, state_probability) |
| `main_service.py` | Main service: MQTT subscribe → buffer → Neo4j write + KPI calculation + real-time print |
| `replay_events.py` | Replay event log CSV to MQTT for main_service testing |

### 2.2 Modified Files

| File | Changes |
|------|----------|
| `neo4j_writer.py` | Read Neo4j config from config; support physical event format (time/component_id) mapping |
| `config.example.json` | Added `neo4j`, `event_buffer`, `kpi_config`, `log_folder` config |

### 2.3 Data Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Event log CSV | `logs/event_log_YYMMDD_HHMMSS.csv` | Saved when record_events.py receives Ctrl+C |
| KPI log TXT | `event-logs/kpi_log_YYMMDD_HHMMSS.txt` | New file created per main_service.py run |

---

## 3. Problems Solved & Implementation

### 3.1 Problem 1: MQTT Event Out-of-Order

**Issue**: Network latency can cause events to arrive in a different order than their occurrence time.

**Solution**:
- Added `event_buffer.py`
- **Time window + bisect insert sort**: New events are inserted by timestamp into a sorted list
- Only output events with `timestamp < now - window_ms`, considered stable
- Use `threading.Lock` for thread safety between MQTT and main thread
- Default `window_ms` 300ms, configurable in config

### 3.2 Problem 2: Physical Event Format Mapping to Neo4j

**Solution**:
- Modified `neo4j_writer.py` to read Neo4j connection from config
- Added `_to_neo4j_format()`: convert physical event (time/component_id) to Neo4j format (timestamp/station_id)
- Each event creates an Event node linked to Station, Entity, Activity
- Consecutive events for the same part are connected with DF (directly follows) edges, Process Mining style

### 3.3 Problem 3: KPI Calculation

**Solution**:
- Added `kpi_calculator.py`, event-driven KPI updates
- No full history storage, only maintain state variables

**KPI definitions:**

| KPI | Definition | Implementation |
|-----|-------------|----------------|
| **Throughput** | Successful completions / observation time | Count when `activity == "FINISH"` |
| **WIP** | Current work-in-progress count | LOAD (first occurrence) → +1; FINISH / SCRAP → -1 |
| **Flow Time** | Average completion time | `FINISH_time - first_LOAD_time`, only successfully completed parts |
| **Utilization** | Station utilization | PROCESSING time / observation time |
| **state_probability** | Time share per state | State accumulation (LOADING, BLOCKED, IDLE, PROCESSING, UNLOADING) |

**Design decisions:**
- **Start**: Part's first LOAD (any station), not tied to fixed start_station, more robust to routing changes
- **Finish**: `activity == "FINISH"` (at splitter5 etc., not a station)
- **Scrap**: `activity == "SCRAP"`, scrapped parts excluded from throughput and flow_time
- **FAIL**: Station fault, not counted as scrap, only used for station state FAILED

### 3.4 Problem 4: Main Service Integration

**Solution**:
- Added `main_service.py`:
  - Subscribe to MQTT `component_event`
  - Store events in buffer
  - Call `flush_ready()` every 0.3s to get stable events
  - For each event: write to Neo4j + update KPI
  - Print KPI snapshot every 2 seconds (throughput, finished, scrap, wip, avg_flow_time, per-station utilization and state_probability)
  - Also write KPI to `event-logs/kpi_log_YYMMDD_HHMMSS.txt`

### 3.5 Problem 5: Replay Mode for Testing

**Solution**:
- Added `replay_events.py`: Read event log CSV, simulate sending to MQTT with time intervals
- main_service supports `--replay`: `observation_time_mode` uses `last_event_ts - first_event_ts` instead of `now()`, suitable for historical replay

---

## 4. Technical Architecture

```
Physical System (mt-ems-pl)
    ↓ MQTT (component_event)
    ├─→ record_events.py  →  logs/event_log_YYMMDD_HHMMSS.csv
    └─→ main_service.py
            ↓
        event_buffer (300ms window, sorted by time)
            ↓ flush_ready()
            ├─→ neo4j_writer  →  Neo4j Event Knowledge Graph
            └─→ kpi_calculator  →  KPI snapshot (print + kpi_log.txt)
```

**Local testing (no physical system):**
- Terminal 1: `python main_service.py --replay`
- Terminal 2: `python replay_events.py` (or specify CSV path)

---

## 5. config.json New Configuration

```json
{
  "neo4j": {
    "uri": "bolt://localhost:7687",
    "username": "neo4j",
    "password": "xxx"
  },
  "mqtt_broker_host": "localhost",
  "mqtt_broker_port": 1883,
  "event_buffer": {
    "window_ms": 300,
    "max_size": 200
  },
  "kpi_config": {
    "observation_time_mode": "realtime",
    "finish_events": ["FINISH"],
    "scrap_events": ["SCRAP"]
  },
  "log_folder": "event-logs"
}
```

---

## 6. KPI Snapshot Example

```
[KPI] throughput=0.05, finished=2, scrap=1, obs_time=120.5s, wip=6, avg_flow_time=45.2s
  station11
    Utilization: 0.52
    Loading: 0.18  Blocked: 0.00  Idle: 0.02  Processing: 0.52  Unloading: 0.28
  ...
```

---

## 7. Relation to Process Mining

The current event format (time, component_id, part_id, activity) is similar to industrial Process Mining logs (e.g. XES), and can be seen as a base implementation of **Streaming Process Mining + Digital Twin**.

---

## 8. Future Extensions

- Frontend UI for KPI visualization
- Process Mining analysis (process discovery, conformance checking, etc.)
- Clear Neo4j or use separate database before each experiment
- Connect to physical LEGO factory system for validation
