"""PDF processing - extract text from PDF files and generate summaries"""
from pathlib import Path
from typing import List, Dict, Tuple
import pdfplumber
import re
from tqdm import tqdm
from datetime import datetime


class PDFExtractor:
    """Extract text from PDF files"""
    
    @staticmethod
    def extract_text(pdf_path: str, max_pages: int = 50) -> str:
        """Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            max_pages: Maximum pages to extract (for performance)
        
        Returns:
            Extracted text content
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                page_limit = min(len(pdf.pages), max_pages)
                
                for page in pdf.pages[:page_limit]:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                return text.strip()
        except Exception as e:
            print(f"  ERROR reading {pdf_path}: {str(e)}")
            return ""


class TextCleaner:
    """Clean and normalize extracted PDF text"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean PDF text by removing noise and normalizing formatting
        
        Args:
            text: Raw extracted text
        
        Returns:
            Cleaned text
        """
        # Remove page numbers and headers/footers (common patterns)
        text = re.sub(r'^-?\s*\d+\s*-?$', '', text, flags=re.MULTILINE)  # Page numbers
        text = re.sub(r'\n\s{10,}\S+.*?\n', '\n', text)  # Headers/footers
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple blank lines
        text = re.sub(r' {2,}', ' ', text)  # Multiple spaces
        text = re.sub(r'\n +', '\n', text)  # Leading spaces on lines
        
        # Remove special characters but keep structure
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)  # Control chars
        
        return text.strip()
    
    @staticmethod
    def extract_sections(text: str) -> Dict[str, str]:
        """Extract major sections from paper text
        
        Args:
            text: Cleaned paper text
        
        Returns:
            Dictionary with section names as keys and text as values
        """
        sections = {}
        
        # Section patterns (case-insensitive)
        section_patterns = {
            'abstract': r'(?:^|\n)(?:abstract|요약)\s*(?:\n|:)',
            'introduction': r'(?:^|\n)(?:introduction|introduction|1\s+introduction|서론)\s*(?:\n|:)',
            'method': r'(?:^|\n)(?:method|methodology|approach|방법|3\s+method)\s*(?:\n|:)',
            'results': r'(?:^|\n)(?:results?|findings?|결과|4\s+results?)\s*(?:\n|:)',
            'experiments': r'(?:^|\n)(?:experiments?|evaluation|실험|4\s+experiments?)\s*(?:\n|:)',
            'conclusion': r'(?:^|\n)(?:conclusion|conclusions?|conclusion|결론|5\s+conclusion)\s*(?:\n|:)',
        }
        
        # Find section positions
        positions = {}
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                positions[section_name] = match.start()
        
        if not positions:
            # If no sections found, return full text as 'content'
            return {'content': text}
        
        # Sort by position and extract sections
        sorted_sections = sorted(positions.items(), key=lambda x: x[1])
        
        for i, (section_name, start_pos) in enumerate(sorted_sections):
            # End position is the start of next section (or end of text)
            if i < len(sorted_sections) - 1:
                end_pos = sorted_sections[i + 1][1]
            else:
                end_pos = len(text)
            
            section_text = text[start_pos:end_pos].strip()
            # Remove section header
            section_text = re.sub(r'^[^:]*:', '', section_text, count=1).strip()
            sections[section_name] = section_text
        
        return sections


class PDFSummaryProcessor:
    """Process PDFs from a directory and generate summaries with streaming output"""
    
    def __init__(self, summary_generator):
        """Initialize with a summary generator
        
        Args:
            summary_generator: SummaryGenerator instance from summarizer module
        """
        self.summary_generator = summary_generator
        self.extractor = PDFExtractor()
        self.cleaner = TextCleaner()
    
    def find_pdfs(self, directory: str) -> List[Path]:
        """Find all PDF files in directory
        
        Args:
            directory: Directory path to search
        
        Returns:
            List of PDF file paths
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return []
        
        if not dir_path.is_dir():
            return []
        
        # Find all PDF files recursively
        pdfs = list(dir_path.glob("**/*.pdf"))
        return sorted(pdfs)
    
    def _prepare_full_text(self, sections: Dict[str, str]) -> str:
        """Prepare full text from sections for LLM
        
        Args:
            sections: Dictionary of extracted sections
        
        Returns:
            Formatted full text
        """
        # Use key sections: abstract + method + results/experiments
        key_sections = ['abstract', 'method', 'experiments', 'results', 'content']
        text_parts = []
        
        for section in key_sections:
            if section in sections and sections[section]:
                text_parts.append(sections[section][:3000])  # Limit each section
        
        return "\n\n".join(text_parts) if text_parts else sections.get('content', '')
    
    def process_directory_streaming(self, directory: str, output_file: Path) -> int:
        """Process all PDFs and write to markdown file in streaming fashion
        
        Args:
            directory: Directory path containing PDF files
            output_file: Path to output markdown file
        
        Returns:
            Count of successfully processed papers
        """
        pdfs = self.find_pdfs(directory)
        
        if not pdfs:
            print(f"  WARNING: No PDF files found in {directory}\n")
            return 0
        
        print(f"\n  Found: {len(pdfs)} PDF files\n")
        
        count = 0
        
        # Write header to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Paper Summary - Papers\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Papers: {len(pdfs)}\n\n")
        
        # Process each PDF and append to file
        for i, pdf_path in enumerate(tqdm(pdfs, desc="  Processing PDFs"), 1):
            # Extract text
            text = self.extractor.extract_text(str(pdf_path), max_pages=50)
            
            if not text:
                continue
            
            # Clean text
            text = self.cleaner.clean_text(text)
            
            if not text or len(text) < 200:
                continue
            
            # Extract sections
            sections = self.cleaner.extract_sections(text)
            
            # Prepare full text for LLM
            full_text = self._prepare_full_text(sections)
            
            # Extract title from filename
            title = pdf_path.stem.replace("_", " ")
            
            # Generate summary
            try:
                summary = self.summary_generator.summarize_paper(full_text, title)
                
                # Write to file
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(f"## {i}. {title}\n\n")
                    
                    if summary.get("overview"):
                        f.write(f"**Overview**:\n")
                        f.write(f"{summary['overview']}\n\n")
                    
                    if summary.get("method"):
                        f.write(f"**Method**:\n")
                        f.write(f"{summary['method']}\n\n")
                    
                    if summary.get("experiments"):
                        f.write(f"**Experiments**:\n")
                        f.write(f"{summary['experiments']}\n\n")
                    
                    f.write(f"---\n\n")
                
                count += 1
            except Exception as e:
                print(f"  Error summarizing {pdf_path.name}: {str(e)}")
                continue
        
        return count
