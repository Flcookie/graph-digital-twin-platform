# Graph Digital Twin Platform

Implementation of an Event Knowledge Graph pipeline for industrial digital twins.

## System Pipeline

```
MQTT (component_event)
    ↓
event_buffer (out-of-order handling)
    ↓
├─→ neo4j_writer  →  Neo4j Event Knowledge Graph
└─→ kpi_calculator  →  Real-time KPI (Throughput, WIP, Flow Time, Utilization)
```

## Repository Structure

| File | Purpose |
|------|---------|
| `main_service.py` | Main service: MQTT → buffer → Neo4j + KPI (run this for live/replay) |
| `event_buffer.py` | Event buffer for MQTT out-of-order handling |
| `kpi_calculator.py` | KPI engine (Throughput, WIP, Flow Time, Utilization, state_probability) |
| `neo4j_writer.py` | Writes events into the Neo4j graph |
| `record_events.py` | MQTT consumer, saves event log CSV |
| `replay_events.py` | Replay event log CSV to MQTT for testing |
| `schema.cypher` | Graph schema definition |
| `config.example.json` | Example config (copy to `config.json`) |

## Quick Start

1. Copy `config.example.json` to `config.json` and set Neo4j password.
2. Start MQTT broker and Neo4j.
3. **Live mode**: `python main_service.py`
4. **Replay mode** (no physical system):
   - Terminal 1: `python main_service.py --replay`
   - Terminal 2: `python replay_events.py` (or `python replay_events.py path/to/event_log.csv`)

## Weekly Progress

- [Week 2 Progress](progress/week2.md)
- [Week 3 Progress](progress/week3.md)
