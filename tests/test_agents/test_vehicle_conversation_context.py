import pytest

from src.agents.nodes.intake_node import intake_node


@pytest.mark.asyncio
async def test_vehicle_followups_and_switches_preserve_topic_without_claiming_ownership():
    state = {"latest_user_message": "VF5 bảo hành bao lâu?"}
    state.update(await intake_node(state))
    assert state["vehicle_model"] == "VF5"
    assert "vehicle_model" not in state["captured_fields"]
    state["latest_user_message"] = "Pin thì sao?"
    state.update(await intake_node(state))
    assert "VF5" in state["resolved_query"]
    assert "bảo hành" in state["resolved_query"].lower()
    state["latest_user_message"] = "Còn VF8?"
    state.update(await intake_node(state))
    assert state["vehicle_model"] == "VF8"
    assert "bảo hành" in state["resolved_query"].lower()
    assert "VF5" not in state["resolved_query"]
    state["latest_user_message"] = "So sánh VF5 và VF8"
    state.update(await intake_node(state))
    assert state["vehicle_model"] is None
    assert state["vehicle_context"]["models"] == ["VF5", "VF8"]
    state["latest_user_message"] = "Xe tôi không nhận sạc"
    state.update(await intake_node(state))
    assert state["vehicle_model"] is None
    assert "vehicle_model" not in state["captured_fields"]


@pytest.mark.asyncio
async def test_explicit_owned_vehicle_is_remembered_for_incidents():
    state = {"latest_user_message": "Tôi đang sử dụng xe VF5"}
    state.update(await intake_node(state))
    state["latest_user_message"] = "Xe tôi không nhận sạc"
    state.update(await intake_node(state))
    assert state["vehicle_model"] == "VF5"
    assert state["captured_fields"]["vehicle_model"] == "VF5"


@pytest.mark.asyncio
async def test_fresh_session_has_no_vehicle_default():
    state = await intake_node({"latest_user_message": "Xin chào"})
    assert state["vehicle_model"] is None


def test_full_new_question_does_not_inherit_old_topic():
    from src.services.vehicle_context import resolve_vehicle_context

    previous = resolve_vehicle_context("VF5 bảo hành bao lâu?")
    current = resolve_vehicle_context("Còn VF8 giá bao nhiêu?", previous)
    assert current["models"] == ["VF8"]
    assert "bảo hành" not in current["resolved_query"]


def test_repeated_followups_keep_bounded_topic_and_normalized_models():
    from src.services.vehicle_context import resolve_vehicle_context

    context = resolve_vehicle_context("VF e34 bảo hành bao lâu?")
    assert context["models"] == ["e34"]
    for _ in range(30):
        context = resolve_vehicle_context("Pin thì sao?", context)
    assert len(context["resolved_query"]) < 150
    assert "bảo hành" in context["resolved_query"]
    assert context["model_source"] == "VF e34 bảo hành bao lâu?"


@pytest.mark.parametrize("text", ["Tôi lái thử VF5", "Nếu xe VF5 của tôi không nhận sạc thì sao?"])
def test_test_drive_and_hypothetical_do_not_confirm_ownership(text):
    from src.services.vehicle_context import resolve_vehicle_context

    context = resolve_vehicle_context(text)
    assert context["owned_model"] is None


def test_explicit_have_vehicle_is_an_ownership_statement():
    from src.services.vehicle_context import resolve_vehicle_context

    context = resolve_vehicle_context("Tôi có xe VF8")
    assert context["owned_model"] == "VF8"

