"""Main source registry for managing source configurations."""

from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from core.config import get_settings
from core.logging import get_logger
from models.source import Source, SourceConfig
from .file_manager import SourceFileManager
from .regional_manager import RegionalManager

logger = get_logger(__name__)


class SourceRegistry:
    """Registry for managing source configurations."""
    
    def __init__(self, sources_dir: Optional[Path] = None):
        self.settings = get_settings()
        self.sources_dir = sources_dir or self.settings.base_dir / "registry" / "sources"
        
        # Initialize managers
        self.file_manager = SourceFileManager(self.sources_dir)
        self.regional_manager = RegionalManager(self.sources_dir)
        
        # Source storage
        self._sources: Dict[UUID, Source] = {}
        self._source_files: Dict[str, Path] = {}  # Track which file each source came from
        
        self._load_sources()
    
    def _load_sources(self) -> None:
        """Load sources using the file manager."""
        if not self.sources_dir.exists():
            logger.warning(
                "Sources directory not found, creating empty registry",
                sources_dir=str(self.sources_dir)
            )
            self.regional_manager.create_empty_structure()
            return
        
        self._sources, self._source_files = self.file_manager.load_all_sources()
    
    # Core source operations
    def get_source(self, source_id: UUID) -> Optional[Source]:
        """Get source by ID."""
        return self._sources.get(source_id)
    
    def get_source_by_name(self, name: str) -> Optional[Source]:
        """Get source by name."""
        for source in self._sources.values():
            if source.config.name == name:
                return source
        return None
    
    def list_sources(self, active_only: bool = False) -> List[Source]:
        """List all sources."""
        sources = list(self._sources.values())
        
        if active_only:
            sources = [s for s in sources if s.config.is_active]
        
        return sources
    
    def add_source(self, config: SourceConfig) -> Source:
        """Add a new source."""
        source = Source(config=config)
        self._sources[config.source_id] = source
        self._save_sources()
        
        logger.info(
            "Added new source",
            source_id=str(config.source_id),
            source_name=config.name
        )
        
        return source
    
    def update_source(self, source_id: UUID, config: SourceConfig) -> Optional[Source]:
        """Update an existing source."""
        if source_id not in self._sources:
            return None
        
        source = Source(config=config)
        # Preserve runtime statistics
        old_source = self._sources[source_id]
        source.total_documents_fetched = old_source.total_documents_fetched
        source.successful_fetches = old_source.successful_fetches
        source.failed_fetches = old_source.failed_fetches
        source.average_fetch_time = old_source.average_fetch_time
        
        self._sources[source_id] = source
        self._save_sources()
        
        logger.info(
            "Updated source",
            source_id=str(source_id),
            source_name=config.name
        )
        
        return source
    
    def remove_source(self, source_id: UUID) -> bool:
        """Remove a source."""
        if source_id not in self._sources:
            return False
        
        source_name = self._sources[source_id].config.name
        del self._sources[source_id]
        
        # Remove from file tracking
        source_id_str = str(source_id)
        if source_id_str in self._source_files:
            del self._source_files[source_id_str]
        
        self._save_sources()
        
        logger.info(
            "Removed source",
            source_id=str(source_id),
            source_name=source_name
        )
        
        return True
    
    def _save_sources(self) -> None:
        """Save sources using the file manager."""
        self.file_manager.save_sources_by_file(self._sources, self._source_files)
    
    # Filtering and organization methods
    def get_sources_by_jurisdiction(self, jurisdiction: str) -> List[Source]:
        """Get sources by jurisdiction."""
        return [
            source for source in self._sources.values()
            if source.config.jurisdiction == jurisdiction
        ]
    
    def get_sources_by_type(self, source_type: str) -> List[Source]:
        """Get sources by type."""
        return [
            source for source in self._sources.values()
            if source.config.source_type == source_type
        ]
    
    def get_sources_by_priority(self, min_priority: int = 1) -> List[Source]:
        """Get sources by minimum priority, sorted by priority (highest first)."""
        sources = [
            source for source in self._sources.values()
            if source.config.priority >= min_priority and source.config.is_active
        ]
        
        return sorted(sources, key=lambda s: s.config.priority, reverse=True)
    
    # Regional organization methods (delegated to regional manager)
    def get_sources_by_region(self, region: str) -> List[Source]:
        """Get sources by region."""
        return self.regional_manager.get_sources_by_region(region, self._sources, self._source_files)
    
    def get_regional_summary(self) -> Dict[str, Dict[str, int]]:
        """Get a summary of sources organized by region and jurisdiction."""
        return self.regional_manager.get_regional_summary(self._source_files, self._sources)
    
    def get_available_regions(self) -> List[str]:
        """Get list of available regions."""
        return self.regional_manager.get_available_regions()
    
    def get_available_jurisdictions(self) -> List[str]:
        """Get list of available jurisdictions."""
        return self.regional_manager.get_available_jurisdictions()
    
    # Utility methods
    def reload_sources(self) -> None:
        """Reload sources from files."""
        logger.info("Reloading sources from files")
        self._load_sources()
    
    def get_source_count_by_status(self) -> Dict[str, int]:
        """Get count of sources by active/inactive status."""
        active_count = sum(1 for s in self._sources.values() if s.config.is_active)
        inactive_count = len(self._sources) - active_count
        
        return {
            'total': len(self._sources),
            'active': active_count,
            'inactive': inactive_count
        } 