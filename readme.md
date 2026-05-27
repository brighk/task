# Notification Service

FastAPI service that listens for incoming `POST /notifications` requests.

Notifications with `Type: "Warning"` are forwarded to Slack using a webhook URL.
Notifications with `Type: "Info"` are ignored.

The service uses one asynchronous queue and one background worker to send Slack
messages without blocking incoming requests.

## Structure

- `main.py`
- `test_main.py`
- `requirements.txt`
- `readme.md`

## Configuration

Set the Slack webhook URL before running the service:

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

## Run

```bash
uvicorn main:app --reload
```

## Test

```bash
pytest
```
