"""
REST API views (Django REST Framework).

Sensitive fields (AI raw errors, internal notes) are never serialized.
Access control mirrors the template views: employees only see their own
tickets, agents/admins see everything.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound

from ai_engine import assistant as ai_assistant
from . import services
from .models import Ticket, TicketComment, KnowledgeBaseArticle
from .serializers import TicketSerializer, TicketCommentSerializer, KnowledgeBaseArticleSerializer


class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return services.visible_tickets_for(self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_object(self):
        obj = super().get_object()
        if not services.can_view_ticket(self.request.user, obj):
            raise PermissionDenied("You do not have permission to access this ticket.")
        return obj


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def ticket_comments(request, pk):
    try:
        ticket = Ticket.objects.get(pk=pk)
    except Ticket.DoesNotExist:
        raise NotFound("Ticket not found.")

    if not services.can_view_ticket(request.user, ticket):
        raise PermissionDenied("You do not have permission to access this ticket.")

    if request.method == "GET":
        serializer = TicketCommentSerializer(ticket.comments.all(), many=True)
        return Response(serializer.data)

    serializer = TicketCommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(ticket=ticket, author=request.user)
    from .models import TicketHistory
    TicketHistory.log(ticket, request.user, "Comment added")
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ticket_analyze(request, pk):
    try:
        ticket = Ticket.objects.get(pk=pk)
    except Ticket.DoesNotExist:
        raise NotFound("Ticket not found.")
    if not services.can_view_ticket(request.user, ticket):
        raise PermissionDenied("You do not have permission to access this ticket.")

    ok, message = services.run_full_ai_analysis(ticket, request.user)
    return Response({"success": ok, "message": message, "ticket": TicketSerializer(ticket).data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ticket_summary(request, pk):
    from ai_engine import summarizer
    try:
        ticket = Ticket.objects.get(pk=pk)
    except Ticket.DoesNotExist:
        raise NotFound("Ticket not found.")
    if not services.can_view_ticket(request.user, ticket):
        raise PermissionDenied("You do not have permission to access this ticket.")

    comments = list(ticket.comments.values_list("body", flat=True))
    response = summarizer.summarize_ticket(ticket.title, ticket.description, comments)
    if not response.ok:
        return Response({"success": False, "error": response.error}, status=503)
    return Response({"success": True, "summary": response.text})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ticket_escalate(request, pk):
    try:
        ticket = Ticket.objects.get(pk=pk)
    except Ticket.DoesNotExist:
        raise NotFound("Ticket not found.")
    if not (services.is_agent(request.user) or services.is_admin(request.user)):
        raise PermissionDenied("Only agents or admins can escalate tickets.")

    team = request.data.get("team", ticket.ai_recommended_team or "Network L2")
    ticket.status = Ticket.Status.ESCALATED
    ticket.save()
    from .models import TicketHistory
    TicketHistory.log(ticket, request.user, f"Escalated to {team}")
    return Response({"success": True, "ticket": TicketSerializer(ticket).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ai_assistant_ask(request):
    if not (services.is_agent(request.user) or services.is_admin(request.user)):
        raise PermissionDenied("The AI Support Assistant is only available to support agents.")
    question = request.data.get("question", "").strip()
    if not question:
        return Response({"success": False, "error": "A question is required."}, status=400)

    response = ai_assistant.ask_assistant(question)
    if not response.ok:
        return Response({"success": False, "error": response.error}, status=503)
    return Response({"success": True, "answer": response.text})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def knowledge_base_list(request):
    q = request.GET.get("q", "")
    articles = services.search_knowledge_base(q).distinct()
    serializer = KnowledgeBaseArticleSerializer(articles, many=True)
    return Response(serializer.data)
