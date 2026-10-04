"""Optional local ONNX E5 embeddings for an isolated, versioned Chroma index."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction
from chromadb.utils.embedding_functions import register_embedding_function

ROOT = Path(__file__).resolve().parents[2]


def mean_pool(hidden: np.ndarray, attention: np.ndarray) -> np.ndarray:
    mask = attention[..., None]
    pooled = np.sum(hidden * mask, axis=1) / np.maximum(np.sum(mask, axis=1), 1)
    return pooled / np.maximum(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12)


@register_embedding_function
class MultilingualE5(EmbeddingFunction[Documents]):
    def __init__(self, model_dir: str = "data/models/multilingual-e5-small"):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.model_dir = model_dir
        path = ROOT / model_dir
        self.tokenizer = Tokenizer.from_file(str(path / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=256)
        pad_token = "[PAD]" if self.tokenizer.token_to_id("[PAD]") is not None else "<pad>"
        self.tokenizer.enable_padding(pad_id=self.tokenizer.token_to_id(pad_token), pad_token=pad_token)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(str(path / "onnx/model_quantized.onnx"), options, providers=["CPUExecutionProvider"])

    @staticmethod
    def name() -> str:
        return "vinfast-multilingual-e5-onnx"

    def get_config(self) -> dict:
        return {"model_dir": self.model_dir}

    @staticmethod
    def build_from_config(config: dict):
        return cached_model(config["model_dir"])

    def _encode(self, texts: list[str], prefix: str):
        vectors = []
        for start in range(0, len(texts), 16):
            encodings = self.tokenizer.encode_batch([prefix + text for text in texts[start:start + 16]])
            inputs = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64),
            }
            accepted = {node.name for node in self.session.get_inputs()}
            hidden = self.session.run(None, {k: v for k, v in inputs.items() if k in accepted})[0]
            vectors.extend(mean_pool(hidden, inputs["attention_mask"]).astype(np.float32))
        return vectors

    def __call__(self, input: Documents):
        return self._encode(list(input), "passage: ")

    def embed_query(self, input: Documents):
        return self._encode(list(input), "query: ")


@lru_cache(maxsize=2)
def _cached_model(model_dir: str):
    return MultilingualE5(model_dir)


def cached_model(model_dir: str):
    from src.services.rag_service import _cache_lock
    with _cache_lock:
        return _cached_model(model_dir)
