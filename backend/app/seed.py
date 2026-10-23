"""
Seeds the aiops database with realistic sample data for the
Text-to-SQL demo: employees, servers, incidents, vulnerabilities.

Run: python -m app.seed
"""
import random
from datetime import date, timedelta

from app.db import Base, engine, SessionLocal
from app.models import Employee, Server, Incident, Vulnerability

FIRST_NAMES = [
    "Arjun", "Priya", "Rahul", "Sneha", "Vikram", "Anita", "Karan", "Divya",
    "Rohan", "Meera", "Sanjay", "Pooja", "Nikhil", "Kavya", "Amit", "Riya",
]
LAST_NAMES = [
    "Sharma", "Patel", "Iyer", "Reddy", "Nair", "Gupta", "Verma", "Menon",
    "Rao", "Kapoor", "Joshi", "Desai", "Chauhan", "Pillai", "Mishra", "Bose",
]
DEPARTMENTS = ["Engineering", "Security", "Infrastructure", "Data", "Support"]
ROLES = ["Engineer", "Senior Engineer", "Lead", "Manager", "Analyst"]
TEAMS = ["Linux Team", "Windows Team", "Network Team", "Database Team", "Cloud Team"]
ENVIRONMENTS = ["prod", "staging", "dev"]
OS_LIST = ["RHEL 8", "RHEL 9", "Ubuntu 22.04", "Windows Server 2019", "Windows Server 2022"]
SEVERITIES = ["Critical", "High", "Medium", "Low"]
INCIDENT_SEVERITIES = ["P1", "P2", "P3", "P4"]
INCIDENT_STATUSES = ["open", "in_progress", "resolved"]


def random_date(start_year=2021, end_year=2025):
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def seed():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Employees
        employees = []
        for i in range(40):
            hire = random_date(2015, 2024)
            years_exp = max(0, (date.today() - hire).days // 365)
            emp = Employee(
                name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                department=random.choice(DEPARTMENTS),
                role=random.choice(ROLES),
                hire_date=hire,
                salary=random.randint(600000, 2500000),
                years_experience=years_exp,
            )
            employees.append(emp)
        db.add_all(employees)

        # Servers
        servers = []
        for i in range(25):
            srv = Server(
                hostname=f"{random.choice(['PROD', 'STG', 'DEV'])}-{100 + i}",
                environment=random.choice(ENVIRONMENTS),
                os=random.choice(OS_LIST),
                team=random.choice(TEAMS),
            )
            servers.append(srv)
        db.add_all(servers)
        db.flush()  # get server IDs

        # Incidents
        incidents = []
        for i in range(60):
            srv = random.choice(servers)
            created = random_date(2023, 2025)
            status = random.choice(INCIDENT_STATUSES)
            resolved = created + timedelta(days=random.randint(0, 10)) if status == "resolved" else None
            inc = Incident(
                title=f"Incident on {srv.hostname}: {random.choice(['High CPU', 'Disk full', 'Service down', 'Network latency', 'Login failures'])}",
                severity=random.choice(INCIDENT_SEVERITIES),
                status=status,
                team=srv.team,
                server_id=srv.id,
                created_date=created,
                resolved_date=resolved,
                description="Auto-generated sample incident for demo purposes.",
            )
            incidents.append(inc)
        db.add_all(incidents)

        # Vulnerabilities
        vulns = []
        for i in range(80):
            srv = random.choice(servers)
            vuln = Vulnerability(
                cve_id=f"CVE-2024-{1000 + i}",
                severity=random.choice(SEVERITIES),
                status=random.choice(["open", "remediated"]),
                server_id=srv.id,
                discovered_date=random_date(2023, 2025),
            )
            vulns.append(vuln)
        db.add_all(vulns)

        db.commit()
        print(f"Seeded {len(employees)} employees, {len(servers)} servers, "
              f"{len(incidents)} incidents, {len(vulns)} vulnerabilities.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
