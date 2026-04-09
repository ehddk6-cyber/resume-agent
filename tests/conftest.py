from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def _stub_sentence_transformers():
    module = types.ModuleType("sentence_transformers")

    class _SentenceTransformer:
        def __init__(self, *_args, **_kwargs):
            pass

        def encode(self, text, normalize_embeddings=True):
            if isinstance(text, list):
                return [[1.0, 0.0] for _ in text]
            return [1.0, 0.0]

    module.SentenceTransformer = _SentenceTransformer
    original = sys.modules.get("sentence_transformers")
    sys.modules["sentence_transformers"] = module
    try:
        yield
    finally:
        if original is None:
            sys.modules.pop("sentence_transformers", None)
        else:
            sys.modules["sentence_transformers"] = original
