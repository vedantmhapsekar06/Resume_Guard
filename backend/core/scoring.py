from typing import Optional

from backend.config import SCORE_WEIGHTS, FIT_THRESHOLDS, MIN_REQUIRED_COVERAGE_FOR_STRONG


def compute_final_score(
    skills_score: float,
    experience_score: float,
    similarity_score: Optional[float],
    evidence_score: float,
) -> float:
    """
    Combines individual scores into a weighted final score (0-100) using the weights in
    config.py (40/30/20/10 by default). If similarity could not be computed (embeddings
    unavailable) that component is dropped and the other weights are re-normalised, rather
    than substituting a made-up number.
    """
    components = {
        "skills_match": skills_score,
        "experience_relevance": experience_score,
        "semantic_similarity": similarity_score,
        "evidence_quality": evidence_score,
    }
    used = {k: v for k, v in components.items() if v is not None}
    total_weight = sum(SCORE_WEIGHTS[k] for k in used)
    final = sum(v * SCORE_WEIGHTS[k] for k, v in used.items()) / total_weight
    return round(max(0.0, min(100.0, final)), 2)


def determine_fit_label(final_score: float, required_coverage: Optional[float] = None) -> str:
    """
    Maps a score to a Fit label (thresholds in config.py), with a knockout rule:
    a candidate covering under half of the required skills cannot be a Strong Fit,
    and one covering none of them is a No Fit, however high the other components are.
    required_coverage = share (0-1) of required skills found at all; None if the JD lists none.
    """
    if final_score >= FIT_THRESHOLDS["strong_fit"]:
        label = "Strong Fit"
    elif final_score >= FIT_THRESHOLDS["partial_fit"]:
        label = "Partial Fit"
    else:
        label = "No Fit"

    if required_coverage is not None:
        if required_coverage <= 0:
            return "No Fit"
        if label == "Strong Fit" and required_coverage < MIN_REQUIRED_COVERAGE_FOR_STRONG:
            return "Partial Fit"
    return label


def determine_priority_label(
    final_score: float, risk_flags: list[str], fit_label: Optional[str] = None
) -> str:
    """
    Priority is separate from Fit - a Strong Fit candidate can still be Medium priority if
    there are risk flags to verify. Priority is always consistent with the fit label shown.
    """
    if fit_label is None:
        fit_label = determine_fit_label(final_score)

    if fit_label == "Strong Fit":
        return "Medium" if risk_flags else "High"
    if fit_label == "Partial Fit":
        return "Medium"
    return "Low"
