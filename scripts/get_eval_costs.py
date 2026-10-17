"""Fetch exact tokens and cost from Langfuse Cloud for each test case."""
import asyncio
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(ROOT / '.env', override=False)

import httpx

RUN_JSON = ROOT / "tmp" / "eval-3models-20261017-102911.json"
RUN_DATA = json.loads(RUN_JSON.read_text(encoding="utf-8"))
TRACE_MAP = {item["trace_id"]: item for item in RUN_DATA}

PRICING_PER_1M = {
    "gemini-2.5-flash-lite": {"input": 0.075, "output": 0.30},
    "gemini-3.5-flash-lite": {"input": 0.075, "output": 0.30},
    "gpt-6-luna":            {"input": 2.50,  "output": 10.00},
    "gpt-4o-mini":           {"input": 0.15,  "output": 0.60},
}


async def main():
    auth = (os.environ['LANGFUSE_PUBLIC_KEY'], os.environ['LANGFUSE_SECRET_KEY'])
    start = (datetime.now(UTC) - timedelta(hours=2)).isoformat()

    async with httpx.AsyncClient(base_url="https://cloud.langfuse.com", auth=auth, timeout=30) as client:
        params = {
            "fields": "core,basic,usage,metadata,model,io,trace_context,time,calculatedTotalCost",
            "limit": 1000,
            "fromStartTime": start,
            "toStartTime": datetime.now(UTC).isoformat()
        }
        resp = await client.get("/api/public/v2/observations", params=params)
        body = resp.json()
        observations = body.get("data", [])

    print(f"Tổng observations thu được từ Langfuse: {len(observations)}")

    # Nhóm observations theo trace_id
    trace_obs = {}
    for obs in observations:
        tid = obs.get("traceId")
        if tid in TRACE_MAP:
            trace_obs.setdefault(tid, []).append(obs)

    summary_results = []
    print("\n" + "=" * 90)
    print(f"{'MÃ CA':<20} | {'MÔ HÌNH':<22} | {'INPUT':<7} | {'OUTPUT':<7} | {'TOTAL':<7} | {'CHI PHÍ (USD)':<15}")
    print("=" * 90)

    total_tokens_all = 0
    total_cost_all = 0.0

    for item in RUN_DATA:
        tid = item["trace_id"]
        cid = item["id"]
        model = item["model"]
        obs_list = trace_obs.get(tid, [])

        generations = [o for o in obs_list if o.get("type") == "GENERATION"]

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        cloud_cost = 0.0

        for g in generations:
            u_details = g.get("usageDetails") or {}
            inp = u_details.get("input") or g.get("inputUsage") or 0
            out = u_details.get("output") or g.get("outputUsage") or 0
            tot = u_details.get("total") or g.get("totalUsage") or (inp + out)
            c = g.get("calculatedTotalCost") or g.get("totalCost") or 0.0

            input_tokens += inp
            output_tokens += out
            total_tokens += tot
            cloud_cost += c

        # Nếu Cloud chưa kịp tính cost cho custom model, dùng pricing chuẩn
        pricing = PRICING_PER_1M.get(model, {"input": 0.15, "output": 0.60})
        estimated_cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        final_cost = cloud_cost if cloud_cost > 0 else estimated_cost

        total_tokens_all += total_tokens
        total_cost_all += final_cost

        summary_results.append({
            "id": cid,
            "title": item["title"],
            "model": model,
            "duration_s": item["duration_s"],
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost_usd": final_cost,
            "cost_vnd": round(final_cost * 25400, 2),
            "trace_url": item["trace_url"]
        })

        print(f"{cid:<20} | {model:<22} | {input_tokens:<7} | {output_tokens:<7} | {total_tokens:<7} | ${final_cost:.6f} ({final_cost * 25400:.2f}đ)")

    print("=" * 90)
    print(f"{'TỔNG CỘNG 10 CA':<45} | {'':<7} | {'':<7} | {total_tokens_all:<7} | ${total_cost_all:.6f} (~{total_cost_all * 25400:.1f} VNĐ)")
    print("=" * 90)

    # Save to file
    out_file = ROOT / "tmp" / "eval_costs_summary.json"
    out_file.write_text(json.dumps(summary_results, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
