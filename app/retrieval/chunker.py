import re
from typing import List, Dict, Any
from app.config import settings
from app.llm.client import llm_client
from app.utils.text import normalize_text, clean_markdown, clean_html


class TextChunker:
    def __init__(self):
        self.min_tokens = settings.chunk_min_tokens
        self.max_tokens = settings.chunk_max_tokens
        self.overlap_percent = settings.chunk_overlap_percent
    
    def chunk_text(self, text: str, title: str = "", section: str = "") -> List[Dict[str, Any]]:
        """Chunk text into overlapping segments"""
        if not text:
            return []
        
        # Clean and normalize text
        text = normalize_text(text)
        
        # Split into sentences first
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        current_tokens = 0
        
        for sentence in sentences:
            sentence_tokens = llm_client.count_tokens(sentence)
            
            # If adding this sentence would exceed max_tokens
            if current_tokens + sentence_tokens > self.max_tokens and current_chunk:
                # Save current chunk
                chunk_data = {
                    'text': current_chunk.strip(),
                    'tokens': current_tokens,
                    'title': title,
                    'section': section
                }
                chunks.append(chunk_data)
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_chunk = overlap_text + " " + sentence
                current_tokens = llm_client.count_tokens(current_chunk)
            else:
                current_chunk += " " + sentence if current_chunk else sentence
                current_tokens += sentence_tokens
        
        # Add final chunk if it meets minimum token requirement
        if current_chunk and current_tokens >= self.min_tokens:
            chunk_data = {
                'text': current_chunk.strip(),
                'tokens': current_tokens,
                'title': title,
                'section': section
            }
            chunks.append(chunk_data)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex"""
        # Split on sentence endings, but preserve abbreviations
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Clean up sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Minimum sentence length
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _get_overlap_text(self, text: str) -> str:
        """Get overlap text from the end of the chunk"""
        if not text:
            return ""
        
        # Calculate overlap tokens
        total_tokens = llm_client.count_tokens(text)
        overlap_tokens = int(total_tokens * self.overlap_percent)
        
        # Split into words and get last N tokens
        words = text.split()
        overlap_words = []
        current_tokens = 0
        
        for word in reversed(words):
            word_tokens = llm_client.count_tokens(word)
            if current_tokens + word_tokens <= overlap_tokens:
                overlap_words.insert(0, word)
                current_tokens += word_tokens
            else:
                break
        
        return " ".join(overlap_words)
    
    def chunk_markdown(self, markdown_text: str, title: str = "") -> List[Dict[str, Any]]:
        """Chunk markdown text while preserving structure"""
        if not markdown_text:
            return []
        
        # Clean markdown
        clean_text = clean_markdown(markdown_text)
        
        # Split by headers to preserve document structure
        sections = self._split_markdown_sections(markdown_text)
        
        chunks = []
        for section_name, section_content in sections:
            section_chunks = self.chunk_text(section_content, title, section_name)
            chunks.extend(section_chunks)
        
        return chunks
    
    def _split_markdown_sections(self, markdown_text: str) -> List[tuple]:
        """Split markdown into sections based on headers"""
        lines = markdown_text.split('\n')
        sections = []
        current_section = ""
        current_section_name = ""
        
        for line in lines:
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            
            if header_match:
                # Save previous section
                if current_section.strip():
                    sections.append((current_section_name, current_section.strip()))
                
                # Start new section
                current_section_name = header_match.group(2).strip()
                current_section = ""
            else:
                current_section += line + "\n"
        
        # Add final section
        if current_section.strip():
            sections.append((current_section_name, current_section.strip()))
        
        return sections
    
    def chunk_html(self, html_text: str, title: str = "") -> List[Dict[str, Any]]:
        """Chunk HTML text while preserving structure"""
        if not html_text:
            return []
        
        # Clean HTML
        clean_text = clean_html(html_text)
        
        # Split by HTML tags to preserve structure
        sections = self._split_html_sections(html_text)
        
        chunks = []
        for section_name, section_content in sections:
            section_chunks = self.chunk_text(section_content, title, section_name)
            chunks.extend(section_chunks)
        
        return chunks
    
    def _split_html_sections(self, html_text: str) -> List[tuple]:
        """Split HTML into sections based on tags"""
        # Extract text from common section tags
        sections = []
        
        # Look for h1-h6 tags
        header_pattern = r'<h([1-6])[^>]*>(.*?)</h\1>'
        headers = re.findall(header_pattern, html_text, re.IGNORECASE | re.DOTALL)
        
        # Split content by headers
        parts = re.split(header_pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        
        current_section = ""
        current_section_name = ""
        
        for i, part in enumerate(parts):
            if i % 3 == 0:  # Content part
                current_section += part
            elif i % 3 == 1:  # Header level
                continue
            else:  # Header text
                # Save previous section
                if current_section.strip():
                    sections.append((current_section_name, current_section.strip()))
                
                # Start new section
                current_section_name = clean_html(part)
                current_section = ""
        
        # Add final section
        if current_section.strip():
            sections.append((current_section_name, current_section.strip()))
        
        return sections


# Global chunker instance
chunker = TextChunker()
