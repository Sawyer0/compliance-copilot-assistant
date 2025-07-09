"""Content quality analysis service for compliance documents."""

import re
from typing import Dict, List, Any


class ContentQualityService:
    """Service for analyzing and scoring content quality."""
    
    @staticmethod
    def analyze_content_quality(chunk_text: str) -> Dict[str, Any]:
        """Analyze the quality of extracted content to identify noise vs. actual content."""
        
        # HTML/markup indicators (heavy penalty)
        html_tags = len(re.findall(r'<[^>]+>', chunk_text))
        html_entities = len(re.findall(r'&[a-zA-Z]+;', chunk_text))
        
        # Navigation/UI indicators (heavy penalty)
        nav_indicators = [
            'menu', 'navigation', 'breadcrumb', 'skip to content', 'header', 'footer',
            'search', 'login', 'sign in', 'home page', 'privacy policy', 'cookie',
            'social media', 'facebook', 'twitter', 'instagram', 'youtube', 'linkedin',
            'site-header', 'mobile-menu', 'hamburger', 'overlay', 'dropdown',
            'screen-reader-text', 'aria-hidden', 'role=', 'class=', 'id=',
            'open in new window', 'external link', 'previous', 'next',
            'share', 'follow us', 'contact us', 'about us', 'subscribe'
        ]
        nav_score = sum(1 for indicator in nav_indicators if indicator.lower() in chunk_text.lower())
        
        # White House specific navigation indicators
        wh_nav_indicators = [
            'The White House', 'Administration', 'Briefing Room', 'President Biden',
            'Vice President Harris', 'First Lady', 'Second Gentleman', 'Cabinet',
            'Executive Offices', 'The Record', 'The Issues', 'The Moments', 'The Story',
            'EspaÃ±ol', 'Copyright Policy', 'Accessibility Statement'
        ]
        wh_nav_score = sum(1 for indicator in wh_nav_indicators if indicator in chunk_text)
        
        # Content quality indicators
        sentences = len(re.findall(r'[.!?]+', chunk_text))
        avg_word_length = sum(len(word) for word in chunk_text.split()) / max(len(chunk_text.split()), 1)
        
        # Legal/compliance content indicators (high boost)
        compliance_terms = [
            'section', 'article', 'regulation', 'compliance', 'shall', 'requirements',
            'standards', 'framework', 'governance', 'privacy', 'data protection',
            'artificial intelligence', 'AI', 'executive order', 'whereas', 'therefore',
            'pursuant to', 'authority vested', 'hereby ordered', 'implementation',
            'federal', 'administration', 'policy', 'principles', 'directive'
        ]
        compliance_score = sum(1 for term in compliance_terms if term.lower() in chunk_text.lower())
        
        # Document structure indicators (good for actual content)
        structure_indicators = [
            'section 1', 'section 2', 'section 3', 'subsection', 'paragraph',
            'chapter', 'part', 'article', 'sec.', '(a)', '(b)', '(c)', 
            'purpose', 'definitions', 'scope', 'effective date'
        ]
        structure_score = sum(1 for indicator in structure_indicators if indicator.lower() in chunk_text.lower())
        
        # Calculate quality score (0-100)
        quality_score = max(0, min(100, 
            compliance_score * 15 +      # High boost for compliance terms
            structure_score * 10 +       # Boost for document structure
            sentences * 1.5 +            # Boost for sentence structure
            (avg_word_length - 3) * 3 +  # Boost for longer words
            -html_tags * 5 +             # Heavy penalty for HTML
            -html_entities * 3 +         # Penalty for HTML entities
            -nav_score * 8 +             # Heavy penalty for navigation
            -wh_nav_score * 10           # Extra penalty for White House nav
        ))
        
        # Additional checks for obvious noise
        is_obvious_noise = (
            html_tags > 50 or           # Too many HTML tags
            nav_score > 5 or            # Too many nav indicators
            wh_nav_score > 3 or         # White House navigation
            chunk_text.count('<') > 20 or  # Too much HTML
            'doctype html' in chunk_text.lower() or
            'svg xmlns' in chunk_text.lower() or
            'viewport' in chunk_text.lower()
        )
        
        if is_obvious_noise:
            quality_score = min(quality_score, 10)  # Cap at very low score
        
        return {
            "quality_score": round(quality_score, 1),
            "html_tags": html_tags,
            "html_entities": html_entities,
            "navigation_indicators": nav_score,
            "wh_navigation_indicators": wh_nav_score,
            "compliance_terms": compliance_score,
            "structure_indicators": structure_score,
            "sentences": sentences,
            "avg_word_length": round(avg_word_length, 1),
            "is_likely_content": quality_score > 40 and not is_obvious_noise,
            "is_likely_noise": quality_score < 20 or is_obvious_noise,
            "is_obvious_navigation": is_obvious_noise
        }
    
    @staticmethod
    def generate_quality_recommendations(avg_quality: float, noise_chunks: int, total_chunks: int) -> List[str]:
        """Generate recommendations for improving content quality."""
        recommendations = []
        
        noise_percentage = (noise_chunks / total_chunks) * 100 if total_chunks > 0 else 0
        
        if avg_quality < 20:
            recommendations.append("⚠️  Very poor content quality - mostly navigation/HTML markup detected")
        elif avg_quality < 40:
            recommendations.append("⚠️  Low content quality - significant noise detected")
        
        if noise_percentage > 50:
            recommendations.append("🔧 High noise content (>50%) - improve HTML content selectors")
        elif noise_percentage > 30:
            recommendations.append("🔧 Moderate noise detected - consider filtering navigation elements")
        
        if avg_quality > 60:
            recommendations.append("✅ Good content quality - suitable for analysis and RAG applications")
        elif avg_quality > 40:
            recommendations.append("✅ Acceptable content quality - minor filtering may improve results")
        
        if noise_chunks > 10:
            recommendations.append("💡 Use the /clean-content endpoint with higher quality threshold (50-60)")
        
        if avg_quality < 30:
            recommendations.append("💡 For better extraction: Use PDF sources when available over HTML")
            recommendations.append("💡 HTML extraction may benefit from site-specific content selectors")
        
        return recommendations
    
    @classmethod
    def analyze_document_quality(cls, document: Dict[str, Any], document_id: str) -> Dict[str, Any]:
        """Analyze the overall quality of a document's content chunks."""
        chunks = document.get("chunks", [])
        if not chunks:
            # Try alternative chunk field names
            chunks = document.get("content_chunks", [])
        
        quality_analysis = []
        high_quality_chunks = 0
        low_quality_chunks = 0
        noise_chunks = 0
        
        for chunk in chunks:
            chunk_text = chunk.get("content", chunk.get("text", ""))
            
            if not chunk_text:
                continue
                
            quality = cls.analyze_content_quality(chunk_text)
            
            analysis = {
                "chunk_id": chunk.get("chunk_id", "unknown"),
                "chunk_index": chunk.get("chunk_index", 0),
                "word_count": chunk.get("word_count", 0),
                "preview": chunk_text[:200] + "..." if len(chunk_text) > 200 else chunk_text,
                **quality
            }
            
            quality_analysis.append(analysis)
            
            if quality["quality_score"] > 60:
                high_quality_chunks += 1
            elif quality["quality_score"] > 30:
                # Medium quality - likely content
                pass
            elif quality["quality_score"] > 15:
                low_quality_chunks += 1
            else:
                noise_chunks += 1
        
        # Calculate overall document quality
        avg_quality = sum(q["quality_score"] for q in quality_analysis) / len(quality_analysis) if quality_analysis else 0
        
        # Identify best content chunks
        best_chunks = sorted(quality_analysis, key=lambda x: x["quality_score"], reverse=True)[:5]
        worst_chunks = sorted(quality_analysis, key=lambda x: x["quality_score"])[:5]
        
        return {
            "document_id": document_id,
            "source_name": document.get("source_name", "Unknown"),
            "total_chunks": len(quality_analysis),
            "overall_quality_score": round(avg_quality, 1),
            "quality_distribution": {
                "high_quality": high_quality_chunks,
                "low_quality": low_quality_chunks,
                "noise_chunks": noise_chunks,
                "usable_content_percentage": round((high_quality_chunks / len(quality_analysis)) * 100, 1) if quality_analysis else 0
            },
            "best_content_chunks": best_chunks,
            "worst_content_chunks": worst_chunks,
            "recommendations": cls.generate_quality_recommendations(avg_quality, noise_chunks, len(quality_analysis))
        }
    
    @classmethod
    def filter_clean_content(cls, document: Dict[str, Any], document_id: str, min_quality: int = 30) -> Dict[str, Any]:
        """Filter document to return only high-quality content chunks."""
        chunks = document.get("chunks", [])
        if not chunks:
            chunks = document.get("content_chunks", [])
        
        clean_chunks = []
        filtered_count = 0
        
        for chunk in chunks:
            chunk_text = chunk.get("content", chunk.get("text", ""))
            
            if not chunk_text:
                continue
                
            quality = cls.analyze_content_quality(chunk_text)
            
            if quality["quality_score"] >= min_quality:
                clean_chunk = {
                    **chunk,
                    "quality_score": quality["quality_score"],
                    "content_indicators": {
                        "compliance_terms": quality["compliance_terms"],
                        "sentences": quality["sentences"]
                    }
                }
                clean_chunks.append(clean_chunk)
            else:
                filtered_count += 1
        
        return {
            "document_id": document_id,
            "source_name": document.get("source_name", "Unknown"),
            "clean_chunks": clean_chunks,
            "total_clean_chunks": len(clean_chunks),
            "filtered_chunks": filtered_count,
            "quality_threshold": min_quality,
            "clean_content_summary": {
                "total_words": sum(chunk.get("word_count", 0) for chunk in clean_chunks),
                "avg_quality_score": round(sum(chunk["quality_score"] for chunk in clean_chunks) / len(clean_chunks), 1) if clean_chunks else 0
            }
        } 