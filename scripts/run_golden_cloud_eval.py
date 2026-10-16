"""Upload the golden dataset and evaluate real chat bridge runs on Langfuse Cloud."""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from uuid import NAMESPACE_URL, uuid4, uuid5

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.golden import evaluate_conversation

DATASET = ROOT / "eval/datasets/golden_testcases_v1.jsonl"


def dataset_payload(case: dict, digest: str) -> dict:
    return {
        "id": str(uuid5(NAMESPACE_URL, f"p142-golden:{digest}:{case['id']}")),
        "input": {"case_id": case["id"], "turns": [t["input"] for t in case["turns"]],
                  "retrieval": case["retrieval"]},
        "expected_output": {"turns": [{k: v for k, v in turn.items() if k != "input"} for turn in case["turns"]]},
        "metadata": {k: case[k] for k in ("id", "category", "label_status")},
    }


def evaluate_item(*, output, expected_output, **kwargs):
    from langfuse.experiment import Evaluation

    checks = evaluate_conversation(output, expected_output)
    failures = [c for c in checks if not c["passed"]]
    # Score comments contain failing checks; complete checks are in the local results.
    comment = json.dumps(failures, ensure_ascii=False)
    return [Evaluation(**score) for score in [{"name": "golden_pass", "value": int(not failures), "data_type": "BOOLEAN", "comment": comment},
            {"name": "golden_assertion_accuracy", "value": sum(c["passed"] for c in checks) / len(checks),
             "data_type": "NUMERIC", "comment": f"{len(checks) - len(failures)}/{len(checks)} checks passed"}]]


def evaluate_run(*, item_results, **kwargs):
    from langfuse.experiment import Evaluation

    scores = [e.value for result in item_results for e in result.evaluations if e.name == "golden_pass"]
    return Evaluation(name="golden_pass_rate", value=sum(scores) / len(item_results) if item_results else 0,
                      data_type="NUMERIC", comment=f"{sum(scores)}/{len(item_results)} cases passed; draft labels")


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def safe_records(records):
    from src.services.observability import mask_telemetry

    safe = mask_telemetry(data=records)
    for original, sanitized in zip(records, safe):
        # Random hex trace IDs can contain digit runs that resemble PII.
        sanitized["trace_id"] = original["trace_id"]
    return safe


def retry_cloud(function, *args, **kwargs):
    import httpx

    for attempt in range(4):
        try:
            return function(*args, **kwargs)
        except Exception as error:
            response = getattr(error, "response", None)
            limited = getattr(error, "status_code", getattr(response, "status_code", None)) == 429
            transient = isinstance(error, (httpx.ConnectError, httpx.TimeoutException))
            if attempt == 3 or not (limited or transient):
                raise
            body = getattr(error, "body", {})
            if limited and response is not None:
                body = response.json()
            retry_after = body.get("details", {}).get("retryAfterSeconds", 30) if limited and isinstance(body, dict) else 5
            delay = min(60, max(1, int(retry_after) + 1))
            print(json.dumps({"cloud_retry": "rate_limited" if limited else "connection", "wait_s": delay}), flush=True)
            time.sleep(delay)


def read_cloud_pages(client, path, params):
    rows, seen = [], set()
    params = dict(params)
    while True:
        def request():
            response = client.get(path, params=params)
            response.raise_for_status()
            return response.json()
        body = retry_cloud(request)
        rows.extend(body.get("data", []))
        cursor = body.get("meta", {}).get("cursor")
        if not cursor:
            return rows
        if cursor in seen:
            raise RuntimeError("Cloud API returned a repeated cursor")
        seen.add(cursor)
        params["cursor"] = cursor


def cloud_reader():
    import httpx

    return httpx.Client(base_url=os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
                        auth=(os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"]), timeout=30)


def verify_cloud(client, dataset_name, run_name, trace_ids, *, started, expected_dataset_id, expected_item_ids,
                 expected_scores=None, deadline_s=50):
    """Read back dataset links and item scores, rather than trusting flush alone."""
    deadline = time.monotonic() + deadline_s
    result = {"verified": False}
    while True:
        experiments = read_cloud_pages(client, "/api/public/experiments", {
            "name": run_name, "fromStartTime": started, "fields": "core,scores", "limit": 100})
        experiments = [e for e in experiments if e["name"] == run_name]
        items = read_cloud_pages(client, "/api/public/experiment-items", {
            "experimentName": run_name, "fromStartTime": started, "fields": "core,dataset,scores", "limit": 100})
        items = [i for i in items if i["experimentName"] == run_name and i["traceId"] in trace_ids]
        scores = [{**score, "trace_id": item["traceId"]} for item in items for score in item.get("scores", [])]
        scores += [{**score, "trace_id": None} for experiment in experiments for score in experiment.get("scores", [])]
        scores = [s for s in scores if s["name"] in {"golden_pass", "golden_assertion_accuracy", "golden_pass_rate"}]
        metric_traces = {name: {s["trace_id"] for s in scores if s["name"] == name}
                         for name in ("golden_pass", "golden_assertion_accuracy", "golden_pass_rate")}
        linked = {item["traceId"] for item in items}
        dataset_linked = (bool(experiments) and all(e.get("datasetId") == expected_dataset_id for e in experiments)
                          and all(i.get("experimentDatasetId") == expected_dataset_id for i in items)
                          and {i.get("experimentItemId") for i in items} == set(expected_item_ids))
        complete = (len(set(trace_ids)) == 60 and set(trace_ids) <= linked
                    and all(set(trace_ids) <= metric_traces[name] for name in ("golden_pass", "golden_assertion_accuracy"))
                    and bool(metric_traces["golden_pass_rate"]) and len(experiments) == 1
                    and experiments[0]["itemCount"] == 60 and dataset_linked)
        values_match = True
        if expected_scores:
            for score in scores:
                expected = (sum(v["golden_pass"] for v in expected_scores.values()) / len(expected_scores)
                            if score["name"] == "golden_pass_rate" else expected_scores[score["trace_id"]][score["name"]])
                values_match = values_match and abs(score["value"] - expected) < 1e-9
        result = {"verified": complete and values_match, "score_values_match": values_match,
                  "dataset_run_id": experiments[0]["id"] if experiments else None,
                  "api": "experiments_and_experiment_items_with_scores_v3",
                  "dataset_name": dataset_name, "dataset_links_match": dataset_linked,
                  "linked_traces": len(linked), "scored_traces": len(metric_traces["golden_pass"]),
                  "metric_trace_counts": {k: len(v) for k, v in metric_traces.items()},
                  "scores": [{k: s[k] for k in ("id", "name", "trace_id", "value")} for s in scores]}
        if result["verified"] or time.monotonic() >= deadline:
            return result
        time.sleep(3)


def run(output: Path, modes: list[str]):
    from scripts.check_langfuse_matrix import isolate, preflight

    checks = asyncio.run(preflight())
    if checks.get("cloud_http_status") != 200:
        raise RuntimeError("Langfuse preflight failed; no experiment started")
    if "online" in modes and not (checks.get("openai_key_present") or checks.get("google_key_present")):
        raise RuntimeError("Online mode requires configured provider credentials")
    digest = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    cases = [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(cases) != 60 or len({c["id"] for c in cases}) != 60:
        raise ValueError("Expected 60 unique golden cases")
    isolation = isolate(output)
    os.environ["LANGFUSE_TRACING_ENABLED"] = "true"
    os.environ["LANGFUSE_TRACING_ENVIRONMENT"] = "p142-golden-eval"
    os.environ.setdefault("LANGFUSE_TIMEOUT", "30")
    from src.services import observability as obs
    from src.services.rag_service import rag_service
    from src.agents.chatbot_agent import process_chat_message
    from src.services.agent_llm import reset_circuits
    from src.services.session_store import get_store
    from src.config import get_settings
    from scripts.langfuse_cloud_evidence import collect_observations, summarize_trace, write_observations
    from eval.golden_metrics import write_metrics

    if not obs.initialize_observability():
        raise RuntimeError("Langfuse client initialization failed")
    client = obs._client
    dataset_name = f"p142-golden-v1-{digest[:12]}"
    retry_cloud(client.create_dataset, name=dataset_name, description="60 proposed golden contracts; synthetic retrieval; draft policy review.",
                          metadata={"dataset_sha256": digest, "label_status": "draft_policy_review"})
    existing = {item.id: item for item in retry_cloud(client.get_dataset, dataset_name).items}
    for case in cases:
        payload = dataset_payload(case, digest)
        previous = existing.get(payload["id"])
        if previous and previous.input == payload["input"] and previous.expected_output == payload["expected_output"] and previous.metadata == payload["metadata"]:
            continue
        retry_cloud(client.create_dataset_item, dataset_name=dataset_name, **payload)
    dataset = retry_cloud(client.get_dataset, dataset_name)
    expected_ids = {dataset_payload(case, digest)["id"] for case in cases}
    if {item.id for item in dataset.items} != expected_ids:
        raise RuntimeError("Cloud dataset items differ from local dataset")
    print(json.dumps({"dataset": dataset_name, "uploaded": len(dataset.items)}), flush=True)
    settings = get_settings()
    runs = []
    try:
        for mode in modes:
            settings.agent_llm_enabled = mode == "online"
            reset_circuits()
            run_id = f"golden-{mode}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{uuid4().hex[:6]}"
            started = datetime.now(UTC).isoformat()
            progress = []

            async def task(*, item, **kwargs):
                case_id = item.input["case_id"]
                outputs = []
                begin = time.monotonic()
                # The existing baseline uses fixed retrieval. Online enables generation,
                # not live KB retrieval. Sequential execution keeps this patch isolated.
                with patch.object(rag_service, "retrieve", side_effect=lambda *a, **k: copy.deepcopy(item.input["retrieval"])):
                    with obs.validation_context(run_id, case_id, fault_injected=True):
                        with obs.observation("p142.golden.case", metadata={"mode": mode}) as handle:
                            try:
                                for message in item.input["turns"]:
                                    outputs.append(await process_chat_message(message, session_id=f"{run_id}-{case_id}",
                                                                             user_role="customer", owner="golden-customer"))
                                result = {"turns": outputs}
                            except Exception as error:
                                from src.services.agent_llm import classify_provider_error
                                result = {"turns": outputs, "error": classify_provider_error(error)}
                            obs.update_observation(handle, output=result)
                result["duration_s"] = round(time.monotonic() - begin, 3)
                verdict = evaluate_item(output=result, expected_output=item.expected_output)[0].value
                progress.append({"id": case_id, "passed": bool(verdict), "output": result})
                write_json(output / f"{mode}-progress.json", obs.mask_telemetry(data=progress))
                print(json.dumps({"mode": mode, "case": case_id, "pass": bool(verdict), "duration_s": result["duration_s"]}), flush=True)
                return result

            link = client.api.dataset_run_items.create
            with patch.object(client.api.dataset_run_items, "create", side_effect=lambda **kw: retry_cloud(link, **kw)):
                experiment = client.run_experiment(name="P142 golden contracts", run_name=run_id, data=dataset.items,
                    task=task, evaluators=[evaluate_item], run_evaluators=[evaluate_run], max_concurrency=1,
                    description=f"{mode} generation; synthetic retrieval fixtures; draft policy labels",
                    metadata={"run_id": run_id, "mode": mode, "retrieval_mode": "fixture"})
            client.flush()
            records = []
            for item_result in experiment.item_results:
                records.append({"id": item_result.item.input["case_id"], "category": item_result.item.metadata["category"],
                                "trace_id": item_result.trace_id, "output": item_result.output,
                                "checks": evaluate_conversation(item_result.output, item_result.item.expected_output),
                                "scores": [{"name": e.name, "value": e.value} for e in item_result.evaluations]})
            trace_ids = [r["trace_id"] for r in records if r["trace_id"]]
            mode_dir = output / mode
            mode_dir.mkdir()
            write_json(mode_dir / "results.json", safe_records(records))
            # Persist paid outputs and trace IDs before any network readback.
            write_json(mode_dir / "run-reference.json", {"run_id": run_id, "run_url": experiment.dataset_run_url,
                       "dataset": dataset_name, "started": started, "trace_ids": trace_ids})
            expected_scores = {r["trace_id"]: {s["name"]: s["value"] for s in r["scores"]} for r in records}
            rows = []
            try:
                with cloud_reader() as reader:
                    cloud = verify_cloud(reader, dataset_name, run_id, trace_ids, started=started,
                        expected_dataset_id=dataset.id, expected_item_ids=expected_ids, expected_scores=expected_scores)
                rows = asyncio.run(collect_observations(run_id, from_time=started, timeout_s=45, expected_cases=60))
            except Exception as error:
                cloud = {"verified": False, "readback_error_type": type(error).__name__}
            write_observations(mode_dir, rows)
            write_metrics(mode_dir, records, rows)
            with get_store().connect() as db:
                events = [json.loads(row[0]) for row in db.execute("SELECT data FROM agent_traces WHERE session_id LIKE ?", (run_id + "%",))]
            outcomes = {}
            for event in events:
                if event["kind"] == "llm":
                    decision = event["gate_decision"]
                    outcomes[decision] = outcomes.get(decision, 0) + 1
            passed = sum(all(c["passed"] for c in r["checks"]) for r in records)
            manifest = {"run_id": run_id, "mode": mode, "dataset": dataset_name, "dataset_id": dataset.id, "dataset_sha256": digest,
                        "run_url": experiment.dataset_run_url, "total": len(records), "passed": passed,
                        "failed": len(records) - passed, "model": settings.model_name, "llm_outcomes": outcomes,
                        "cloud_verification": cloud, "cloud_usage": summarize_trace(rows), "isolation": isolation,
                        "online_generation_confirmed": bool(mode == "online" and any(r.get("type") == "GENERATION" for r in rows)),
                        "project_id": checks["project_id"], "label_status": "draft_policy_review"}
            write_json(mode_dir / "manifest.json", manifest)
            runs.append(manifest)
            write_json(output / "runs.json", runs)
            print(json.dumps({"mode": mode, "passed": passed, "failed": len(records) - passed,
                              "cloud_verified": cloud["verified"], "url": experiment.dataset_run_url}), flush=True)
    finally:
        client.flush()
        asyncio.run(obs.flush_observability(shutdown=True))
    return runs


def refresh_cloud(output: Path):
    """Reconcile completed runs without repeating model calls."""
    from dotenv import load_dotenv
    from scripts.langfuse_cloud_evidence import collect_observations, summarize_trace, write_observations
    from eval.golden_metrics import write_metrics

    load_dotenv(ROOT / ".env", override=False)
    output = output.resolve()
    if not output.is_relative_to(ROOT / ".test-runs"):
        raise ValueError("Verification output must be inside project .test-runs")
    runs = []
    for mode in ("offline", "online"):
        directory = output / mode
        if not (directory / "manifest.json").is_file():
            continue
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        reference = json.loads((directory / "run-reference.json").read_text(encoding="utf-8"))
        records = json.loads((directory / "results.json").read_text(encoding="utf-8"))
        # Recover technical IDs in evidence written by the initial blanket masker.
        from src.services.observability import mask_telemetry
        if len(reference["trace_ids"]) != len(records):
            raise ValueError("Trace reference and result counts differ")
        for record, trace_id in zip(records, reference["trace_ids"]):
            if record["trace_id"] not in (trace_id, mask_telemetry(data=trace_id)):
                raise ValueError("Trace reference and result order differ")
            record["trace_id"] = trace_id
        write_json(directory / "results.json", safe_records(records))
        expected_scores = {r["trace_id"]: {s["name"]: s["value"] for s in r["scores"]} for r in records}
        # Older evidence stores the SDK-returned dataset ID in its run URL.
        manifest.setdefault("dataset_id", manifest["run_url"].split("/datasets/")[1].split("/")[0])
        expected_ids = {str(uuid5(NAMESPACE_URL, f"p142-golden:{manifest['dataset_sha256']}:{r['id']}")) for r in records}
        with cloud_reader() as reader:
            manifest["cloud_verification"] = verify_cloud(reader, manifest["dataset"], manifest["run_id"],
                reference["trace_ids"], started=reference["started"], expected_scores=expected_scores,
                expected_dataset_id=manifest["dataset_id"], expected_item_ids=expected_ids)
        rows = asyncio.run(collect_observations(manifest["run_id"], from_time=reference["started"], expected_cases=60))
        write_observations(directory, rows)
        write_metrics(directory, records, rows)
        manifest["cloud_usage"] = summarize_trace(rows)
        manifest["online_generation_confirmed"] = bool(mode == "online" and any(r.get("type") == "GENERATION" for r in rows))
        write_json(directory / "manifest.json", manifest)
        runs.append(manifest)
        print(json.dumps({"mode": mode, "cloud_verified": manifest["cloud_verification"]["verified"],
                          "generations": manifest["cloud_usage"]["generation_count"]}), flush=True)
    if not runs:
        raise ValueError("No completed runs found")
    write_json(output / "runs.json", runs)
    return runs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--preflight", action="store_true")
    actions.add_argument("--run", action="store_true")
    actions.add_argument("--verify-output", type=Path, help="Read back saved runs without executing model calls")
    parser.add_argument("--mode", choices=["offline", "online", "both"], default="offline")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.preflight:
        from scripts.check_langfuse_matrix import preflight
        print(json.dumps(asyncio.run(preflight()), indent=2))
        return
    output = args.verify_output or args.output_dir or ROOT / ".test-runs/langfuse-golden" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:6])
    output = output.resolve()
    results = refresh_cloud(output) if args.verify_output else run(output, ["offline", "online"] if args.mode == "both" else [args.mode])
    print(json.dumps({"output": str(output), "runs": [{k: r[k] for k in ("mode", "passed", "failed", "run_url")} for r in results]}, indent=2))
    if not all(r["cloud_verification"]["verified"] for r in results):
        raise SystemExit(2)
    if any(r["mode"] == "online" and not r["online_generation_confirmed"] for r in results):
        raise SystemExit(2)
    if any(r["failed"] for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
