"""API endpoints for accessing processed documents."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from core.logging import get_logger
from services.document_service import DocumentService
from services.content_quality_service import ContentQualityService

logger = get_logger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

# Initialize services
document_service = DocumentService()
quality_service = ContentQualityService()


@router.get("/")
async def list_documents():
    """List all processed documents with basic information."""
    try:
        return document_service.list_all_documents()
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to list documents")


@router.get("/statistics")
async def get_document_statistics():
    """Get overall statistics about all processed documents."""
    try:
        return document_service.get_document_statistics()
    except Exception as e:
        logger.error(f"Error getting document statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Retrieve a specific document by ID."""
    try:
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.get("/{document_id}/metadata")
async def get_document_metadata(document_id: str):
    """Retrieve metadata for a specific document."""
    try:
        metadata = document_service.get_document_metadata(document_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="Document metadata not found")
        return metadata
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving metadata for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve metadata")


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    start: int = Query(0, ge=0, description="Starting chunk index"),
    limit: int = Query(10, ge=1, le=100, description="Number of chunks to return")
):
    """Retrieve paginated chunks from a document."""
    try:
        result = document_service.get_document_chunks(document_id, start, limit)
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chunks for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chunks")


@router.get("/{document_id}/quality")
async def analyze_document_quality(document_id: str):
    """Analyze the content quality of a specific document."""
    try:
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        quality_analysis = quality_service.analyze_document_quality(document, document_id)
        return quality_analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing quality for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze document quality")


@router.get("/{document_id}/clean-content")
async def get_clean_content(
    document_id: str,
    min_quality: int = Query(30, ge=0, le=100, description="Minimum quality score for chunks")
):
    """Filter document to return only high-quality content chunks."""
    try:
        document = document_service.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        clean_content = quality_service.filter_clean_content(document, document_id, min_quality)
        return clean_content
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error filtering clean content for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to filter clean content")


@router.get("/{document_id}/raw")
async def download_raw_file(document_id: str):
    """Download the original raw file for a document."""
    try:
        raw_file_path = document_service.get_raw_file(document_id)
        if not raw_file_path:
            raise HTTPException(status_code=404, detail="Raw file not found")
        
        return FileResponse(
            path=str(raw_file_path),
            filename=raw_file_path.name,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading raw file for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to download raw file")


@router.get("/search/content")
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results")
):
    """Search across all documents for specific content."""
    try:
        results = document_service.search_documents(query, limit)
        return results
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to search documents") 