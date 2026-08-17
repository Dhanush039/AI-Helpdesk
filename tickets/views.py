import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q

from ai_engine import assistant as ai_assistant
from ai_engine.client import is_configured as ai_is_configured

from . import services
from .forms import (
    RegisterForm, TicketForm, CommentForm, AssistantQuestionForm,
    TicketAssignForm, StyledAuthenticationForm,
)
from .models import Ticket, TicketComment, TicketHistory, KnowledgeBaseArticle, Category, Profile

logger = logging.getLogger("tickets")


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------

class HelpdeskLoginView(LoginView):
    template_name = "tickets/login.html"
    authentication_form = StyledAuthenticationForm


class HelpdeskLogoutView(LogoutView):
    next_page = "login"


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Account created successfully. Welcome!")
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "tickets/register.html", {"form": form})


# --------------------------------------------------------------------------
# Dashboard (role-aware)
# --------------------------------------------------------------------------

@login_required
def dashboard(request):
    role = services.user_role(request.user)

    if role == "ADMIN":
        return admin_dashboard(request)
    if role == "L1_AGENT":
        return agent_dashboard(request)
    return employee_dashboard(request)


@login_required
def employee_dashboard(request):
    tickets = Ticket.objects.filter(created_by=request.user)
    context = {
        "total": tickets.count(),
        "open": tickets.filter(status=Ticket.Status.OPEN).count(),
        "in_progress": tickets.filter(status=Ticket.Status.IN_PROGRESS).count(),
        "resolved": tickets.filter(status=Ticket.Status.RESOLVED).count(),
        "closed": tickets.filter(status=Ticket.Status.CLOSED).count(),
        "recent_tickets": tickets[:8],
        "ai_configured": ai_is_configured(),
    }
    return render(request, "tickets/employee_dashboard.html", context)


@login_required
def agent_dashboard(request):
    if not (services.is_agent(request.user) or services.is_admin(request.user)):
        return HttpResponseForbidden("You do not have access to the agent dashboard.")

    tickets = Ticket.objects.all()
    context = {
        "total": tickets.count(),
        "open": tickets.filter(status=Ticket.Status.OPEN).count(),
        "in_progress": tickets.filter(status=Ticket.Status.IN_PROGRESS).count(),
        "high": tickets.filter(priority=Ticket.Priority.HIGH).count(),
        "critical": tickets.filter(priority=Ticket.Priority.CRITICAL).count(),
        "escalated": tickets.filter(status=Ticket.Status.ESCALATED).count(),
        "resolved": tickets.filter(status=Ticket.Status.RESOLVED).count(),
        "my_assigned": tickets.filter(assigned_to=request.user),
        "by_category": list(tickets.values("category").annotate(count=Count("id")).order_by("-count")),
        "by_status": list(tickets.values("status").annotate(count=Count("id")).order_by("-count")),
        "by_priority": list(tickets.values("priority").annotate(count=Count("id")).order_by("-count")),
        "recent_tickets": tickets[:10],
        "ai_configured": ai_is_configured(),
    }
    return render(request, "tickets/agent_dashboard.html", context)


@login_required
def admin_dashboard(request):
    if not services.is_admin(request.user):
        return HttpResponseForbidden("You do not have access to the admin dashboard.")

    tickets = Ticket.objects.all()
    context = {
        "total": tickets.count(),
        "escalated": tickets.filter(status=Ticket.Status.ESCALATED).count(),
        "resolved": tickets.filter(status=Ticket.Status.RESOLVED).count(),
        "employees": Profile.objects.filter(role=Profile.Role.EMPLOYEE).count(),
        "agents": Profile.objects.filter(role=Profile.Role.L1_AGENT).count(),
        "kb_articles": KnowledgeBaseArticle.objects.count(),
        "by_category": list(tickets.values("category").annotate(count=Count("id")).order_by("-count")),
        "recent_tickets": tickets[:10],
        "ai_configured": ai_is_configured(),
    }
    return render(request, "tickets/admin_dashboard.html", context)


# --------------------------------------------------------------------------
# Tickets
# --------------------------------------------------------------------------

@login_required
def ticket_list(request):
    tickets = services.visible_tickets_for(request.user)

    status = request.GET.get("status")
    q = request.GET.get("q")
    if status:
        tickets = tickets.filter(status=status)
    if q:
        tickets = tickets.filter(Q(title__icontains=q) | Q(description__icontains=q))

    return render(request, "tickets/ticket_list.html", {
        "tickets": tickets,
        "status_choices": Ticket.Status.choices,
        "current_status": status or "",
        "q": q or "",
    })


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            TicketHistory.log(ticket, request.user, "Ticket created")
            messages.success(request, f"Ticket #{ticket.pk} created successfully.")
            return redirect("ticket_detail", pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, "tickets/ticket_form.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not services.can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("You do not have permission to view this ticket.")

    if request.method == "POST" and "comment_submit" in request.POST:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.ticket = ticket
            comment.author = request.user
            comment.save()
            TicketHistory.log(ticket, request.user, "Comment added")
            messages.success(request, "Comment added.")
            return redirect("ticket_detail", pk=ticket.pk)
    else:
        comment_form = CommentForm()

    assign_form = TicketAssignForm() if (services.is_agent(request.user) or services.is_admin(request.user)) else None
    similar_tickets = services.find_similar_tickets(ticket) if (services.is_agent(request.user) or services.is_admin(request.user)) else []
    kb_articles = KnowledgeBaseArticle.objects.filter(category=ticket.category)[:5]

    return render(request, "tickets/ticket_detail.html", {
        "ticket": ticket,
        "comments": ticket.comments.select_related("author"),
        "comment_form": comment_form,
        "assign_form": assign_form,
        "history": ticket.history.select_related("actor"),
        "similar_tickets": similar_tickets,
        "kb_articles": kb_articles,
        "can_manage": services.is_agent(request.user) or services.is_admin(request.user),
        "ai_configured": ai_is_configured(),
    })


@login_required
def ticket_analyze(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not services.can_view_ticket(request.user, ticket):
        return HttpResponseForbidden("You do not have permission to access this ticket.")
    if request.method != "POST":
        return redirect("ticket_detail", pk=pk)

    ok, message = services.run_full_ai_analysis(ticket, request.user)
    if ok:
        messages.success(request, message)
    else:
        messages.warning(request, message)
    return redirect("ticket_detail", pk=pk)


@login_required
def ticket_assign(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not (services.is_agent(request.user) or services.is_admin(request.user)):
        return HttpResponseForbidden("Only agents or admins can assign tickets.")
    if request.method == "POST":
        form = TicketAssignForm(request.POST)
        if form.is_valid():
            agent = form.cleaned_data["agent"]
            ticket.assigned_to = agent
            ticket.status = Ticket.Status.ASSIGNED
            ticket.save()
            TicketHistory.log(ticket, request.user, f"Assigned to {agent.username}")
            messages.success(request, f"Ticket assigned to {agent.username}.")
    return redirect("ticket_detail", pk=pk)


@login_required
def ticket_update_status(request, pk, new_status):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not (services.is_agent(request.user) or services.is_admin(request.user)):
        return HttpResponseForbidden("Only agents or admins can update ticket status.")

    valid_statuses = dict(Ticket.Status.choices)
    if new_status not in valid_statuses:
        raise PermissionDenied("Invalid status.")

    if request.method == "POST":
        ticket.status = new_status
        if new_status == Ticket.Status.RESOLVED:
            ticket.mark_resolved()
        else:
            ticket.save()
        TicketHistory.log(ticket, request.user, f"Status changed to {new_status}")
        messages.success(request, f"Ticket status updated to {new_status}.")
    return redirect("ticket_detail", pk=pk)


# --------------------------------------------------------------------------
# Knowledge Base
# --------------------------------------------------------------------------

@login_required
def knowledge_base_list(request):
    q = request.GET.get("q", "")
    articles = services.search_knowledge_base(q).distinct()
    return render(request, "tickets/knowledge_base.html", {"articles": articles, "q": q})


@login_required
def knowledge_base_detail(request, pk):
    article = get_object_or_404(KnowledgeBaseArticle, pk=pk)
    return render(request, "tickets/knowledge_base_detail.html", {"article": article})


# --------------------------------------------------------------------------
# AI Support Assistant (L1 agents)
# --------------------------------------------------------------------------

@login_required
def ai_support_assistant(request):
    if not (services.is_agent(request.user) or services.is_admin(request.user)):
        return HttpResponseForbidden("The AI Support Assistant is only available to support agents.")

    answer = None
    error = None
    if request.method == "POST":
        form = AssistantQuestionForm(request.POST)
        if form.is_valid():
            question = form.cleaned_data["question"]
            response = ai_assistant.ask_assistant(question)
            if response.ok:
                answer = response.text
            else:
                error = response.error
    else:
        form = AssistantQuestionForm()

    return render(request, "tickets/ai_assistant.html", {
        "form": form, "answer": answer, "error": error, "ai_configured": ai_is_configured(),
    })


# --------------------------------------------------------------------------
# Error handlers - never leak tracebacks to normal users
# --------------------------------------------------------------------------

def error_404(request, exception=None):
    return render(request, "tickets/404.html", status=404)


def error_500(request):
    return render(request, "tickets/500.html", status=500)
