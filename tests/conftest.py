"""Test setup: no Ollama, no model download. Embeddings are replaced by a tiny deterministic fake."""
import os
import re
import sys
import tempfile
import types
import zlib

import numpy as np
import pytest

os.environ.setdefault("DB_PATH", os.path.join(tempfile.mkdtemp(), "test.db"))

if "sentence_transformers" not in sys.modules:   # avoid importing torch in unit tests
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        sys.modules["sentence_transformers"] = types.SimpleNamespace(SentenceTransformer=object)


def fake_embed_texts(texts):
    """Hashed bag-of-words, L2-normalised: texts that share words are similar."""
    out = np.zeros((len(texts), 512))
    for i, t in enumerate(texts):
        for w in re.findall(r"[a-z0-9+#.]+", t.lower()):
            out[i, zlib.crc32(w.encode()) % 512] += 1.0
        n = np.linalg.norm(out[i])
        if n:
            out[i] /= n
    return out


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    from backend.core import embeddings
    monkeypatch.setattr(embeddings, "embed_texts", fake_embed_texts)


@pytest.fixture(autouse=True)
def _fake_embedding_scale(monkeypatch):
    # The fake bag-of-words vectors have a different cosine distribution than BGE;
    # use a matching useful range so rescaling behaves sensibly in tests.
    from backend.core import similarity
    monkeypatch.setattr(similarity, "SIM_COSINE_LOW", 0.0)
    monkeypatch.setattr(similarity, "SIM_COSINE_HIGH", 0.5)
