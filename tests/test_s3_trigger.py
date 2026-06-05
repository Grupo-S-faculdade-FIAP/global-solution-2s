"""Tests for S3 trigger event handler."""

from unittest.mock import MagicMock

from app.interfaces.events.s3_trigger import S3TriggerHandler


def test_handle_processes_all_records():
    use_case = MagicMock()
    use_case.execute.side_effect = [
        {"detected": True, "count": 2},
        {"detected": False, "count": 0},
    ]
    handler = S3TriggerHandler(use_case)

    event = {
        "Records": [
            {"s3": {"bucket": {"name": "bucket-a"}, "object": {"key": "a.png"}}},
            {"s3": {"bucket": {"name": "bucket-b"}, "object": {"key": "b.png"}}},
        ]
    }

    result = handler.handle(event)

    assert result["processed"] == 2
    assert len(result["results"]) == 2
    assert use_case.execute.call_count == 2
    use_case.execute.assert_any_call(bucket="bucket-a", key="a.png")


def test_handle_empty_event():
    use_case = MagicMock()
    handler = S3TriggerHandler(use_case)

    result = handler.handle({})

    assert result == {"processed": 0, "results": []}
    use_case.execute.assert_not_called()
