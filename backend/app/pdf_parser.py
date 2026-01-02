"""PDF text extraction and section detection."""
import fitz  # PyMuPDF
from typing import List, Tuple
from loguru import logger


def extract_pages(pdf_path: str) -> List[str]:
    """
    Extract text from each page of a PDF.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        List of text strings, one per page
    """
    pages_text = []
    try:
        doc = fitz.open(pdf_path)
        logger.info(f"Opened PDF with {len(doc)} pages")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            pages_text.append(text)
        
        doc.close()
        logger.info(f"Extracted text from {len(pages_text)} pages")
        return pages_text
    except Exception as e:
        logger.error(f"Error extracting PDF pages: {e}")
        raise


def is_heading_line(line: str, context: dict) -> bool:
    """
    Heuristic to identify heading-like lines.
    
    A heading is likely:
    - Short (less than 100 chars)
    - Has uppercase words or title case
    - Doesn't start with numbers (unless it's a section number)
    - Not a table row (doesn't have multiple numbers)
    
    Args:
        line: Text line to check
        context: Dict with stats about previous lines (for adaptive thresholds)
        
    Returns:
        True if line looks like a heading
    """
    line = line.strip()
    
    # Too long to be a heading
    if len(line) > 100:
        return False
    
    # Empty or just whitespace
    if not line:
        return False
    
    # Too many numbers suggests it's a table row
    words = line.split()
    num_count = sum(1 for w in words if any(c.isdigit() for c in w))
    if num_count > 3:
        return False
    
    # Check for uppercase/title case pattern
    # Headings often have first letter of each word capitalized
    words = line.split()
    if len(words) > 0:
        # Count words that start with uppercase
        upper_start = sum(1 for w in words if w and w[0].isupper())
        # If most words start uppercase, likely a heading
        if len(words) <= 5 and upper_start >= len(words) * 0.6:
            return True
    
    # Check for all caps (common in government documents)
    if line.isupper() and len(line) > 5 and len(line) < 80:
        return True
    
    # Check for common heading patterns (Roman numerals, numbered sections)
    if line.startswith(("I.", "II.", "III.", "IV.", "V.", "VI.", "VII.", "VIII.", "IX.", "X.")):
        return True
    if line.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")) and len(line) < 60:
        return True
    
    return False


def build_sections(pages_text: List[str]) -> List[Tuple[str, int, int]]:
    """
    Build sections from pages by detecting headings.
    
    Uses a simple heuristic:
    - Scan each page for heading-like lines
    - Maintain a title stack (breadcrumb path)
    - Group consecutive pages under the same heading
    
    Args:
        pages_text: List of text strings, one per page
        
    Returns:
        List of tuples: (title_path, page_start, page_end)
        title_path format: "L1 > L2 > L3"
    """
    sections = []
    title_stack = []  # Stack of current heading levels
    current_section_start = 0
    current_path = ""
    
    logger.info(f"Building sections from {len(pages_text)} pages")
    
    for page_idx, page_text in enumerate(pages_text):
        lines = page_text.split('\n')
        page_has_heading = False
        new_heading = None
        new_level = None
        
        # Scan lines for headings
        for line in lines:
            if is_heading_line(line, {}):
                # Determine heading level (simplified: by indentation or position)
                # In practice, we could use font size, but for text-only we use position
                stripped = line.strip()
                
                # Simple level detection: if it's shorter and more prominent, it's higher level
                if len(stripped) < 30:
                    level = 1
                elif len(stripped) < 50:
                    level = 2
                else:
                    level = 3
                
                # If we find a heading at a higher or same level, start a new section
                if not title_stack or level <= len(title_stack):
                    # Pop stack to appropriate level
                    while len(title_stack) >= level:
                        title_stack.pop()
                    
                    title_stack.append(stripped)
                    new_heading = stripped
                    new_level = level
                    page_has_heading = True
                    break
        
        # If we found a new heading, finalize previous section and start new one
        if page_has_heading and new_heading:
            # Save previous section if it exists
            if current_path:
                sections.append((current_path, current_section_start, page_idx - 1))
            
            # Start new section
            current_path = " > ".join(title_stack)
            current_section_start = page_idx
        
        # If no heading found but we have a current section, continue it
        # (sections span multiple pages until a new heading is found)
    
    # Finalize last section
    if current_path:
        sections.append((current_path, current_section_start, len(pages_text) - 1))
    
    # If no sections found, create one big section
    if not sections:
        sections.append(("Document", 0, len(pages_text) - 1))
    
    logger.info(f"Created {len(sections)} sections")
    return sections

