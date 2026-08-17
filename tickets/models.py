from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Profile(models.Model):
    """Extends the built-in Django User with an application role."""

    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        L1_AGENT = "L1_AGENT", "L1 Support Agent"
        ADMIN = "ADMIN", "Admin"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_agent(self):
        return self.role == self.Role.L1_AGENT

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.user.is_superuser


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    class Priority(models.TextChoices):
        LOW = "Low", "Low"
        MEDIUM = "Medium", "Medium"
        HIGH = "High", "High"
        CRITICAL = "Critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "Open", "Open"
        ASSIGNED = "Assigned", "Assigned"
        IN_PROGRESS = "In Progress", "In Progress"
        PENDING = "Pending", "Pending"
        RESOLVED = "Resolved", "Resolved"
        CLOSED = "Closed", "Closed"
        ESCALATED = "Escalated", "Escalated"

    CATEGORY_CHOICES = [
        ("Network", "Network"),
        ("Hardware", "Hardware"),
        ("Software", "Software"),
        ("Email", "Email"),
        ("Access / IAM", "Access / IAM"),
        ("Security", "Security"),
        ("Printer", "Printer"),
        ("VPN", "VPN"),
        ("Other", "Other"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="Other")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tickets_created")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets_assigned"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # --- AI-generated fields ---
    ai_category = models.CharField(max_length=30, blank=True)
    ai_priority = models.CharField(max_length=10, blank=True)
    ai_issue_type = models.CharField(max_length=100, blank=True)
    ai_summary = models.TextField(blank=True)
    ai_diagnosis = models.JSONField(blank=True, null=True)
    ai_suggested_solution = models.TextField(blank=True)
    ai_escalation_recommendation = models.CharField(max_length=10, blank=True)  # "Yes"/"No"
    ai_recommended_team = models.CharField(max_length=50, blank=True)
    ai_last_analyzed_at = models.DateTimeField(null=True, blank=True)
    ai_error = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def get_absolute_url(self):
        return reverse("ticket_detail", args=[self.pk])

    def mark_resolved(self):
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(update_fields=["status", "resolved_at", "updated_at"])

    @property
    def priority_badge_class(self):
        return {
            "Low": "bg-success", "Medium": "bg-info text-dark",
            "High": "bg-warning text-dark", "Critical": "bg-danger",
        }.get(self.priority, "bg-secondary")

    @property
    def status_badge_class(self):
        return {
            "Open": "bg-secondary", "Assigned": "bg-info text-dark",
            "In Progress": "bg-primary", "Pending": "bg-warning text-dark",
            "Resolved": "bg-success", "Closed": "bg-dark",
            "Escalated": "bg-danger",
        }.get(self.status, "bg-secondary")


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on ticket #{self.ticket_id}"


class TicketHistory(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="history")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    event = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Ticket history entries"

    def __str__(self):
        return f"[{self.ticket_id}] {self.event}"

    @staticmethod
    def log(ticket, actor, event):
        return TicketHistory.objects.create(ticket=ticket, actor=actor, event=event)


class KnowledgeBaseArticle(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=Ticket.CATEGORY_CHOICES, default="Other")
    summary = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
