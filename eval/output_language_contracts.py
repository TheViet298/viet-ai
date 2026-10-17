"""Acceptance regressions over captured real API outputs; not a mocked model test.

Run explicitly after the live language audit. Red results describe open defects;
this module is outside the project's default unit-test collection.
"""
import json
import os
from pathlib import Path

import pytest


@pytest.fixture(scope='module')
def outputs():
    root = Path(os.environ['OUTPUT_LANGUAGE_AUDIT_DIR'])
    return [*json.loads((root / 'live/results.json').read_text(encoding='utf-8')),
            *json.loads((root / 'repeat/results.json').read_text(encoding='utf-8'))]


@pytest.mark.parametrize('case', ['smoke-en', 'brakes-en', 'fire-connector-en'])
def test_english_danger_keeps_emergency_workflow(outputs, case):
    actual = [row['data'] for row in outputs if row['case'] == case]
    assert actual
    assert all(row.get('show_emergency_banner') and row.get('priority') == 'CRITICAL' for row in actual)


def test_english_vf7_consultation_has_same_variants_as_vietnamese(outputs):
    rows = {row['case']: row['data'] for row in outputs}
    expected = [card['variant'] for card in rows['product-vf7-vi']['vehicle_cards']]
    assert expected == ['eco', 'plus', 'plus-awd']
    assert [card['variant'] for card in rows['product-vf7-en'].get('vehicle_cards') or []] == expected


def test_explicit_english_request_does_not_return_vietnamese_copy(outputs):
    actual = [row['data'] for row in outputs if row['case'] == 'switch-to-en' and row['turn'] == 2]
    assert len(actual) == 3
    # Necessary condition only; fluent, correct English also needs semantic review.
    assert all(row.get('language') == 'en' and 'Quý khách' not in row['message']
               and 'Em chưa' not in row['message'] and 'Infinity Blanc' in row['message'] for row in actual)


def test_english_vf8_colors_preserve_verified_evidence(outputs):
    actual = [row['data'] for row in outputs if row['case'] == 'color-vf8-en']
    assert actual
    assert all(row.get('citations') for row in actual)
    assert all('Infinity Blanc' in row['message'] and 'Jet Black' in row['message'] for row in actual)


@pytest.mark.parametrize('case', ['thanks-vi', 'thanks-en'])
def test_thanking_the_assistant_is_not_rejected_as_out_of_scope(outputs, case):
    actual = [row['data']['message'] for row in outputs if row['case'] == case]
    assert actual
    assert all('vui lòng cho biết yêu cầu liên quan đến VinFast' not in message for message in actual)
    assert all(('welcome' in message.lower()) if case.endswith('-en') else ('rất vui được hỗ trợ' in message)
               for message in actual)


def test_booking_confirmation_requires_a_server_receipt(outputs):
    actual = [row for row in outputs if row['case'] == 'booking-confirm-en' and row['turn'] == 2]
    assert len(actual) == 2
    assert all(row['progress'].get('action_receipt') or row['data']['message'].startswith('No appointment has been booked through this chat.')
               for row in actual)
