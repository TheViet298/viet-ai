from scripts.evaluate_vehicle_checkpoint import summarize


def test_selective_accuracy_counts_confident_mistakes_and_rejected_correct_images():
    rows = [
        {"truth": "a", "prediction": "a", "correct": True, "confidence": .9, "top5": ["a", "b"]},
        {"truth": "b", "prediction": "a", "correct": False, "confidence": .8, "top5": ["a", "b"]},
        {"truth": "b", "prediction": "b", "correct": True, "confidence": .6, "top5": ["b", "a"]},
    ]
    result = summarize(rows, ["a", "b"], .7)
    assert result["top1"] == 2 / 3
    assert result["top5"] == 1
    assert result["coverage"] == 2 / 3
    assert result["accepted_accuracy"] == .5
    assert result["accepted_correct"] == 1
    assert result["per_class"]["b"]["recall"] == .5


def test_empty_evaluation_has_no_claim_of_accuracy():
    result = summarize([], ["vf8"], .7)
    assert result["top1"] is None
    assert result["accepted_accuracy"] is None
    assert result["count"] == 0
