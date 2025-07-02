"""Storage management for documents and metadata."""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from uuid import UUID

import aiofiles
import yaml
from pydantic import BaseModel

from models.document import Document, DocumentMetadata
from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class StorageManager:
    """Manages file storage and metadata for documents."""
    
    def __init__(self):
        self.settings = get_settings()
        self.raw_dir = self.settings.raw_output_path
        self.parsed_dir = self.settings.parsed_output_path
        self.metadata_dir = self.settings.metadata_output_path
        self.logs_dir = self.settings.logs_output_path
    
    async def save_raw_content(
        self, 
        content: Union[bytes, str], 
        document_id: UUID,
        source_name: str,
        extension: str = "bin"
    ) -> Path:
        """Save raw document content to storage."""
        filename = f"{document_id}.{extension}"
        source_dir = self.raw_dir / source_name
        source_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = source_dir / filename
        
        if isinstance(content, str):
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
        else:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        
        logger.info(
            "Saved raw content",
            document_id=str(document_id),
            source_name=source_name,
            file_path=str(file_path),
            file_size=len(content)
        )
        
        return file_path
    
    async def save_parsed_content(
        self,
        content: str,
        document_id: UUID,
        source_name: str,
        format_type: str = "txt"
    ) -> Path:
        """Save parsed document content to storage."""
        filename = f"{document_id}.{format_type}"
        source_dir = self.parsed_dir / source_name
        source_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = source_dir / filename
        
        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        logger.info(
            "Saved parsed content",
            document_id=str(document_id),
            source_name=source_name,
            file_path=str(file_path),
            content_length=len(content)
        )
        
        return file_path
    
    async def save_metadata(
        self,
        metadata: DocumentMetadata,
        source_name: str,
        format_type: str = "yaml"
    ) -> Path:
        """Save document metadata to storage."""
        filename = f"{metadata.doc_id}.{format_type}"
        source_dir = self.metadata_dir / source_name
        source_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = source_dir / filename
        
        # Convert to dict for serialization
        metadata_dict = metadata.dict()
        
        if format_type == "yaml":
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(yaml.dump(metadata_dict, default_flow_style=False))
        else:  # json
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata_dict, indent=2, default=str))
        
        logger.info(
            "Saved metadata",
            document_id=str(metadata.doc_id),
            source_name=source_name,
            file_path=str(file_path)
        )
        
        return file_path
    
    async def load_metadata(
        self,
        document_id: UUID,
        source_name: str,
        format_type: str = "yaml"
    ) -> Optional[DocumentMetadata]:
        """Load document metadata from storage."""
        filename = f"{document_id}.{format_type}"
        file_path = self.metadata_dir / source_name / filename
        
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            if format_type == "yaml":
                data = yaml.safe_load(content)
            else:  # json
                data = json.loads(content)
            
            return DocumentMetadata(**data)
        
        except Exception as e:
            logger.error(
                "Failed to load metadata",
                document_id=str(document_id),
                source_name=source_name,
                error=str(e)
            )
            return None
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    async def check_duplicate(
        self,
        content_hash: str,
        source_name: str
    ) -> Optional[UUID]:
        """Check if content already exists by hash."""
        if not self.settings.enable_deduplication:
            return None
        
        # Search metadata files for matching hash
        source_metadata_dir = self.metadata_dir / source_name
        
        if not source_metadata_dir.exists():
            return None
        
        for metadata_file in source_metadata_dir.glob("*.yaml"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                if data.get('file_hash') == content_hash:
                    return UUID(data['doc_id'])
            
            except Exception as e:
                logger.warning(
                    "Error checking duplicate",
                    metadata_file=str(metadata_file),
                    error=str(e)
                )
                continue
        
        return None
    
    async def get_document_stats(self, source_name: str) -> Dict[str, int]:
        """Get statistics for documents in a source."""
        source_metadata_dir = self.metadata_dir / source_name
        
        if not source_metadata_dir.exists():
            return {"total": 0, "processed": 0, "failed": 0}
        
        stats = {"total": 0, "processed": 0, "failed": 0}
        
        for metadata_file in source_metadata_dir.glob("*.yaml"):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                stats["total"] += 1
                
                # This would need to be updated based on your status tracking
                if data.get('status') == 'processed':
                    stats["processed"] += 1
                elif data.get('status') == 'failed':
                    stats["failed"] += 1
            
            except Exception:
                continue
        
        return stats
    
    async def cleanup_old_versions(
        self,
        document_id: UUID,
        source_name: str,
        keep_versions: int = 5
    ) -> None:
        """Clean up old versions of a document."""
        if not self.settings.enable_versioning:
            return
        
        # Implementation would depend on versioning strategy
        # For now, just log the operation
        logger.info(
            "Cleanup old versions requested",
            document_id=str(document_id),
            source_name=source_name,
            keep_versions=keep_versions
        ) 