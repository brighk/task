import respx
import httpx
from fastapi.testclient import TestClient
import main

TEST_WEBHOOK_URL = "https://example.test/slack-webhook"


@respx.mock
def test_warning_notification_is_queued_and_forwarded(monkeypatch):
    monkeypatch.setattr(main, "SLACK_WEBHOOK_URL", TEST_WEBHOOK_URL)

    route = respx.post(TEST_WEBHOOK_URL).mock(return_value=httpx.Response(200, text="ok"))
    
    warning_payload = {
        "Type": "Warning",
        "Name": "Backup Failure",
        "Description": "The backup failed due to a database problem",
        "ServerID": "db-prod-01",
        "Timestamp": "2026-05-27T10:00:00Z"
    }

    with TestClient(main.app) as client:
        response = client.post("/notifications", json=warning_payload)
    
    assert response.status_code == 200
    assert response.json() == {"status": "queued", "name": "Backup Failure"}
    assert route.called


@respx.mock(assert_all_called=False)
def test_info_notification_is_ignored(monkeypatch):
    monkeypatch.setattr(main, "SLACK_WEBHOOK_URL", TEST_WEBHOOK_URL)

    route = respx.post(TEST_WEBHOOK_URL).mock(return_value=httpx.Response(200, text="ok"))

    info_payload = {
        "Type": "Info",
        "Name": "Quota Exceeded",
        "Description": "Compute Quota exceeded",
        "User": "admin_user_9"
    }

    with TestClient(main.app) as client:
        response = client.post("/notifications", json=info_payload)
    
    assert response.status_code == 200
    assert response.json() == {
        "status": "ignored", 
        "reason": "Info messages are skipped", 
        "name": "Quota Exceeded"
    }

    assert not route.called


def test_unknown_notification_type_is_ignored():
    unknown_payload = {
        "Type": "Debug",
        "Name": "Trace Event",
        "Description": "This is only useful during debugging"
    }

    with TestClient(main.app) as client:
        response = client.post("/notifications", json=unknown_payload)

    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "reason": "Unknown notification type"}


def test_warning_notification_fails_when_webhook_url_is_missing(monkeypatch):
    monkeypatch.setattr(main, "SLACK_WEBHOOK_URL", None)

    warning_payload = {
        "Type": "Warning",
        "Name": "Backup Failure",
        "Description": "The backup failed due to a database problem"
    }

    with TestClient(main.app) as client:
        response = client.post("/notifications", json=warning_payload)

    assert response.status_code == 500
    assert response.json() == {"detail": "Slack webhook URL is not configured"}


@respx.mock
def test_warning_notification_is_still_queued_when_webhook_is_unreachable(monkeypatch, caplog):
    monkeypatch.setattr(main, "SLACK_WEBHOOK_URL", TEST_WEBHOOK_URL)
    caplog.set_level("WARNING", logger=main.__name__)

    route = respx.post(TEST_WEBHOOK_URL).mock(side_effect=httpx.ConnectError("Connection failed"))

    warning_payload = {
        "Type": "Warning",
        "Name": "Backup Failure",
        "Description": "The backup failed due to a database problem"
    }

    with TestClient(main.app) as client:
        response = client.post("/notifications", json=warning_payload)

    assert response.status_code == 200
    assert response.json() == {"status": "queued", "name": "Backup Failure"}
    assert route.called

    assert "Slack webhook is unreachable" in caplog.text
    assert "Backup Failure" in caplog.text


def test_validation_error_on_missing_fields():
    broken_payload = {
        "Type": "Warning",
        "Name": "Broken Alert"
    }
    
    with TestClient(main.app) as client:
        response = client.post("/notifications", json=broken_payload)
    
    assert response.status_code == 422
