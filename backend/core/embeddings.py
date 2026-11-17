import numpy as np
from backend.config import EMBEDDING_MODEL

# Loaded once and reused across requests (avoids reloading the model every call)
_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Batched, L2-normalised embeddings, shape (len(texts), dim)."""
    if not texts:
        return np.zeros((0, 1))
    model = get_model()
    return model.encode(
        list(texts), convert_to_numpy=True, normalize_embeddings=True, batch_size=32
    )


def embed_text(text: str) -> np.ndarray:
    """Single embedding vector. Prefer embed_texts() when you have several strings."""
    return embed_texts([text])[0]
