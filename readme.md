# Notification Service

FastAPI service that listens for incoming `POST /notifications` requests.

Notifications with `Type: "Warning"` are forwarded to Slack using a webhook URL.
Notifications with `Type: "Info"` are ignored.

The service uses one asynchronous queue and one background worker to send Slack
messages without blocking incoming requests.
The max count of messages in the queue is 1000.
If Slack delivery fails, the message is logged in the dead letter queue.


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

## Manual testing

Test a `Warning` notification:

```bash
curl -X POST http://127.0.0.1:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{
    "Type": "Warning",
    "Name": "Backup Failure",
    "Description": "The backup failed due to a database problem"
  }'
```

Test an `Info` notification:

```bash
curl -X POST http://127.0.0.1:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{
    "Type": "Info",
    "Name": "Quota Exceeded",
    "Description": "Compute Quota exceeded"
  }'
```
