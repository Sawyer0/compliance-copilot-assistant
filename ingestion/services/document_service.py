"""Document management service for compliance documents."""

import json
from pathlib import Path
from typing import List, Optional, Dict, Any

from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for managing and retrieving processed documents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.parsed_dir = self.settings.parsed_output_path
        self.metadata_dir = self.settings.metadata_output_path
        self.raw_dir = self.settings.raw_output_path
    
    def list_all_documents(self) -> Dict[str, Any]:
        """List all processed documents with basic information."""
        if not self.parsed_dir.exists():
            return {"documents": [], "total": 0}
        
        documents = []
        
        # Scan parsed directory for processed documents
        for parsed_file in self.parsed_dir.glob("*_parsed.json"):
            try:
                # Extract document ID from filename
                filename = parsed_file.stem
                if filename.endswith("_parsed"):
                    doc_id = filename[:-7]  # Remove _parsed suffix
                else:
                    continue
                
                # Load basic document info
                with open(parsed_file, 'r', encoding='utf-8') as f:
                    doc_data = json.load(f)
                
                # Load metadata if available
                metadata_file = self.metadata_dir / f"{doc_id}_metadata.json"
                metadata = {}
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {doc_id}: {e}")
                
                # Count chunks
                chunks = doc_data.get("chunks", [])
                if not chunks:
                    chunks = doc_data.get("content_chunks", [])
                
                doc_info = {
                    "document_id": doc_id,
                    "source_name": doc_data.get("source_name", metadata.get("source_name", "Unknown")),
                    "url": metadata.get("source_url", "Unknown"),
                    "file_size": parsed_file.stat().st_size,
                    "chunk_count": len(chunks),
                    "processing_date": metadata.get("processing_date"),
                    "content_type": metadata.get("content_type", "text"),
                    "source_type": metadata.get("source_type", "html")
                }
                
                documents.append(doc_info)
                
            except Exception as e:
                logger.error(f"Error processing document {parsed_file}: {e}")
        
        # Sort by processing date (newest first)
        documents.sort(key=lambda x: x.get("processing_date", ""), reverse=True)
        
        return {
            "documents": documents,
            "total": len(documents),
            "total_size_mb": round(sum(doc["file_size"] for doc in documents) / (1024 * 1024), 2),
            "total_chunks": sum(doc["chunk_count"] for doc in documents)
        }
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific document by its ID."""
        parsed_file = self.parsed_dir / f"{document_id}_parsed.json"
        
        if not parsed_file.exists():
            logger.warning(f"Document {document_id} not found")
            return None
        
        try:
            with open(parsed_file, 'r', encoding='utf-8') as f:
                document = json.load(f)
            
            # Load metadata if available
            metadata_file = self.metadata_dir / f"{document_id}_metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    document["metadata"] = metadata
                except Exception as e:
                    logger.warning(f"Failed to load metadata for {document_id}: {e}")
            
            return document
            
        except Exception as e:
            logger.error(f"Error loading document {document_id}: {e}")
            return None
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a specific document."""
        metadata_file = self.metadata_dir / f"{document_id}_metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metadata for {document_id}: {e}")
            return None
    
    def get_document_chunks(self, document_id: str, start: int = 0, limit: int = 10) -> Dict[str, Any]:
        """Retrieve paginated chunks from a document."""
        document = self.get_document_by_id(document_id)
        
        if not document:
            return {"error": "Document not found"}
        
        chunks = document.get("chunks", [])
        if not chunks:
            chunks = document.get("content_chunks", [])
        
        # Apply pagination
        total_chunks = len(chunks)
        paginated_chunks = chunks[start:start + limit]
        
        return {
            "document_id": document_id,
            "source_name": document.get("source_name", "Unknown"),
            "chunks": paginated_chunks,
            "pagination": {
                "start": start,
                "limit": limit,
                "total": total_chunks,
                "has_more": start + limit < total_chunks,
                "next_start": start + limit if start + limit < total_chunks else None
            }
        }
    
    def search_documents(self, query: str, limit: int = 50) -> Dict[str, Any]:
        """Search across all documents for specific content."""
        all_docs = self.list_all_documents()["documents"]
        matching_chunks = []
        
        query_lower = query.lower()
        
        for doc_info in all_docs:
            document = self.get_document_by_id(doc_info["document_id"])
            if not document:
                continue
            
            chunks = document.get("chunks", [])
            if not chunks:
                chunks = document.get("content_chunks", [])
            
            for chunk in chunks:
                chunk_text = chunk.get("content", chunk.get("text", "")).lower()
                
                if query_lower in chunk_text:
                    matching_chunks.append({
                        "document_id": doc_info["document_id"],
                        "source_name": doc_info["source_name"],
                        "chunk_id": chunk.get("chunk_id", "unknown"),
                        "chunk_index": chunk.get("chunk_index", 0),
                        "content": chunk.get("content", chunk.get("text", "")),
                        "word_count": chunk.get("word_count", 0)
                    })
                    
                    if len(matching_chunks) >= limit:
                        break
            
            if len(matching_chunks) >= limit:
                break
        
        return {
            "query": query,
            "matching_chunks": matching_chunks,
            "total_matches": len(matching_chunks),
            "searched_documents": len(all_docs)
        }
    
    def get_raw_file(self, document_id: str) -> Optional[Path]:
        """Get the path to the raw downloaded file for a document."""
        # Check for various file extensions
        for ext in ['.pdf', '.html', '.txt', '.json']:
            raw_file = self.raw_dir / f"{document_id}{ext}"
            if raw_file.exists():
                return raw_file
        
        # Try with timestamp pattern
        for raw_file in self.raw_dir.glob(f"{document_id}*"):
            if raw_file.is_file():
                return raw_file
        
        return None
    
    def get_document_statistics(self) -> Dict[str, Any]:
        """Get overall statistics about all documents."""
        all_docs = self.list_all_documents()
        
        if not all_docs["documents"]:
            return {"error": "No documents found"}
        
        source_types = {}
        content_types = {}
        total_chunks = 0
        total_size = 0
        
        for doc in all_docs["documents"]:
            source_type = doc.get("source_type", "unknown")
            content_type = doc.get("content_type", "unknown")
            
            source_types[source_type] = source_types.get(source_type, 0) + 1
            content_types[content_type] = content_types.get(content_type, 0) + 1
            
            total_chunks += doc.get("chunk_count", 0)
            total_size += doc.get("file_size", 0)
        
        return {
            "total_documents": all_docs["total"],
            "total_chunks": total_chunks,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "avg_chunks_per_document": round(total_chunks / all_docs["total"], 1),
            "source_type_distribution": source_types,
            "content_type_distribution": content_types,
            "storage_locations": {
                "parsed_directory": str(self.parsed_dir),
                "metadata_directory": str(self.metadata_dir),
                "raw_directory": str(self.raw_dir)
            }
        } 