import pytest


@pytest.mark.asyncio
async def test_get_redis_returns_client():
    import app.core.redis as redis_module
    redis_module._redis_client = None

    client = await redis_module.get_redis()
    assert client is not None

    await redis_module.close_redis()
    assert redis_module._redis_client is None


def test_celery_app_configured():
    from workers.celery_app import celery_app
    assert celery_app.conf.task_serializer == "json"
    assert "workers.discovery_worker" in celery_app.conf.include
