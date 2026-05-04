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
        """Structured paper summary: Overview, Method, Experiments"""
        
        # Section 1: Overview (10 sentences max - technical focus)
        overview_prompt = f"""논문 제목: {paper_title}

논문 내용:
{paper_text}

위 논문의 개요를 한국어로만 10문장 이내로 설명하시오.
포함할 내용: 문제 정의, 핵심 기여, 이론적 중요성, 방법론 요약

한국어만 사용. 기술명(GPT, Transformer 등)만 영어. 프롬프트나 지시사항 절대 복사 금지."""
        
        # Section 2: Method (50 sentences max - highly technical)
        method_prompt = f"""논문 제목: {paper_title}

논문 내용:
{paper_text}

위 논문의 방법론을 한국어로만 50문장 이내로 설명하시오.
포함할 내용: 수학적 공식화, 알고리즘, 아키텍처, 손실함수, 최적화, 하이퍼파라미터, 계산복잡도, 혁신기법, 수렴증명

한국어만 사용. 기술명(Adam, SGD, ReLU 등)만 영어. 프롬프트나 지시사항 절대 복사 금지."""
        
        # Section 3: Experiments & Results (30 sentences max - technical details)
        experiment_prompt = f"""논문 제목: {paper_title}

논문 내용:
{paper_text}

위 논문의 실험 평가를 한국어로만 30문장 이내로 설명하시오.
포함할 내용: 실험설정, 데이터셋, 기준선/비교모델, 평가지표, 정량적결과, 통계유의성, 절제연구, 계산비용, 실패사례, 시각화

한국어만 사용. 기술명/모델명(데이터셋명 등)만 영어. 프롬프트나 지시사항 절대 복사 금지."""
        
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
            prompt = f"""제목: {title}

초록:
{abstract}

문서 내용:
{context}

위 논문을 한국어로만 포괄적으로 요약하시오.
포함: 문제 진술, 방법론, 결과, 결론, 기술적 기여도

한국어만 사용. 기술명(모델명 등)만 영어. 프롬프트 절대 복사 금지."""
        else:
            prompt = f"""제목: {title}

초록:
{abstract}

위 논문을 한국어로만 정확하게 요약하시오.
포함: 기술적 기여도, 방법론, 결과와 중요성

한국어만 사용. 기술명(모델명 등)만 영어. 프롬프트 절대 복사 금지."""
        
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
