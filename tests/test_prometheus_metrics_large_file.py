from __future__ import annotations

from unittest.mock import MagicMock, patch

from insureflow.observability import prometheus_metrics as pm


def test_oversized_document_rejection_counter_increments() -> None:
    before = pm._METRICS["oversized_document_rejections"].labels(endpoint="/pipeline/run")._value.get()
    pm.observe_oversized_document_rejection("/pipeline/run")
    after = pm._METRICS["oversized_document_rejections"].labels(endpoint="/pipeline/run")._value.get()
    assert after == before + 1


def test_doc_quality_decision_counter_increments() -> None:
    before = pm._METRICS["doc_quality_decisions"].labels(decision="block")._value.get()
    pm.observe_doc_quality_decision("block")
    after = pm._METRICS["doc_quality_decisions"].labels(decision="block")._value.get()
    assert after == before + 1


def test_pipeline_dispatch_counter_labels_queue_and_backend() -> None:
    before = pm._METRICS["pipeline_dispatch"].labels(queue="pipeline-large", backend="celery")._value.get()
    pm.observe_pipeline_dispatch("pipeline-large", "celery")
    after = pm._METRICS["pipeline_dispatch"].labels(queue="pipeline-large", backend="celery")._value.get()
    assert after == before + 1


def test_inprocess_job_slot_gauge_tracks_acquire_release() -> None:
    gauge = pm._METRICS["inprocess_job_slots_in_use"]
    before = gauge._value.get()
    pm.inprocess_job_slot_acquired()
    assert gauge._value.get() == before + 1
    pm.inprocess_job_slot_released()
    assert gauge._value.get() == before


def test_celery_queue_depth_collector_reads_redis_llen() -> None:
    collector = pm.CeleryQueueDepthCollector()
    fake_pipe = MagicMock()
    fake_pipe.execute.return_value = [3, 0, 7, 1]
    fake_client = MagicMock()
    fake_client.pipeline.return_value = fake_pipe
    with patch("redis.from_url", return_value=fake_client):
        metrics = list(collector.collect())
    assert len(metrics) == 1
    samples = {s.labels["queue"]: s.value for s in metrics[0].samples}
    assert samples == {"agents": 3.0, "pipeline": 0.0, "pipeline-large": 7.0, "mortgage": 1.0}


def test_celery_queue_depth_collector_degrades_to_zero_on_redis_error() -> None:
    collector = pm.CeleryQueueDepthCollector()
    with patch("redis.from_url", side_effect=ConnectionError("no redis")):
        metrics = list(collector.collect())
    samples = {s.labels["queue"]: s.value for s in metrics[0].samples}
    assert all(v == 0.0 for v in samples.values())
