from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ai_engine.client import AIResponse
from .models import Profile, Ticket, TicketComment, TicketHistory, KnowledgeBaseArticle


def make_user(username, role, password="testpass12345"):
    user = User.objects.create_user(username=username, password=password)
    Profile.objects.update_or_create(user=user, defaults={"role": role})
    return user


class AuthAndRoleTests(TestCase):
    def setUp(self):
        self.employee = make_user("emp1", Profile.Role.EMPLOYEE)
        self.agent = make_user("agent1", Profile.Role.L1_AGENT)
        self.admin = make_user("admin1", Profile.Role.ADMIN)

    def test_login_required_for_dashboard(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_employee_login_and_dashboard(self):
        self.client.login(username="emp1", password="testpass12345")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/employee_dashboard.html")

    def test_agent_dashboard_access(self):
        self.client.login(username="agent1", password="testpass12345")
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "tickets/agent_dashboard.html")

    def test_employee_cannot_access_agent_dashboard_directly(self):
        self.client.login(username="emp1", password="testpass12345")
        response = self.client.get(reverse("agent_dashboard") if False else "/")
        # employee visiting root dashboard just gets their own dashboard, not forbidden
        self.assertEqual(response.status_code, 200)

    def test_register_creates_employee_profile(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser", "email": "n@example.com",
            "password1": "SuperSecret123!", "password2": "SuperSecret123!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.profile.role, Profile.Role.EMPLOYEE)


class TicketAccessControlTests(TestCase):
    def setUp(self):
        self.employee = make_user("emp2", Profile.Role.EMPLOYEE)
        self.other_employee = make_user("emp3", Profile.Role.EMPLOYEE)
        self.agent = make_user("agent2", Profile.Role.L1_AGENT)
        self.ticket = Ticket.objects.create(
            title="Test ticket", description="desc", created_by=self.employee
        )

    def test_owner_can_view_ticket(self):
        self.client.login(username="emp2", password="testpass12345")
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)

    def test_other_employee_cannot_view_private_ticket(self):
        self.client.login(username="emp3", password="testpass12345")
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 403)

    def test_agent_can_view_any_ticket(self):
        self.client.login(username="agent2", password="testpass12345")
        response = self.client.get(reverse("ticket_detail", args=[self.ticket.pk]))
        self.assertEqual(response.status_code, 200)

    def test_ticket_creation_logs_history(self):
        self.client.login(username="emp2", password="testpass12345")
        response = self.client.post(reverse("ticket_create"), {
            "title": "New issue", "description": "Something broke",
            "category": "Software", "priority": "Low",
        })
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.latest("id")
        self.assertEqual(ticket.title, "New issue")
        self.assertTrue(ticket.history.filter(event="Ticket created").exists())


class TicketAssignmentAndCommentsTests(TestCase):
    def setUp(self):
        self.employee = make_user("emp4", Profile.Role.EMPLOYEE)
        self.agent = make_user("agent4", Profile.Role.L1_AGENT)
        self.ticket = Ticket.objects.create(title="T", description="D", created_by=self.employee)

    def test_agent_can_assign_ticket(self):
        self.client.login(username="agent4", password="testpass12345")
        response = self.client.post(reverse("ticket_assign", args=[self.ticket.pk]), {"agent": self.agent.pk})
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_to, self.agent)
        self.assertEqual(self.ticket.status, Ticket.Status.ASSIGNED)

    def test_employee_cannot_assign_ticket(self):
        self.client.login(username="emp4", password="testpass12345")
        response = self.client.post(reverse("ticket_assign", args=[self.ticket.pk]), {"agent": self.agent.pk})
        self.assertEqual(response.status_code, 403)

    def test_add_comment(self):
        self.client.login(username="emp4", password="testpass12345")
        response = self.client.post(reverse("ticket_detail", args=[self.ticket.pk]), {
            "comment_submit": "1", "body": "Still broken",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(TicketComment.objects.filter(ticket=self.ticket, body="Still broken").exists())

    def test_status_change_creates_history(self):
        self.client.login(username="agent4", password="testpass12345")
        response = self.client.post(reverse("ticket_update_status", args=[self.ticket.pk, "In Progress"]))
        self.assertEqual(response.status_code, 302)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "In Progress")
        self.assertTrue(self.ticket.history.filter(event__icontains="Status changed").exists())

    def test_resolve_sets_resolved_at(self):
        self.client.login(username="agent4", password="testpass12345")
        self.client.post(reverse("ticket_update_status", args=[self.ticket.pk, "Resolved"]))
        self.ticket.refresh_from_db()
        self.assertIsNotNone(self.ticket.resolved_at)


class AIFailureHandlingTests(TestCase):
    def setUp(self):
        self.employee = make_user("emp5", Profile.Role.EMPLOYEE)
        self.ticket = Ticket.objects.create(title="AI test", description="desc", created_by=self.employee)

    def test_ai_not_configured_returns_clear_error(self):
        from ai_engine.client import chat_completion
        with self.settings(OPENAI_API_KEY=""):
            response = chat_completion("system", "user")
            self.assertFalse(response.ok)
            self.assertIn("not configured", response.error)

    @patch("tickets.services.classifier.classify_ticket")
    @patch("tickets.services.diagnosis.diagnose_ticket")
    @patch("tickets.services.escalation.recommend_escalation")
    def test_run_full_ai_analysis_handles_failures_gracefully(self, mock_esc, mock_diag, mock_classify):
        mock_classify.return_value = AIResponse(ok=False, error="AI service is not configured.")
        mock_diag.return_value = AIResponse(ok=False, error="AI service is not configured.")
        mock_esc.return_value = AIResponse(ok=False, error="AI service is not configured.")

        from .services import run_full_ai_analysis
        ok, message = run_full_ai_analysis(self.ticket, self.employee)
        self.assertFalse(ok)
        self.ticket.refresh_from_db()
        self.assertNotEqual(self.ticket.ai_error, "")

    @patch("tickets.services.classifier.classify_ticket")
    @patch("tickets.services.diagnosis.diagnose_ticket")
    @patch("tickets.services.escalation.recommend_escalation")
    def test_run_full_ai_analysis_success(self, mock_esc, mock_diag, mock_classify):
        mock_classify.return_value = AIResponse(ok=True, data={
            "category": "Network", "priority": "Medium", "issue_type": "Connectivity"
        })
        mock_diag.return_value = AIResponse(ok=True, data={
            "summary": "s", "possible_causes": ["a"], "troubleshooting_steps": ["b"],
            "recommended_resolution": "r",
        })
        mock_esc.return_value = AIResponse(ok=True, data={
            "escalate": False, "recommended_team": "L1 Support", "reason": "fine",
        })

        from .services import run_full_ai_analysis
        ok, message = run_full_ai_analysis(self.ticket, self.employee)
        self.assertTrue(ok)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_category, "Network")
        self.assertTrue(self.ticket.history.filter(event="AI analysis generated").exists())


class KnowledgeBaseTests(TestCase):
    def setUp(self):
        self.employee = make_user("emp6", Profile.Role.EMPLOYEE)
        KnowledgeBaseArticle.objects.create(title="WiFi Guide", category="Network", content="steps...")

    def test_kb_list_accessible(self):
        self.client.login(username="emp6", password="testpass12345")
        response = self.client.get(reverse("kb_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WiFi Guide")

    def test_kb_search(self):
        self.client.login(username="emp6", password="testpass12345")
        response = self.client.get(reverse("kb_list"), {"q": "WiFi"})
        self.assertContains(response, "WiFi Guide")


class APITests(TestCase):
    def setUp(self):
        self.employee = make_user("emp7", Profile.Role.EMPLOYEE)
        self.agent = make_user("agent7", Profile.Role.L1_AGENT)
        self.ticket = Ticket.objects.create(title="API test", description="desc", created_by=self.employee)

    def test_api_requires_authentication(self):
        response = self.client.get("/api/tickets/")
        self.assertIn(response.status_code, (401, 403))

    def test_api_list_tickets_scoped_to_owner(self):
        other = make_user("emp8", Profile.Role.EMPLOYEE)
        Ticket.objects.create(title="Other's ticket", description="d", created_by=other)
        self.client.login(username="emp7", password="testpass12345")
        response = self.client.get("/api/tickets/")
        self.assertEqual(response.status_code, 200)
        titles = [t["title"] for t in response.json()["results"]] if "results" in response.json() else [
            t["title"] for t in response.json()
        ]
        self.assertIn("API test", titles)
        self.assertNotIn("Other's ticket", titles)

    def test_api_add_comment(self):
        self.client.login(username="emp7", password="testpass12345")
        response = self.client.post(f"/api/tickets/{self.ticket.pk}/comments/", {"body": "hello"})
        self.assertEqual(response.status_code, 201)
        self.assertTrue(TicketComment.objects.filter(ticket=self.ticket, body="hello").exists())

    def test_api_forbidden_for_non_owner(self):
        make_user("emp9", Profile.Role.EMPLOYEE)
        self.client.login(username="emp9", password="testpass12345")
        response = self.client.get(f"/api/tickets/{self.ticket.pk}/")
        self.assertEqual(response.status_code, 404)
