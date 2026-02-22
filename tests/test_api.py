from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


def setup_test_client() -> TestClient:
    engine = create_engine("sqlite:///./test_jobs_automation.db", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def seed_profile(client: TestClient) -> None:
    payload = {
        "full_name": "Jeet Joshi",
        "email": "jeet@example.com",
        "skills": ["Python", "FastAPI", "SQL", "Kubernetes"],
        "achievements": ["Scaled API to 10M requests/day"],
        "preferences": {"remote_preferred": True},
        "raw_profile": {"linkedin_url": "https://linkedin.com/in/example"},
        "cv_variants": [
            {"name": "Backend CV", "content": "Backend-focused CV", "metadata": {"style": "concise"}},
            {"name": "Platform CV", "content": "Platform-focused CV", "metadata": {"style": "impact"}},
        ],
        "targeting_policy": {
            "role_families": ["backend", "platform"],
            "geos": ["US"],
            "seniority": ["senior"],
            "compensation": {"min": 150000},
            "must_have": ["python"],
            "avoid": [],
            "suppression_companies": [],
            "suppression_domains": [],
            "daily_rate_limits": {"application": 40, "outreach": 40},
        },
    }
    response = client.post("/ingest/profile", json=payload)
    assert response.status_code == 200
    assert response.json()["profile_version_id"] == 1


def test_end_to_end_workflow() -> None:
    client = setup_test_client()
    seed_profile(client)

    discover = client.post("/jobs/discover/run", json={"source_config_id": "daily-all"})
    assert discover.status_code == 200
    # 6 discovered - 1 duplicate from mocked sources
    assert discover.json()["discovered_count"] == 5

    queue_response = client.get("/jobs/queue", params={"status": "pending_review"})
    assert queue_response.status_code == 200
    batches = queue_response.json()
    assert len(batches) == 1
    batch = batches[0]
    assert batch["item_count"] == 5
    assert len(batch["items"]) == 5

    # Verify cover-letter conditional behavior exists in generated set.
    cover_letters = [item["cover_letter"] for item in batch["items"]]
    assert any(letter is None for letter in cover_letters)
    assert any(letter is not None for letter in cover_letters)

    decisions = {
        "decisions": [
            {"batch_item_id": batch["items"][0]["batch_item_id"], "decision": "approve"},
            {"batch_item_id": batch["items"][1]["batch_item_id"], "decision": "reject"},
        ]
    }
    decision_response = client.post(f"/review/batch/{batch['batch_id']}/decision", json=decisions)
    assert decision_response.status_code == 200
    body = decision_response.json()
    assert body["approved_count"] == 1
    assert body["rejected_count"] == 1
    assert body["deferred_count"] == 0

    run_response = client.post(f"/execute/plan/{body['execution_plan_id']}")
    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["status"] == "completed"
    # 1 approved queue item generates 2 actions (apply + outreach).
    assert len(run_data["items"]) == 2
    assert all(item["status"] == "success" for item in run_data["items"])

    funnel_response = client.get("/analytics/funnel")
    assert funnel_response.status_code == 200
    funnel = funnel_response.json()
    assert funnel["applied"] == 1
    assert funnel["replied"] == 0
    assert funnel["interview"] == 0
    assert funnel["offers"] == 0


def test_autonomous_daily_orchestrator_run() -> None:
    client = setup_test_client()
    seed_profile(client)

    run = client.post("/orchestrator/run-daily", json={"source_config_id": "autonomous-v1"})
    assert run.status_code == 200
    payload = run.json()
    assert payload["discovered_count"] == 5
    assert payload["approved_items"] == 5
    # 5 approved items, each with apply + outreach.
    assert payload["executed_items"] == 10
    assert payload["followups_created"] == 5
    assert payload["tracking_snapshot_path"]

    tracking_info = client.get("/tracking/snapshot-path")
    assert tracking_info.status_code == 200
    assert tracking_info.json()["exists"] is True

    dashboard_data = client.get("/dashboard/data")
    assert dashboard_data.status_code == 200
    payload = dashboard_data.json()
    assert "kpis" in payload
    assert "recent_events" in payload
    assert "top_targets" in payload

    vc_filtered = client.get("/dashboard/data", params={"role_family": "vc"})
    assert vc_filtered.status_code == 200
    vc_payload = vc_filtered.json()
    assert "top_targets" in vc_payload

    dashboard_ui = client.get("/dashboard")
    assert dashboard_ui.status_code == 200
    assert "Job Ops Command Deck" in dashboard_ui.text
    assert "Top Targets (VC / Consulting / High-Pay)" in dashboard_ui.text


def test_apply_now_action_executes_single_job() -> None:
    client = setup_test_client()
    seed_profile(client)
    discover = client.post("/jobs/discover/run", json={"source_config_id": "apply-now"})
    assert discover.status_code == 200

    dash = client.get("/dashboard/data")
    assert dash.status_code == 200
    queue = dash.json()["queue_preview"]
    assert queue
    job_id = queue[0]["job_id"]

    apply_response = client.post(f"/actions/apply-now/{job_id}")
    assert apply_response.status_code == 200
    payload = apply_response.json()
    assert payload["job_id"] == job_id
    assert len(payload["results"]) == 2
    assert all(item["status"] == "success" for item in payload["results"])
