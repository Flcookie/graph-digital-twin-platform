import csv
from neo4j_writer import write_event_to_graph, close as neo4j_close

CSV_PATH = "data/test_log.csv"

with open(CSV_PATH, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    # CSV rows must be sorted by time already (or sort before importing)
    for row in reader:
        event = {
            "timestamp": float(row["timestamp"]),
            "station_id": row["station_id"],
            "part_id": row["part_id"],
            "part_type": row["part_type"],
            "activity": row["activity"],
        }
        write_event_to_graph(event)

neo4j_close()
print("CSV import finished.")




























