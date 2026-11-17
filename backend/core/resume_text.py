"""Helpers that turn a ResumeProfile into text the deterministic agents can search."""
from backend.models.schemas import ResumeProfile


def _as_list(value) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if isinstance(v, (str, int, float)) and str(v).strip()]
    return []


def bullet_items(resume: ResumeProfile) -> list[dict]:
    """Every experience/project bullet with its source: [{'source','kind','text'}]."""
    items = []
    for job in resume.work_history:
        label = f"{job.get('title') or 'Role'} @ {job.get('company') or 'Company'}"
        for b in _as_list(job.get("bullets")):
            items.append({"source": label, "kind": "work", "text": b})
    for proj in resume.projects:
        label = f"Project: {proj.get('name') or 'Untitled'}"
        for b in _as_list(proj.get("bullets")):
            items.append({"source": label, "kind": "project", "text": b})
    return items


def evidence_corpus(resume: ResumeProfile) -> str:
    """
    Text in which a skill counts as DEMONSTRATED: job titles, bullets, project names,
    project descriptions/technologies. Deliberately excludes the plain Skills list.
    """
    parts = []
    for job in resume.work_history:
        parts.append(str(job.get("title") or ""))
        parts.extend(_as_list(job.get("bullets")))
    for proj in resume.projects:
        parts.append(str(proj.get("name") or ""))
        parts.extend(_as_list(proj.get("technologies")))
        parts.extend(_as_list(proj.get("bullets")))
    return "\n".join(p for p in parts if p)


def role_texts(resume: ResumeProfile) -> list[str]:
    return [
        " ".join([str(j.get("title") or "")] + _as_list(j.get("bullets"))).strip()
        for j in resume.work_history
    ]


def project_texts(resume: ResumeProfile) -> list[str]:
    return [
        " ".join(
            [str(p.get("name") or "")] + _as_list(p.get("technologies")) + _as_list(p.get("bullets"))
        ).strip()
        for p in resume.projects
    ]
