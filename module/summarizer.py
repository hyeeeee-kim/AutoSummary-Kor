"""LLM-based paper summarization via Ollama with Mistral 7B

Mistral 7B is recommended for RAG systems:
- Better instruction following for structured summaries
- Longer context window (8K tokens)
- Faster inference than larger models
- Optimized for information extraction and summarization

Configure in .env:
  LLM_MODEL=mistral
  LLM_SERVER_URL=http://localhost:11434
"""
import requests
from config.settings import LLM_SERVER_URL, LLM_MODEL, LLM_MAX_TOKENS

class SummaryGenerator:
    def __init__(self):
        self.url = f"{LLM_SERVER_URL.rstrip('/')}/api/generate"
        self.model = LLM_MODEL

    def summarize_paper(self, paper_text: str, paper_title: str = "Paper") -> dict:
        """Structured paper summary: Overview, Method, Experiments (all in English)"""
        
        # Section 1: Overview (10 sentences max - technical focus)
        overview_prompt = f"""Analyze the following academic paper and provide a technical summary.

Paper Title: {paper_title}

Paper Content:
{paper_text}

Instructions: Summarize the paper's overview in no more than 10 sentences. Include:
- Problem statement and research gap that motivates the work
- Core technical contribution and novelty
- Key innovations that distinguish this work from prior art
- Theoretical or practical significance of the contribution
- Method category (e.g., supervised learning, reinforcement learning, generative model, graph neural network)

Requirements:
- Provide only the technical summary without additional explanation or preamble
- Be precise and use domain-specific terminology
- Avoid marketing language; focus on scientific accuracy
- Output must be translated in Korean, and should be maintained in English only for technical terms and model names"""
        
        # Section 2: Method (50 sentences max - highly technical)
        method_prompt = f"""Analyze the following academic paper and provide a detailed technical summary of the methodology.

Paper Title: {paper_title}

Paper Content:
{paper_text}

Instructions: Summarize the proposed methodology in no more than 50 sentences. Include:
- Mathematical formulation and theoretical framework
- Detailed algorithm description or pseudocode
- Architectural design (encoder-decoder, attention mechanisms, convolutional layers, etc.)
- Key technical components and their mathematical specifications
- Loss functions used and optimization strategies employed
- Hyperparameters and implementation details
- Computational complexity analysis (time and space complexity)
- Novel techniques or innovations that distinguish this work from prior art
- Any theoretical guarantees or convergence proofs

Requirements:
- Be mathematically rigorous where applicable
- Use specific technical terms from the paper
- Include notation and formulas where relevant
- Do not exceed 50 sentences
- Output must be translated in Korean, and should be maintained in English only for technical terms and model names"""
        
        # Section 3: Experiments & Results (30 sentences max - technical details)
        experiment_prompt = f"""Analyze the following academic paper and provide a technical summary of the experimental evaluation.

Paper Title: {paper_title}

Paper Content:
{paper_text}

Instructions: Summarize experiments and results in no more than 30 sentences. Include:
- Experimental setup and protocol design
- Datasets used with specific details (size, number of samples, splits, characteristics)
- Baseline methods and comparison models with exact names and parameter settings
- Evaluation metrics used (e.g., accuracy, precision, recall, F1-score, BLEU, ROUGE, AUC, etc.)
- Quantitative results with absolute values and performance improvements (percentage gains)
- Statistical significance testing and confidence intervals if reported
- Ablation study findings showing contribution of each component
- Computational costs and training time comparisons with baselines
- Analysis of failure cases, limitations, and edge cases
- Qualitative analysis or visualization of results

Requirements:
- Provide specific numbers, percentages, and metric values
- Include model names and exact parameter configurations
- Report statistical significance where applicable
- Do not exceed 30 sentences
- Output must be translated in Korean, and should be maintained in English only for technical terms and model names"""
        
        try:
            # Generate Overview
            r1 = requests.post(
                self.url,
                json={"model": self.model, "prompt": overview_prompt, "stream": False},
                timeout=300,
            )
            overview = r1.json().get("response", "").strip()
            
            # Generate Method
            r2 = requests.post(
                self.url,
                json={"model": self.model, "prompt": method_prompt, "stream": False},
                timeout=300,
            )
            method = r2.json().get("response", "").strip()
            
            # Generate Experiments
            r3 = requests.post(
                self.url,
                json={"model": self.model, "prompt": experiment_prompt, "stream": False},
                timeout=300,
            )
            experiments = r3.json().get("response", "").strip()
            
            return {
                "overview": overview or "Failed to generate overview",
                "method": method or "Failed to generate method",
                "experiments": experiments or "Failed to generate experiments",
            }
        except Exception as e:
            error_msg = str(e)
            print(f"\n  ERROR in summarize_paper: {error_msg}\n")
            return {
                "overview": f"Error: {error_msg[:100]}",
                "method": f"Error: {error_msg[:100]}",
                "experiments": f"Error: {error_msg[:100]}",
            }

    def generate(self, title: str, abstract: str, context: str = None) -> str:
        """Generate summary from title and abstract (for conference paper search)"""
        if context:
            prompt = f"""Analyze the following paper and provide a comprehensive technical summary.

Title: {title}

Abstract:
{abstract}

Document Content:
{context}

Instructions:
- Provide a comprehensive summary that covers all key aspects
- Include problem statement, proposed methodology, experimental results, and conclusions
- Use specific technical terminology and metrics where applicable
- Focus on technical precision and accuracy
- Output must be translated in Korean, and should be maintained in English only for technical terms and model names"""
        else:
            prompt = f"""Analyze the following paper and provide an accurate technical summary.

Title: {title}

Abstract:
{abstract}

Instructions:
- Summarize the main technical contributions and methodology
- Include key results and their significance
- Maintain scientific accuracy and precision
- Use domain-specific terminology
- Output must be translated in Korean, and should be maintained in English only for technical terms and model names"""
        
        try:
            r = requests.post(
                self.url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=300,
            )
            response = r.json().get("response", "Summary generation failed").strip()
            return response if response else "Summary generation failed"
        except Exception as e:
            return f"Failed to generate summary: {str(e)[:50]}"
