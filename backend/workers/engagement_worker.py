import asyncio
import logging

from workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="workers.engagement_worker.process_facebook_event",
    queue="engagement",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_facebook_event(self, tenant_id: str, event: dict) -> None:
    """
    Proses satu event Facebook (komentar atau Messenger DM) untuk tenant.
    event["channel_type"]: "comment" | "dm"
    """
    channel_type = event.get("channel_type", "comment")

    async def _run() -> None:
        from app.core.database import AsyncSessionLocal
        from app.services.engagement_service import (
            process_facebook_comment,
            process_messenger_message,
        )

        async with AsyncSessionLocal() as session:
            async with session.begin():
                if channel_type == "comment":
                    await process_facebook_comment(tenant_id, event, session)
                elif channel_type == "dm":
                    await process_messenger_message(tenant_id, event, session)
                else:
                    logger.warning(
                        "Unknown channel_type",
                        extra={"channel_type": channel_type, "tenant_id": tenant_id},
                    )

    try:
        asyncio.run(_run())
        logger.info(
            "Facebook event processed",
            extra={"tenant_id": tenant_id, "channel_type": channel_type},
        )
    except Exception as exc:
        logger.error(
            "process_facebook_event failed",
            extra={"tenant_id": tenant_id, "error": str(exc)},
        )
        raise
