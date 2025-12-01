from .db_client import call_database


def get_person_by_name(name: str) -> dict | None:
    query_data = {
        "query": """
            MATCH (p:Person {name: $name})
            RETURN p
            LIMIT 1
        """,
        "parameters": {
            "name": name
        }
    }

    result = call_database("POST", "query/cypher", query_data)

    if result.get("results") and len(result["results"]) > 0:
        record = result["results"][0]
        if "p" in record:
            return record["p"]

    return None


def person_exists(name: str) -> bool:
    return get_person_by_name(name) is not None


def get_file_by_person_and_filename(person_name: str, filename: str) -> dict | None:
    query_data = {
        "query": """
            MATCH (p:Person {name: $person_name})-[:UPLOADED]->(f:File {filename: $filename})
            RETURN f
            LIMIT 1
        """,
        "parameters": {
            "person_name": person_name,
            "filename": filename
        }
    }

    result = call_database("POST", "query/cypher", query_data)

    if result.get("results") and len(result["results"]) > 0:
        record = result["results"][0]
        if "f" in record:
            return record["f"]

    return None


def file_exists_for_person(person_name: str, filename: str) -> bool:
    return get_file_by_person_and_filename(person_name, filename) is not None
