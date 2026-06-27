# 02 — Vector Database & pgvector 기초

> Vector DB 기초 개념부터 pgvector 심층 분석(아키텍처, 인덱스, 성능, 튜닝)까지

기준 버전: DSM(Data Services Manager) 9.1 (pgvector 0.8.0 번들). 대상 독자: Private AI Foundation으로 AI Agent 서비스를 제공하려는 인프라/플랫폼 팀.

---

## 2.1 Vector Database 기초 개념

### 2.1.1 왜 Vector Database가 필요한가

기존 관계형 데이터베이스(RDBMS)는 정형 데이터를 행과 열로 저장하고, **정확한 값 매칭(exact match)** 기반으로 검색합니다. "고객번호 = 10032"처럼 명확한 조건이 있어야 결과를 반환할 수 있습니다.

AI/ML 워크로드에서는 텍스트·이미지·음성·영상 같은 **비정형(unstructured) 데이터**가 엔터프라이즈 데이터의 80% 이상을 차지하며, "의미적으로 유사한 것"을 찾는 검색 수요가 빠르게 늘고 있습니다. 예를 들어 "서버 장애 대응 절차"를 검색했을 때, "시스템 다운 복구 가이드"라는 문서도 함께 찾아주는 것이 **의미 기반 검색(semantic search)** 입니다.

Vector Database는 이 문제를 해결하기 위해 설계된 데이터 저장/검색 시스템입니다.

### 2.1.2 Vector Embedding이란

Embedding은 텍스트, 이미지 등 비정형 데이터를 **고차원 숫자 배열(벡터)** 로 변환한 것입니다.

- 입력: "VMware vSAN은 HCI 스토리지 솔루션이다"
- 출력: `[0.023, -0.187, 0.442, ..., 0.091]` (수백–수천 차원의 실수 배열)

이 변환은 사전 학습된 ML 모델(Embedding Model)이 수행합니다. 대표적인 모델은 다음과 같습니다.

| Embedding Model | 제공사 | 차원 수 | 특징 |
|---|---|---|---|
| text-embedding-3-small | OpenAI | 1,536 (기본값, 차원 축소 옵션 지원) | 범용 텍스트, 상용 API |
| text-embedding-3-large | OpenAI | 3,072 (기본값, 차원 축소 옵션 지원) | 고정밀, 비용 높음 |
| all-MiniLM-L6-v2 | Hugging Face (오픈소스) | 384 | 경량, 로컬 실행 가능 |
| bge-large-en-v1.5 | BAAI (오픈소스) | 1,024 | 오픈소스 최상위 성능 |
| Cohere embed-v3 | Cohere | 1,024 | 다국어 지원 |

핵심 원리: **의미가 유사한 데이터일수록 벡터 공간에서 서로 가까이 위치**합니다. "고양이"와 "kitty"의 벡터는 가깝고, "고양이"와 "서버"의 벡터는 멉니다.

### 2.1.3 전통 DB vs Vector DB — 검색 방식의 근본적 차이

| 비교 항목 | 전통 RDBMS | Vector Database |
|---|---|---|
| **검색 방식** | 키워드 정확 매칭 (WHERE col = 'value') | 유사도 기반 근접 탐색 (Nearest Neighbor) |
| **데이터 타입** | 정형 (숫자, 문자열, 날짜) | 고차원 벡터 (수백–수천 차원 실수 배열) |
| **인덱스 구조** | B-tree, Hash | HNSW, IVFFlat, DiskANN |
| **질의 결과** | 조건에 정확히 일치하는 행 | 유사도 순으로 정렬된 상위 N개 결과 |
| **대표 연산자** | =, >, <, LIKE | <-> (L2 거리), <=> (Cosine 거리), <#> (내적) |
| **활용 분야** | 트랜잭션, 리포팅 | 의미 검색, 추천, RAG, 이상탐지 |

### 2.1.4 Vector DB의 주요 활용 시나리오

**RAG (Retrieval-Augmented Generation)**
LLM이 학습하지 않은 사내 문서, 규정, 매뉴얼 등을 벡터로 저장해 두고, 사용자 질문 시 관련 문서를 검색하여 LLM에 컨텍스트로 전달하는 방식입니다. 현재 엔터프라이즈 AI 적용의 가장 대표적인 패턴이며, Vector DB 시장 성장의 핵심 동인입니다. Vector DB 시장은 빠르게 성장 중이며, 리서치 기관에 따라 2024년 기준 $1.5B–$4.3B, 2030년대 초반까지 연평균 20% 이상 성장이 예상됩니다 (출처: MarketsandMarkets, Grand View Research 등 — 기관마다 시장 정의와 추정치에 차이가 있음).

**의미 기반 문서 검색 (Semantic Search)**
키워드가 달라도 의미가 같으면 검색되는 차세대 검색 엔진. 사내 지식 관리, 법률 문서 검색, 기술 문서 검색 등에 적용됩니다.

**추천 시스템 (Recommendation)**
사용자 행동이나 상품 속성을 벡터화하여 유사 상품/콘텐츠를 추천합니다. 유통, 미디어, 이커머스 분야에서 활용됩니다.

**이상 탐지 (Anomaly Detection)**
정상 패턴을 벡터로 학습한 뒤, 새로운 데이터가 정상 벡터 군집에서 벗어나는 정도를 측정하여 이상을 탐지합니다. 금융 이상거래, IoT 센서 모니터링 등에 적용됩니다.

**이미지/멀티모달 검색**
이미지를 벡터화하여 유사 이미지를 검색하거나, 텍스트로 이미지를 검색하는 크로스모달 검색에 활용됩니다.

### 2.1.5 핵심 용어 정리

| 용어 | 설명 |
|---|---|
| **Embedding** | 비정형 데이터를 고차원 벡터로 변환한 수치 표현 |
| **Dimension** | 벡터의 차원 수. 모델에 따라 384 – 3,072 차원이 일반적 |
| **Similarity Search** | 쿼리 벡터와 가장 가까운(유사한) 벡터를 찾는 검색 |
| **KNN (K-Nearest Neighbor)** | 정확한 최근접 이웃 탐색. 완벽한 정확도, 느린 속도 |
| **ANN (Approximate Nearest Neighbor)** | 근사 최근접 이웃 탐색. 약간의 정확도를 포기하고 속도를 획득 |
| **Recall** | 검색 정확도 지표. 실제 최근접 이웃 중 몇 %를 찾았는가 (99%면 매우 우수) |
| **HNSW** | Hierarchical Navigable Small World. 그래프 기반 ANN 알고리즘. 현재 가장 널리 쓰이는 고성능 인덱스 |
| **IVFFlat** | Inverted File Flat. 벡터를 클러스터로 분할 후 탐색하는 ANN 알고리즘. 빌드 빠르고 메모리 적음 |
| **Distance Function** | 두 벡터 간 거리를 측정하는 함수. L2(유클리드), Cosine, Inner Product 등 |
| **RAG** | Retrieval-Augmented Generation. 외부 지식을 검색하여 LLM 응답을 강화하는 기법 |
| **Hybrid Search** | 벡터 유사도 검색과 키워드/메타데이터 필터링을 결합한 검색 |

---

## 2.2 pgvector 심층 분석

### 2.2.1 프로젝트 개요

**pgvector**는 PostgreSQL에 벡터 유사도 검색 기능을 추가하는 **오픈소스 확장(Extension)** 입니다.

| 항목 | 내용 |
|---|---|
| GitHub | https://github.com/pgvector/pgvector |
| 라이선스 | PostgreSQL License (매우 관대한 오픈소스) |
| 커뮤니티 최신 버전 | 0.8.2 (CVE-2026-3172 수정 포함) |
| **DSM 9.1 번들 버전** | **0.8.0** (VMware Postgres 17.7 기준) |
| 지원 PostgreSQL (오픈소스) | 13 이상 (현재 18까지 빌드 가능) |
| **지원 PostgreSQL (DSM 9.1)** | **12 – 17** (12.22, 13.23, 14.20, 15.15, 16.11, 17.7) |
| 개발 언어 | C (PostgreSQL 네이티브 확장) |
| 플랫폼 | Linux, macOS, Windows, FreeBSD |
| CPU 아키텍처 | x86-64, ARM64, i386, PowerPC, RISC-V |
| SIMD 최적화 | AVX, F16C, FMA, AVX-512 런타임 디스패치 (CPU가 지원하는 최적의 SIMD 명령어를 자동으로 선택하여 실행) |

pgvector의 가장 중요한 특징은 **PostgreSQL의 확장으로 동작**한다는 점입니다. 별도의 데이터베이스를 운영할 필요 없이, 기존 PostgreSQL 인프라 위에 `CREATE EXTENSION vector;` 한 줄로 활성화되며, SQL 문법 그대로 벡터 연산을 수행할 수 있습니다. 조직의 기존 PostgreSQL 운영 역량, 백업/복구 체계, 모니터링 도구, 보안 정책을 그대로 활용할 수 있습니다.

> **DSM 기준 참고**: VCF DSM 9.1에서 프로비저닝되는 PostgreSQL에는 pgvector 0.8.0이 포함되어 있으며, Iterative Index Scan 등 0.8.0의 핵심 기능을 모두 사용할 수 있습니다. 커뮤니티 최신 버전 0.8.2의 개선 및 보안 수정(CVE-2026-3172)은 향후 VMware Postgres 번들 업데이트 시 반영될 예정이며, 반영 시점은 DSM 릴리스 노트로 확인이 필요합니다.
> **PostgreSQL 12/13 지원 종료 예고**: DSM 9.1.0은 PostgreSQL 12/13을 지원하는 마지막 릴리스입니다(다음 maintenance 릴리스에서 제거 예정). 신규 배포는 PostgreSQL 15 이상을 권장합니다.
> 출처: [DSM 9.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-91-release-notes.html), [pgvector 0.8.2 릴리스](https://www.postgresql.org/about/news/pgvector-082-released-3245/)

### 2.2.2 버전 히스토리 및 주요 진화

| 버전 | 릴리스 | 핵심 변경 사항 | VMware Postgres 번들 |
|---|---|---|---|
| 0.4.0 | 2023-01 | 최대 차원 1,024 → 16,000 확장, `avg` 집계 함수 | 0.4.4 (최초 도입) |
| 0.5.0 | 2023-08 | **HNSW 인덱스 추가**, IVFFlat 병렬 빌드, `l1_distance` 함수 | — |
| 0.6.0 | 2024-01 | HNSW 성능 대폭 개선, 메모리 사용량 감소, WAL 생성 감소 | — |
| 0.7.0 | 2024-04 | **halfvec 타입**, **sparsevec 타입**, bit 벡터 인덱싱, binary_quantize 함수, Hamming/Jaccard 거리, CPU SIMD 디스패치 | 0.7.0 (PG 15.7/16.3~) |
| 0.8.0 | 2024-10 | **Iterative Index Scan** (필터링 개선), HNSW 빌드/검색 성능 향상, 비용 추정 개선 | **0.8.0 (PG 17.7, DSM 9.1 현재 번들)** |
| 0.8.1 | 2025-09 | on-disk HNSW 빌드 성능 개선, sparsevec 버그 수정 | DSM 미반영 |
| 0.8.2 | 2026 | **병렬 HNSW 빌드 buffer overflow 수정 (CVE-2026-3172)** | DSM 미반영 (확인 필요) |

특히 0.5.0의 HNSW 도입은 pgvector의 전환점이었으며, 이후 버전마다 성능이 급격히 향상되었습니다. Jonathan Katz(pgvector 핵심 기여자)에 따르면 0.4.0 대비 약 1년간 인덱스 빌드와 쿼리 성능을 포함해 최대 **150배의 성능 향상**을 달성했습니다 (출처: [jkatz05.com](https://jkatz05.com/post/postgres/pgvector-performance-150x-speedup/), 벤치마크 조건 및 워크로드에 따라 개선 폭은 다를 수 있음).

### 2.2.3 지원 벡터 타입

pgvector는 다양한 정밀도와 희소성 수준의 벡터 타입을 지원합니다.

| 타입 | 정밀도 | 최대 차원 | 스토리지 | 인덱싱 가능 차원 | 용도 |
|---|---|---|---|---|---|
| `vector` | 32-bit float (단정밀도) | 16,000 | 4×dim + 8 bytes | 2,000 | 범용, 최고 정밀도 |
| `halfvec` | 16-bit float (반정밀도) | 16,000 | 2×dim + 8 bytes | 4,000 | 메모리 절감, 대규모 데이터 |
| `sparsevec` | 32-bit float (희소) | 16,000 | 8×nonzero + 16 bytes | 1,000 (비영 요소) | 희소 임베딩 (BM25, SPLADE 등) |
| `bit` | 1-bit (바이너리) | — | dim/8 bytes | 64,000 | Binary Quantization, 초저비용 검색 |

실무 Tip: OpenAI text-embedding-3-small (기본 1,536차원)을 사용할 경우, `vector(1536)` 타입을 쓰면 행당 약 6KB를 소비합니다. 500만 벡터 기준 약 30GB 테이블이 필요하며, HNSW 인덱스(m=16 기준)는 테이블의 약 2배 수준인 60GB 이상이 될 수 있습니다. 정확한 인덱스 크기는 m, ef_construction 값과 데이터 특성에 따라 달라지므로 실측이 필요합니다. halfvec으로 전환하면 스토리지를 절반으로 줄이면서도 대부분의 유스케이스에서 recall 손실이 미미합니다.

### 2.2.4 거리 함수 (Distance Functions)

| 거리 함수 | SQL 연산자 | 수학적 의미 | 주요 용도 |
|---|---|---|---|
| L2 (유클리드) | `<->` | 두 벡터 간 직선 거리 | 범용. 벡터 크기가 의미 있는 경우 |
| Inner Product (내적) | `<#>` | 두 벡터의 내적 (음수 반환) | 정규화된 벡터에서 최고 연산 속도 |
| Cosine Distance | `<=>` | 1 - cosine similarity | 텍스트 임베딩 기본 선택. 방향만 비교 |
| L1 (맨해튼) | `<+>` | 각 차원 차이의 절대값 합 | 이상치에 강건한 비교 |
| Hamming Distance | `hamming_distance()` | 다른 비트 수 | 바이너리 벡터 비교 |
| Jaccard Distance | `jaccard_distance()` | 1 - (교집합/합집합) | 바이너리 벡터 집합 유사도 |

실무 권장: 텍스트 임베딩에는 **Cosine Distance (<=>)** 를 기본 사용하고, 벡터가 사전 정규화(normalized)되어 있다면 **Inner Product (<#>)** 가 연산 속도가 가장 빠릅니다.

### 2.2.5 인덱스 타입: HNSW vs IVFFlat

pgvector의 두 가지 ANN 인덱스는 각기 다른 트레이드오프를 가집니다.

#### HNSW (Hierarchical Navigable Small World)

다층 그래프 구조를 사용하는 ANN 알고리즘입니다. 상위 레이어에서 대략적인 위치를 찾고, 하위 레이어로 내려가며 정밀 탐색합니다.

- 장점: 검색 속도-recall 트레이드오프가 우수, 데이터 없이도 인덱스 생성 가능, 실시간 삽입/삭제 가능
- 단점: 빌드 시간이 길고 메모리 사용량이 큼
- 주요 파라미터:
  - `m` (기본 16): 레이어당 최대 연결 수. 높을수록 recall 향상, 빌드 느려짐
  - `ef_construction` (기본 64): 빌드 시 후보 리스트 크기. 높을수록 정밀
  - `hnsw.ef_search` (기본 40): 쿼리 시 탐색 범위. 높을수록 recall 향상, 속도 저하

#### IVFFlat (Inverted File Flat)

벡터를 K개 클러스터로 분할한 뒤, 쿼리와 가장 가까운 클러스터만 탐색하는 방식입니다.

- 장점: 빌드 빠르고 메모리 적음, 대량 배치 업데이트에 유리
- 단점: 데이터가 있어야 인덱스 생성 가능(학습 필요), recall-속도 트레이드오프가 HNSW보다 열위
- 주요 파라미터:
  - `lists`: 클러스터 수. pgvector README 권장 기준으로 100만 행 이하일 때 rows/1000, 100만 행 초과 시 sqrt(rows)가 적절한 시작점입니다
  - `ivfflat.probes` (기본 1): 검색 시 탐색할 클러스터 수. sqrt(lists)가 시작점입니다

#### 비교 요약

| 비교 항목 | HNSW | IVFFlat |
|---|---|---|
| 검색 성능 (recall/속도) | 우수 (로그 스케일) | 보통 (선형 스케일) |
| 인덱스 빌드 시간 | 느림 | 빠름 |
| 메모리 사용량 | 높음 (O(n × m × dim)) | 낮음 (O(n × d)) |
| 데이터 없이 생성 | 가능 | 불가 (학습 단계 필요) |
| 실시간 삽입 | 지원 | 재빌드 권장 |
| 권장 시나리오 | 실시간 서비스, 고정밀 검색 | 배치 분석, 제한된 메모리 환경 |

실무 권장: **대부분의 프로덕션 환경에서는 HNSW를 기본 선택**합니다. IVFFlat은 메모리가 제한되거나 배치 워크로드에서 보조적으로 활용합니다.

#### HNSW 핵심 파라미터 튜닝 (recall · 지연 · 빌드시간 트레이드오프)

HNSW의 세 파라미터(`m`, `ef_construction`, `hnsw.ef_search`)는 recall과 지연·빌드시간을 맞바꾸는 핵심 조절 파라미터입니다. pgvector 공식 README 기준으로 `m`은 기본 16, `ef_construction`은 기본 64, `hnsw.ef_search`는 기본 40입니다. 공식 가이드는 "`ef_construction` 값이 높을수록 빌드/삽입 속도를 대가로 recall이 향상되고", `ef_search`도 "값이 높을수록 속도를 대가로 recall이 향상된다"고 명시합니다.

| 파라미터 | 적용 시점 | 기본값 | 올릴 때 효과 | 올릴 때 비용 | 실무 시작 범위 |
|---|---|---|---|---|---|
| `m` | 인덱스 생성 | 16 | recall 향상, 그래프 연결성 강화 | 빌드 느려짐, 메모리·인덱스 크기 증가 | 16 (고차원·고recall 요구 시 24–48) |
| `ef_construction` | 인덱스 생성 | 64 | 인덱스 품질·recall 향상 | 빌드 시간 증가(어느 지점 이후 효익 감소) | 64–200 |
| `hnsw.ef_search` | 쿼리 실행 | 40 | recall 향상 | 쿼리 지연 증가 | 40–200, recall 목표로 조정 |

권장 접근: 빌드 시점 파라미터(`m`, `ef_construction`)는 재생성 비용이 크므로 처음에 다소 넉넉히 잡고, 런타임 recall 미세조정은 세션 단위로 바꿀 수 있는 `hnsw.ef_search`로 수행합니다. recall 목표(예: Recall@10 95%)를 정한 뒤 `ef_search`를 단계적으로 올리며 지연과의 균형점을 찾습니다.

> **빌드 시 메모리·병렬 워커 주의**: pgvector 공식 문서는 "그래프가 `maintenance_work_mem`에 들어갈 때 인덱스 빌드가 현저히 빨라진다"고 명시합니다. 빌드 전 `SET maintenance_work_mem = '8GB';`처럼 충분히 올리고(그래프가 메모리를 초과하면 경고가 발생하며 속도가 급락), `SET max_parallel_maintenance_workers = 7;`(기본 2)로 병렬 빌드를 활용합니다. 워커 수를 크게 잡으면 `max_parallel_workers`(기본 8)도 함께 상향해야 합니다. 단, **병렬 HNSW 빌드는 CVE-2026-3172 영향 경로**이므로(2.12 보안 주의 참조) DSM 번들 pgvector의 패치 적용 시점을 확인하시기 바랍니다.
> 출처: [pgvector README (HNSW Index Options / Indexing Progress)](https://github.com/pgvector/pgvector/blob/master/README.md)

### 2.2.6 임베딩 차원 · 타입 · 거리함수 결정 가이드

벡터 컬럼을 설계할 때는 "차원 결정 → 타입 선택 → 거리함수 선택 → 정규화 여부"를 하나의 흐름으로 결정하면 됩니다. 모두 pgvector 공식 동작에 근거합니다.

1. **임베딩 차원 결정**: 사용할 임베딩 모델이 차원을 결정합니다(예: text-embedding-3-small 1,536, bge-large 1,024, all-MiniLM-L6-v2 384). 차원이 클수록 표현력은 높지만 스토리지·메모리·검색 비용이 증가하므로, 모델이 차원 축소(Matryoshka 등)를 지원하면 품질이 허용되는 선에서 축소를 검토합니다.

2. **타입 선택 (`vector` vs `halfvec`, 2,000차원 한계)**: pgvector에서 `vector` 타입은 **인덱싱 가능 차원이 2,000까지**입니다. 2,000을 초과하는 차원을 인덱싱하려면 공식 문서가 제시하는 대로 **`halfvec`(반정밀도, 최대 4,000차원 인덱싱)** 를 사용하거나, binary quantization(최대 64,000차원)을 적용합니다. 예를 들어 text-embedding-3-large(3,072차원)는 `vector`로는 인덱싱이 불가하므로 `halfvec(3072)`로 저장·인덱싱합니다. `halfvec`은 스토리지를 절반으로 줄이면서도 대부분의 유스케이스에서 recall 손실이 작습니다.

3. **거리함수 선택**: pgvector는 세 가지 주요 연산자와 대응 opclass를 제공합니다.

   | 거리 | 연산자 | opclass | 권장 용도 |
   |---|---|---|---|
   | Cosine | `<=>` | `vector_cosine_ops` | 텍스트 임베딩 기본 선택(방향만 비교) |
   | Inner Product | `<#>` | `vector_ip_ops` | 정규화된 벡터에서 최고 속도(음수 내적 반환) |
   | L2(유클리드) | `<->` | `vector_l2_ops` | 벡터 크기 자체가 의미를 가질 때 |

   `<#>`는 PostgreSQL이 `ASC` 정렬만 지원하므로 **음수 내적(negative inner product)** 을 반환한다는 점에 유의합니다.

4. **정규화 여부**: 공식 가이드는 "**벡터가 길이 1로 정규화되어 있으면(OpenAI 임베딩처럼) 최고 성능을 위해 inner product를 사용**"하도록 권장합니다. 즉 임베딩을 사전 정규화한다면 `<#>` + `vector_ip_ops` 조합이 가장 빠르고, 정규화를 보장하기 어렵다면 크기에 둔감한 Cosine(`<=>` + `vector_cosine_ops`)을 기본값으로 사용하는 것이 안전합니다. 인덱스 opclass는 실제 쿼리에 쓰는 연산자와 반드시 일치해야 인덱스가 사용됩니다.

> 출처: [pgvector README (Vector Types / Indexing / Distances)](https://github.com/pgvector/pgvector/blob/master/README.md)

### 2.2.7 pgvector 0.8.x의 핵심 기능: Iterative Index Scan

0.8.0에서 추가된 가장 중요한 기능은 **Iterative Index Scan**입니다. DSM 9.1에서 프로비저닝되는 pgvector 0.8.0에 이 기능이 포함되어 있습니다.

기존 문제: ANN 인덱스 스캔 후 WHERE 절 필터를 적용하면, 인덱스가 반환한 결과 중 필터 조건을 만족하는 행이 부족한 "overfiltering" 문제가 발생했습니다. 예를 들어 HNSW의 기본 `ef_search=40`으로 40개 후보를 가져왔는데, WHERE 조건에 10%만 매칭되면 실제 결과는 4개에 불과했습니다.

해결: Iterative Scan이 활성화되면, 초기 스캔 결과가 부족할 경우 인덱스를 추가로 스캔하여 충분한 결과를 확보합니다.

```sql
-- HNSW Iterative Scan 활성화
SET hnsw.iterative_scan = relaxed_order;  -- 또는 strict_order
SET hnsw.max_scan_tuples = 10000;

-- IVFFlat Iterative Scan 활성화
SET ivfflat.iterative_scan = on;
SET ivfflat.max_probes = 100;
```

이 기능은 멀티테넌트 환경(tenant_id 필터), 카테고리별 검색, 시간 범위 필터 등 **실제 엔터프라이즈 워크로드에서 매우 중요**합니다.

### 2.2.8 성능 벤치마크

pgvector 성능은 버전마다 크게 향상되었으며, 최신 벤치마크에서는 전용 Vector DB와 견줄 만한 수준입니다.

> **주의**: 아래 벤치마크는 모두 **pgvector + pgvectorscale** (StreamingDiskANN 인덱스 + Statistical Binary Quantization)을 함께 사용한 결과입니다. pgvector 단독 HNSW/IVFFlat 인덱스만으로는 동일 수준의 성능을 기대하기 어렵습니다. pgvectorscale은 Timescale(현 Tiger Data)이 개발한 별도의 오픈소스 확장입니다.

#### pgvector + pgvectorscale vs Pinecone (50M 벡터, 768차원, Cohere 데이터셋)

| 비교 항목 | pgvector + pgvectorscale | Pinecone s1 | Pinecone p2 |
|---|---|---|---|
| p95 Latency (99% recall) | 기준 | 28배 느림 | 1.4배 느림 |
| QPS (99% recall) | 기준 | 16배 낮음 | 1.5배 낮음 |
| 월 비용 (AWS self-hosted 기준) | 기준 | 4배 비쌈 | 약 5배 비쌈 |

> 출처: Timescale(현 Tiger Data) 벤치마크, 2024-2025, https://www.tigerdata.com/blog/pgvector-vs-pinecone

#### pgvector + pgvectorscale vs Qdrant (50M 벡터, 768차원)

| 비교 항목 | pgvector + pgvectorscale | Qdrant |
|---|---|---|
| QPS (99% recall) | 471.57 QPS | 41.47 QPS (pgvectorscale 대비 1/11.4) |
| p50 Latency | 31.07 ms | 30.75 ms (1% 우위) |
| p95 Latency | 60.42 ms | 36.73 ms (39% 우위) |
| p99 Latency | 74.60 ms | 38.71 ms (48% 우위) |

> 출처: Tiger Data 벤치마크, 2025-05, https://www.tigerdata.com/blog/pgvector-vs-qdrant
> 참고: Timescale은 2024–2025년에 Tiger Data로 사명을 변경했으며, 위 URL은 리브랜딩 후의 도메인입니다.

해석: pgvectorscale과 결합된 pgvector는 **처리량(QPS)에서 큰 우위**를 보이며, Qdrant는 **단일 쿼리 꼬리 지연(tail latency)에서 우위**를 보입니다. 대부분의 엔터프라이즈 워크로드에서는 처리량이 더 중요한 지표입니다.

pgvector 단독(HNSW 인덱스)의 경우, 대규모 데이터셋에서 전용 Vector DB보다 성능이 낮을 수 있습니다. 단, **1,000만 벡터 이하 규모에서는 pgvector 단독으로도 100ms 미만의 응답 시간을 달성할 수 있어 대부분의 엔터프라이즈 RAG 워크로드에 충분**합니다. 벤치마크 결과는 하드웨어, 데이터셋, 쿼리 패턴에 따라 크게 달라질 수 있으므로 반드시 실제 워크로드 기반 테스트가 필요합니다.

### 2.2.9 스케일링 전략과 한계

pgvector는 PostgreSQL의 스케일링 방식을 그대로 따릅니다.

**수직 확장 (Scale Up)**
메모리, CPU, 스토리지 증설. HNSW 인덱스가 shared_buffers에 올라가야 최적 성능을 발휘하므로, 인덱스 크기의 110% 이상의 메모리를 확보해야 합니다. 인덱스가 메모리에 올라가지 못하면 성능이 10–100배 저하됩니다.

**읽기 확장 (Read Replicas)**
PostgreSQL의 표준 스트리밍 복제를 통해 읽기 분산. 벡터 검색은 대부분 읽기 워크로드이므로 효과적입니다.

**수평 확장 (Sharding)**
Citus 등의 분산 확장 또는 파티셔닝을 활용한 샤딩. tenant_id, locale, product_line 등 쿼리 필터와 상관관계가 높은 컬럼으로 파티셔닝하면 각 파티션별 벡터 인덱스만 스캔하여 지연 시간을 줄일 수 있습니다.

**실무 가이드라인**

| 벡터 규모 | 권장 접근법 |
|---|---|
| ~100만 | 단일 인스턴스 + HNSW, 대부분의 PoC/초기 서비스 |
| 100만 – 1,000만 | 수직 확장 + 파티셔닝 + Read Replica |
| 1,000만 – 5,000만 | pgvectorscale(StreamingDiskANN) 도입 검토 |
| 5,000만 이상 | 전용 Vector DB 또는 Citus 기반 분산 검토 |

### 2.2.10 AI 프레임워크 연동 (에코시스템)

pgvector는 현재 주요 AI/ML 프레임워크와 광범위하게 통합되어 있습니다.

| 프레임워크 / 라이브러리 | 연동 방식 | 비고 |
|---|---|---|
| **LangChain** | `langchain-postgres` 패키지, PGVector 클래스 | RAG 파이프라인 구축의 사실상 표준 |
| **LlamaIndex** | PGVectorStore 내장 | LangChain 대안 프레임워크 |
| **Python (psycopg3)** | `pgvector` PyPI 패키지 | SQLAlchemy, Django, Peewee ORM 지원 |
| **Java / Spring** | JDBC + pgvector 타입 | Spring AI 프로젝트 통합 |
| **.NET** | Npgsql + pgvector 타입 | .NET 에코시스템 |
| **Node.js** | pg 드라이버 + 확장 | JS/TS 백엔드 |

LangChain 연동 예시 (Python):

```python
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
connection = "postgresql+psycopg://user:pass@host:5432/dbname"

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="my_docs",
    connection=connection,
    use_jsonb=True,
)

# 문서 추가
vector_store.add_documents(documents)

# 유사도 검색
results = vector_store.similarity_search("VCF 9 설치 절차", k=5)

# RAG Retriever로 변환
retriever = vector_store.as_retriever(
    search_type="mmr",  # Maximal Marginal Relevance
    search_kwargs={"k": 5}
)
```

### 2.2.11 pgvector 기본 사용법 Quick Reference

```sql
-- 1. 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 벡터 테이블 생성
CREATE TABLE documents (
    id        bigserial PRIMARY KEY,
    content   text,
    metadata  jsonb,
    embedding vector(1536)   -- OpenAI text-embedding-3-small 기준
);

-- 3. 데이터 삽입
INSERT INTO documents (content, metadata, embedding)
VALUES (
    'VCF 9은 차세대 프라이빗 클라우드 플랫폼이다',
    '{"source": "vcf-docs", "category": "infrastructure"}',
    '[0.023, -0.187, 0.442, ..., 0.091]'  -- 1536차원 벡터
);

-- 4. HNSW 인덱스 생성 (Cosine Distance 기준)
SET maintenance_work_mem = '4GB';
SET max_parallel_maintenance_workers = 7;

CREATE INDEX idx_docs_embedding ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 100);

-- 5. 유사도 검색 (Cosine Distance, 상위 5개)
SELECT id, content, embedding <=> '[쿼리벡터]' AS distance
FROM documents
ORDER BY embedding <=> '[쿼리벡터]'
LIMIT 5;

-- 6. 하이브리드 검색 (벡터 + 메타데이터 필터)
SET hnsw.iterative_scan = relaxed_order;

SELECT id, content, embedding <=> '[쿼리벡터]' AS distance
FROM documents
WHERE metadata->>'category' = 'infrastructure'
ORDER BY embedding <=> '[쿼리벡터]'
LIMIT 5;

-- 7. 검색 정밀도 조정
SET hnsw.ef_search = 100;  -- 기본 40, 높이면 recall 향상
```

### 2.2.12 PostgreSQL 메모리 튜닝 가이드 (pgvector 워크로드)

500만 벡터(1,536차원) 기준 권장 설정:

| 파라미터 | 권장값 | 설명 |
|---|---|---|
| `shared_buffers` | HNSW 인덱스 전체를 수용할 수 있는 크기 (m=16 기준 약 60GB 이상, 인덱스 크기의 110%) | HNSW 인덱스가 반드시 메모리에 상주해야 함. 정확한 인덱스 크기는 데이터 적재 후 `pg_relation_size()`로 확인 |
| `maintenance_work_mem` | 8GB | 인덱스 빌드 속도 향상 |
| `effective_cache_size` | 가용 메모리의 75% | 쿼리 플래너 최적화 |
| `work_mem` | 256MB | 정렬/해시 조인 작업 메모리 |
| `max_parallel_maintenance_workers` | CPU 코어 - 1 | 인덱스 병렬 빌드 |

> **보안 주의 (CVE-2026-3172)**: pgvector 0.8.2 미만에서 병렬 HNSW 인덱스 빌드에 buffer overflow 취약점이 있어, 타 릴레이션의 민감 데이터 유출 또는 DB 크래시가 가능합니다. `max_parallel_maintenance_workers`로 병렬 빌드를 사용하는 환경은 DSM 번들 pgvector의 패치 적용 시점을 확인하고, 가능하면 0.8.2 이상을 적용합니다. 출처: [pgvector 0.8.2 릴리스](https://www.postgresql.org/about/news/pgvector-082-released-3245/)

커넥션 관리: pgvector 워크로드에서도 PgBouncer 등 커넥션 풀러를 사용하되, `pool_mode=transaction`으로 설정합니다. 동시 접속 100 이상이면 반드시 커넥션 풀링을 적용해야 합니다.

---

## 참고 자료

| 자료 | URL |
|---|---|
| pgvector GitHub (공식) | https://github.com/pgvector/pgvector |
| pgvector 0.8.0 릴리스 노트 | https://www.postgresql.org/about/news/pgvector-080-released-2952/ |
| pgvector 0.8.2 릴리스 (CVE-2026-3172) | https://www.postgresql.org/about/news/pgvector-082-released-3245/ |
| pgvector CHANGELOG | https://github.com/pgvector/pgvector/blob/master/CHANGELOG.md |
| pgvector 150x 성능 향상 분석 (Jonathan Katz) | https://jkatz05.com/post/postgres/pgvector-performance-150x-speedup/ |
| pgvector + pgvectorscale vs Pinecone 벤치마크 | https://www.tigerdata.com/blog/pgvector-vs-pinecone |
| pgvector + pgvectorscale vs Qdrant 벤치마크 | https://www.tigerdata.com/blog/pgvector-vs-qdrant |
| LangChain PGVector 연동 | https://python.langchain.com/docs/integrations/vectorstores/pgvector/ |
| DSM 9.1 릴리스 노트 | https://techdocs.broadcom.com/us/en/vmware-cis/dsm/data-services-manager/9-1/release-notes/vmware-data-services-manager-91-release-notes.html |

---
[← 이전: 01 버전 호환 매트릭스](01-version-compatibility.md) · [목차](../README.md) · [다음: 03 VCF DSM 아키텍처 →](03-vcf-dsm-architecture.md)
