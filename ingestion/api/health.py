"""Health check and status endpoints."""

import datetime
import logging
from pathlib import Path
from typing import Dict, Any

import yaml
from fastapi import APIRouter, HTTPException

from core.config import get_settings
from ingestion_functions.client import inngest_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "compliance-ingestion", 
        "timestamp": datetime.datetime.now().isoformat(),
        "version": "1.0.0"
    }


@router.get("/status")
async def system_status() -> Dict[str, Any]:
    """Get system status and configuration."""
    settings = get_settings()
    
    # Check source configurations
    sources_dir = Path("registry/sources")
    total_sources = 0
    active_sources = 0
    
    try:
        for sources_file in sources_dir.glob("**/*.yaml"):
            with open(sources_file, 'r') as f:
                data = yaml.safe_load(f)
                sources = data.get('sources', [])
                total_sources += len(sources)
                active_sources += len([s for s in sources if s.get('is_active', False)])
    except Exception as e:
        logger.error(f"Error reading sources: {e}")
    
    return {
        "status": "operational",
        "sources": {
            "total": total_sources,
            "active": active_sources
        },
        "directories": {
            "raw_output": str(settings.raw_output_path),
            "parsed_output": str(settings.parsed_output_path),
            "metadata_output": str(settings.metadata_output_path)
        },
        "inngest_client_id": inngest_client.app_id,
        "timestamp": datetime.datetime.now().isoformat()
    } 