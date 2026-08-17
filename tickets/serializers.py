from rest_framework import serializers
from .models import Ticket, TicketComment, KnowledgeBaseArticle


class TicketCommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TicketComment
        fields = ["id", "ticket", "author", "body", "created_at"]
        read_only_fields = ["ticket", "author", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    assigned_to = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            "id", "title", "description", "category", "priority", "status",
            "created_by", "assigned_to", "created_at", "updated_at", "resolved_at",
            "ai_category", "ai_priority", "ai_issue_type", "ai_summary",
            "ai_diagnosis", "ai_suggested_solution", "ai_escalation_recommendation",
            "ai_recommended_team", "ai_last_analyzed_at",
        ]
        read_only_fields = [
            "created_by", "created_at", "updated_at", "resolved_at",
            "ai_category", "ai_priority", "ai_issue_type", "ai_summary",
            "ai_diagnosis", "ai_suggested_solution", "ai_escalation_recommendation",
            "ai_recommended_team", "ai_last_analyzed_at",
        ]


class KnowledgeBaseArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBaseArticle
        fields = ["id", "title", "category", "summary", "content", "created_at", "updated_at"]
