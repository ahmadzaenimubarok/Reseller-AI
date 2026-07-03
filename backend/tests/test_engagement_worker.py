from unittest.mock import MagicMock, patch

from workers.engagement_worker import process_facebook_event


def test_task_is_registered():
    from workers.celery_app import celery_app
    assert "workers.engagement_worker.process_facebook_event" in celery_app.tasks


def test_task_has_retry_config():
    task = process_facebook_event
    assert task.max_retries == 3
    assert task.retry_backoff is True


def test_process_facebook_event_comment():
    tenant_id = "tenant-123"
    event = {
        "channel_type": "comment",
        "comment_id": "c1",
        "message": "test",
        "from_id": "u1",
        "from_name": "User",
        "post_id": "p1",
    }

    with patch("workers.engagement_worker.asyncio.run") as mock_run:
        mock_run.return_value = None
        process_facebook_event(tenant_id, event)

    mock_run.assert_called_once()


def test_process_facebook_event_dm():
    tenant_id = "tenant-456"
    event = {
        "channel_type": "dm",
        "message_id": "m1",
        "message": "halo",
        "sender_id": "u2",
    }

    with patch("workers.engagement_worker.asyncio.run") as mock_run:
        mock_run.return_value = None
        process_facebook_event(tenant_id, event)

    mock_run.assert_called_once()
