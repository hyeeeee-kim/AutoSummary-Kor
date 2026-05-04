"""Modular pipeline for paper processing - step by step execution"""
import os
import sqlite3
import time
from pathlib import Path
from tqdm import tqdm

# Set ChromaDB telemetry BEFORE importing
os.environ["CHROMA_TELEMETRY_DISABLED"] = "True"

from module.scrapers import ConferenceScraper
from module.database import PaperDatabase
from module.rag import VectorStore, Retriever
from module.summarizer import SummaryGenerator
from module.outputs import MarkdownBuilder
from config.settings import DATA_DIR


class DatabaseManager:
    """Manage database creation and status"""
    
    def __init__(self):
        self.db_path = DATA_DIR / "papers.db"
    
    def exists(self) -> bool:
        """Check if database exists and has papers"""
        if not self.db_path.exists():
            return False
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM papers")
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except:
            return False
    
    def get_stats(self) -> dict:
        """Get database statistics"""
        if not self.exists():
            return {"total": 0, "by_source": {}}
        
        try:
            db = PaperDatabase()
            stats = db.get_stats()
            return {
                "total": stats.get("total", 0),
                "by_source": stats.get("by_source", {})
            }
        except:
            return {"total": 0, "by_source": {}}
    
    def build(self) -> dict:
        """Build database by scraping conferences"""
        print("\n" + "="*60)
        print("[STEP 1] Building Database")
        print("="*60 + "\n")
        
        print("[1/3] Scraping conferences...")
        papers_dict = ConferenceScraper().scrape_all_enabled()
        total = sum(len(p) for p in papers_dict.values())
        
        if total == 0:
            print("  WARNING: No papers scraped. Check network or URLs.")
            return {"added": 0, "duplicates": 0, "papers": []}
        
        print(f"  OK: {total} papers collected\n")
        
        print("[2/3] Saving to database...")
        all_papers = [{
            "id": f"{source}_{idx}",
            "title": p.title,
            "abstract": p.abstract,
            "content": f"{p.title}\n{p.abstract}",
            "source": source,
            "link": p.link or "",
        } for source, papers in papers_dict.items() for idx, p in enumerate(papers)]
        
        db = PaperDatabase()
        result = db.add_papers_batch(all_papers)
        print(f"  Added: {result['added']}, Duplicates: {result['duplicates']}\n")
        
        print("[3/3] Database Statistics")
        stats = db.get_stats()
        for source, count in sorted(stats['by_source'].items()):
            print(f"  {source}: {count}")
        print()
        
        return result


class PaperManager:
    """Manage loading papers from database"""
    
    def __init__(self):
        self.db_path = DATA_DIR / "papers.db"
    
    def load_papers(self) -> list:
        """Load all papers from database"""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers")
        papers_rows = cursor.fetchall()
        conn.close()

        return [{
            "id": p["paper_id"],
            "title": p["title"],
            "abstract": p["abstract"] or "",
            "content": f"{p['title']}\n{p['abstract'] or ''}",
            "source": p["source"],
            "link": p["link"] or "",
        } for p in papers_rows]


class SearchManager:
    """Manage search functionality"""
    
    def __init__(self, papers: list = None):
        self.papers = papers or []
        self.vectorstore = None
        self.retriever = None
    
    def build_index(self) -> None:
        """Build vectorization index"""
        if not self.papers:
            print("ERROR: No papers to index\n")
            return
        
        print("\n" + "="*60)
        print("[STEP 2] Build Search Index")
        print("="*60 + "\n")
        
        print(f"Loaded: {len(self.papers)} papers\n")
        
        print("[1/2] Building vector index...")
        self.vectorstore = VectorStore()
        
        if self.vectorstore.count() == 0:
            for i in tqdm(range(0, len(self.papers), 50), desc="  Vectorizing"):
                self.vectorstore.add_papers(self.papers[i:i+50])
            print(f"  OK: Indexed {len(self.papers)} papers\n")
        else:
            print(f"  OK: Using cached vectors ({self.vectorstore.count()} papers)\n")
        
        print("[2/2] Building hybrid index...")
        self.retriever = Retriever(self.vectorstore)
        self.retriever.build_index(self.papers)
        print("  OK: Hybrid index ready\n")
    
    def search(self, query: str, top_k: int = 50) -> list:
        """Search papers by query"""
        if not self.retriever:
            print("ERROR: Index not built. Call build_index() first.\n")
            return []
        
        print("\n" + "="*60)
        print("[STEP 3] Search Papers")
        print("="*60 + "\n")
        
        print(f"Query: '{query}'\n")
        results = self.retriever.search(query, top_k=top_k)
        
        print(f"Found: {len(results)} papers\n")
        for i, p in enumerate(results[:15], 1):
            score = p.get('final_score', 0) * 100
            print(f"{i:2}. [{score:5.1f}%] {p['title']}")
            print(f"    {p['source']}")
            if p.get('link'):
                print(f"    {p['link']}")
            print()
        
        if len(results) > 15:
            print(f"... and {len(results) - 15} more\n")
        
        return results


class SummaryManager:
    """Manage paper summarization"""
    
    def __init__(self):
        self.generator = SummaryGenerator()
    
    def summarize_papers(self, papers: list, progress: bool = True) -> list:
        """Generate summaries for papers"""
        if not papers:
            print("ERROR: No papers to summarize\n")
            return []
        
        print("\n" + "="*60)
        print("[STEP 4] Generate Summaries")
        print("="*60 + "\n")
        
        print(f"Summarizing {len(papers)} papers...\n")
        
        summaries = []
        iterator = tqdm(papers, desc="  Summarizing") if progress else papers
        
        for p in iterator:
            summary = self.generator.generate(
                p["title"], 
                p.get("abstract", ""), 
                context=None
            )
            summaries.append({**p, "summary": summary})
        
        print(f"OK: Generated {len(summaries)} summaries\n")
        return summaries



class ExportManager:
    """Manage export to various formats"""
    
    def export_markdown(self, papers: list, query: str = "", filename: str = None) -> Path:
        """Export papers to markdown"""
        if not papers:
            print("ERROR: No papers to export\n")
            return None
        
        print("\n" + "="*60)
        print("[STEP 5] Export to Markdown")
        print("="*60 + "\n")
        
        if filename is None:
            filename = f"summary_{query.replace(' ', '_')}_{int(time.time())}.md"
        
        content = MarkdownBuilder.build_collection(papers, query)
        filepath = MarkdownBuilder.save(content, filename)
        
        print(f"OK: Saved: {filepath}\n")
        return filepath
    



class Pipeline:
    """Main pipeline manager - orchestrates all steps"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.paper_manager = PaperManager()
        self.search_manager = None
        self.summary_manager = SummaryManager()
        self.export_manager = ExportManager()
        self.papers = []
        self.search_results = []
    
    def show_menu(self) -> None:
        """Display main menu"""
        db_status = "EXISTS" if self.db_manager.exists() else "NOT FOUND"
        
        print("\n" + "="*60)
        print("PAPER SUMMARY SYSTEM - PIPELINE")
        print("="*60)
        print(f"Database Status: {db_status}\n")
        
        if self.db_manager.exists():
            stats = self.db_manager.get_stats()
            print(f"Papers in DB: {stats['total']}")
            for source, count in sorted(stats['by_source'].items()):
                print(f"  • {source}: {count}")
            print()
        
        print("STEPS:")
        print("  1. Build/Rebuild Database (scrape conferences)")
        print("  2. Build Search Index (vectorize)")
        print("  3. Search Papers (by keyword)")
        print("  4. Generate Summaries (from PDF directory)")
        print("  0. Exit")
        print("="*60 + "\n")
    
    def run_step_1_build_db(self) -> bool:
        """Step 1: Build database"""
        result = self.db_manager.build()
        if result['added'] > 0:
            self.papers = []  # Reset papers
            return True
        return False
    
    def run_step_2_build_index(self) -> bool:
        """Step 2: Build search index"""
        if not self.papers:
            self.papers = self.paper_manager.load_papers()
        
        if not self.papers:
            print("ERROR: No papers to index. Build database first.\n")
            return False
        
        self.search_manager = SearchManager(self.papers)
        self.search_manager.build_index()
        return True
    
    def run_step_3_search(self) -> bool:
        """Step 3: Search papers"""
        # Auto-initialize index if needed
        if not self.search_manager:
            if not self.papers:
                self.papers = self.paper_manager.load_papers()
            
            if not self.papers:
                print("ERROR: No papers available. Run step 1 first.\n")
                return False
            
            print("Initializing search index...\n")
            self.search_manager = SearchManager(self.papers)
            self.search_manager.build_index()
        
        query = input("Enter search query: ").strip() or "transformer"
        self.search_results = self.search_manager.search(query, top_k=50)
        
        if not self.search_results:
            print("ERROR: No results found.\n")
            return False
        
        return True
    
    def run_step_4_summarize(self) -> bool:
        """Step 4: Generate summaries from PDF files"""
        print("\n" + "="*60)
        print("[STEP 4] Generate Summaries")
        print("="*60 + "\n")
        
        directory = input("Enter directory path containing PDF files: ").strip()
        
        if not directory:
            print("Cancelled.\n")
            return False
        
        return self._summarize_from_pdfs(directory)
    
    def _summarize_from_pdfs(self, directory: str) -> bool:
        """Summarize from PDF files in a directory with streaming output"""
        from module.pdf_processor import PDFSummaryProcessor
        from config.settings import OUTPUT_DIR
        from datetime import datetime
        
        processor = PDFSummaryProcessor(self.summary_manager.generator)
        
        # Generate output filename with timestamp
        timestamp = int(datetime.now().timestamp())
        output_filename = f"summary_pdf_{timestamp}.md"
        output_path = OUTPUT_DIR / output_filename
        
        print("\n[Processing PDFs with streaming output]")
        count = processor.process_directory_streaming(directory, output_path)
        
        if count == 0:
            print("ERROR: No PDFs processed.\n")
            return False
        
        print(f"\nOK: Processed {count} PDFs")
        print(f"Output: {output_path}\n")
        return True
    
    def _summarize_from_search(self) -> bool:
        """Summarize from search results (deprecated)"""
        if not self.search_results:
            print("ERROR: No search results. Run step 3 first.\n")
            return False
        
        count = min(
            int(input(f"Select papers to summarize (max {len(self.search_results)}, default 5): ") or "5"),
            len(self.search_results)
        )
        selected = self.search_results[:count]
        
        self.search_results = self.summary_manager.summarize_papers(selected)
        return True
    

    
    def run(self) -> None:
        """Main loop - show menu and process user input"""
        while True:
            self.show_menu()
            choice = input("Select step (0-4): ").strip()
            
            if choice == "0":
                print("Paper Summary Pipeline terminated.\n")
                break
            elif choice == "1":
                self.run_step_1_build_db()
            elif choice == "2":
                self.run_step_2_build_index()
            elif choice == "3":
                self.run_step_3_search()
            elif choice == "4":
                self.run_step_4_summarize()
            else:
                print("ERROR: Invalid choice. Try again.\n")


if __name__ == "__main__":
    pipeline = Pipeline()
    pipeline.run()
