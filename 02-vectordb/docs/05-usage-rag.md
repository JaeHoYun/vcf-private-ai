# 05 — 사용 및 RAG 구성 (Day-1 / Day-2)

> pgvector 사용법과 PAIS 기반 RAG 파이프라인 구성

기준 버전: DSM 9.1(pgvector 0.8.0 번들) / PAIS 2.1. pgvector 심층 개념은 02 기초 문서를 참조합니다.

---

## 5.1 pgvector 기본 사용

### 테이블 및 인덱스 생성

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE documents (
    id        bigserial PRIMARY KEY,
    content   text,
    metadata  jsonb,
    embedding vector(1536)   -- OpenAI text-embedding-3-small 기준
);

-- HNSW 인덱스 (Cosine Distance)
SET maintenance_work_mem = '4GB';
SET max_parallel_maintenance_workers = 7;

CREATE INDEX idx_docs_embedding ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);
```

### 유사도 검색

```sql
-- 상위 5개 (Cosine Distance)
SELECT id, content, embedding <=> '[쿼리벡터]' AS distance
FROM documents
ORDER BY embedding <=> '[쿼리벡터]'
LIMIT 5;

-- 검색 정밀도 조정 (기본 40)
SET hnsw.ef_search = 100;
```

거리 연산자는 텍스트 임베딩에 Cosine(`<=>`)을 기본 사용하고, 사전 정규화된 벡터는 Inner Product(`<#>`)가 가장 빠릅니다.

### 하이브리드 검색 (벡터 + 메타데이터 + JOIN)

pgvector의 핵심 강점은 벡터 검색과 관계형 조건을 단일 SQL로 처리하는 것입니다.

```sql
SET hnsw.iterative_scan = relaxed_order;   -- 0.8.0+ overfiltering 완화

SELECT c.id, c.content, c.embedding <=> $query_vector AS distance
FROM complaints c
JOIN customers cu ON c.customer_id = cu.id
WHERE cu.grade = 'VIP'
  AND c.created_at >= NOW() - INTERVAL '30 days'
ORDER BY c.embedding <=> $query_vector
LIMIT 10;
```

Iterative Index Scan(0.8.0)은 WHERE 필터로 결과가 부족할 때 인덱스를 추가 스캔해 충분한 결과를 확보합니다. 멀티테넌트(tenant_id), 카테고리, 시간 범위 필터가 결합된 실제 워크로드에서 중요합니다.

```sql
-- HNSW
SET hnsw.iterative_scan = relaxed_order;   -- 또는 strict_order
SET hnsw.max_scan_tuples = 10000;

-- IVFFlat
SET ivfflat.iterative_scan = on;
SET ivfflat.max_probes = 100;
```

---

## 5.2 애플리케이션 연동

| 프레임워크 | 연동 방식 |
|---|---|
| LangChain | `langchain-postgres`, PGVector 클래스 |
| LlamaIndex | PGVectorStore 내장 |
| Python | `pgvector` PyPI (psycopg3, SQLAlchemy, Django) |
| Java/Spring | JDBC + pgvector 타입, Spring AI |
| .NET | Npgsql + pgvector 타입 |

LangChain 예시

```python
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings

vector_store = PGVector(
    embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
    collection_name="my_docs",
    connection="postgresql+psycopg://user:pass@dsm-pg-host:5432/dbname",
    use_jsonb=True,
)

vector_store.add_documents(documents)
retriever = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": 5})
```

커넥션은 PgBouncer 등 풀러를 `pool_mode=transaction`으로 사용하고, 동시 접속 100 이상이면 풀링을 필수 적용합니다.

---

## 5.3 PAIS 기반 RAG 파이프라인

PAIS는 모델 서빙(Model Runtime), 지식 기반 구축(Data Indexing & Retrieval), 에이전트(Agent Builder)와 DSM(pgvector)을 묶어 프라이빗 RAG를 구성합니다.

| 서비스 | 역할 | pgvector 연관 |
|---|---|---|
| Model Gallery | 모델 거버넌스(Harbor 레지스트리 기반) | 간접 |
| Model Runtime | 추론 서빙(vLLM completion, Infinity embedding, NVIDIA NIM 연동) | 임베딩 모델이 텍스트를 벡터로 변환 |
| Data Indexing & Retrieval | 지식 기반 구축(소스 연결 to 청킹 to 임베딩 to 저장 to 갱신) | pgvector가 벡터 저장소 |
| Agent Builder | RAG 에이전트 구성(노코드) | 에이전트가 pgvector에서 컨텍스트 검색 |
| DSM (Vector DB) | PostgreSQL + pgvector 프로비저닝/관리 | 핵심 인프라 |

### Phase 1: 지식 기반 구축 (오프라인, 주기적)

1. Data Indexing & Retrieval에서 데이터 소스(Google Drive, Confluence, SharePoint, S3) 연결
2. 문서 청킹 (500-1,000 토큰 권장, 구조에 따라 조정)
3. Model Runtime의 임베딩 모델로 각 chunk 벡터화
4. DSM이 관리하는 PostgreSQL + pgvector에 원문·메타데이터·벡터 저장
5. 갱신 정책 설정(스케줄/온디맨드 재인덱싱)

### Phase 2: 질의 응답 (실시간)

사용자 질문 → Agent Builder 에이전트 수신 → 임베딩 모델이 질문 벡터화 → pgvector 유사도 검색으로 관련 chunk 추출 → (선택) Re-ranker 재정렬 → LLM이 컨텍스트 기반 답변 생성 → 출처와 함께 응답

### 임베딩 모델 배포 (Model Runtime)

- 한국어 환경은 다국어 임베딩(bge-m3, multilingual-e5-large) 또는 한국어 대응 모델 검토
- LLM은 vLLM, 임베딩은 Infinity 기반으로 서빙하며 NVIDIA NIM과 연동 가능
- GPU 모델 추론·임베딩 시 NVIDIA AI Enterprise 라이선스와 GPU 하드웨어 필요. PoC 단계는 외부 API(OpenAI, Cohere)로 GPU 없이 검증 가능

출처: Private AI Services Detailed Design(Broadcom TechDocs); Building your GenAI Agents on VCF with Private AI Services(VCF Blog).

### 지원 소스와 커스텀 인제스트 경계

PAIS Data Indexing & Retrieval가 관리형(네이티브)으로 처리하는 범위와, 설계자가 별도 파이프라인을 구성해야 하는 범위를 구분합니다. 네이티브 데이터 소스 커넥터는 정확히 4종이며, 소스 유형은 지식 기반 생성 후 변경할 수 없습니다. 커넥터별 입력 정보는 Google Drive=폴더 URL과 서비스 계정 JSON 키, Confluence=사이트 URL과 스페이스 키 또는 페이지 ID, SharePoint=사이트 URL(하위 사이트·폴더 포함), S3=엔드포인트 URL과 자격증명, 버킷입니다. 관리형 파이프라인이 인식하는 문서 형식은 PDF, DOCX, PPTX, HTML, Markdown, CSV, Plaintext와 Google 네이티브 Docs/Sheets/Slides(2.1 신규)입니다.

| 소스/형식 | 관리형 커넥터 지원 | 비고 |
|---|---|---|
| Google Drive (폴더) | 지원 | 폴더 URL + 서비스 계정 JSON 키 |
| Confluence (스페이스/페이지) | 지원 | 사이트 URL + 스페이스 키 또는 페이지 ID |
| SharePoint (사이트) | 지원 | 사이트 URL(하위 사이트·폴더 포함) |
| S3 호환 스토리지 (버킷) | 지원 | 엔드포인트 URL + 자격증명 + 버킷 |
| PDF / DOCX / PPTX / HTML / Markdown / CSV / Plaintext | 지원(위 4종 소스에 한함) | 관리형 파이프라인이 파싱·청킹·임베딩 |
| Google Docs / Sheets / Slides (네이티브) | 지원(2.1 신규) | Google Drive 커넥터 경유 |
| 웹/URL 크롤 | 미지원(커스텀 경로) | 네이티브 크롤 커넥터 없음 |
| 데이터베이스(RDB 등) | 미지원(커스텀 경로) | 네이티브 DB 커넥터 없음 |
| 범용 파일 서버/직접 업로드 | 미지원(커스텀 경로) | 네이티브 파일 업로드 커넥터 없음 |
| 레거시·기타 외부 시스템 | 미지원(커스텀 경로) | 4종 밖 소스 |
| 미지원 문서 형식 | 미지원(커스텀 경로) | 위 형식 목록 밖 |

인덱스 갱신은 지식 기반별로 설정하며, 소스 변경 수집 주기를 정하는 자동 스케줄 모드 또는 GPU 자원 절약을 위한 수동 새로고침 중에서 선택합니다(구체적 주기 값은 공식 문서에 열거되어 있지 않습니다). 구축된 지식 기반은 MCP(Model Context Protocol) 서버로 노출되어, 에이전트가 검색 도구로 활용합니다.

관리형 vs 커스텀 결정

- 4종 관리형으로 충분한 경우: 지식 원천이 Google Drive·Confluence·SharePoint·S3 안에 있고, 문서가 위 지원 형식에 해당하며, 표준 갱신 주기로 운영 가능한 경우입니다. 별도 코드 없이 소스 연결·청킹·임베딩·저장·갱신이 제품 기능으로 처리됩니다.
- 커스텀 파이프라인이 필요한 경우: 웹/URL 크롤, 데이터베이스, 범용 파일 서버, 레거시 외부 시스템 등 4종 밖 소스이거나, 지원 목록 밖 형식을 다뤄야 하는 경우입니다. 이때는 PAIS의 OpenAI 호환 임베딩 엔드포인트로 임베딩을 생성한 뒤, 직접 운영하는 pgvector에 자체 스키마로 적재하는 경로를 설계합니다. 커스텀 경로의 추출·청킹·적재 설계 상세는 시리즈 ④를 참조합니다([VCF RAG Reference Architecture — Ingestion & Indexing](../../04-rag/docs/02-ingestion-indexing.md)).

> 주의: 임베딩 엔드포인트는 제품 기능으로 존재하나, 직접 pgvector 적재 경로는 Broadcom 공식 문서가 규정한 제품 API가 아니라 설계자 책임의 아키텍처 패턴입니다(별도 표준 인제스트 REST API는 문서화되어 있지 않음).

출처: [Add a Data Source for a Knowledge Base](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-context-to-model-responses-by-using-knowledge-bases/add-a-data-source-for-a-knowledge-base.html); [Create a Knowledge Base with Linked Data Sources](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-context-to-model-responses-by-using-knowledge-bases/create-a-knowledge-base-with-linked-data-sources.html); [Running Completion or Embedding Models by Using Model Endpoints](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/deploying-model-endpoints.html); [PAIS Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html).

---

## 5.4 검색 품질 점검

- Recall@k: Ground Truth 대비 상위 k개 결과의 정답 포함률
- `hnsw.ef_search` 상향으로 recall 개선(속도 트레이드오프)
- 필터 결합 시 Iterative Scan 활성화로 overfiltering 완화
- 임베딩 모델 교체 시 전체 재임베딩 필요(05 운영 문서 재임베딩 전략 참조)

품질·성능 측정 절차는 07 PoC 가이드의 검증 단계를 활용합니다.

---

## 출처

| 자료 | URL |
|---|---|
| pgvector GitHub | https://github.com/pgvector/pgvector |
| pgvector 0.8.0 릴리스 노트 | https://www.postgresql.org/about/news/pgvector-080-released-2952/ |
| LangChain PGVector 연동 | https://python.langchain.com/docs/integrations/vectorstores/pgvector/ |
| Private AI Services Detailed Design | https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html |
| Building your GenAI Agents on VCF with PAIS | https://blogs.vmware.com/cloud-foundation/2025/08/26/vmware-private-ai-services-demo/ |

---
[← 이전: 04 배포 (Day-0 / Day-1)](04-deployment.md) · [목차](../README.md) · [다음: 06 운영 (Day-2) →](06-operations.md)
