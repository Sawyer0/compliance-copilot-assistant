"""Inngest-native workflow for compliance document processing."""

import os
import hashlib
import datetime
from typing import Dict, Any
from pathlib import Path

import yaml
import inngest
from ingestion_functions.client import inngest_client

# ==========================================
# STEP 1: Orchestrator - Triggers the workflow
# ==========================================

@inngest_client.create_function(
    fn_id="trigger_compliance_ingestion",
    trigger=inngest.TriggerEvent(event="compliance/ingestion.start"),
)
async def trigger_compliance_ingestion(ctx: inngest.Context) -> Dict[str, Any]:
    """Orchestrator function that triggers document processing for all active sources."""
    
    try:
        # Load source configurations - use absolute path from current working directory
        current_dir = Path.cwd()
        sources_dir = current_dir / "registry" / "sources"
        
        ctx.logger.info(f"Looking for sources in: {sources_dir}")
        
        if not sources_dir.exists():
            ctx.logger.error(f"Sources directory does not exist: {sources_dir}")
            return {
                "status": "error",
                "message": f"Sources directory not found: {sources_dir}",
                "workflow_id": ctx.run_id
            }
        
        all_sources = []
        
        for sources_file in sources_dir.glob("**/*.yaml"):
            ctx.logger.info(f"Loading sources from: {sources_file}")
            try:
                with open(sources_file, 'r') as f:
                    data = yaml.safe_load(f)
                    sources = data.get('sources', [])
                    all_sources.extend(sources)
                    ctx.logger.info(f"Loaded {len(sources)} sources from {sources_file.name}")
            except Exception as e:
                ctx.logger.error(f"Error loading {sources_file}: {e}")
        
        # Filter active sources
        active_sources = [s for s in all_sources if s.get('is_active', False)]
        ctx.logger.info(f"Found {len(active_sources)} active sources out of {len(all_sources)} total")
        
        if not active_sources:
            return {
                "status": "no_sources",
                "message": "No active sources found",
                "total_sources": len(all_sources),
                "workflow_id": ctx.run_id
            }
        
        # Send events for each source (Inngest will handle them in parallel)
        for source in active_sources:
            ctx.logger.info(f"Triggering processing for source: {source.get('name')}")
            await inngest_client.send(inngest.Event(
                name="compliance/source.fetch",
                data={
                    "source_config": source,
                    "workflow_id": ctx.run_id,
                    "triggered_at": datetime.datetime.now().isoformat()
                }
            ))
        
        return {
            "status": "triggered",
            "sources_count": len(active_sources),
            "workflow_id": ctx.run_id
        }
        
    except Exception as e:
        ctx.logger.error(f"Error in trigger_compliance_ingestion: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "workflow_id": ctx.run_id
        }

# ==========================================
# STEP 2: Document Fetcher - Downloads raw content
# ==========================================

@inngest_client.create_function(
    fn_id="fetch_document",
    trigger=inngest.TriggerEvent(event="compliance/source.fetch"),
    retries=3  # Inngest handles retries automatically
)
async def fetch_document(ctx: inngest.Context) -> Dict[str, Any]:
    """Fetch raw document content from source endpoints."""
    
    source_config = ctx.event.data["source_config"]
    source_name = source_config.get("name", "Unknown")
    
    ctx.logger.info(f"Fetching documents from: {source_name}")
    
    base_url = source_config.get("base_url", "")
    endpoints = source_config.get("endpoints", [])
    
    # Process each endpoint
    for endpoint in endpoints:
        full_url = f"{base_url}{endpoint}"
        
        # Generate document metadata
        doc_id = hashlib.md5(full_url.encode()).hexdigest()[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Send event to content extractor for each document
        await inngest_client.send(inngest.Event(
            name="compliance/document.extract",
            data={
                "source_config": source_config,
                "url": full_url,
                "doc_id": doc_id,
                "timestamp": timestamp,
                "workflow_id": ctx.event.data.get("workflow_id")
            }
        ))
    
    return {
        "status": "fetch_completed",
        "source_name": source_name,
        "endpoints_processed": len(endpoints)
    }

# ==========================================
# STEP 3: Content Extractor - Extracts text using Playwright/PyMuPDF
# ==========================================

@inngest_client.create_function(
    fn_id="extract_content",
    trigger=inngest.TriggerEvent(event="compliance/document.extract"),
    retries=2
)
async def extract_content(ctx: inngest.Context) -> Dict[str, Any]:
    """Extract content from documents using appropriate extractors."""
    
    event_data = ctx.event.data
    url = event_data["url"]
    doc_id = event_data["doc_id"]
    timestamp = event_data["timestamp"]
    source_config = event_data["source_config"]
    
    ctx.logger.info(f"Extracting content from: {url}")
    
    # Determine content type
    if any(ext in url.lower() for ext in ['.pdf', 'pdf']):
        content_type = 'application/pdf'
        file_ext = 'pdf'
    else:
        content_type = 'text/html'
        file_ext = 'html'
    
    # Create file paths
    source_name = source_config.get("name", "unknown").replace(" ", "_")
    filename_base = f"{source_name}_{doc_id}_{timestamp}"
    
    os.makedirs("outputs/raw", exist_ok=True)
    raw_file_path = f"outputs/raw/{filename_base}.{file_ext}"
    
    # Use Inngest's step function for extraction
    if content_type == 'application/pdf':
        text_content = await ctx.step.run("extract_pdf", _extract_pdf_step, url, raw_file_path)
    else:
        text_content = await ctx.step.run("extract_html", _extract_html_step, url, raw_file_path)
    
    if not text_content or len(text_content.strip()) < 100:
        ctx.logger.warning(f"No substantial content extracted from {url}")
        return {"status": "extraction_failed", "url": url}
    
    # Send to processor
    await inngest_client.send(inngest.Event(
        name="compliance/document.process",
        data={
            "source_config": source_config,
            "url": url,
            "doc_id": doc_id,
            "timestamp": timestamp,
            "text_content": text_content,
            "raw_file_path": raw_file_path,
            "content_type": content_type,
            "workflow_id": event_data.get("workflow_id")
        }
    ))
    
    return {
        "status": "extraction_completed",
        "url": url,
        "content_length": len(text_content)
    }

# ==========================================
# STEP 4: Content Processor - Chunks and structures content  
# ==========================================

@inngest_client.create_function(
    fn_id="process_content",
    trigger=inngest.TriggerEvent(event="compliance/document.process")
)
async def process_content(ctx: inngest.Context) -> Dict[str, Any]:
    """Process and chunk document content using Inngest steps."""
    
    event_data = ctx.event.data
    text_content = event_data["text_content"]
    
    ctx.logger.info(f"Processing content for: {event_data['url']}")
    
    # Use Inngest steps for processing pipeline
    cleaned_text = await ctx.step.run("clean_text", _clean_text_step, text_content)
    chunks = await ctx.step.run("create_chunks", _create_chunks_step, cleaned_text, event_data["doc_id"])
    parsed_doc = await ctx.step.run("create_document", _create_document_step, event_data, chunks)
    
    # Send to storage
    await inngest_client.send(inngest.Event(
        name="compliance/document.save",
        data={
            **event_data,
            "parsed_document": parsed_doc,
            "chunks": chunks
        }
    ))
    
    return {
        "status": "processing_completed",
        "chunks_created": len(chunks),
        "total_words": sum(chunk["word_count"] for chunk in chunks)
    }

# ==========================================
# STEP 5: Document Saver - Saves processed documents
# ==========================================

@inngest_client.create_function(
    fn_id="save_document", 
    trigger=inngest.TriggerEvent(event="compliance/document.save")
)
async def save_document(ctx: inngest.Context) -> Dict[str, Any]:
    """Save processed documents and metadata."""
    
    event_data = ctx.event.data
    parsed_doc = event_data["parsed_document"]
    
    ctx.logger.info(f"Saving document: {parsed_doc['document_id']}")
    
    # Use Inngest steps for file operations
    await ctx.step.run("save_parsed_doc", _save_parsed_doc_step, parsed_doc, event_data)
    await ctx.step.run("save_metadata", _save_metadata_step, parsed_doc, event_data)
    
    # Send completion event
    await inngest_client.send(inngest.Event(
        name="compliance/document.completed",
        data={
            "document_id": parsed_doc["document_id"],
            "source_name": event_data["source_config"]["name"],
            "url": event_data["url"],
            "chunks": len(event_data["chunks"]),
            "words": parsed_doc["total_words"],
            "workflow_id": event_data.get("workflow_id"),
            "completed_at": datetime.datetime.now().isoformat()
        }
    ))
    
    return {
        "status": "save_completed",
        "document_id": parsed_doc["document_id"]
    }

# ==========================================
# STEP FUNCTIONS - Pure functions for Inngest steps
# ==========================================

async def _extract_pdf_step(url: str, raw_file_path: str) -> str:
    """Inngest step function for PDF extraction."""
    try:
        from extractors.pdf_extractor import PDFExtractor
        extractor = PDFExtractor()
        return await extractor.extract_content(url, raw_file_path)
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""

async def _extract_html_step(url: str, raw_file_path: str) -> str:
    """Inngest step function for HTML extraction."""
    try:
        from extractors.html_extractor import HTMLExtractor
        extractor = HTMLExtractor()
        return await extractor.extract_content(url, raw_file_path)
    except Exception as e:
        print(f"HTML extraction error: {e}")
        return ""

async def _clean_text_step(text_content: str) -> str:
    """Inngest step function for text cleaning."""
    return ' '.join(text_content.split())

async def _create_chunks_step(cleaned_text: str, doc_id: str) -> list:
    """Inngest step function for content chunking."""
    try:
        from processors.content_processor import ContentProcessor
        processor = ContentProcessor()
        return processor._create_chunks(cleaned_text, doc_id)
    except Exception as e:
        print(f"Chunking error: {e}")
        return []

async def _create_document_step(event_data: dict, chunks: list) -> dict:
    """Inngest step function for document creation."""
    try:
        from processors.content_processor import ContentProcessor
        processor = ContentProcessor()
        return processor._create_parsed_document(
            event_data["source_config"],
            event_data["url"],
            event_data["doc_id"],
            chunks,
            event_data["raw_file_path"],
            event_data["content_type"]
        )
    except Exception as e:
        print(f"Document creation error: {e}")
        return {}

async def _save_parsed_doc_step(parsed_doc: dict, event_data: dict) -> None:
    """Inngest step function for saving parsed documents."""
    import json
    
    source_name = event_data["source_config"]["name"].replace(" ", "_")
    filename = f"{source_name}_{event_data['doc_id']}_{event_data['timestamp']}_parsed.json"
    file_path = f"outputs/parsed/{filename}"
    
    os.makedirs("outputs/parsed", exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(parsed_doc, f, indent=2, ensure_ascii=False)

async def _save_metadata_step(parsed_doc: dict, event_data: dict) -> None:
    """Inngest step function for saving metadata."""
    import json
    
    metadata = {
        "document_id": parsed_doc["document_id"],
        "source_name": event_data["source_config"]["name"],
        "source_url": event_data["url"],
        "raw_file_path": event_data["raw_file_path"],
        "content_type": event_data["content_type"],
        "total_chunks": len(event_data["chunks"]),
        "total_words": parsed_doc["total_words"],
        "processing_timestamp": datetime.datetime.now().isoformat(),
        "processing_status": "success"
    }
    
    source_name = event_data["source_config"]["name"].replace(" ", "_")
    filename = f"{source_name}_{event_data['doc_id']}_{event_data['timestamp']}_metadata.json"
    file_path = f"outputs/metadata/{filename}"
    
    os.makedirs("outputs/metadata", exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False) 