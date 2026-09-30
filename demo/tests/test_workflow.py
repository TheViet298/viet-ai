import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import Engine
from store import Store


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store(Path(self.directory.name) / "demo.db", ROOT / "datasets/knowledge.json")
        self.engine = Engine(self.store, ROOT / "datasets/rules.json")

    def test_product_context_and_citations(self):
        first = self.engine.respond("Tôi cần tư vấn xe cho gia đình")
        self.assertEqual(first["status"], "CLARIFICATION")
        second = self.engine.respond("Gia đình, 5 chỗ", first["session_id"])
        self.assertEqual(second["intent"], "product")
        self.assertTrue(second["citations"])
        self.assertEqual(second["context"]["seats"], 5)

    def test_known_model_direct_retrieval(self):
        result = self.engine.respond("Tôi muốn tìm hiểu VF 8")
        self.assertEqual(result["status"], "ANSWER")
        self.assertEqual(result["context"]["model"], "VF8")
        self.assertIn("VF 8", result["message"])

    def test_customer_care_database_lookup(self):
        result = self.engine.respond("Làm thế nào đặt lịch bảo dưỡng?")
        self.assertEqual(result["intent"], "customer_care")
        self.assertTrue(result["citations"])

    def test_urgent_skips_clarification(self):
        result = self.engine.respond("Xe đang bốc khói")
        self.assertEqual(result["priority"], "URGENT")
        self.assertEqual(result["status"], "HANDOFF")
        self.assertTrue(result["case_id"])
        self.assertEqual(len(self.store.cases()), 1)

    def test_composite_emergency(self):
        result = self.engine.respond("VF9 báo rùa vàng trên cao tốc")
        self.assertEqual(result["priority"], "URGENT")

    def test_negated_emergency_not_urgent(self):
        result = self.engine.respond("VF8 không có khói, không cháy, đã dừng an toàn, màn hình lỗi")
        self.assertEqual(result["priority"], "LOW")

    def test_running_is_not_fire(self):
        result = self.engine.respond("Xe đang chạy bình thường")
        self.assertNotEqual(result["priority"], "URGENT")

    def test_positive_emergency_after_negation(self):
        result = self.engine.respond("Không có khói nhưng xe bị mất phanh")
        self.assertEqual(result["priority"], "URGENT")

    def test_technical_context_across_turns(self):
        first = self.engine.respond("Xe không nhận sạc")
        self.assertEqual(first["priority"], "HIGH")
        second = self.engine.respond("VF8 đã dừng an toàn", first["session_id"])
        self.assertEqual(second["status"], "HANDOFF")
        context = json.loads(self.store.cases()[0]["context"])
        self.assertEqual(context["model"], "VF8")

    def test_max_two_clarification_turns(self):
        first = self.engine.respond("Xe bị lỗi")
        second = self.engine.respond("Chưa rõ", first["session_id"])
        third = self.engine.respond("Tôi chưa biết", first["session_id"])
        self.assertEqual(second["status"], "CLARIFICATION")
        self.assertEqual(third["status"], "HANDOFF")
        self.assertTrue(third["missing_fields"])

    def test_low_medium_high(self):
        for text, expected in [("VF8 màn hình lỗi đã dừng an toàn", "LOW"), ("VF8 có tiếng kêu đã dừng an toàn", "MEDIUM"), ("VF8 không nhận sạc đã dừng an toàn", "HIGH")]:
            self.assertEqual(self.engine.respond(text)["priority"], expected)

    def test_queue_priority_and_transitions(self):
        normal = self.engine.respond("VF8 có tiếng kêu đã dừng an toàn")
        urgent = self.engine.respond("Xe bị cháy")
        self.assertEqual(self.store.cases()[0]["id"], urgent["case_id"])
        self.assertEqual(self.store.update_case(normal["case_id"], "ACCEPT"), "IN_PROGRESS")
        with self.assertRaises(ValueError):
            self.store.update_case(normal["case_id"], "ACCEPT")
        self.assertEqual(self.store.update_case(normal["case_id"], "RESOLVE"), "RESOLVED")

    def test_session_isolation_and_persistence(self):
        first = self.engine.respond("Xe không nhận sạc")
        second = self.engine.respond("Tôi muốn tìm hiểu VF5")
        self.assertNotEqual(first["session_id"], second["session_id"])
        reopened = Engine(Store(self.store.path, ROOT / "datasets/knowledge.json"), ROOT / "datasets/rules.json")
        self.assertEqual(reopened.respond("VF8 đã dừng an toàn", first["session_id"])["status"], "HANDOFF")

    def test_switch_topic_after_handoff(self):
        first = self.engine.respond("Xe bị cháy")
        next_turn = self.engine.respond("Cách đặt lịch bảo dưỡng", first["session_id"])
        self.assertEqual(next_turn["intent"], "customer_care")
        self.assertIsNone(next_turn["case_id"])

    def test_unknown_source_and_redaction(self):
        result = self.engine.respond("Thời tiết trên sao Hỏa?")
        self.assertEqual(result["status"], "NO_SOURCE")
        private = self.engine.respond("Xe cháy, email demo@example.invalid, số 0912345678")
        summary = self.store.cases()[0]["summary"]
        self.assertNotIn("0912345678", summary)
        self.assertNotIn("demo@example.invalid", summary)
        self.assertEqual(private["priority"], "URGENT")


if __name__ == "__main__":
    unittest.main()
