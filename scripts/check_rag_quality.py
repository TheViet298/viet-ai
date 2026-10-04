"""Acceptance report validation. Engineering fixture mode is a separate gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.rag_measurement import check_acceptance  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    parser.add_argument('--config', type=Path, default=ROOT / 'eval/rag_gate_config.json')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--engineering', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.engineering:
            from eval.rag_engineering import run_engineering
            result = run_engineering()
        else:
            report = json.loads(args.report.read_text(encoding='utf-8'))
            config = json.loads(args.config.read_text(encoding='utf-8'))
            if not isinstance(report, dict) or not isinstance(config, dict):
                raise ValueError('Expected objects')
            reasons = check_acceptance(report, config)
            result = {'gate_kind': 'acceptance', 'passed': not reasons, 'production_acceptance': not reasons, 'failure_reasons': reasons}
        exit_code = 0 if result['passed'] else 1
    except (ValueError, TypeError, KeyError, AttributeError, OSError):
        result = {'gate_kind': 'input_error', 'passed': False, 'production_acceptance': False, 'failure_reasons': ['malformed_input']}
        exit_code = 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
