"""
Database schema for the AI Ops Assistant demo dataset.
Run with: python -m app.seed  (after activating the venv)
"""
from sqlalchemy import (
    Column, Integer, String, Date, Numeric, ForeignKey, Text
)
from sqlalchemy.orm import relationship

from app.db import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    role = Column(String, nullable=False)
    hire_date = Column(Date, nullable=False)
    salary = Column(Numeric, nullable=False)
    years_experience = Column(Integer, nullable=False)


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True)
    hostname = Column(String, nullable=False, unique=True)
    environment = Column(String, nullable=False)  # prod, staging, dev
    os = Column(String, nullable=False)
    team = Column(String, nullable=False)

    vulnerabilities = relationship("Vulnerability", back_populates="server")
    incidents = relationship("Incident", back_populates="server")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # P1, P2, P3, P4
    status = Column(String, nullable=False)    # open, in_progress, resolved
    team = Column(String, nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"))
    created_date = Column(Date, nullable=False)
    resolved_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)

    server = relationship("Server", back_populates="incidents")


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"

    id = Column(Integer, primary_key=True)
    cve_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)  # Critical, High, Medium, Low
    status = Column(String, nullable=False)    # open, remediated
    server_id = Column(Integer, ForeignKey("servers.id"))
    discovered_date = Column(Date, nullable=False)

    server = relationship("Server", back_populates="vulnerabilities")
