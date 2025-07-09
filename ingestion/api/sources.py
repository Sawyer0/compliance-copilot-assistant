"""Sources management endpoints."""

import logging
from pathlib import Path
from typing import Dict, Any, List

import yaml
from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/sources")
async def list_sources() -> Dict[str, Any]:
    """List all configured compliance sources."""
    try:
        sources_dir = Path("registry/sources")
        all_sources = []
        
        for sources_file in sources_dir.glob("**/*.yaml"):
            with open(sources_file, 'r') as f:
                data = yaml.safe_load(f)
                for source in data.get('sources', []):
                    all_sources.append({
                        "name": source.get('name'),
                        "source_id": source.get('source_id'),
                        "jurisdiction": source.get('jurisdiction'),
                        "regulation_type": source.get('regulation_type'),
                        "is_active": source.get('is_active', False),
                        "fetch_frequency": source.get('fetch_frequency'),
                        "priority": source.get('priority', 5)
                    })
        
        return {
            "sources": all_sources,
            "total": len(all_sources),
            "active": len([s for s in all_sources if s['is_active']])
        }
        
    except Exception as e:
        logger.error(f"Error listing sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 