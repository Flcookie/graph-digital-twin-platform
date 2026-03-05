# Graph Digital Twin Platform

Implementation of an Event Knowledge Graph pipeline for industrial digital twins.

## System Pipeline

MQTT → Event ingestion → Neo4j Event Knowledge Graph

## Repository Structure

- `record_events.py` – MQTT consumer for event ingestion  
- `neo4j_writer.py` – writes events into the graph  
- `send_test_events.py` – event simulator  
- `schema.cypher` – graph schema definition  

## Weekly Progress

- [Week 2 Progress](progress/week2.md)

## Future Work

- Connect to LEGO factory physical system
- Real-time digital twin visualization
- Process mining analysis