from django.urls import path
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r"tickets", api_views.TicketViewSet, basename="api-ticket")

urlpatterns = router.urls + [
    path("tickets/<int:pk>/comments/", api_views.ticket_comments, name="api_ticket_comments"),
    path("tickets/<int:pk>/analyze/", api_views.ticket_analyze, name="api_ticket_analyze"),
    path("tickets/<int:pk>/summary/", api_views.ticket_summary, name="api_ticket_summary"),
    path("tickets/<int:pk>/escalate/", api_views.ticket_escalate, name="api_ticket_escalate"),
    path("ai/assistant/", api_views.ai_assistant_ask, name="api_ai_assistant"),
    path("knowledge-base/", api_views.knowledge_base_list, name="api_kb_list"),
]
