# 학술논문 요약 시스템

DBLP에서 학술논문을 스크래핑하고, 검색 가능한 벡터 데이터베이스를 구축한 후 Ollama LLM을 사용하여 AI 기반 요약을 생성하는 모듈식 Python 파이프라인입니다.

---

## 파이프라인 개요

시스템은 각 단계가 독립적이며 순차적으로 실행할 수 있는 4단계 모듈식 파이프라인으로 작동합니다.

### 단계 1: 데이터베이스 구축/재구축
- DBLP에서 활성화된 학회의 논문 스크래핑
- 논문 제목, 초록(가능한 경우), 링크 가져오기
- SQLite 데이터베이스에 중복 제거하여 저장
- 제목 해시(MD5)를 기반으로 중복 감지

### 단계 2: 검색 인덱스 구축
- 데이터베이스에서 모든 논문을 메모리에 로드
- sentence-transformers(UAE-Large-V1 모델)를 사용하여 벡터 임베딩 생성
- 임베딩을 Chroma 벡터 데이터베이스에 저장
- 키워드 매칭을 위한 BM25 sparse index 구축

### 단계 3: 논문 검색
- 하이브리드 검색 수행(BM25 sparse index 0.3 + dense embedding 0.7)
- 결합 점수로 순위가 지정된 상위 50개 결과 반환
- 관련성 점수와 링크와 함께 결과 표시

### 단계 4: 요약 생성
- 사용자가 지정한 디렉토리에서 PDF 파일 읽기
- PDF 파일에서 텍스트 추출
- 각 PDF에 대해 Ollama LLM을 사용하여 AI 기반 요약 생성
- 요약 생성: 개요, 방법, 실험
- `data/output/`에 자동으로 마크다운 파일(`summary_pdf_[timestamp].md`) 생성
- **파일명을 논문 제목으로 사용**

---

## 설치 및 설정

### 필수 요구사항
- Python 3.8+
- Conda (Anaconda 또는 Miniconda)
- Ollama (LLM 기능용)

### 환경 설정

1. **Conda 환경 생성**
```bash
conda create -n paper_summary python=3.10
conda activate paper_summary
```

2. **종속성 설치**
```bash
pip install -r requirements.txt
```

### 구성 파일

#### 1. `.env` 파일 생성
`.env.example`을 `.env`로 복사하고 설정을 구성

```bash
cp .env.example .env
```

`.env` 세팅 (하단 환경 구성 섹션 참조)

#### 2. `conferences.yaml` 구성
`config/conferences.yaml`을 편집하여 스크래핑할 학회를 선택(하단 학회 구성 섹션 참조)

---

## 애플리케이션 실행

### 기본 사용법

```bash
python main.py
```

원하는 Step을 선택 가능한 대화형 메뉴 구성

### 프로그래밍 방식으로 특정 단계 실행

```python
from module.pipeline import Pipeline

pipeline = Pipeline()

# Step 1: Build database
pipeline.run_step_1_build_db()

# Step 2: Build search index
pipeline.run_step_2_build_index()

# Step 3: Search
pipeline.run_step_3_search()

# Step 4: Summarize from PDFs (generates markdown automatically)
pipeline.run_step_4_summarize()
# Prompts: "Enter directory path containing PDF files: "
# Output: Creates summary_pdf_[timestamp].md in data/output/
```

### PDF 처리 워크플로우

```bash
Select step (0-5): 4

Enter directory path containing PDF files: D:\papers

[Processing PDFs with streaming output]
  Processing PDFs: 100%|████████| 10/10 [02:30<00:00, 15.00s/it]

OK: Processed 10 PDFs
Output: data/output/summary_pdf_1777856449.md
```

**주요 기능**:
- 마크다운 파일은 처리 중에 직접 작성됨(메모리 버퍼링 없음)
- 각 PDF는 처리된 후 즉시 파일에 작성됨
- PDF 개수에 관계없이 메모리 사용량이 일정함
- 완료 시 출력 경로 표시

---

## 환경 구성(.env)

### 필수 설정

#### HF_TOKEN (선택사항)
```
HF_TOKEN=your_huggingface_token_here
```
- HuggingFace 모델에 접근하기 위해 사용
- 필요하지 않으면 플레이스홀더로 남겨도 괜찮음

#### LLM 구성
```
LLM_SERVER_URL=http://localhost:11434
LLM_MODEL=mistral
```

- **LLM_SERVER_URL**: Ollama API가 실행 중인 URL
  - 기본값: `http://localhost:11434` (로컬 Ollama)
  - 원격 서버로 변경 가능: `http://remote-host:11434`
  
- **LLM_MODEL**: 요약에 사용할 모델
  - 기본값: `mistral`
  - 대체 옵션: `llama2`, `neural-chat`, `phi` 등
  - Ollama에서 사용 가능해야 함

#### 임베딩 모델 구성
```
EMBEDDING_MODEL=UAE-Large-V1
```

- 논문 임베딩 생성을 위한 모델
- 기본값: `UAE-Large-V1` (WhereIsAI/UAE-Large-V1)
- 내부적으로 HuggingFace 모델 식별자에 매핑됨

### 예제 .env 파일

```python
# 이 파일을 .env로 복사하고 실제 값으로 채우기

HF_TOKEN=your_huggingface_token_here

LLM_SERVER_URL=http://localhost:11434
LLM_MODEL=mistral

EMBEDDING_MODEL=UAE-Large-V1

CHROMA_TELEMETRY_DISABLED=True # 유지
```

---

## 학회 구성(conferences.yaml)

### 구조

`config/conferences.yaml` 파일은 스크래핑할 학술 학회를 정의합니다:

```yaml
conferences:
  conference_key:
    name: "학회 전체 이름 YYYY"
    url: "https://dblp.org/db/conf/xxx/xxxYYYY.html"
    enabled: true/false
```

### 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `conference_key` | 문자열 | 고유 식별자(내부적으로 사용, 표시되지 않음) |
| `name` | 문자열 | 연도가 포함된 전체 학회명(사용자에게 표시) |
| `url` | 문자열 | DBLP 학회 페이지 URL |
| `enabled` | 부울 | 스크래핑에 포함하려면 `true`, 건너뛰려면 `false` |

### 기존 학회 수정

학회를 스크래핑에서 제외하려면 `enabled`를 `false`로 변경

```yaml
neurips:
  name: "NeurIPS 2024"
  url: "https://dblp.org/db/conf/nips/neurips2024.html"
  enabled: false  # Skip
```

### 새 학회 추가

1. 학회의 DBLP 페이지 찾기
   - https://dblp.org/ 방문
   - 학회명 검색
   - 특정 연도의 URL 가져오기

2. `config/conferences.yaml`에 추가

```yaml
your_new_conference:
  name: "학회명 YYYY"
  url: "https://dblp.org/db/conf/xxx/xxxYYYY.html"
  enabled: true
```

---

## LLM 설정 및 구성

### Ollama 설치

#### Windows
1. https://ollama.ai/download에서 다운로드
2. 설치 프로그램 실행
3. Ollama가 백그라운드 서비스로 시작됨

#### macOS
1. https://ollama.ai/download에서 다운로드
2. `.dmg` 파일 실행
3. Ollama가 서비스로 실행됨

#### Linux
```bash
curl https://ollama.ai/install.sh | sh
```

### LLM 서버 시작

#### 방법 1: 자동(권장)
Ollama는 설치 후 기본적으로 백그라운드 서비스로 실행됩니다.
실행 중인지 확인:
```bash
curl http://localhost:11434/api/tags
```

#### 방법 2: 수동 시작
```bash
# 터미널 1: Ollama 서버 시작
ollama serve

# 터미널 2: 모델 풀 및 실행
ollama run mistral
```

### 사용 가능한 모델

사용 가능한 모델 확인:
```bash
ollama list
```

새 모델 풀:
```bash
ollama pull mistral      # 더 빠름, 대부분의 작업에 적합
ollama pull llama2       # 기본값, 균형잡힌 성능
ollama pull neural-chat  # 대화형, 더 작은 크기
```

### LLM 모델 변경

다른 모델을 사용하려면 `.env`를 업데이트

```
LLM_MODEL=mistral
```

모델이 Ollama에서 사용 가능한지 확인
```bash
ollama pull mistral
```

---

## LLM 프롬프트 사용자 지정

### 프롬프트 저장 위치

프롬프트는 `module/summarizer.py`의 `SummaryGenerator` 클래스에서 정의됩니다.

### 현재 요약 형식

기본 요약은 3부로 생성: **개요, 방법, 실험**

### 프롬프트 수정

#### 프롬프트 템플릿 편집

`module/summarizer.py`

```python
def generate(self, title: str, abstract: str, context: str = None) -> str:
    """Generate summary from title and abstract"""
    prompt = f"""
Please provide a concise summary of this paper in 3 parts:

Title: {title}
Abstract: {abstract}

Summary format:
1. Overview: What is this paper about?
2. Method: How did they approach the problem?
3. Experiments: What experiments were conducted?

Keep each section to 2-3 sentences maximum.
"""
    # ... codes
```

### LLM 매개변수 조정

`summarizer.py` API 호출

```python
response = requests.post(
    f"{self.server_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "temperature": 0.7,        # 0.0 = deterministic, 1.0 = creative
        "num_predict": 500,         # Maximum tokens in response
        "top_p": 0.95,              # Sampling
        "top_k": 40,                # Top-k sampling
    }
)
```

---

## 프로젝트 구조

```
paper_summary/
├── main.py                 # 진입점
├── requirements.txt        # Python 종속성
├── .env                    # 환경 변수 (추가 설정 필요)
├── .gitignore             
├── README.md              
│
├── config/
│   ├── __init__.py
│   ├── settings.py        
│   └── conferences.yaml   # 학회 설정
│
├── module/
│   ├── database.py        # SQLite 데이터베이스 작업
│   ├── scrapers.py        # DBLP 웹 스크래핑
│   ├── rag.py             # 벡터 검색 및 하이브리드 검색
│   ├── summarizer.py      # LLM 기반 요약
│   ├── pdf_processor.py   # PDF 텍스트 추출 및 처리
│   ├── outputs.py         # 마크다운 내보내기
│   └── pipeline.py        # 메인 오케스트레이터
│
└── data/
    ├── papers.db          # SQLite 데이터베이스
    ├── chroma/            # 벡터 데이터베이스 저장소
    └── output/            # 생성된 마크다운 파일
```

---

## 참고사항

- 모든 데이터는 `data/` 디렉토리에 로컬로 저장됨
- 데이터베이스는 SQLite 형식(Portable, 서버 불필요)
- 학회 스크래핑은 DBLP 속도 제한 준수(재시도 로직 포함)
- LLM 프롬프트는 코드 변경 없이 사용자 지정 가능(`summarizer.py` 편집)
