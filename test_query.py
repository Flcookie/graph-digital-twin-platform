from neo4j import GraphDatabase

URI = "bolt://localhost:7687"
USER = "neo4j"
PASSWORD = "password"

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))


def create_event(tx, sys_id, timestamp):
    tx.run("""
        CREATE (e:Event {
            sysId: $id,
            timestamp: $ts
        })
    """, id=sys_id, ts=timestamp)


def get_all_events(tx):
    result = tx.run("""
        MATCH (e:Event)
        RETURN e.sysId AS id, e.timestamp AS ts
        ORDER BY e.timestamp
    """)
    return [(record["id"], record["ts"]) for record in result]


if __name__ == "__main__":

    with driver.session() as session:

        session.execute_write(create_event, "E4", 400)

        events = session.execute_read(get_all_events)

        print("Current Events in DB:")
        for e in events:
            print(e)

    driver.close()