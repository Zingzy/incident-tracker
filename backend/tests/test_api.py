def open_incident(client, **fields):
    body = {"title": "Checkout returns 502", "service": "checkout", "severity": "SEV2"} | fields
    response = client.post("/api/incidents", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_ready_checks_the_database(client):
    assert client.get("/ready").json() == {"status": "READY"}


def test_info_reports_environment(client):
    assert set(client.get("/api/info").json()) == {"site_title", "environment", "version"}


def test_create_incident_starts_open_with_a_note(client):
    incident = open_incident(client)
    assert incident["status"] == "open"
    assert incident["resolved_at"] is None
    assert [note["body"] for note in incident["notes"]] == ["Opened as SEV2 on checkout"]


def test_invalid_severity_is_rejected(client):
    response = client.post("/api/incidents", json={"title": "x", "service": "api", "severity": "SEV9"})
    assert response.status_code == 422


def test_list_newest_first(client):
    first = open_incident(client, title="first")
    second = open_incident(client, title="second")
    assert [i["id"] for i in client.get("/api/incidents").json()] == [second["id"], first["id"]]


def test_filters(client):
    open_incident(client, service="checkout", severity="SEV1")
    open_incident(client, service="search", severity="SEV3")
    resolved = open_incident(client, service="search", severity="SEV3")
    client.post(f"/api/incidents/{resolved['id']}/status", json={"status": "resolved"})
    assert len(client.get("/api/incidents", params={"severity": "SEV1"}).json()) == 1
    assert len(client.get("/api/incidents", params={"service": "search"}).json()) == 2
    assert len(client.get("/api/incidents", params={"status": "resolved"}).json()) == 1
    assert client.get("/api/incidents", params={"status": "closed"}).status_code == 422


def test_get_returns_timeline(client):
    incident = open_incident(client)
    detail = client.get(f"/api/incidents/{incident['id']}").json()
    assert detail["title"] == "Checkout returns 502"
    assert len(detail["notes"]) == 1


def test_update_incident(client):
    incident = open_incident(client)
    response = client.put(f"/api/incidents/{incident['id']}", json={"severity": "SEV1", "title": "Checkout down"})
    assert response.status_code == 200
    assert response.json()["severity"] == "SEV1"
    assert response.json()["title"] == "Checkout down"
    assert response.json()["service"] == "checkout"


def test_delete_incident_removes_notes(client):
    incident = open_incident(client)
    client.post(f"/api/incidents/{incident['id']}/notes", json={"body": "looking"})
    assert client.delete(f"/api/incidents/{incident['id']}").status_code == 204
    assert client.get(f"/api/incidents/{incident['id']}").status_code == 404
    assert client.get(f"/api/incidents/{incident['id']}/notes").status_code == 404


def test_missing_incident_returns_404(client):
    assert client.get("/api/incidents/999").status_code == 404
    assert client.put("/api/incidents/999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/incidents/999").status_code == 404
    assert client.post("/api/incidents/999/status", json={"status": "resolved"}).status_code == 404


def test_add_and_list_notes(client):
    incident = open_incident(client)
    note = client.post(f"/api/incidents/{incident['id']}/notes", json={"body": "Rolled back deploy 42"})
    assert note.status_code == 201
    bodies = [n["body"] for n in client.get(f"/api/incidents/{incident['id']}/notes").json()]
    assert bodies == ["Opened as SEV2 on checkout", "Rolled back deploy 42"]
    assert client.post(f"/api/incidents/{incident['id']}/notes", json={"body": ""}).status_code == 422


def test_status_change_sets_and_clears_resolved_at(client):
    incident = open_incident(client)
    url = f"/api/incidents/{incident['id']}/status"
    investigating = client.post(url, json={"status": "investigating"}).json()
    assert investigating["resolved_at"] is None
    resolved = client.post(url, json={"status": "resolved"}).json()
    assert resolved["status"] == "resolved"
    assert resolved["resolved_at"] is not None
    assert resolved["notes"][-1]["body"] == "Status investigating -> resolved"
    reopened = client.post(url, json={"status": "open"}).json()
    assert reopened["resolved_at"] is None


def test_stats(client):
    open_incident(client, severity="SEV1")
    open_incident(client, severity="SEV1")
    open_incident(client, severity="SEV4")
    done = open_incident(client, severity="SEV2")
    client.post(f"/api/incidents/{done['id']}/status", json={"status": "resolved"})
    body = client.get("/api/stats").json()
    assert body["open"] == 3
    assert body["open_by_severity"] == {"SEV1": 2, "SEV2": 0, "SEV3": 0, "SEV4": 1}
    assert body["resolved"] == 1
    assert body["mean_time_to_resolve_seconds"] >= 0


def test_metrics_expose_incident_counters(client):
    incident = open_incident(client, severity="SEV1")
    client.post(f"/api/incidents/{incident['id']}/status", json={"status": "resolved"})
    open_incident(client, severity="SEV3")
    body = client.get("/metrics").text
    assert 'incidents_created_total{severity="SEV1"}' in body
    assert "incidents_resolved_total" in body
    assert "incidents_open 1.0" in body
    assert "incidents_time_to_resolve_seconds_count" in body
    assert "http_requests_total" in body
