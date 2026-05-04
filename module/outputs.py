"""Markdown output"""
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from config.settings import OUTPUT_DIR

class MarkdownBuilder:
    @staticmethod
    def build_collection(papers: List[Dict], query: str = "") -> str:
        md = [f"# Paper Summary - {query or 'Papers'}", "", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", f"Papers: {len(papers)}", ""]
        for i, p in enumerate(papers, 1):
            md.append(f"## {i}. {p['title']}")
            md.append("")
            
            # Display structured summary if available
            if p.get("overview") or p.get("method") or p.get("experiments"):
                if p.get("overview"):
                    md.append("**Overview**:")
                    md.append(p["overview"])
                    md.append("")
                if p.get("method"):
                    md.append("**Method**:")
                    md.append(p["method"])
                    md.append("")
                if p.get("experiments"):
                    md.append("**Experiments**:")
                    md.append(p["experiments"])
                    md.append("")
            elif p.get("summary"):
                md.append(p["summary"])
                md.append("")
            
            md.append("---\n")
        return "\n".join(md)

    @staticmethod
    def save(content: str, filename: str) -> Path:
        filepath = OUTPUT_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath
