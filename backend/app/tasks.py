"""Celery tasks for background processing."""
import os
from decimal import Decimal
from sqlalchemy.orm import Session
from celery import Celery
from loguru import logger
from app.database import SessionLocal
from app.models import (
    Document, Page, Section, BudgetItem, ImportJob,
    ImportJobStatusEnum, SideEnum, UnitEnum
)
from app.pdf_parser import extract_pages, build_sections
from app.llm.client import llm_client
from app.config import settings

# Initialize Celery
celery_app = Celery(
    "budget_processor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)



def normalize_to_eur(value: float, unit: UnitEnum) -> float:
    """Convert value to EUR for comparisons."""
    if value is None:
        return 0.0
    
    if unit == UnitEnum.EUR:
        return float(value)
    elif unit == UnitEnum.THOUSAND_EUR:
        return float(value) * 1000
    elif unit == UnitEnum.MILLION_EUR:
        return float(value) * 1000000
    else:
        return float(value)  # UNKNOWN: assume EUR


@celery_app.task(bind=True)
def process_document(self, document_id: str, import_job_id: str):
    """
    Main task to process a document: extract pages, build sections, extract items.
    
    Args:
        document_id: UUID of the document
        import_job_id: UUID of the import job
    """
    db: Session = SessionLocal()
    
    try:
        # Update job status
        job = db.query(ImportJob).filter(ImportJob.id == import_job_id).first()
        if not job:
            logger.error(f"Import job {import_job_id} not found")
            return
        
        job.status = ImportJobStatusEnum.RUNNING
        job.progress = 0
        db.commit()
        
        # Get document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            job.status = ImportJobStatusEnum.FAILED
            job.error_message = "Document not found"
            db.commit()
            return
        
        logger.info(f"Processing document {document_id} (year {document.year})")
        
        # Step 1: Extract pages (10% progress)
        logger.info("Step 1: Extracting pages...")
        pages_text = extract_pages(document.filepath)
        
        # Store pages in database
        for page_num, text in enumerate(pages_text, start=1):
            page = Page(
                document_id=document.id,
                page_number=page_num,
                text_raw=text
            )
            db.add(page)
        db.commit()
        logger.info(f"Stored {len(pages_text)} pages")
        
        job.progress = 10
        db.commit()
        
        # Step 2: Build sections (20% progress)
        logger.info("Step 2: Building sections...")
        sections_data = build_sections(pages_text)
        
        # Store sections
        for title_path, page_start, page_end in sections_data:
            section = Section(
                document_id=document.id,
                title_path=title_path,
                page_start=page_start + 1,  # Convert 0-based to 1-based
                page_end=page_end + 1
            )
            db.add(section)
        db.commit()
        logger.info(f"Stored {len(sections_data)} sections")
        
        job.progress = 20
        db.commit()
        
        # Step 3: Extract items from each section (20-90% progress)
        total_sections = len(sections_data)
        items_processed = 0
        
        for section_idx, (title_path, page_start, page_end) in enumerate(sections_data):
            logger.info(f"Processing section {section_idx + 1}/{total_sections}: {title_path}")
            
            # Build text for this section with page markers
            section_text_parts = []
            for page_idx in range(page_start, page_end + 1):
                if page_idx <= len(pages_text):
                    page_text = pages_text[page_idx - 1]  # Convert to 0-based
                    section_text_parts.append(f"--- PAGE {page_idx} ---\n{page_text}")
            
            pages_text_combined = "\n\n".join(section_text_parts)
            
            # Extract items using LLM
            extracted_items = llm_client.extract_items(title_path, pages_text_combined)
            
            # Process each extracted item
            for extracted in extracted_items:
                # Categorize
                category = llm_client.categorize_item(
                    extracted.side,
                    title_path,
                    extracted.descriptionOriginal
                )
                
                # Generate explanation
                explanation = llm_client.explain_item(
                    title_path,
                    extracted.evidenceText
                )
                
                # Normalize value to EUR for storage (keep original unit for display)
                value_eur = None
                if extracted.value is not None:
                    value_eur = normalize_to_eur(extracted.value, extracted.unit)
                
                # Create budget item
                budget_item = BudgetItem(
                    document_id=document.id,
                    year=document.year,
                    side=extracted.side,
                    category=category,
                    description_original=extracted.descriptionOriginal,
                    value=Decimal(str(value_eur)) if value_eur is not None else None,
                    unit=extracted.unit,
                    page_number=extracted.pageNumber,
                    evidence_text=extracted.evidenceText,
                    explanation=explanation
                )
                db.add(budget_item)
                items_processed += 1
            
            # Update progress
            progress = 20 + int((section_idx + 1) / total_sections * 70)
            job.progress = progress
            db.commit()
        
        logger.info(f"Processed {items_processed} budget items")
        
        # Finalize
        job.progress = 100
        job.status = ImportJobStatusEnum.DONE
        db.commit()
        
        logger.info(f"Document {document_id} processing complete")
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        job = db.query(ImportJob).filter(ImportJob.id == import_job_id).first()
        if job:
            job.status = ImportJobStatusEnum.FAILED
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()

