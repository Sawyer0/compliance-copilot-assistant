"""Content processing and chunking for compliance documents."""

import json
import os
import datetime
from typing import Dict, List, Any


class ContentProcessor:
    """Processes and structures extracted content into chunks."""
    
    def __init__(self, max_words_per_chunk: int = 500):
        self.max_words_per_chunk = max_words_per_chunk
    
    def process_and_save_content(
        self,
        text_content: str,
        source_config: dict,
        url: str,
        doc_id: str,
        raw_file_path: str,
        parsed_file_path: str,
        metadata_file_path: str,
        content_type: str
    ) -> dict:
        """Process and save extracted content with chunking."""
        
        # Clean and chunk the text content
        cleaned_text = self._clean_text(text_content)
        chunks = self._create_chunks(cleaned_text, doc_id)
        
        # Create parsed document structure
        parsed_doc = self._create_parsed_document(
            source_config, url, doc_id, chunks, raw_file_path, content_type
        )
        
        # Save parsed document
        self._save_parsed_document(parsed_doc, parsed_file_path)
        
        # Create and save metadata
        metadata = self._create_metadata(
            parsed_doc, source_config, url, raw_file_path, 
            parsed_file_path, content_type, chunks
        )
        self._save_metadata(metadata, metadata_file_path)
        
        return {
            "url": url,
            "document_id": parsed_doc["document_id"],
            "chunks": len(chunks),
            "words": sum(chunk["word_count"] for chunk in chunks),
            "status": "success"
        }
    
    def _clean_text(self, text_content: str) -> str:
        """Clean and normalize text content."""
        return ' '.join(text_content.split())
    
    def _create_chunks(self, cleaned_text: str, doc_id: str) -> List[Dict[str, Any]]:
        """Create content chunks from cleaned text."""
        sentences = cleaned_text.split('. ')
        chunks = []
        current_chunk = ""
        chunk_index = 0
        
        for sentence in sentences:
            test_chunk = current_chunk + sentence + ". "
            
            if len(test_chunk.split()) > self.max_words_per_chunk and current_chunk:
                chunks.append(self._create_chunk(current_chunk, doc_id, chunk_index))
                current_chunk = sentence + ". "
                chunk_index += 1
            else:
                current_chunk = test_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(self._create_chunk(current_chunk, doc_id, chunk_index))
        
        return chunks
    
    def _create_chunk(self, content: str, doc_id: str, chunk_index: int) -> Dict[str, Any]:
        """Create a single chunk object."""
        content = content.strip()
        return {
            "chunk_id": f"{doc_id}_chunk_{chunk_index:03d}",
            "content": content,
            "chunk_index": chunk_index,
            "chunk_type": "paragraph",
            "word_count": len(content.split()),
            "char_count": len(content)
        }
    
    def _create_parsed_document(
        self,
        source_config: dict,
        url: str,
        doc_id: str,
        chunks: List[Dict[str, Any]],
        raw_file_path: str,
        content_type: str
    ) -> Dict[str, Any]:
        """Create the parsed document structure."""
        return {
            "document_id": f"{source_config.get('source_id', 'unknown')}_{doc_id}",
            "source_name": source_config.get("name"),
            "source_url": url,
            "title": source_config.get("description", source_config.get("name")),
            "document_type": source_config.get("regulation_type", "compliance_document"),
            "jurisdiction": source_config.get("jurisdiction", "Unknown"),
            "tags": source_config.get("tags", []),
            "content_chunks": chunks,
            "total_chunks": len(chunks),
            "total_words": sum(chunk["word_count"] for chunk in chunks),
            "total_characters": sum(chunk["char_count"] for chunk in chunks),
            "processed_at": datetime.datetime.now().isoformat(),
            "raw_file_path": raw_file_path,
            "content_type": content_type
        }
    
    def _create_metadata(
        self,
        parsed_doc: Dict[str, Any],
        source_config: dict,
        url: str,
        raw_file_path: str,
        parsed_file_path: str,
        content_type: str,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create metadata for the processed document."""
        return {
            "document_id": parsed_doc["document_id"],
            "source_name": source_config.get("name"),
            "source_url": url,
            "raw_file_path": raw_file_path,
            "parsed_file_path": parsed_file_path,
            "content_type": content_type,
            "file_size_bytes": os.path.getsize(raw_file_path) if os.path.exists(raw_file_path) else 0,
            "total_chunks": len(chunks),
            "total_words": sum(chunk["word_count"] for chunk in chunks),
            "processing_timestamp": datetime.datetime.now().isoformat(),
            "processing_status": "success",
            "extraction_method": "playwright" if content_type == 'text/html' else "pymupdf"
        }
    
    def _save_parsed_document(self, parsed_doc: Dict[str, Any], file_path: str) -> None:
        """Save parsed document to file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(parsed_doc, f, indent=2, ensure_ascii=False)
    
    def _save_metadata(self, metadata: Dict[str, Any], file_path: str) -> None:
        """Save metadata to file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False) 