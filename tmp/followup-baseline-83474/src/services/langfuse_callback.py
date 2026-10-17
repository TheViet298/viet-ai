"""Sanitize callback payloads before the SDK processes media or exceptions."""
from copy import deepcopy


def safe_callback(base):
    from src.services.observability import mask_telemetry
    from src.services.agent_llm import classify_provider_error

    def clean(value):
        if hasattr(value, 'content'):
            result = deepcopy(value)
            result.content = mask_telemetry(data=value.content)
            return result
        if isinstance(value, list):
            return [clean(item) for item in value]
        return mask_telemetry(data=value)

    class SafeCallback(base):
        def on_chat_model_start(self, serialized, messages, **kwargs):
            return super().on_chat_model_start(serialized, clean(messages), **kwargs)

        def on_llm_end(self, response, **kwargs):
            response = deepcopy(response)
            for group in response.generations:
                for generation in group:
                    generation.text = mask_telemetry(data=generation.text)
                    if hasattr(generation, 'message'):
                        generation.message = clean(generation.message)
            return super().on_llm_end(response, **kwargs)

    def error_method(name):
        def invoke(self, error, **kwargs):
            return getattr(super(SafeCallback, self), name)(
                RuntimeError(classify_provider_error(error)), **kwargs)
        return invoke

    def payload_method(name):
        def invoke(self, *args, **kwargs):
            return getattr(super(SafeCallback, self), name)(*(clean(arg) for arg in args), **kwargs)
        return invoke

    for name in ('on_llm_error', 'on_chain_error', 'on_tool_error', 'on_retriever_error'):
        setattr(SafeCallback, name, error_method(name))
    for name in ('on_llm_start', 'on_chain_start', 'on_chain_end', 'on_tool_start',
                 'on_tool_end', 'on_retriever_start', 'on_retriever_end'):
        setattr(SafeCallback, name, payload_method(name))
    return SafeCallback
