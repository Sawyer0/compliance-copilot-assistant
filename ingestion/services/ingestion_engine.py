"""Main ingestion engine for document processing."""

import asyncio
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from ..core.config import get_settings
from ..core.logging import get_logger, DocumentLogger
from ..core.storage import StorageManager
from ..core.registry import SourceRegistry
from ..fetchers import BaseFetcher, NISTFetcher, EUAIActFetcher, FPFFetcher
from ..parsers import BaseParser, PDFParser, HTMLParser, OCRParser
from ..models.document import Document, DocumentMetadata, DocumentStatus, DocumentFormat
from ..models.source import Source
from ..models.ingestion import IngestionJob, IngestionResult, TaskResult, JobStatus

logger = get_logger(__name__)


class IngestionEngine:
    """Main engine for document ingestion orchestration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.storage = StorageManager()
        self.registry = SourceRegistry()
        
        # Initialize parsers
        self.parsers = [
            PDFParser(),
            HTMLParser(),
            OCRParser(),
        ]
        
        # Fetcher mapping
        self.fetcher_map = {
            "nist": NISTFetcher,
            "eu_ai_act": EUAIActFetcher,
            "fpf": FPFFetcher,
        }
    
    async def run_ingestion_job(self, job: IngestionJob) -> IngestionResult:
        """Run a complete ingestion job."""
        job.update_status(JobStatus.RUNNING)
        job.add_log("Starting ingestion job")
        
        logger.info(
            "Starting ingestion job",
            job_id=str(job.job_id),
            job_type=job.job_type.value,
            source_count=len(job.source_ids)
        )
        
        task_results = []
        
        try:
            # Process each source
            for source_id in job.source_ids:
                source = self.registry.get_source(source_id)
                
                if not source:
                    logger.error("Source not found", source_id=str(source_id))
                    continue
                
                if not source.config.is_active:
                    logger.info("Skipping inactive source", source_name=source.config.name)
                    continue
                
                source_results = await self._process_source(source, job)
                task_results.extend(source_results)
            
            # Update job progress
            successful_tasks = sum(1 for r in task_results if r.success)
            failed_tasks = sum(1 for r in task_results if not r.success)
            
            job.update_progress(successful_tasks, failed_tasks)
            
            if failed_tasks == 0:
                job.update_status(JobStatus.COMPLETED)
            elif successful_tasks > 0:
                job.update_status(JobStatus.COMPLETED, f"Completed with {failed_tasks} failures")
            else:
                job.update_status(JobStatus.FAILED, "All tasks failed")
        
        except Exception as e:
            logger.error("Ingestion job failed", job_id=str(job.job_id), error=str(e))
            job.update_status(JobStatus.FAILED, str(e))
        
        # Create result
        result = IngestionResult(
            job=job,
            task_results=task_results,
            total_documents_processed=len(task_results),
            successful_documents=sum(1 for r in task_results if r.success),
            failed_documents=sum(1 for r in task_results if not r.success)
        )
        
        result.calculate_metrics()
        
        logger.info(
            "Ingestion job completed",
            job_id=str(job.job_id),
            total_docs=result.total_documents_processed,
            successful=result.successful_documents,
            failed=result.failed_documents,
            duration=result.total_execution_time
        )
        
        return result
    
    async def _process_source(self, source: Source, job: IngestionJob) -> List[TaskResult]:
        """Process a single source."""
        logger.info("Processing source", source_name=source.config.name)
        
        task_results = []
        
        try:
            # Get appropriate fetcher
            fetcher_class = self._get_fetcher_class(source)
            
            async with fetcher_class(source) as fetcher:
                # Health check
                if not await fetcher.health_check():
                    logger.warning("Source health check failed", source_name=source.config.name)
                
                # Fetch documents
                fetch_results = await fetcher.fetch_documents()
                
                # Process each fetched document
                for fetch_result in fetch_results:
                    task_result = await self._process_document(fetch_result, source)
                    task_results.append(task_result)
        
        except Exception as e:
            logger.error(
                "Source processing failed",
                source_name=source.config.name,
                error=str(e)
            )
            
            # Create failure task result
            task_result = TaskResult(
                source_id=source.config.source_id,
                status=JobStatus.FAILED,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=False,
                error_message=str(e)
            )
            task_results.append(task_result)
        
        return task_results
    
    async def _process_document(self, fetch_result, source: Source) -> TaskResult:
        """Process a single document."""
        task_result = TaskResult(
            source_id=source.config.source_id,
            status=JobStatus.RUNNING,
            started_at=datetime.utcnow()
        )
        
        if not fetch_result.success:
            task_result.status = JobStatus.FAILED
            task_result.error_message = fetch_result.error_message
            task_result.completed_at = datetime.utcnow()
            return task_result
        
        doc_id = uuid4()
        doc_logger = DocumentLogger(str(doc_id), source.config.name)
        
        try:
            # Create document metadata
            metadata = DocumentMetadata(
                doc_id=doc_id,
                source_name=source.config.name,
                jurisdiction=source.config.jurisdiction,
                regulation_type=source.config.regulation_type,
                tags=source.config.tags,
                fetch_timestamp=datetime.utcnow(),
                file_size=fetch_result.file_size,
                extraction_method="fetched"
            )
            
            # Add fetch metadata
            if fetch_result.metadata:
                metadata.title = fetch_result.metadata.get('document_title', metadata.title)
                metadata.url = fetch_result.metadata.get('url', metadata.url)
                metadata.custom_fields.update(fetch_result.metadata)
            
            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(fetch_result.content).hexdigest()
            metadata.file_hash = content_hash
            
            # Check for duplicates
            existing_doc_id = await self.storage.check_duplicate(content_hash, source.config.name)
            if existing_doc_id:
                doc_logger.info("Document already exists, skipping", existing_id=str(existing_doc_id))
                task_result.status = JobStatus.COMPLETED
                task_result.success = True
                task_result.artifacts = {"duplicate_of": str(existing_doc_id)}
                task_result.completed_at = datetime.utcnow()
                return task_result
            
            # Determine document format
            doc_format = self._determine_format(fetch_result.content_type, fetch_result.file_extension)
            
            # Create document
            document = Document(
                metadata=metadata,
                format=doc_format,
                status=DocumentStatus.FETCHING
            )
            
            # Save raw content
            raw_path = await self.storage.save_raw_content(
                fetch_result.content,
                doc_id,
                source.config.name,
                fetch_result.file_extension or "bin"
            )
            document.raw_file_path = raw_path
            document.update_status(DocumentStatus.PARSING)
            
            # Parse document
            parse_result = await self._parse_document(
                fetch_result.content,
                fetch_result.content_type or "",
                fetch_result.file_extension or ""
            )
            
            if parse_result.success and parse_result.content:
                document.content = parse_result.content
                metadata.parse_timestamp = datetime.utcnow()
                metadata.parse_quality_score = parse_result.quality_score
                metadata.extraction_method = parse_result.extraction_method
                
                # Save parsed content
                parsed_path = await self.storage.save_parsed_content(
                    parse_result.content.raw_text,
                    doc_id,
                    source.config.name,
                    "txt"
                )
                document.parsed_file_path = parsed_path
                
                document.update_status(DocumentStatus.PROCESSED)
                doc_logger.info("Document processed successfully")
            else:
                document.update_status(DocumentStatus.FAILED, parse_result.error_message)
                doc_logger.error("Document parsing failed", error=parse_result.error_message)
            
            # Save metadata
            metadata_path = await self.storage.save_metadata(metadata, source.config.name)
            document.metadata_file_path = metadata_path
            
            # Update task result
            task_result.document_id = doc_id
            task_result.status = JobStatus.COMPLETED
            task_result.success = document.status == DocumentStatus.PROCESSED
            task_result.completed_at = datetime.utcnow()
            task_result.duration_seconds = (
                task_result.completed_at - task_result.started_at
            ).total_seconds()
            
            task_result.artifacts = {
                "document_status": document.status.value,
                "raw_file": str(document.raw_file_path) if document.raw_file_path else None,
                "parsed_file": str(document.parsed_file_path) if document.parsed_file_path else None,
                "metadata_file": str(document.metadata_file_path) if document.metadata_file_path else None,
                "parse_quality": parse_result.quality_score,
                "content_length": len(parse_result.content.raw_text) if parse_result.content else 0
            }
        
        except Exception as e:
            doc_logger.error("Document processing failed", error=str(e))
            task_result.status = JobStatus.FAILED
            task_result.success = False
            task_result.error_message = str(e)
            task_result.completed_at = datetime.utcnow()
        
        return task_result
    
    async def _parse_document(
        self, 
        content: bytes, 
        content_type: str, 
        file_extension: str
    ) -> "ParseResult":
        """Parse document using appropriate parser."""
        # Try each parser in order
        for parser in self.parsers:
            if parser.can_parse(content_type, file_extension):
                logger.debug(
                    "Attempting parse",
                    parser=parser.__class__.__name__,
                    content_type=content_type,
                    file_extension=file_extension
                )
                
                result = await parser.parse(content, content_type=content_type)
                
                if result.success:
                    logger.info(
                        "Document parsed successfully",
                        parser=parser.__class__.__name__,
                        quality_score=result.quality_score
                    )
                    return result
                else:
                    logger.warning(
                        "Parser failed",
                        parser=parser.__class__.__name__,
                        error=result.error_message
                    )
        
        # No parser succeeded
        from ..parsers.base_parser import ParseResult
        return ParseResult(
            success=False,
            error_message="No suitable parser found or all parsers failed",
            extraction_method="no_parser"
        )
    
    def _get_fetcher_class(self, source: Source) -> type:
        """Get appropriate fetcher class for source."""
        # Check if source name matches known fetchers
        source_name_lower = source.config.name.lower()
        
        for key, fetcher_class in self.fetcher_map.items():
            if key in source_name_lower:
                return fetcher_class
        
        # Default to base fetcher (won't work, but provides error info)
        return BaseFetcher
    
    def _determine_format(self, content_type: str, file_extension: str) -> DocumentFormat:
        """Determine document format from content type and extension."""
        content_type = (content_type or "").lower()
        file_extension = (file_extension or "").lower()
        
        if 'pdf' in content_type or file_extension == 'pdf':
            return DocumentFormat.PDF
        elif 'html' in content_type or file_extension in ['html', 'htm']:
            return DocumentFormat.HTML
        elif file_extension in ['docx']:
            return DocumentFormat.DOCX
        elif file_extension in ['md', 'markdown']:
            return DocumentFormat.MARKDOWN
        else:
            return DocumentFormat.TXT
    
    async def process_single_source(self, source_name: str) -> IngestionResult:
        """Process a single source by name."""
        source = self.registry.get_source_by_name(source_name)
        
        if not source:
            raise ValueError(f"Source '{source_name}' not found")
        
        job = IngestionJob(
            job_type="single_source",
            source_ids=[source.config.source_id]
        )
        
        return await self.run_ingestion_job(job)
    
    async def process_all_sources(self) -> IngestionResult:
        """Process all active sources."""
        sources = self.registry.list_sources(active_only=True)
        
        if not sources:
            raise ValueError("No active sources found")
        
        job = IngestionJob(
            job_type="full_ingestion",
            source_ids=[s.config.source_id for s in sources]
        )
        
        return await self.run_ingestion_job(job) 