import json
import collections


def load_json(path):
    with open(path, encoding="utf-8") as file:
        return json.load(file, object_pairs_hook=lambda p: collections.OrderedDict(p))

def render_topic(context, source_id, target_id):
    return "/".join([context, source_id, target_id])

def parse_topic(topic):
    return tuple(topic.split("/"))

def serialize_object(object_):
    return json.dumps(object_, separators=(",", ":"))

def deserialize_object(string):
    return json.loads(string, object_pairs_hook=lambda p: collections.OrderedDict(p))
