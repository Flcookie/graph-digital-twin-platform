from neo4j import GraphDatabase
import uuid
import json
import datetime

import common

# neo4j_writer - write events to graph DB, config from config.json
_config = common.load_json("config.json")
_neo4j_cfg = _config["neo4j"]
NEO4J_URI = _neo4j_cfg["uri"]
NEO4J_USER = _neo4j_cfg["username"]
NEO4J_PASSWORD = _neo4j_cfg["password"]

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

_last_event_per_part: dict[str, str] = {}


def _to_neo4j_format(event: dict) -> dict | None:
    """Convert physical event (time/component_id) to neo4j format (timestamp/station_id)."""
    time_str = event.get("time")
    if not time_str:
        return None
    ts = datetime.datetime.fromisoformat(time_str).timestamp()
    return {
        "timestamp": ts,
        "station_id": event.get("component_id", ""),
        "part_id": event.get("part_id", ""),
        "part_type": event.get("part_type", "part"),
        "activity": event.get("activity", ""),
    }


def write_event_to_graph(event: dict):
    """Write one event to Neo4j. Accepts physical or neo4j format."""
    if "time" in event and "timestamp" not in event:
        event = _to_neo4j_format(event)
        if event is None:
            return
    event_id = str(uuid.uuid4())
    part_id = event["part_id"]

    with driver.session() as session:
        session.execute_write(_create_event_tx, event_id, event)

        # DF edge: same part's consecutive events
        previous_id = _last_event_per_part.get(part_id)
        if previous_id is not None:
            session.execute_write(_create_df_tx, previous_id, event_id)

    _last_event_per_part[part_id] = event_id


def _create_event_tx(tx, event_id, event):
    query = """
    MERGE (e:Event {id: $event_id})
    SET e.timestamp = $timestamp,
        e.label = $activity + "@" + toString($timestamp)

    MERGE (s:Station {sysId: $station_id})
    MERGE (en:Entity {sysId: $part_id})
    MERGE (et:EntityType {name: $part_type})
    MERGE (a:Activity {name: $activity})

    MERGE (e)-[:OCCURRED_AT]->(s)
    MERGE (e)-[:ACTS_ON]->(en)
    MERGE (en)-[:OF_TYPE]->(et)
    MERGE (e)-[:OF_ACTIVITY]->(a)
    """
    tx.run(
        query,
        event_id=event_id,
        timestamp=event["timestamp"],
        station_id=event["station_id"],
        part_id=event["part_id"],
        part_type=event["part_type"],
        activity=event["activity"],
    )


def _create_df_tx(tx, previous_id, current_id):
    query = """
    MATCH (e1:Event {id: $previous_id})
    MATCH (e2:Event {id: $current_id})
    MERGE (e1)-[:DF]->(e2)
    """
    tx.run(query, previous_id=previous_id, current_id=current_id)


def close():
    """Close Neo4j connection."""
    driver.close()