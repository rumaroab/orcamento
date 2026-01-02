"""Database models for budget documents."""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, String, Integer, Numeric, Text, ForeignKey, DateTime, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class SideEnum(str, Enum):
    """Budget side: revenue or expense."""
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class CategoryEnum(str, Enum):
    """Budget categories in Portuguese."""
    # Receitas (5)
    PERSONAL_TAXES = "Impostos sobre pessoas"
    CORPORATE_TAXES = "Impostos sobre empresas"
    TAXES_ON_PURCHASES = "Impostos sobre compras"
    SOCIAL_SECURITY_CONTRIBUTIONS = "Contribuições para segurança social"
    OTHER_REVENUE = "Outras receitas"
    
    # Despesas (8)
    HEALTH = "Saúde"
    EDUCATION = "Educação"
    PENSIONS_SOCIAL_SUPPORT = "Pensões e apoio social"
    RUNNING_GOVERNMENT = "Funcionamento do governo"
    SECURITY_DEFENSE = "Segurança e defesa"
    JUSTICE = "Justiça"
    INFRASTRUCTURE_ENVIRONMENT = "Infraestrutura e ambiente"
    PUBLIC_DEBT = "Dívida pública"


class UnitEnum(str, Enum):
    """Value unit."""
    EUR = "EUR"
    THOUSAND_EUR = "THOUSAND_EUR"
    MILLION_EUR = "MILLION_EUR"
    UNKNOWN = "UNKNOWN"


class ImportJobStatusEnum(str, Enum):
    """Import job status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class Document(Base):
    """Budget document (PDF)."""
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    year = Column(Integer, nullable=False, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    archived = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    pages = relationship("Page", back_populates="document", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="document", cascade="all, delete-orphan")
    budget_items = relationship("BudgetItem", back_populates="document", cascade="all, delete-orphan")
    import_jobs = relationship("ImportJob", back_populates="document", cascade="all, delete-orphan")


class Page(Base):
    """Extracted text from a PDF page."""
    __tablename__ = "pages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    text_raw = Column(Text, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="pages")


class Section(Base):
    """Document section with breadcrumb path."""
    __tablename__ = "sections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    title_path = Column(String, nullable=False)  # e.g., "L1 > L2 > L3"
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="sections")


class BudgetItem(Base):
    """Extracted budget line item."""
    __tablename__ = "budget_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    side = Column(SQLEnum(SideEnum), nullable=False, index=True)
    category = Column(SQLEnum(CategoryEnum), nullable=False, index=True)
    description_original = Column(Text, nullable=False)
    value = Column(Numeric(20, 2), nullable=True)
    unit = Column(SQLEnum(UnitEnum), nullable=False)
    page_number = Column(Integer, nullable=False)
    evidence_text = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="budget_items")


class ImportJob(Base):
    """Background job for processing a document."""
    __tablename__ = "import_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    status = Column(SQLEnum(ImportJobStatusEnum), default=ImportJobStatusEnum.PENDING, nullable=False)
    progress = Column(Integer, default=0, nullable=False)  # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", back_populates="import_jobs")

