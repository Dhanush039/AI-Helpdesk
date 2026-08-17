from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.HelpdeskLoginView.as_view(), name="login"),
    path("logout/", views.HelpdeskLogoutView.as_view(), name="logout"),
    path("register/", views.register_view, name="register"),

    path("tickets/", views.ticket_list, name="ticket_list"),
    path("tickets/new/", views.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", views.ticket_detail, name="ticket_detail"),
    path("tickets/<int:pk>/analyze/", views.ticket_analyze, name="ticket_analyze"),
    path("tickets/<int:pk>/assign/", views.ticket_assign, name="ticket_assign"),
    path("tickets/<int:pk>/status/<str:new_status>/", views.ticket_update_status, name="ticket_update_status"),

    path("knowledge-base/", views.knowledge_base_list, name="kb_list"),
    path("knowledge-base/<int:pk>/", views.knowledge_base_detail, name="kb_detail"),

    path("ai-assistant/", views.ai_support_assistant, name="ai_assistant"),
]
