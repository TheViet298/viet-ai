import csv

from src.agents.context_manager import PROMPT_DIR, load_prompt


def test_prompt_artifacts_have_contracts_and_metadata():
    for path in PROMPT_DIR.glob("*_prompt.md"):
        text = path.read_text(encoding="utf-8")
        for header in ("owner:", "version:", "variables:", "contract:", "eval_cases:", "rollback:"):
            assert header in text, (path, header)
        assert load_prompt(path.stem.removesuffix("_prompt"))
    with (PROMPT_DIR / "version_log.csv").open(encoding="utf-8") as file:
        assert {"version", "artifact", "pass_rate", "routing_acc", "decision"}.issubset(next(csv.reader(file)))
