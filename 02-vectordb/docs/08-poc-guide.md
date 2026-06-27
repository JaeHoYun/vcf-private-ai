# 08 — PoC 가이드

> 4주 PoC 로드맵, 최소 사양, 성공 기준, 핵심 인사이트

기준 버전: VCF 9.1 / DSM 9.1. 사용·운영 상세는 [05 사용](05-usage-rag.md), [06 운영](06-operations.md)을 참조하시기 바랍니다.

---

## 8.1 PoC 가이드

### 8.1.1 PoC 목표

pgvector 기반 벡터 검색의 실효성을 실제 업무 데이터로 검증하되, 최소한의 리소스와 시간으로 빠르게 결과를 확보하는 것이 목표입니다. 4주 안에 "동작하는 RAG 프로토타입"을 만들어 의사결정자에게 시연할 수 있어야 합니다.

### 8.1.2 4주 타임라인 - 본 시나리오는 예제로써 실제 PoC는 환경과 목적에 따라 달라집니다

#### Week 1: 환경 구성 및 데이터 준비

**인프라 구성 (Day 1–2)**
- 기존 VCF 환경에 DSM 어플라이언스 배포 (이미 DSM이 활성화되어 있다면 생략)
- DSM에서 PostgreSQL 인스턴스 프로비저닝 (Standalone으로 시작, PoC이므로 HA 불필요)
- pgvector 확장 활성화: `CREATE EXTENSION vector;`
- 기본 연결 테스트

**데이터 준비 (Day 3–5)**
- 대상 문서 선정: 100–1,000건의 대표 문서(규정, 매뉴얼, FAQ 등) 선정
- 문서 전처리: PDF/Word/HTML에서 텍스트 추출, 적절한 크기로 청킹 (500–1,000 토큰 권장)
- 임베딩 모델 선정: 상용 API(OpenAI text-embedding-3-small)로 빠르게 시작하거나, 로컬 모델(bge-m3 또는 multilingual-e5-large)로 데이터 외부 전송 없이 처리

#### Week 2: 벡터 적재 및 검색 검증

**벡터 적재 (Day 6–7)**
- 청킹된 문서를 임베딩 모델로 벡터화
- pgvector 테이블에 적재 (content + metadata + embedding)
- HNSW 인덱스 생성

```sql
-- PoC용 테이블 생성 예시
CREATE TABLE poc_documents (
    id bigserial PRIMARY KEY,
    title text,
    content text,
    source text,
    category text,
    created_at timestamptz DEFAULT now(),
    embedding vector(1536)
);

-- HNSW 인덱스 생성
CREATE INDEX idx_poc_embedding ON poc_documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);
```

**검색 품질 검증 (Day 8–10)**
- 20–50개의 테스트 질문 작성 (실제 사용자가 물을 법한 질문)
- 각 질문에 대한 기대 답변 문서를 사전 태깅 (Ground Truth)
- pgvector 검색 결과와 Ground Truth를 비교하여 Recall 측정
- ef_search 파라미터 조정, 필터 조건 추가 등으로 검색 품질 최적화
- 검색 지연 시간(Latency) 측정 — 100ms 미만 목표

#### Week 3: RAG 파이프라인 구축

**RAG 애플리케이션 (Day 11–14)**
- LangChain 또는 LlamaIndex 기반 RAG 파이프라인 구성

```python
# LangChain RAG 파이프라인 예시
from langchain_postgres import PGVector
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA

# pgvector 연결
vector_store = PGVector(
    embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
    collection_name="poc_documents",
    connection="postgresql+psycopg://user:pass@dsm-pg-host:5432/pocdb",
)

# RAG 체인 구성
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-4o"),  # 또는 온프레미스 LLM
    retriever=vector_store.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 5}
    ),
    return_source_documents=True,
)

# 질의
result = qa_chain.invoke({"query": "투자 상품 불완전판매 시 고객 보상 절차는?"})
print(result["result"])
print(result["source_documents"])
```

- 간단한 웹 UI(Gradio 또는 Streamlit) 구성
- PAIS가 구성되어 있다면 Agent Builder에서 직접 에이전트 구성도 가능

**품질 평가 (Day 14–15)**
- 테스트 질문 세트로 RAG 답변 품질 평가
- 답변의 정확성, 관련성, 출처 제시 여부를 확인
- 환각(Hallucination) 발생 빈도 측정

#### Week 4: 성능 테스트 및 결과 보고

**성능 테스트 (Day 16–18)**
- 동시 사용자 시뮬레이션: 10–50명 동시 쿼리
- 응답 시간 측정: p50, p95, p99 Latency
- 처리량 측정: QPS (Queries Per Second)
- 리소스 사용량 모니터링: CPU, 메모리, 디스크 I/O

**결과 보고서 작성 (Day 19–20)**
- PoC 결과 요약: 검색 품질(Recall), 응답 시간, 답변 정확도
- 프로덕션 전환 시 아키텍처 제안: HA 구성, 리소스 사이징
- TCO 비교: 전용 벡터 DB 대안 대비 VCF DSM 비용 이점
- 의사결정자 시연 준비

### 8.1.3 PoC 인프라 최소 사양

| 컴포넌트 | 사양 | 비고 |
|---|---|---|
| PostgreSQL VM | 4 vCPU, 16GB RAM, 200GB SSD | DSM에서 프로비저닝 |
| 임베딩/LLM 처리 | 클라우드 API 사용 시 별도 GPU 불필요 | 온프레미스 LLM 시 GPU VM 필요 |
| RAG 애플리케이션 VM | 2 vCPU, 8GB RAM, 50GB | LangChain/Streamlit 실행 |
| 네트워크 | DSM PostgreSQL ↔ RAG App VM 간 통신 | NSX 규칙 확인 |

PoC에서는 외부 LLM API(OpenAI, Anthropic)를 사용하여 GPU 인프라 없이도 빠르게 검증할 수 있습니다. 프로덕션에서 데이터 주권이 요구되면 PAIS Model Runtime으로 전환합니다.

### 8.1.4 PoC 성공 기준

| 지표 | 목표값 | 측정 방법 |
|---|---|---|
| 검색 Recall@5 | 85% 이상 | Ground Truth 대비 상위 5개 결과 중 정답 포함 비율 |
| 검색 Latency (p95) | 100ms 이하 | pgvector 쿼리 단독 측정 |
| RAG 답변 정확도 | 80% 이상 | 테스트 질문 세트 기반 사람 평가 |
| 환각율 | 10% 이하 | 출처 없는 답변 또는 사실과 다른 답변 비율 |
| 엔드투엔드 응답 시간 | 5초 이하 | 질문 입력 → 답변 표시 |

---

## 8.2 핵심 인사이트 요약

### 8.2.1 전체 가이드를 관통하는 세 가지 메시지

**1. Vector DB는 "새로운 DB"가 아니라 "기존 DB의 새로운 기능"이다**

Vector 검색은 AI 시대의 새로운 요구사항이지만, 이를 위해 반드시 새로운 전용 데이터베이스를 도입해야 하는 것은 아닙니다. PostgreSQL의 pgvector 확장은 30년 검증된 관계형 DB에 벡터 검색을 추가하는 것이므로, 기존의 운영 역량, 도구, 인력, 보안 체계를 그대로 활용할 수 있습니다. 엔터프라이즈 AI 워크로드의 80%는 pgvector로 충분히 대응됩니다.

**2. "벡터만 저장하는 DB"는 비효율적이다. 벡터와 데이터가 함께 있어야 한다**

현실의 AI 애플리케이션은 벡터 유사도 검색만으로 동작하지 않습니다. 메타데이터 필터링, 권한 제어, 비즈니스 로직 적용이 필수적이며, 이를 위해 벡터 DB + 관계형 DB를 이중으로 운영하면 동기화 문제, 운영 복잡성, 비용이 상당히 늘어납니다. pgvector는 벡터와 관계형 데이터를 하나의 SQL 쿼리로 통합 처리하여 이 문제를 원천 해소합니다.

**3. VCF + DSM은 pgvector를 "확장 설치"에서 "관리형 서비스"로 격상시킨다**

pgvector의 기술적 우수성은 DSM의 자동화된 라이프사이클 관리와 결합될 때 엔터프라이즈 프로덕션 품질에 도달합니다. 프로비저닝 자동화, HA 클러스터, 자동 백업/PITR, 통합 모니터링, 보안 하드닝이 모두 포함되며, VCF의 vSAN, NSX, VCF Operations와의 통합이 전체 인프라의 일관된 운영을 보장합니다. 여기에 Private AI Services(PAIS)가 더해지면 모델 서빙부터 지식 기반 구축, 에이전트 빌더까지 엔드투엔드 RAG 파이프라인이 프라이빗 클라우드에서 완성됩니다.

### 8.2.2 의사결정 요약

| 도입 상황 | 권장 접근 |
|---|---|
| VCF를 이미 사용 중이고 AI 도입을 검토 중 | **DSM + pgvector로 즉시 시작**. PoC 가능 |
| 금융/의료 등 데이터 주권 필수 | **VCF + DSM + PAIS**. 온프레미스에서 풀스택 RAG를 제공하는 플랫폼 (NVIDIA AI Enterprise 라이선스 별도 필요) |
| 벡터 수 1,000만 이하, 관계형 데이터와 통합 필요 | **pgvector 최적 구간**. 전용 벡터 DB 대비 60–80% TCO 절감 |
| 수십억 벡터 + 수천 QPS 요구 | 전용 벡터 DB(Milvus) 검토. 단, 이런 규모의 워크로드는 극소수 |

---
[← 이전: 07 산업 도입 시나리오](07-scenarios.md) · [목차](../README.md) · [다음: A1 Vector Database 경쟁 비교 →](../appendix/A1-vectordb-comparison.md)
