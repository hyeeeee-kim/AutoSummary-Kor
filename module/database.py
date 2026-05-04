"""SQLite-based paper database"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
import hashlib
from config.settings import DATA_DIR

class PaperDatabase:
    def __init__(self):
        self.db_path = DATA_DIR / "papers.db"
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT,
                source TEXT,
                link TEXT,
                title_hash TEXT UNIQUE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source ON papers(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON papers(title_hash)")
        conn.commit()
        conn.close()

    @staticmethod
    def _hash_title(title: str) -> str:
        return hashlib.md5(" ".join(title.lower().split()).encode()).hexdigest()

    def add_paper(self, paper: Dict) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM papers WHERE title_hash = ?", (self._hash_title(paper["title"]),))
        if cursor.fetchone():
            conn.close()
            return False
        try:
            cursor.execute("""
                INSERT INTO papers (paper_id, title, abstract, source, link, title_hash)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (paper["id"], paper["title"], paper.get("abstract", ""), paper["source"], paper.get("link", ""), self._hash_title(paper["title"])))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    def add_papers_batch(self, papers: List[Dict]) -> Dict:
        added, result = 0, []
        for p in papers:
            if self.add_paper(p):
                added += 1
                result.append(p)
        return {"added": added, "duplicates": len(papers) - added, "papers": result}

    def get_stats(self) -> Dict:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM papers")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT source, COUNT(*) FROM papers GROUP BY source")
        by_source = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return {"total_papers": total, "by_source": by_source}
