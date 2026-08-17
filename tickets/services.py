"""
tickets.services
=================

Shared business logic kept out of views/templates:
* role/permission helpers
* AI orchestration glue (calls ai_engine, writes results onto the Ticket)
* a lightweight "similar tickets" text-similarity search

Similarity search uses Python's stdlib difflib so there is zero extra
dependency for the first version, while keeping the function signature
generic enough to swap in embeddings/vector search later without
touching call sites.
"""

from __future__ import annotations

import difflib
from django.utils import timezone

from ai_engine import classifier, diagnosis, escalation
from .models import Ticket, TicketHistory


def user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return "ADMIN"
    profile = getattr(user, "profile", None)
    return profile.role if profile else None


def is_admin(user):
    return user_role(user) == "ADMIN"


def is_agent(user):
    return user_role(user) == "L1_AGENT"


def is_employee(user):
    return user_role(user) == "EMPLOYEE"


def can_view_ticket(user, ticket: Ticket) -> bool:
    if is_admin(user) or is_agent(user):
        return True
    return ticket.created_by_id == user.id


def visible_tickets_for(user):
    """Return the Ticket queryset a given user is allowed to see."""
    if is_admin(user):
        return Ticket.objects.all()
    if is_agent(user):
        return Ticket.objects.all()
    return Ticket.objects.filter(created_by=user)


def run_full_ai_analysis(ticket: Ticket, actor) -> tuple[bool, str]:
    """
    Run classification + diagnosis + escalation recommendation for a ticket
    and persist the results. Returns (success, message).
    Never raises - all AI failures are caught and stored on the ticket.
    """
    errors = []

    classify_resp = classifier.classify_ticket(ticket.title, ticket.description)
    if classify_resp.ok:
        data = classify_resp.data or {}
        ticket.ai_category = data.get("category", "")
        ticket.ai_priority = data.get("priority", "")
        ticket.ai_issue_type = data.get("issue_type", "")
    else:
        errors.append(classify_resp.error or "Classification failed.")

    diag_resp = diagnosis.diagnose_ticket(ticket.title, ticket.description)
    if diag_resp.ok:
        data = diag_resp.data or {}
        ticket.ai_diagnosis = data
        ticket.ai_summary = data.get("summary", "")
        ticket.ai_suggested_solution = data.get("recommended_resolution", "")
    else:
        errors.append(diag_resp.error or "Diagnosis failed.")

    esc_resp = escalation.recommend_escalation(ticket.title, ticket.description)
    if esc_resp.ok:
        data = esc_resp.data or {}
        ticket.ai_escalation_recommendation = "Yes" if data.get("escalate") else "No"
        ticket.ai_recommended_team = data.get("recommended_team", "")
    else:
        errors.append(esc_resp.error or "Escalation recommendation failed.")

    ticket.ai_last_analyzed_at = timezone.now()
    ticket.ai_error = " | ".join(errors)[:255]
    ticket.save()

    TicketHistory.log(ticket, actor, "AI analysis generated" if not errors else "AI analysis generated with errors")

    if errors and not (classify_resp.ok or diag_resp.ok):
        return False, ticket.ai_error
    return True, "AI analysis complete." if not errors else f"AI analysis partially completed ({ticket.ai_error})"


def find_similar_tickets(ticket: Ticket, limit: int = 5):
    """
    Very small first-pass "similar ticket" search using difflib text
    similarity over title+description. Good enough for a first version;
    the signature is intentionally simple so it can later be replaced
    with an embeddings/vector-search backed implementation without
    changing call sites.
    """
    target_text = f"{ticket.title} {ticket.description}".lower()

    candidates = Ticket.objects.exclude(pk=ticket.pk).exclude(
        status__in=[Ticket.Status.OPEN]
    ).order_by("-created_at")[:200]

    scored = []
    for candidate in candidates:
        candidate_text = f"{candidate.title} {candidate.description}".lower()
        score = difflib.SequenceMatcher(None, target_text, candidate_text).ratio()
        if score > 0.25:
            scored.append((score, candidate))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [c for _, c in scored[:limit]]


def search_knowledge_base(query: str):
    from .models import KnowledgeBaseArticle
    if not query:
        return KnowledgeBaseArticle.objects.all()
    return KnowledgeBaseArticle.objects.filter(title__icontains=query) | \
        KnowledgeBaseArticle.objects.filter(content__icontains=query)
