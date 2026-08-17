"""
Management command to populate the database with demo/sample data:
- demo accounts (admin / agent / employee)
- sample knowledge-base articles
- at least 10 realistic tickets with comments and history

Usage:
    python manage.py load_demo_data
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import Profile, Ticket, TicketComment, TicketHistory, KnowledgeBaseArticle

DEMO_PASSWORD_ADMIN = "admin12345"
DEMO_PASSWORD_AGENT = "agent12345"
DEMO_PASSWORD_EMPLOYEE = "employee12345"


class Command(BaseCommand):
    help = "Load demo accounts, knowledge-base articles, and sample tickets."

    def handle(self, *args, **options):
        self.stdout.write("Loading demo data...")

        admin = self._get_or_create_user("admin", DEMO_PASSWORD_ADMIN, Profile.Role.ADMIN,
                                          is_staff=True, is_superuser=True)
        agent = self._get_or_create_user("agent", DEMO_PASSWORD_AGENT, Profile.Role.L1_AGENT)
        agent2 = self._get_or_create_user("agent2", DEMO_PASSWORD_AGENT, Profile.Role.L1_AGENT)
        employee = self._get_or_create_user("employee", DEMO_PASSWORD_EMPLOYEE, Profile.Role.EMPLOYEE)
        employee2 = self._get_or_create_user("employee2", DEMO_PASSWORD_EMPLOYEE, Profile.Role.EMPLOYEE)

        self._load_knowledge_base()
        self._load_tickets(admin, agent, agent2, employee, employee2)

        self.stdout.write(self.style.SUCCESS("Demo data loaded successfully."))
        self.stdout.write("Demo accounts (development only):")
        self.stdout.write(f"  admin    / {DEMO_PASSWORD_ADMIN}")
        self.stdout.write(f"  agent    / {DEMO_PASSWORD_AGENT}")
        self.stdout.write(f"  employee / {DEMO_PASSWORD_EMPLOYEE}")

    def _get_or_create_user(self, username, password, role, is_staff=False, is_superuser=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": f"{username}@example.com", "is_staff": is_staff, "is_superuser": is_superuser},
        )
        if created:
            user.set_password(password)
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.save()
        Profile.objects.update_or_create(user=user, defaults={"role": role})
        return user

    def _load_knowledge_base(self):
        articles = [
            ("WiFi Troubleshooting Guide", "Network",
             "Steps to resolve common WiFi connectivity issues.",
             "1. Toggle WiFi off/on.\n2. Forget and reconnect to the network.\n"
             "3. Check the WiFi adapter driver is up to date.\n4. Restart the router if you control it.\n"
             "5. Escalate to Network L2 if the issue affects multiple users."),
            ("DNS Troubleshooting Guide", "Network",
             "How to diagnose and fix DNS resolution problems on Windows.",
             "1. Run 'ipconfig /all' to check current DNS servers.\n2. Run 'ipconfig /flushdns'.\n"
             "3. Try a public DNS (e.g. 8.8.8.8) temporarily to isolate the issue.\n"
             "4. Ping the default gateway to confirm local connectivity.\n"
             "5. If the problem persists, escalate to Network L2."),
            ("VPN Troubleshooting Guide", "VPN",
             "Common fixes for VPN client connection failures.",
             "1. Confirm the user's credentials and MFA are working.\n2. Restart the VPN client.\n"
             "3. Check for an expired VPN certificate.\n4. Verify local internet connectivity first.\n"
             "5. Escalate to Network L2 for persistent authentication failures."),
            ("Outlook Troubleshooting Guide", "Email",
             "Resolving common Outlook send/receive and profile issues.",
             "1. Check Outlook is in 'Connected' mode (bottom status bar).\n"
             "2. Restart Outlook, then restart the machine.\n"
             "3. Run Outlook in Safe Mode to rule out add-ins.\n"
             "4. Recreate the Outlook profile if the mailbox fails to load.\n"
             "5. Escalate to the Email/Exchange team for server-side mailbox issues."),
            ("Printer Troubleshooting Guide", "Printer",
             "Steps for resolving common printer connectivity/print-job issues.",
             "1. Check the printer is powered on and has paper/toner.\n"
             "2. Clear the print queue and resend the job.\n"
             "3. Reinstall or update the printer driver.\n"
             "4. Confirm the printer is on the correct network/VLAN.\n"
             "5. Escalate to the Hardware team for physical printer faults."),
            ("Windows Password Reset Guide", "Access / IAM",
             "How agents should assist with password reset requests.",
             "1. Verify the requester's identity per company policy.\n"
             "2. Use the IAM portal to trigger a password reset.\n"
             "3. Confirm the account is not locked due to repeated failed attempts.\n"
             "4. Have the user set a new password on next login.\n"
             "5. Escalate to IAM Team for accounts with unusual lockout patterns."),
            ("Shared Drive Access Guide", "Access / IAM",
             "Diagnosing shared/network drive access problems.",
             "1. Confirm the user is connected to VPN if working remotely.\n"
             "2. Check the user is a member of the correct security group.\n"
             "3. Try accessing the drive via UNC path directly.\n"
             "4. Restart the machine to refresh Kerberos tickets/group membership.\n"
             "5. Escalate to IAM Team if group membership needs to be changed."),
            ("Basic Windows Network Troubleshooting", "Network",
             "General first-line steps for 'no internet access' style tickets.",
             "1. Check physical/WiFi connection status.\n2. Run 'ipconfig /all' and look for an APIPA (169.254.x.x) address.\n"
             "3. Run 'ipconfig /release' then 'ipconfig /renew'.\n4. Ping the default gateway, then a public IP, then a domain name.\n"
             "5. Escalate to Network L2 if DHCP/DNS steps do not resolve it."),
        ]
        for title, category, summary, content in articles:
            KnowledgeBaseArticle.objects.get_or_create(
                title=title, defaults={"category": category, "summary": summary, "content": content}
            )

    def _load_tickets(self, admin, agent, agent2, employee, employee2):
        if Ticket.objects.count() >= 10:
            self.stdout.write("Tickets already loaded, skipping.")
            return

        sample_tickets = [
            ("Laptop WiFi not working", "Network", "Medium",
             "My laptop is connected to WiFi but I cannot access any websites.", employee, agent),
            ("Outlook emails not sending", "Email", "Medium",
             "I can receive emails in Outlook but anything I send stays stuck in the Outbox.", employee2, agent),
            ("Printer not responding", "Printer", "Low",
             "The 3rd floor printer shows online but nothing prints, jobs just disappear from the queue.", employee, None),
            ("VPN connection failed", "VPN", "High",
             "I can't connect to the company VPN from home, it fails right after entering my password.", employee2, agent2),
            ("Windows password reset", "Access / IAM", "Medium",
             "I forgot my Windows login password and I'm locked out of my laptop.", employee, agent),
            ("Software installation request", "Software", "Low",
             "I need Adobe Acrobat Pro installed on my laptop for a client project.", employee2, None),
            ("Laptop overheating", "Hardware", "High",
             "My laptop fan is running constantly and the bottom gets very hot, it shuts down randomly.", employee, agent2),
            ("DNS issue - internal sites unreachable", "Network", "Medium",
             "I can reach the internet but internal company sites like the wiki won't load.", employee2, agent),
            ("Account locked after failed logins", "Security", "High",
             "My account got locked after a few failed login attempts, possibly a phishing attempt beforehand.", employee, agent2),
            ("Shared drive inaccessible", "Access / IAM", "Medium",
             "I can't access the Finance shared drive anymore, it worked yesterday.", employee2, agent),
            ("Monitor not detected", "Hardware", "Low",
             "My second monitor is not being detected after a Windows update.", employee, None),
            ("Critical: production app down for whole team", "Software", "Critical",
             "Our order-processing application is throwing 500 errors for the entire team since this morning.", employee2, agent2),
        ]

        statuses_cycle = [
            Ticket.Status.RESOLVED, Ticket.Status.CLOSED, Ticket.Status.OPEN,
            Ticket.Status.ESCALATED, Ticket.Status.IN_PROGRESS,
        ]

        for i, (title, category, priority, description, creator, assignee) in enumerate(sample_tickets):
            status = statuses_cycle[i % len(statuses_cycle)] if assignee else Ticket.Status.OPEN
            ticket = Ticket.objects.create(
                title=title, description=description, category=category, priority=priority,
                status=status, created_by=creator, assigned_to=assignee,
            )
            if status == Ticket.Status.RESOLVED:
                ticket.resolved_at = timezone.now()
                ticket.save(update_fields=["resolved_at"])

            TicketHistory.log(ticket, creator, "Ticket created")
            if assignee:
                TicketHistory.log(ticket, admin, f"Assigned to {assignee.username}")
                TicketComment.objects.create(ticket=ticket, author=assignee,
                                              body="Thanks for reporting this - looking into it now.")
                TicketComment.objects.create(ticket=ticket, author=creator,
                                              body="Sure, let me know if you need any more details.")
                TicketHistory.log(ticket, assignee, "Comment added")
            if status in (Ticket.Status.RESOLVED, Ticket.Status.CLOSED):
                TicketHistory.log(ticket, assignee or admin, f"Status changed to {status}")
            if status == Ticket.Status.ESCALATED:
                TicketHistory.log(ticket, assignee or admin, "Escalated to Network L2")

        self.stdout.write(f"Created {len(sample_tickets)} sample tickets with comments and history.")
