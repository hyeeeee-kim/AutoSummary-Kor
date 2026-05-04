"""PDF processing - extract text from PDF files and generate summaries"""
from pathlib import Path
from typing import List
import pdfplumber
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


class PDFSummaryProcessor:
    """Process PDFs from a directory and generate summaries with streaming output"""
    
    def __init__(self, summary_generator):
        """Initialize with a summary generator
        
        Args:
            summary_generator: SummaryGenerator instance from summarizer module
        """
        self.summary_generator = summary_generator
        self.extractor = PDFExtractor()
    
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
            
            # Extract title from filename
            title = pdf_path.stem.replace("_", " ")
            
            # Generate summary
            try:
                summary = self.summary_generator.summarize_paper(text, title)
                
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
