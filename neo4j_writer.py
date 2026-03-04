from neo4j import GraphDatabase
import uuid
import json

# Load Neo4j config from config.json
with open("config.json", encoding="utf-8") as f:
    _config = json.load(f)

_neo4j_cfg = _config["neo4j"]
NEO4J_URI = _neo4j_cfg["uri"]
NEO4J_USER = _neo4j_cfg["username"]
NEO4J_PASSWORD = _neo4j_cfg["password"]

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Track last event per part (for correct DF relationship)
# Key: part_id, Value: event_id of the last event for that part
_last_event_per_part: dict[str, str] = {}


def write_event_to_graph(event: dict):
    """
    Write one event into the Neo4j knowledge graph.

    Required fields in event:
        time        - timestamp (float or int)
        station_id  - e.g. "S1"
        part_id     - e.g. "P1"
        part_type   - e.g. "part"
        activity    - e.g. "START", "PROCESS", "END"
    """
    event_id = str(uuid.uuid4())
    part_id = event["part_id"]

    with driver.session() as session:
        session.execute_write(_create_event_tx, event_id, event)

        # DF: only connect events of the SAME part
        previous_id = _last_event_per_part.get(part_id)
        if previous_id is not None:
            session.execute_write(_create_df_tx, previous_id, event_id)

    _last_event_per_part[part_id] = event_id


def _create_event_tx(tx, event_id, event):
    query = """
    MERGE (e:Event {id: $event_id})
    SET e.time = $time

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
        time=event["time"],
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
    """Call this when shutting down to cleanly close the Neo4j connection."""
    driver.close()