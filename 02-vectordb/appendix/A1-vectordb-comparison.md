# A1 — Vector Database 경쟁 비교

> 전용/확장형 벡터 DB 10종 경쟁 분석 (본문 [03 아키텍처](../docs/03-vcf-dsm-architecture.md)의 보조 자료)

기준 시점: 2026년 중반. 경쟁 솔루션 버전·가격은 변동되므로 도입 전 각 벤더 공식 자료로 재확인이 필요합니다. 대상 독자: Private AI Foundation으로 AI Agent 서비스를 제공하려는 인프라/플랫폼 팀.

---

## A1.1 전용 Vector Database 분석

이 섹션에서는 Vector 검색만을 위해 설계된 전용(purpose-built) 벡터 데이터베이스를 분석합니다. 이들은 벡터 인덱싱과 유사도 검색에 최적화된 전용 엔진을 갖추고 있으며, 대규모 벡터 워크로드에 특화되어 있습니다.

### A1.1.1 Pinecone

**개요**: 대표적인 완전 관리형(Fully Managed) SaaS 벡터 데이터베이스. 2019년 설립, $138M+ 투자 유치. Serverless 아키텍처로 인프라 관리 없이 벡터 검색을 제공합니다.

| 항목 | 상세 |
|---|---|
| 유형 | 상용 SaaS (Closed Source) |
| 배포 모델 | Serverless (AWS, Azure, GCP) / BYOC |
| 인덱스 알고리즘 | 독자 알고리즘 (Graph + Tree 하이브리드) |
| 최대 차원 | 20,000 |
| 거리 메트릭 | Cosine, Euclidean, Dot Product |
| 주요 기능 | Serverless 자동 스케일링, Namespace 기반 멀티테넌시, Metadata 필터링, Hybrid Search (Dense + Sparse), Pinecone Assistant (RAG 파이프라인 내장), Pinecone Inference (임베딩/리랭킹 모델 호스팅) |
| 보안/컴플라이언스 | SOC 2 Type II, ISO 27001, GDPR, HIPAA |
| 가격 모델 | 사용량 기반 — Read Units, Write Units, Storage. Standard / Enterprise 티어 제공 (최신 가격은 공식 사이트 참조) |

**강점**: 가장 쉬운 시작점. API 키 하나로 즉시 사용 가능하며, 인프라 운영 부담이 전혀 없습니다. RAG 파이프라인 통합(Pinecone Assistant)으로 벡터 검색→LLM 답변 생성까지 단일 엔드포인트로 처리 가능. 2024년 말 Dedicated Read Nodes 출시로 대규모 워크로드의 예측 가능한 성능 제공.

**약점**: 비용 예측이 어렵습니다. Read Unit 소비량이 네임스페이스 크기, 쿼리 복잡도, 리전에 따라 달라지며 정확한 단가를 사전에 알기 어렵습니다. 실제 사례에서 워크로드 증가에 따라 월 비용이 수십 배로 급증하는 패턴이 보고되고 있습니다. 데이터가 Pinecone 인프라에 저장되므로 데이터 주권(Data Sovereignty) 이슈가 있는 금융권에서는 도입 장벽이 높습니다. 벡터 외 관계형 데이터는 별도 DB가 필요해 데이터 동기화 비용이 추가됩니다.

---

### A1.1.2 Milvus / Zilliz Cloud

**개요**: LF AI & Data Foundation 소속 오픈소스 벡터 데이터베이스. Cloud-native 분산 아키텍처로 수십억 벡터 규모 처리에 특화. 관리형 버전은 Zilliz Cloud.

| 항목 | 상세 |
|---|---|
| 유형 | 오픈소스 (Apache 2.0) / 관리형 Zilliz Cloud |
| 배포 모델 | Standalone (Docker), Cluster (Kubernetes), Zilliz Cloud (AWS/GCP/Azure) |
| 인덱스 알고리즘 | IVF, HNSW, DiskANN, CAGRA (GPU), PQ, SCANN 등 가장 다양한 인덱스 지원 |
| 최대 차원 | 32,768 |
| 거리 메트릭 | L2, IP, Cosine, Jaccard, Hamming |
| 주요 기능 | 분산 아키텍처(Compute/Storage/Metadata 분리), Multi-vector Search, Hybrid Search (Dense + BM25 네이티브 Full-text Search, Milvus 2.5+), Partition Key, GPU 가속(NVIDIA CAGRA), Time Travel, CDC |
| GitHub Stars | 40,000+ (벡터 DB 중 1위, 2025년 말 기준) |
| 가격 (Zilliz) | Serverless / Dedicated 티어 제공, Free Tier 포함 (최신 가격은 공식 사이트 참조) |

**강점**: 가장 많은 인덱스 알고리즘을 지원하여 워크로드 특성에 맞는 최적 구성이 가능합니다. Compute, Storage, Metadata가 분리된 마이크로서비스 아키텍처로 각 컴포넌트를 독립적으로 스케일링할 수 있습니다. GPU 가속(NVIDIA CAGRA)을 통한 대규모 인덱싱 성능이 탁월하며, VDBBench 벤치마크에서 가장 낮은 p50 레이턴시를 기록했습니다. Milvus 2.5부터 BM25 기반 네이티브 Full-text Search가 추가되어, 별도 Elasticsearch 연동 없이 키워드+벡터 하이브리드 검색이 가능합니다. 2.5–2.6 버전에서 72% 메모리 절감, 100K collections 지원 등 대폭 개선되었습니다.

**약점**: 분산 아키텍처의 복잡성이 높습니다. Kubernetes 환경에서 etcd, MinIO, Pulsar(또는 Kafka) 등 다수의 의존성을 운영해야 하며, 소규모 팀에게는 부담이 큽니다. 학습 곡선이 가파르며, SQL이 아닌 자체 API를 사용해야 합니다. Standalone 모드와 Cluster 모드 간 마이그레이션이 단순하지 않습니다.

---

### A1.1.3 Qdrant

**개요**: Rust로 작성된 고성능 오픈소스 벡터 데이터베이스. 메타데이터 필터링과 결합된 벡터 검색에 강점.

| 항목 | 상세 |
|---|---|
| 유형 | 오픈소스 (Apache 2.0) / 관리형 Qdrant Cloud |
| 배포 모델 | Docker, Kubernetes, Qdrant Cloud (AWS/GCP/Azure), Hybrid Cloud |
| 인덱스 알고리즘 | HNSW (커스텀 구현) |
| 최대 차원 | 65,536 |
| 거리 메트릭 | Cosine, Euclidean, Dot Product, Manhattan |
| 주요 기능 | Payload 기반 고급 필터링(Boolean 조합, Geo, Range), Named Vectors(하나의 포인트에 다수 벡터), Quantization (Scalar, Binary, Product), 네이티브 Full-text Filtering (다국어 토큰화, 스테밍, 구문 매칭), Snapshot/Backup, gRPC + REST API |
| GitHub Stars | 27,000+ (2025년 말 기준) |
| 가격 (Cloud) | Free 티어 영구 무료, Hybrid Cloud / Custom Private Cloud 옵션 (최신 가격은 공식 사이트 참조) |

**강점**: Rust 기반으로 메모리 안전성과 성능이 우수합니다. 특히 복잡한 메타데이터 필터링이 벡터 검색과 통합되어 실행되며(post-filter가 아닌 integrated filter), 다중 조건 검색이 필요한 엔터프라이즈 시나리오에 적합합니다. Docker 단일 컨테이너로 간단히 시작할 수 있어 개발자 경험이 좋습니다. 1GB 영구 무료 티어 제공. 2025년에 네이티브 Full-text Filtering(다국어 토큰화, 스테밍, 구문 매칭)이 추가되어 기본적인 키워드 검색이 가능해졌습니다.

**약점**: 클러스터링(Sharding)이 상대적으로 새로운 기능이며, Milvus만큼 대규모 분산 환경에서 검증된 사례가 적습니다. Full-text Filtering이 추가되었으나 BM25 수준의 본격적인 하이브리드 키워드+벡터 검색이 필요하면 Weaviate나 Elasticsearch 수준에는 미치지 못하므로 별도 시스템 연동을 검토해야 할 수 있습니다. 고카디널리티 필드에서 복잡한 필터를 적용하면 쿼리 성능이 저하될 수 있습니다.

---

### A1.1.4 Weaviate

**개요**: 벡터 검색과 Knowledge Graph를 결합한 오픈소스 벡터 데이터베이스. GraphQL 인터페이스와 모듈형 아키텍처가 특징.

| 항목 | 상세 |
|---|---|
| 유형 | 오픈소스 (BSD-3) / 관리형 Weaviate Cloud |
| 배포 모델 | Docker, Kubernetes, Weaviate Cloud (AWS/GCP), Embedded |
| 인덱스 알고리즘 | HNSW (커스텀 구현), Flat |
| 최대 차원 | 65,536 |
| 거리 메트릭 | Cosine, L2, Dot, Manhattan, Hamming |
| 주요 기능 | 모듈형 Vectorizer (OpenAI, Cohere, Hugging Face 플러그인), Hybrid Search (Dense + BM25), GraphQL API, Generative Search (v1.30+, LLM 통합 답변 생성), Multi-modal (텍스트+이미지), Multi-tenancy |
| GitHub Stars | 15,000+ (2025년 말 기준) |
| 가격 (Cloud) | Serverless / Enterprise 티어 제공, HIPAA 지원 (AWS) (최신 가격은 공식 사이트 참조) |

**강점**: 내장 하이브리드 검색 — Dense Vector + BM25 Sparse Vector를 단일 쿼리로 결합 가능. Vectorizer 모듈을 통해 데이터 입력 시 자동 임베딩 생성이 가능하며, v1.30부터 Generative Search 모듈로 검색→LLM 답변 생성까지 DB 내부에서 처리합니다. Knowledge Graph 구조로 객체 간 관계를 모델링할 수 있어 복잡한 도메인에 적합합니다.

**약점**: 그래프 기능의 오버헤드로 인해 순수 벡터 검색 벤치마크에서는 Milvus, Qdrant보다 느립니다. 1억 벡터 이상에서 메모리와 컴퓨트 소비가 급증합니다. 무료 체험 기간이 14일로 가장 짧으며, 가격 구조(AIU 기반)가 다소 복잡합니다.

---

### A1.1.5 Chroma (ChromaDB)

**개요**: AI 애플리케이션 개발자를 위한 경량 오픈소스 벡터 데이터베이스. LangChain과의 긴밀한 통합으로 RAG 프로토타이핑에 가장 빠른 선택지.

| 항목 | 상세 |
|---|---|
| 유형 | 오픈소스 (Apache 2.0) / 관리형 Chroma Cloud |
| 배포 모델 | In-memory (로컬), Client/Server, Chroma Cloud (BYOC) |
| 인덱스 알고리즘 | HNSW |
| 최대 차원 | 제한 없음 (실질적 수천 차원) |
| 거리 메트릭 | Cosine, L2, IP |
| 주요 기능 | 내장 Embedding 함수 (Sentence Transformers 기본), 자동 토큰화/임베딩/인덱싱, Metadata 필터링, Full-text Search, Python/JS SDK |
| GitHub Stars | 24,000+ (2025년 말 기준) |
| 가격 | 오픈소스 무료, Chroma Cloud (크레딧 기반, 무료 크레딧 제공) |

**강점**: `pip install chromadb` 한 줄로 즉시 사용 가능. 임베딩 모델 내장으로 별도 임베딩 서비스 없이 문서 저장→검색이 가능합니다. 2025년 Rust 재작성으로 기존 Python 대비 4배 빠른 읽기/쓰기 성능. LangChain, LlamaIndex와의 통합이 가장 간단합니다.

**약점**: 프로덕션 대규모 워크로드용이 아닙니다. 10만 벡터 이상에서 성능이 저하되며, HA(High Availability), 엔터프라이즈 보안 기능이 미비합니다. 엔터프라이즈 지원 패키지가 없으며, 커뮤니티 포럼에 의존해야 합니다. 프로토타입→프로덕션 전환 시 다른 DB로 마이그레이션이 필요합니다.

---

## A1.2 기존 DB의 벡터 검색 확장

이 섹션에서는 이미 운영 중인 범용 데이터베이스에 벡터 검색 기능을 추가한 솔루션을 분석합니다. 별도의 벡터 DB 없이 기존 인프라를 활용하는 접근입니다.

### A1.2.1 Oracle AI Vector Search (Oracle Database 23ai)

**개요**: Oracle Database 23ai(2024년 5월 GA)에 도입된 네이티브 벡터 검색 기능. 엔터프라이즈 관계형 DB에 벡터 검색을 일급 시민(first-class citizen)으로 통합한 대표 사례.

| 항목 | 상세 |
|---|---|
| 유형 | 상용 (Oracle Database 라이선스) |
| 벡터 타입 | VECTOR (FLOAT32, FLOAT64, INT8) |
| 인덱스 | IVF, HNSW (Exadata GPU 가속 지원) |
| 최대 차원 | 65,535 |
| 거리 메트릭 | Cosine, Euclidean, Dot Product, Manhattan, Hamming |
| 주요 기능 | ONNX 모델 DB 내 임포트 및 임베딩 생성, DBMS_VECTOR_CHAIN (PL/SQL 기반 RAG 파이프라인), Exact + Approximate Search, Hybrid Vector Index, Real Application Clusters(RAC) 연동, Partitioning, GoldenGate 23ai 벡터 실시간 복제 |

**강점**: 기존 Oracle 인프라 투자를 100% 활용하면서 벡터 검색 추가. SQL 단일 쿼리로 관계형 데이터와 벡터 유사도 검색을 JOIN할 수 있습니다. ONNX 런타임 내장으로 DB 내에서 직접 임베딩을 생성하여 외부 서비스 호출이 불필요합니다. Oracle RAC, Data Guard, SQL Firewall 등 검증된 엔터프라이즈 기능을 벡터 데이터에도 동일하게 적용 가능. 금융권에서 이미 Oracle을 사용 중이라면 가장 자연스러운 선택지.

**약점**: Oracle Database 라이선스 비용이 매우 높습니다. 신규 도입 시 벡터 검색만을 위한 비용 정당화가 어렵습니다. 벡터 검색 전용 벤치마크에서의 성능 데이터가 Pinecone, Milvus 등에 비해 부족합니다. Oracle 에코시스템에 대한 깊은 의존도가 생기며, 클라우드 네이티브 아키텍처와의 괴리가 있을 수 있습니다.

---

### A1.2.2 MongoDB Atlas Vector Search

**개요**: MongoDB의 도큐먼트 데이터베이스에 벡터 검색을 통합한 기능. Atlas 관리형 서비스에서 제공되며, 기존 MongoDB 데이터와 벡터를 동일 컬렉션에 저장합니다.

| 항목 | 상세 |
|---|---|
| 유형 | 상용 SaaS (MongoDB Atlas) |
| 인덱스 알고리즘 | HNSW |
| 최대 차원 | 8,192 |
| 거리 메트릭 | Cosine, Euclidean, Dot Product |
| 주요 기능 | Aggregation Pipeline 기반 $vectorSearch 스테이지, ANN + ENN(Exact) 검색, 메타데이터 사전 필터링, Scalar/Binary Quantization, Search Nodes (워크로드 격리), Automated Embedding (자동 임베딩 생성) |
| 가격 | Atlas 구독에 포함. Search Nodes 별도 과금 (최신 가격은 공식 사이트 참조) |

**강점**: 이미 MongoDB를 사용하는 팀이라면 추가 인프라 없이 벡터 검색을 시작할 수 있습니다. Document 모델 특성상 벡터와 메타데이터를 같은 도큐먼트에 저장하여 데이터 동기화 문제가 없습니다. Search Nodes를 통해 벡터 검색 워크로드를 별도 노드로 격리하여 운영 DB에 영향 없이 쿼리 수행이 가능합니다. 15.3M 벡터(2048차원)에서 Quantization 적용 시 50ms 미만 레이턴시, 90–95% recall 달성.

**약점**: Atlas(클라우드 관리형)에서만 Vector Search가 제공되며, Self-managed MongoDB에서는 사용 불가. 엔터프라이즈 규모 비용이 높습니다. 전용 벡터 DB(Milvus, Qdrant) 대비 ANN 알고리즘 다양성과 튜닝 옵션이 제한적입니다.

---

### A1.2.3 Redis Vector Search

**개요**: Redis의 RediSearch 모듈(현재 Redis 8.0부터 내장)을 통한 벡터 유사도 검색. 인메모리 아키텍처 기반의 초저지연 벡터 검색.

| 항목 | 상세 |
|---|---|
| 유형 | 오픈소스 (RSALv2/SSPLv1/AGPLv3) + 상용 Redis Enterprise |
| 인덱스 알고리즘 | FLAT (Brute-force), HNSW, SVS-VAMANA (Intel 플랫폼 전용 최적화¹) |
| 지원 타입 | FLOAT32, FLOAT64 |
| 거리 메트릭 | Cosine, L2, Inner Product |
| 주요 기능 | KNN 검색 + Range 쿼리, Hybrid 검색 (TAG/NUMERIC/GEO/TEXT 필터와 결합), Hash 및 JSON 데이터 구조 지원, LVQ8 압축 (Intel SVS-VAMANA) |
| 가격 | Redis OSS 무료, Redis Enterprise/Cloud 별도 |

> ¹ SVS-VAMANA 및 LVQ(Locally-adaptive Vector Quantization), LeanVec 압축은 Intel SVS 프로젝트 기반으로, Intel 플랫폼에 최적화되어 있습니다. Intel이 아닌 플랫폼에서는 8-bit 스칼라 양자화로 폴백됩니다. Redis 8.2(2025.10)부터 정식 포함.

**강점**: 인메모리 아키텍처로 벡터 DB 중 가장 낮은 쿼리 레이턴시(sub-millisecond). 이미 캐싱/세션 스토어로 Redis를 사용하는 환경이라면 듀얼 용도(캐싱 + 벡터 검색)로 인프라를 효율적으로 활용할 수 있습니다. Tag, Numeric, Geo, Full-text 필터와 벡터 검색을 단일 FT.SEARCH 명령어로 결합하는 하이브리드 쿼리를 지원합니다.

**약점**: 모든 벡터가 메모리에 상주해야 하므로 대규모 데이터셋에서 비용이 급증합니다. 768차원 float32 벡터 100만 개가 약 3GB의 메모리를 소비합니다. 벡터 전용 기능(다양한 인덱스 알고리즘, 양자화 옵션)이 전용 벡터 DB에 비해 제한적입니다. Redis 8.0 이전 버전은 RediSearch 모듈을 별도 설치해야 합니다.

---

### A1.2.4 Elasticsearch Vector Search

**개요**: Elasticsearch 8.0(2022)부터 HNSW 기반 ANN 검색을 정식 지원. 기존 전문 검색(Full-text Search) 인프라에 벡터 검색을 추가하는 접근.

| 항목 | 상세 |
|---|---|
| 유형 | AGPL v3 (OSS) / SSPL / Elastic License 2.0 (트리플 라이선스¹) + 상용 Elastic Cloud |
| 필드 타입 | dense_vector (Dense), sparse_vector (Sparse) |
| 인덱스 알고리즘 | HNSW (Lucene 기반), int8_hnsw (기본값, ES 9.0+), int4_hnsw, bbq_hnsw (Better Binary Quantization) |
| 최대 차원 | 4,096 (동적 매핑), 수동 설정 시 더 높은 값 가능 |
| 거리 메트릭 | Cosine (기본값), L2, Dot Product, Max Inner Product |
| 주요 기능 | knn 검색 옵션 + knn DSL 쿼리 (8.12+), Hybrid Search (knn + BM25 + Retriever), semantic_text 필드 (자동 임베딩), Inference API (내장 모델 배포), ELSER (Elastic Learned Sparse EncodeR), BBQ/Scalar/Binary Quantization, GPU 가속 인덱싱 (NVIDIA cuVS, Tech Preview — ES 9.3 예정²) |
| 가격 | OSS 무료, Elastic Cloud 사용량 기반 |

> ¹ 2024년 9월부터 AGPLv3가 추가되어 트리플 라이선스 체계. Free OSS 버전은 AGPLv3, Basic 이상 바이너리 릴리스는 Elastic License 2.0이 적용됩니다. Elastic License 2.0은 호스팅 서비스 제공 시 제한이 있어 완전한 오픈소스와 차이가 있습니다.

> ² GPU 가속(NVIDIA cuVS)은 2025년 기준 Tech Preview 상태이며, ES 9.3(2026년 초 예정)에서 정식 GA가 계획되어 있습니다. 프로덕션 사용 시 상태를 확인해야 합니다.

**강점**: 10년 이상 대규모 프로덕션에서 검증된 운영 성숙도. 기존 Elasticsearch 클러스터에 벡터 기능을 추가하면 검증된 안정성, 모니터링 도구, 장애 패턴을 그대로 활용할 수 있습니다. Dense + Sparse 벡터를 결합한 하이브리드 검색이 가장 성숙하며, 8.x 시리즈에서 sub-50ms kNN 쿼리를 달성했습니다. BBQ(Better Binary Quantization)로 메모리 사용량을 약 95% 절감(최대 32배 압축) 가능.

**약점**: 벡터 검색만을 위해 Elasticsearch를 새로 도입하는 것은 비효율적입니다 — 리소스 오버헤드가 크고, 운영 복잡성이 높습니다. HNSW 그래프 빌드가 연산 집약적이어서 대량 벡터 인덱싱 시 시간이 오래 걸립니다. dense_vector 필드는 aggregation이나 sorting을 지원하지 않습니다. 라이선스 구조가 트리플 라이선스(AGPLv3/SSPL/ELv2)로 복잡하여, 호스팅 서비스를 제공하려는 경우 법적 검토가 필요합니다.

---

### A1.2.5 PostgreSQL + pgvector (기초 요약 + 포지셔닝)

[02 기초](../docs/02-vectordb-pgvector-basics.md)에서 상세 분석한 pgvector의 핵심을 경쟁 관점에서 재정리합니다.

| 항목 | 상세 |
|---|---|
| 유형 | 오픈소스 (PostgreSQL License) |
| 인덱스 알고리즘 | HNSW, IVFFlat |
| 최대 차원 | 16,000 (HNSW), 2,000 (IVFFlat) |
| 거리 메트릭 | L2, Cosine, Inner Product, L1, Hamming, Jaccard |
| 주요 기능 | SQL 기반 벡터 + 관계형 통합 쿼리, ACID 트랜잭션, Iterative Index Scan (0.8.0+), halfvec/sparsevec/bit 타입, pgvectorscale 확장(StreamingDiskANN, Statistical Binary Quantization) |
| 가격 | 완전 무료 (PostgreSQL + pgvector 모두 오픈소스) |
| 커뮤니티 최신 | 0.8.2 (CVE-2026-3172 수정) |

> 커뮤니티 최신 pgvector는 0.8.2이며 병렬 HNSW 빌드 buffer overflow(CVE-2026-3172)를 수정했습니다. DSM 9.1 번들은 0.8.0이므로, 병렬 빌드 사용 환경은 패치 적용 시점을 확인합니다.

**pgvector의 경쟁 포지션**:

1. **80%의 실제 워크로드에 충분**: 대부분의 엔터프라이즈 AI 워크로드는 수십억 벡터가 아닌 수백만–수천만 벡터 규모이며, 이 범위에서 pgvector(+pgvectorscale)는 전용 벡터 DB와 경쟁력 있는 성능을 보입니다.
2. **TCO 절감 60–80%**: 별도 벡터 DB를 운영하면 DB 구독료 + 기존 관계형 DB(메타데이터 저장용) + 동기화 인프라 + 운영 인력이 필요합니다. pgvector는 이 모든 것을 단일 PostgreSQL 인스턴스로 해결합니다. 실제 마이그레이션 사례에서 연간 TCO 60–80% 절감이 보고되고 있습니다.
3. **운영 전문성 재활용**: PostgreSQL DBA를 찾는 데는 며칠이면 충분하지만, Weaviate나 Milvus 전문가를 찾기는 극히 어렵습니다. 백업, 모니터링, 보안, HA 등 30년간 축적된 PostgreSQL 운영 패턴을 그대로 적용할 수 있습니다.
4. **실제 마이그레이션 트렌드**: Instacart(2025년 5월)가 Elasticsearch에서 PostgreSQL + pgvector로 전환하여 스토리지/인덱싱 비용 80% 절감, zero-result 검색 6% 감소를 달성. Firecrawl은 Pinecone에서 pgvector로, Berri AI는 별도 벡터 DB에서 PostgreSQL(Supabase/pgvector)로 전환하여 비용 절감과 운영 통합을 실현했습니다.

---

## A1.3 종합 비교 매트릭스

### A1.3.1 카테고리별 비교표

#### 전용 Vector DB 비교

| 항목 | Pinecone | Milvus | Qdrant | Weaviate | Chroma |
|---|---|---|---|---|---|
| **라이선스** | Closed (SaaS) | Apache 2.0 | Apache 2.0 | BSD-3 | Apache 2.0 |
| **Self-hosted** | 불가 (BYOC만) | 가능 | 가능 | 가능 | 가능 |
| **인덱스** | 독자 알고리즘 | IVF, HNSW, DiskANN, CAGRA 등 | HNSW | HNSW, Flat | HNSW |
| **최대 차원** | 20,000 | 32,768 | 65,536 | 65,536 | 무제한 |
| **Hybrid Search** | Dense + Sparse | Dense + BM25 네이티브 (2.5+) | 기본 Full-text Filtering 지원¹ | Dense + BM25 | Full-text 지원 |
| **내장 임베딩** | Pinecone Inference | 미지원 | 미지원 | Vectorizer 모듈 | Sentence Transformers |
| **RAG 파이프라인** | Pinecone Assistant | 미지원 | 미지원 | Generative Search | 미지원 |
| **최대 규모** | 수십억+ | 수십억+ | 수억 | 1억 이하 권장 | 1,000만 이하 |
| **GPU 가속** | 미지원 | NVIDIA CAGRA | 미지원 | 미지원 | 미지원 |
| **주 타겟** | 빠른 프로덕션 배포 | 대규모 엔터프라이즈 | 필터링 중심 검색 | 하이브리드 검색/그래프 | 프로토타이핑/MVP |

> ¹ Qdrant는 2025년에 네이티브 Full-text Filtering(다국어 토큰화, 스테밍, 구문 매칭)을 추가했습니다. BM25 수준의 완전한 하이브리드 검색에는 미치지 못하지만, 기본적인 키워드 필터링이 내장되어 외부 연동 없이 사용 가능합니다.

#### 기존 DB 벡터 확장 비교

| 항목 | pgvector | Oracle 23ai | MongoDB Atlas VS | Redis VSS | Elasticsearch |
|---|---|---|---|---|---|
| **기반 DB** | PostgreSQL | Oracle DB | MongoDB | Redis | Elasticsearch |
| **라이선스** | PostgreSQL (OSS) | 상용 | 상용 (Atlas) | OSS + 상용 | AGPLv3 / SSPL / ELv2 (트리플) |
| **인덱스** | HNSW, IVFFlat | IVF, HNSW | HNSW | FLAT, HNSW, SVS-VAMANA | HNSW (Lucene) |
| **최대 차원** | 16,000 | 65,535 | 8,192 | 제한 없음 | 4,096+ |
| **SQL/쿼리** | 표준 SQL | 표준 SQL + PL/SQL | Aggregation Pipeline | FT.SEARCH | DSL + knn |
| **ACID** | 완전 지원 | 완전 지원 | 도큐먼트 레벨 | 미지원 | 미지원 |
| **Hybrid Search** | SQL WHERE + 벡터 | SQL WHERE + 벡터 | $vectorSearch filter | Tag/Numeric/Geo 필터 | knn + BM25 |
| **내장 임베딩** | 미지원 | ONNX 런타임 | Automated Embedding | Vectorize 모듈 | Inference API |
| **Self-hosted** | 가능 | 가능 | 불가 (VS 기능) | 가능 | 가능 |
| **엔터프라이즈 성숙도** | 30년+ (PG) | 40년+ | 15년+ | 15년+ | 10년+ |
| **추가 비용** | 무료 | Oracle 라이선스 | Atlas 구독 | Redis Enterprise | Elastic 구독 |

---

### A1.3.2 워크로드별 추천 매트릭스

| 시나리오 | 1순위 추천 | 2순위 추천 | 비고 |
|---|---|---|---|
| **신규 RAG PoC (빠른 시작)** | Chroma | Pinecone (Free) | 개발 속도 우선 |
| **프로덕션 RAG (<10M 벡터)** | **pgvector** | Qdrant | PostgreSQL 기존 운영 활용 |
| **프로덕션 RAG (10M–100M)** | **pgvector + pgvectorscale** | Milvus | 벤치마크상 경쟁력 확인 필요 |
| **초대규모 (>1B 벡터)** | Milvus | Pinecone | 분산 아키텍처 필수 |
| **복잡한 메타데이터 필터링** | Qdrant | **pgvector (0.8.0+)** | Iterative Index Scan 활용 |
| **Hybrid Search (키워드+벡터)** | Weaviate | Elasticsearch | Dense + Sparse 통합 |
| **초저지연 (<1ms)** | Redis | Pinecone Dedicated Read Nodes | 인메모리 필수 |
| **Oracle 기존 고객** | Oracle 23ai | **pgvector** | 라이선스 비용 대비 검토 |
| **MongoDB 기존 고객** | MongoDB Atlas VS | **pgvector** | Atlas 전용 제약 확인 |
| **금융권 (데이터 주권 + 규제)** | **pgvector (On-prem)** | Oracle 23ai | Self-hosted + ACID 필수 |
| **비용 최적화 우선** | **pgvector** | Qdrant (Self-hosted) | 라이선스 비용 0원 |

---

### A1.3.3 성능 벤치마크 요약

50M 벡터(768차원, Cohere Dataset) 기준, 99% Recall 목표 시:

| 솔루션 | QPS | p95 Latency | 비용 대비 | 출처 |
|---|---|---|---|---|
| **pgvector + pgvectorscale** | 471 | 낮음 | 기준점 | Tiger Data (2025.05) |
| Qdrant | 41 | 보통 | pgvectorscale 대비 11.4x 낮은 QPS | Tiger Data (2025.05) |
| Pinecone (s1) | 기준 | 기준 대비 28x 높음 | pgvectorscale 대비 75% 더 비쌈 | Tiger Data (2024) |

> **벤치마크 출처에 대한 참고**: 위 벤치마크의 출처인 Tiger Data(구 Timescale)는 pgvectorscale의 개발사이자 PostgreSQL 에코시스템 기업입니다. 벤치마크 코드와 데이터셋은 공개되어 재현 가능하지만, 출처의 이해관계를 인지하고 해석할 필요가 있습니다. 반드시 실제 워크로드 기반으로 자체 벤치마크를 수행하여 검증해야 합니다.

참고: 벤치마크 결과는 하드웨어, 데이터셋, 쿼리 패턴에 따라 크게 달라질 수 있으며, 반드시 실제 워크로드 기반 테스트가 필요합니다.

---

### A1.3.4 의사결정 흐름도

```
[벡터 검색이 필요한가?]
      │
      ├─ PoC/프로토타입 → Chroma 또는 Pinecone Free
      │
      ├─ 프로덕션 배포
      │    │
      │    ├─ 기존 PostgreSQL 사용 중?
      │    │    ├─ YES → pgvector 우선 검토
      │    │    │    ├─ <50M 벡터 → pgvector + pgvectorscale
      │    │    │    └─ >50M 벡터 → 벤치마크 후 전용 DB 검토
      │    │    └─ NO → 아래 계속
      │    │
      │    ├─ 기존 Oracle 사용 중?
      │    │    └─ YES → Oracle 23ai AI Vector Search
      │    │
      │    ├─ 기존 MongoDB 사용 중?
      │    │    └─ YES → MongoDB Atlas Vector Search
      │    │
      │    ├─ 기존 Elasticsearch 사용 중?
      │    │    └─ YES → Elasticsearch dense_vector
      │    │
      │    ├─ 기존 Redis 사용 중 + 초저지연 필요?
      │    │    └─ YES → Redis Vector Search
      │    │
      │    └─ 신규 인프라 구축
      │         ├─ 관리형 SaaS 선호 → Pinecone
      │         ├─ Self-hosted + 대규모 → Milvus
      │         ├─ Self-hosted + 중규모 → Qdrant
      │         └─ Hybrid Search 필수 → Weaviate
      │
      └─ [데이터 주권/금융 규제 필수?]
           └─ YES → pgvector (On-prem) 또는 Oracle 23ai
```

---

### A1.3.5 pgvector가 적합하지 않은 경우

객관적 판단을 위해 pgvector의 한계도 명확히 정리합니다.

1. **수십억 벡터 + 수천 QPS**: 단일 PostgreSQL 인스턴스의 수직 확장에는 한계가 있습니다. Citus를 통한 수평 확장이 가능하지만, Milvus의 네이티브 분산 아키텍처에 비해 복잡도가 높습니다.
2. **GPU 가속이 필수인 경우**: pgvector는 CPU 기반(SIMD 최적화)이며, NVIDIA GPU 가속은 지원하지 않습니다. 대규모 인덱스 빌드에 GPU가 필요하면 Milvus(CAGRA)를 검토해야 합니다. Elasticsearch의 cuVS GPU 가속은 2025년 기준 Tech Preview 상태이므로 프로덕션 사용 시 GA 여부를 확인해야 합니다.
3. **네이티브 하이브리드 검색(Dense + Sparse)**: pgvector는 SQL WHERE 절과 벡터 검색을 결합할 수 있지만, BM25 등 Sparse Vector 기반 키워드 검색을 벡터 검색과 통합하려면 추가 구성이 필요합니다. Weaviate, Elasticsearch, 그리고 최근 네이티브 Full-text Search를 추가한 Milvus(2.5+)가 이 영역에서 우위.
4. **서버리스/자동 스케일링**: Pinecone처럼 트래픽에 따라 자동으로 스케일업/다운하는 기능은 없습니다. 직접 인프라를 프로비저닝해야 합니다.
5. **ORM 지원 미비**: Prisma 등 주요 ORM에서 pgvector와 파티셔닝을 완전히 지원하지 않아 Workaround가 필요할 수 있습니다 (2025년 9월 기준).

---

## A1.4 핵심 인사이트 요약

### A1.4.1 전용 Vector DB vs. DB 확장 — 어떤 접근이 맞는가?

| 기준 | 전용 Vector DB | DB 벡터 확장 (pgvector 등) |
|---|---|---|
| **최적 시나리오** | 벡터가 주요 워크로드, 수십억 규모, 최극단 성능 | 벡터가 기존 데이터와 통합, 수천만 규모, 운영 단순성 |
| **TCO** | 높음 (DB 구독 + 관계형 DB + 동기화) | 낮음 (단일 DB) |
| **운영 복잡도** | 높음 (별도 시스템 학습/운영) | 낮음 (기존 DBA 스킬 활용) |
| **성능 상한** | 더 높음 (전용 최적화) | 충분 (80% 워크로드 커버) |
| **데이터 일관성** | 별도 동기화 필요 | 단일 트랜잭션 보장 |
| **인재 확보** | 어려움 | 용이 (PostgreSQL 생태계) |

### A1.4.2 pgvector 도입을 권장하는 핵심 이유 (도입 검토팀 관점)

1. **"새 DB를 배우지 않아도 됩니다"** — SQL로 벡터 검색. 기존 PostgreSQL 스킬 100% 활용.
2. **"데이터가 한 곳에 있습니다"** — 벡터 + 메타데이터 + 비즈니스 데이터가 동일 DB. 동기화 문제 원천 제거.
3. **"검증된 엔터프라이즈 기능"** — 백업, PITR, 복제, HA, 보안, 모니터링. 30년간 축적된 PostgreSQL 생태계 전체 활용.
4. **"비용이 0원"** — pgvector는 오픈소스. 라이선스 비용 없음. TCO 60–80% 절감.
5. **"규모가 커지면 확장 가능"** — pgvectorscale(StreamingDiskANN)로 50M+ 벡터까지. 정말 부족하면 그때 전용 DB를 검토해도 늦지 않습니다.
6. **"금융 규제에 적합"** — On-premise 배포, ACID 트랜잭션, 데이터 주권 보장. 금융감독원 규제 대응 가능.

---
[← 이전: 08 PoC 가이드](../docs/08-poc-guide.md) · [목차](../README.md)
