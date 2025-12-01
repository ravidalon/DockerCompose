"""Integration tests for fileshare service with database verification."""

import io
import requests


def test_person_creation_in_database(fileshare_url, neo4j_driver, cleanup_test_data):
    """Test that creating a person via API creates a node in Neo4j."""
    person_name = "TestUser_PersonCreation"
    email = "testuser_personcreation@test.com"
    response = requests.post(
        f"{fileshare_url}/persons",
        json={"name": person_name, "email": email}
    )
    assert response.status_code in [200, 201]

    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (p:Person {name: $name}) RETURN p.name, p.email",
            name=person_name
        )
        record = result.single()
        assert record is not None, "Person not found in database"
        assert record["p.name"] == person_name
        assert record["p.email"] == email


def test_file_upload_creates_nodes_and_relationships(
    fileshare_url, neo4j_driver, test_person
):
    """Test that uploading a file creates File node and UPLOADED relationship."""
    filename = "test_upload.txt"
    file_content = b"Test file content for upload"
    files = {"file": (filename, io.BytesIO(file_content), "text/plain")}
    data = {"person": test_person}

    response = requests.post(f"{fileshare_url}/files/upload", files=files, data=data)
    assert response.status_code in [200, 201]

    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (f:File {filename: $filename}) RETURN f.filename, f.size, f.content_type",
            filename=filename
        )
        record = result.single()
        assert record is not None, "File node not found in database"
        assert record["f.filename"] == filename
        assert record["f.size"] == len(file_content)
        assert record["f.content_type"] == "text/plain"

    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person {name: $person_name})-[r:UPLOADED]->(f:File {filename: $filename})
            RETURN r, r.timestamp
            """,
            person_name=test_person,
            filename=filename
        )
        record = result.single()
        assert record is not None, "UPLOADED relationship not found in database"
        assert record["r.timestamp"] is not None


def test_file_download_creates_relationship(fileshare_url, neo4j_driver, test_person):
    """Test that downloading a file creates DOWNLOADED relationship."""
    filename = "test_download.txt"
    file_content = b"Test file for download"
    files = {"file": (filename, io.BytesIO(file_content), "text/plain")}
    data = {"person": test_person}

    response = requests.post(f"{fileshare_url}/files/upload", files=files, data=data)
    assert response.status_code in [200, 201]

    response = requests.get(
        f"{fileshare_url}/files/{test_person}/{filename}/download"
    )
    assert response.status_code == 200
    assert response.content == file_content

    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person {name: $person_name})-[r:DOWNLOADED]->(f:File {filename: $filename})
            RETURN count(r) as download_count
            """,
            person_name=test_person,
            filename=filename
        )
        record = result.single()
        assert record is not None
        assert record["download_count"] == 1, "DOWNLOADED relationship not found"


def test_file_edit_creates_relationship(fileshare_url, neo4j_driver, test_person):
    """Test that editing a file creates EDITED relationship."""
    filename = "test_edit.txt"
    original_content = b"Original content"
    files = {"file": (filename, io.BytesIO(original_content), "text/plain")}
    data = {"person": test_person}

    response = requests.post(f"{fileshare_url}/files/upload", files=files, data=data)
    assert response.status_code in [200, 201]

    new_content = b"Edited content"
    files = {"file": (filename, io.BytesIO(new_content), "text/plain")}

    response = requests.put(
        f"{fileshare_url}/files/{test_person}/{filename}",
        files=files
    )
    assert response.status_code == 200

    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (p:Person {name: $person_name})-[r:EDITED]->(f:File {filename: $filename})
            RETURN count(r) as edit_count
            """,
            person_name=test_person,
            filename=filename
        )
        record = result.single()
        assert record is not None
        assert record["edit_count"] == 1, "EDITED relationship not found"


def test_batch_upload_creates_relationships(fileshare_url, neo4j_driver, test_person):
    """Test that batch uploading files creates UPLOADED_WITH relationships."""
    file1_name = "test_batch_1.txt"
    file2_name = "test_batch_2.txt"
    file1_content = b"Batch file 1"
    file2_content = b"Batch file 2"

    files = [
        ("files", (file1_name, io.BytesIO(file1_content), "text/plain")),
        ("files", (file2_name, io.BytesIO(file2_content), "text/plain"))
    ]
    data = {"person": test_person}

    response = requests.post(
        f"{fileshare_url}/files/upload/batch",
        files=files,
        data=data
    )
    assert response.status_code in [200, 201]

    with neo4j_driver.session() as session:
        result = session.run(
            "MATCH (f:File) WHERE f.filename IN [$file1, $file2] RETURN count(f) as file_count",
            file1=file1_name,
            file2=file2_name
        )
        record = result.single()
        assert record["file_count"] == 2, "Not all batch files found in database"

    with neo4j_driver.session() as session:
        result = session.run(
            """
            MATCH (f1:File {filename: $file1})-[r:UPLOADED_WITH]-(f2:File {filename: $file2})
            RETURN count(r) as relationship_count
            """,
            file1=file1_name,
            file2=file2_name
        )
        record = result.single()
        assert record is not None
        assert record["relationship_count"] >= 1, "UPLOADED_WITH relationship not found"
