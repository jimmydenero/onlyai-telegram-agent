import re
import html
from typing import List, Optional
from urllib.parse import urlparse


def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and normalizing line breaks"""
    if not text:
        return ""
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize line breaks
    text = re.sub(r'\n\s*\n', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def safe_truncate(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Safely truncate text to max_length, preserving word boundaries"""
    if len(text) <= max_length:
        return text
    
    # Find the last space before max_length
    truncated = text[:max_length - len(suffix)]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + suffix


def extract_filename_from_path(file_path: str) -> str:
    """Extract filename without extension from file path"""
    import os
    filename = os.path.basename(file_path)
    name, _ = os.path.splitext(filename)
    return name


def format_citations(sources: List[str]) -> str:
    """Format sources as a citation string"""
    if not sources:
        return ""
    
    # Extract short names from sources
    short_names = []
    for source in sources:
        if isinstance(source, dict) and 'title' in source:
            short_names.append(source['title'][:20])
        elif isinstance(source, str):
            # Try to extract meaningful part
            if '/' in source:
                short_names.append(source.split('/')[-1][:20])
            else:
                short_names.append(source[:20])
        else:
            short_names.append(str(source)[:20])
    
    # Remove duplicates while preserving order
    unique_names = []
    for name in short_names:
        if name not in unique_names:
            unique_names.append(name)
    
    return f"Sources: [{', '.join(unique_names)}]"


def clean_markdown(text: str) -> str:
    """Clean markdown formatting from text"""
    if not text:
        return ""
    
    # Remove markdown links but keep text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove markdown formatting
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
    text = re.sub(r'`([^`]+)`', r'\1', text)        # Code
    text = re.sub(r'#{1,6}\s+', '', text)           # Headers
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return normalize_text(text)


def clean_html(text: str) -> str:
    """Clean HTML formatting from text"""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities
    text = html.unescape(text)
    
    return normalize_text(text)


def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract potential keywords from text"""
    if not text:
        return []
    
    # Convert to lowercase and split
    words = re.findall(r'\b\w+\b', text.lower())
    
    # Filter by length and common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
    }
    
    keywords = [word for word in words if len(word) >= min_length and word not in stop_words]
    
    return list(set(keywords))  # Remove duplicates


def should_keep_message(text: str, keywords: List[str] = None) -> bool:
    """Determine if a message should be kept for digest based on content"""
    if not text:
        return False
    
    # Default keywords for course-related content
    default_keywords = [
        'ai', 'artificial', 'intelligence', 'machine', 'learning', 'model',
        'prompt', 'engineering', 'strategy', 'business', 'automation',
        'workflow', 'process', 'efficiency', 'productivity', 'course',
        'training', 'education', 'knowledge', 'skill', 'technique'
    ]
    
    keywords = keywords or default_keywords
    text_lower = text.lower()
    
    # Check for question marks
    if '?' in text:
        return True
    
    # Check for keywords
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    
    # Check for mentions (common in Telegram)
    if '@' in text:
        return True
    
    return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 100:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:100-len(ext)-1] + ('.' + ext if ext else '')
    
    return filename or 'unnamed_file'
