import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from backend.config import SIM_COSINE_LOW, SIM_COSINE_HIGH


def compute_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Returns cosine similarity between two vectors, scaled to 0-100 (raw, not stretched)."""
    vec_a = vec_a.reshape(1, -1)
    vec_b = vec_b.reshape(1, -1)
    score = cosine_similarity(vec_a, vec_b)[0][0]
    score = max(0.0, min(1.0, float(score)))
    return round(score * 100, 2)


def compute_similarity_matrix(vectors_a, vectors_b) -> np.ndarray:
    """Cosine matrix (rows = a, cols = b), values in [-1, 1]."""
    a = np.asarray(vectors_a)
    b = np.asarray(vectors_b)
    if a.size == 0 or b.size == 0:
        return np.zeros((len(a), len(b)))
    return cosine_similarity(a, b)


def rescale_cosine(cos: float) -> float:
    """
    Maps a raw embedding cosine onto 0-100 using the configured useful range.
    BGE embeddings rarely go below ~0.4 even for unrelated text, so a raw
    'x * 100' would make every resume look at least 40% similar to every JD.
    """
    span = max(SIM_COSINE_HIGH - SIM_COSINE_LOW, 1e-6)
    return float(max(0.0, min(100.0, (cos - SIM_COSINE_LOW) / span * 100.0)))
