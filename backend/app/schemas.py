"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models import SideEnum, CategoryEnum, UnitEnum, ImportJobStatusEnum
import uuid


# Document schemas
class DocumentBase(BaseModel):
    year: int


class DocumentCreate(DocumentBase):
    filename: str


class DocumentResponse(DocumentBase):
    id: uuid.UUID
    filename: str
    uploaded_at: datetime
    archived: bool = False
    
    class Config:
        from_attributes = True


# Budget item schemas
class BudgetItemBase(BaseModel):
    side: SideEnum
    category: CategoryEnum
    description_original: str
    value: Optional[float] = None
    unit: UnitEnum
    page_number: int
    evidence_text: str
    explanation: str


class BudgetItemResponse(BudgetItemBase):
    id: uuid.UUID
    document_id: uuid.UUID
    year: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Summary schemas
class CategorySummary(BaseModel):
    category: CategoryEnum
    total_value: float
    item_count: int


class DocumentSummary(BaseModel):
    document_id: uuid.UUID
    year: int
    revenue_total: float
    expense_total: float
    revenue_by_category: List[CategorySummary]
    expense_by_category: List[CategorySummary]


# Import job schemas
class ImportJobResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    status: ImportJobStatusEnum
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# LLM extraction schemas (for validation)
class ExtractedItem(BaseModel):
    """Single extracted budget item from LLM."""
    side: SideEnum
    descriptionOriginal: str = Field(..., alias="descriptionOriginal")
    value: Optional[float] = None
    unit: UnitEnum
    pageNumber: int = Field(..., alias="pageNumber")
    evidenceText: str = Field(..., alias="evidenceText")
    
    class Config:
        populate_by_name = True


class ExtractResponse(BaseModel):
    """LLM response for item extraction."""
    items: List[ExtractedItem]

