"""FastAPI application."""
import os
import uuid
import shutil
from pathlib import Path
from typing import List
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger
from app.database import get_db, Base, engine
from app.models import (
    Document, BudgetItem, ImportJob, Page,
    SideEnum, CategoryEnum, ImportJobStatusEnum
)
from app.schemas import (
    DocumentResponse, DocumentSummary, BudgetItemResponse,
    CategorySummary, ImportJobResponse
)
from app.tasks import process_document
from app.config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Ensure storage directory exists
os.makedirs(settings.STORAGE_PATH, exist_ok=True)

app = FastAPI(title="Budget Document API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post(f"{settings.API_V1_PREFIX}/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    year: int = Query(..., description="Year of the budget document"),
    db: Session = Depends(get_db)
):
    """Upload a budget PDF document."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate document ID
    doc_id = uuid.uuid4()
    filepath = os.path.join(settings.STORAGE_PATH, f"{doc_id}.pdf")
    
    # Save file
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logger.info(f"Saved uploaded file to {filepath}")
    
    # Create document record
    document = Document(
        id=doc_id,
        year=year,
        filename=file.filename,
        filepath=filepath
    )
    db.add(document)
    
    # Create import job
    import_job = ImportJob(
        document_id=doc_id,
        status=ImportJobStatusEnum.PENDING
    )
    db.add(import_job)
    db.commit()
    
    # Start background processing
    process_document.delay(str(doc_id), str(import_job.id))
    
    return {
        "document_id": doc_id,
        "import_job_id": import_job.id,
        "status": "uploaded"
    }


@app.get(f"{settings.API_V1_PREFIX}/documents", response_model=List[DocumentResponse])
def list_documents(
    include_archived: bool = Query(False, description="Include archived documents"),
    db: Session = Depends(get_db)
):
    """List all documents. Archived documents are excluded by default."""
    query = db.query(Document)
    if not include_archived:
        query = query.filter(Document.archived == False)
    documents = query.order_by(Document.year.desc()).all()
    return documents


@app.get(f"{settings.API_V1_PREFIX}/documents/{{document_id}}", response_model=DocumentResponse)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a single document. Returns 404 if document is archived."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.archived:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@app.get(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/summary", response_model=DocumentSummary)
def get_document_summary(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get summary statistics for a document. Returns 404 if document is archived."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.archived:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get all items
    items = db.query(BudgetItem).filter(BudgetItem.document_id == document_id).all()
    
    # Calculate totals
    revenue_total = sum(
        float(item.value) if item.value else 0
        for item in items
        if item.side == SideEnum.REVENUE
    )
    
    expense_total = sum(
        float(item.value) if item.value else 0
        for item in items
        if item.side == SideEnum.EXPENSE
    )
    
    # Group by category
    revenue_by_category = {}
    expense_by_category = {}
    
    for item in items:
        value = float(item.value) if item.value else 0
        if item.side == SideEnum.REVENUE:
            if item.category not in revenue_by_category:
                revenue_by_category[item.category] = {"total": 0, "count": 0}
            revenue_by_category[item.category]["total"] += value
            revenue_by_category[item.category]["count"] += 1
        else:
            if item.category not in expense_by_category:
                expense_by_category[item.category] = {"total": 0, "count": 0}
            expense_by_category[item.category]["total"] += value
            expense_by_category[item.category]["count"] += 1
    
    # Convert to response format
    revenue_categories = [
        CategorySummary(
            category=cat,
            total_value=data["total"],
            item_count=data["count"]
        )
        for cat, data in revenue_by_category.items()
    ]
    
    expense_categories = [
        CategorySummary(
            category=cat,
            total_value=data["total"],
            item_count=data["count"]
        )
        for cat, data in expense_by_category.items()
    ]
    
    return DocumentSummary(
        document_id=document_id,
        year=document.year,
        revenue_total=revenue_total,
        expense_total=expense_total,
        revenue_by_category=revenue_categories,
        expense_by_category=expense_categories
    )


@app.get(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/categories/{{category}}", response_model=List[BudgetItemResponse])
def get_category_items(
    document_id: uuid.UUID,
    category: CategoryEnum,
    sort_by: str = Query("value", description="Sort by: value, page_number, description"),
    db: Session = Depends(get_db)
):
    """Get all items for a specific category in a document. Returns 404 if document is archived."""
    # Check if document exists and is not archived
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.archived:
        raise HTTPException(status_code=404, detail="Document not found")
    
    query = db.query(BudgetItem).filter(
        BudgetItem.document_id == document_id,
        BudgetItem.category == category
    )
    
    if sort_by == "value":
        query = query.order_by(BudgetItem.value.desc().nulls_last())
    elif sort_by == "page_number":
        query = query.order_by(BudgetItem.page_number)
    elif sort_by == "description":
        query = query.order_by(BudgetItem.description_original)
    
    items = query.all()
    return items


@app.get(f"{settings.API_V1_PREFIX}/items/{{item_id}}", response_model=BudgetItemResponse)
def get_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a single budget item. Returns 404 if document is archived."""
    item = db.query(BudgetItem).filter(BudgetItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check if document is archived
    document = db.query(Document).filter(Document.id == item.document_id).first()
    if document and document.archived:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item


@app.get(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/pdf")
def get_pdf(document_id: uuid.UUID, page: int = Query(None, description="Page number to jump to"), db: Session = Depends(get_db)):
    """Serve the PDF file. Returns 404 if document is archived."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.archived:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not os.path.exists(document.filepath):
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    # Note: Browser PDF viewer may not support page parameter in URL fragment
    # This is a limitation of browser PDF viewers
    return FileResponse(
        document.filepath,
        media_type="application/pdf",
        filename=document.filename
    )


@app.get(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/pages/{{page_number}}")
def get_page_text(document_id: uuid.UUID, page_number: int, db: Session = Depends(get_db)):
    """Get raw extracted text for a specific page (debug endpoint). Returns 404 if document is archived."""
    # Check if document exists and is not archived
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.archived:
        raise HTTPException(status_code=404, detail="Document not found")
    
    page = db.query(Page).filter(
        Page.document_id == document_id,
        Page.page_number == page_number
    ).first()
    
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    
    return {
        "document_id": str(document_id),
        "page_number": page_number,
        "text": page.text_raw
    }


@app.get(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/import-jobs", response_model=List[ImportJobResponse])
def get_import_jobs(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get import jobs for a document. Returns 404 if document is archived."""
    # Check if document exists and is not archived
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.archived:
        raise HTTPException(status_code=404, detail="Document not found")
    
    jobs = db.query(ImportJob).filter(
        ImportJob.document_id == document_id
    ).order_by(ImportJob.created_at.desc()).all()
    return jobs


@app.patch(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/archive")
def archive_document(
    document_id: uuid.UUID,
    archived: bool = Query(True, description="Set archived status (true to archive, false to unarchive)"),
    db: Session = Depends(get_db)
):
    """Archive or unarchive a document. Archived documents are hidden from the frontend."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    document.archived = archived
    db.commit()
    
    logger.info(f"Document {document_id} {'archived' if archived else 'unarchived'}")
    return {
        "document_id": document_id,
        "archived": archived,
        "message": f"Document {'archived' if archived else 'unarchived'} successfully"
    }


@app.delete(f"{settings.API_V1_PREFIX}/documents/{{document_id}}/purge")
def purge_document(document_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Permanently delete a document and all associated data.
    This removes the document, pages, sections, budget items, import jobs, and the PDF file.
    This action cannot be undone.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete the PDF file if it exists
    if os.path.exists(document.filepath):
        try:
            os.remove(document.filepath)
            logger.info(f"Deleted PDF file: {document.filepath}")
        except Exception as e:
            logger.warning(f"Could not delete PDF file {document.filepath}: {e}")
    
    # Delete the document (cascade will handle related records)
    db.delete(document)
    db.commit()
    
    logger.info(f"Purged document {document_id} and all associated data")
    return {
        "document_id": document_id,
        "message": "Document and all associated data permanently deleted"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

