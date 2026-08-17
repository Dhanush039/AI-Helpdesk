from django.contrib import admin
from .models import Profile, Category, Ticket, TicketComment, TicketHistory, KnowledgeBaseArticle


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "department")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description")


class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 0
    readonly_fields = ("created_at",)


class TicketHistoryInline(admin.TabularInline):
    model = TicketHistory
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "priority", "status", "created_by", "assigned_to", "created_at")
    list_filter = ("status", "priority", "category")
    search_fields = ("title", "description")
    inlines = [TicketCommentInline, TicketHistoryInline]
    readonly_fields = (
        "created_at", "updated_at", "resolved_at", "ai_category", "ai_priority",
        "ai_issue_type", "ai_summary", "ai_diagnosis", "ai_suggested_solution",
        "ai_escalation_recommendation", "ai_recommended_team", "ai_last_analyzed_at", "ai_error",
    )


@admin.register(KnowledgeBaseArticle)
class KnowledgeBaseArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "updated_at")
    list_filter = ("category",)
    search_fields = ("title", "content")
