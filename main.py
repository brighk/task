import asyncio
import logging
import os
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
WEBHOOK_TIMEOUT_SECONDS = 5.0
NOTIFICATION_QUEUE_MAX_SIZE = 1000

logger = logging.getLogger(__name__)


async def send_slack_message(client: httpx.AsyncClient, slack_payload: dict):
    try:
        response = await client.post(SLACK_WEBHOOK_URL, json=slack_payload)

        if not response.is_success:
            logger.warning(
                "Slack rejected message with status %s. Failed payload: %s",
                response.status_code,
                slack_payload,
            )
    except httpx.RequestError as exc:
        logger.warning("Slack webhook is unreachable: %s. Failed payload: %s", exc, slack_payload)


async def notification_worker(app: FastAPI):
    while True:
        slack_payload = await app.state.notification_queue.get()
        try:
            if slack_payload is None:
                return

            await send_slack_message(app.state.http_client, slack_payload)
        finally:
            app.state.notification_queue.task_done()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS)
    app.state.notification_queue = asyncio.Queue(maxsize=NOTIFICATION_QUEUE_MAX_SIZE)
    app.state.notification_worker = asyncio.create_task(notification_worker(app))

    try:
        yield
    finally:
        await app.state.notification_queue.put(None)
        await app.state.notification_worker
        await app.state.http_client.aclose()


app = FastAPI(lifespan=lifespan)


class Notification(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(..., alias="Type")
    name: str = Field(..., alias="Name")
    description: str = Field(..., alias="Description")


@app.post("/notifications")
async def handle_notification(notification: Notification):
    if notification.type.lower() == "info":
        return {"status": "ignored", "reason": "Info messages are skipped", "name": notification.name}

    if notification.type.lower() == "warning":
        if not SLACK_WEBHOOK_URL:
            raise HTTPException(status_code=500, detail="Slack webhook URL is not configured")

        slack_payload = {
            "text": f"*[{notification.type}] {notification.name}* \n>{notification.description}"
        }

        try:
            app.state.notification_queue.put_nowait(slack_payload)
        except asyncio.QueueFull:
            raise HTTPException(status_code=503, detail="Notification queue is full")

        return {"status": "queued", "name": notification.name}

    return {"status": "ignored", "reason": "Unknown notification type"}
