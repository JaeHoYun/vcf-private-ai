# A1 — 부록

[← 목차로](../README.md)

## A1.1 FAQ

**Q1. 파인튜닝 대신 RAG를 쓰는 이유는?**
사내 지식은 자주 바뀝니다. RAG는 문서를 재인덱싱하면 즉시 반영되고(재학습 불필요), 답변에 출처를 달 수 있으며, 데이터가 모델 가중치에 박히지 않아 접근 통제가 쉽습니다. 문체·도메인 적응이 필요하면 RAG와 파인튜닝을 병행할 수 있습니다.

**Q2. Agent Builder(경로 A)와 직접 구현(경로 B) 중 무엇으로 시작할까?**
경로 A로 시작하세요. 표준 문서 Q&A는 Agent Builder가 청킹·검색·조립을 처리해 빠르게 동작합니다. 검색 품질의 한계가 보이는 단계(하이브리드/리랭킹/커스텀 청킹)에서 해당 부분만 경로 B로 내려 보완하는 하이브리드가 현실적입니다. ([01 §1.4](../docs/01-reference-architecture.md#14-빌드-vs-바이--두-가지-조립-방식))

**Q3. 답변이 자꾸 지어냅니다(환각).**
순서대로 점검: ① 검색 recall이 충분한가(06) → 부족하면 청킹/top-k/하이브리드(02·03). ② 근거는 들어오는데 무시하는가 → 프롬프트에 "근거에 있는 내용만, 없으면 모른다" 고정 + temperature 낮춤(04). ③ "근거 없음 폴백"이 동작하는가(03).

**Q4. 출처는 어떻게 정확히 답니까?**
모델이 본문에 쓴 인용이 아니라, **앱이 실제로 검색한 청크의 메타데이터**를 1차 진실로 삼아 출처 카드를 만드세요. 모델 인용은 보조입니다. ([04 §4.5](../docs/04-inference-integration.md#45-인용출처-표기))

**Q5. 모델을 바꾸면 다시 인덱싱해야 하나요?**
**임베딩 모델**을 바꾸면 벡터 공간이 달라져 전면 재인덱싱이 필요합니다. **완성(LLM) 모델**만 바꾸면 인덱스는 그대로 두고 06 회귀 테스트만 하면 됩니다. ([02 §2.5](../docs/02-ingestion-indexing.md#25-재인덱싱증분-갱신), [07 §7.6](../docs/07-production-operations.md#76-신뢰성--day-2))

**Q6. 폐쇄망에서도 됩니까?**
PAIS(Private AI Services) 2.1의 Artifact Mirroring Tool(아티팩트 미러링 도구)로 모델·아티팩트를 미러링해 폐쇄망에서 RAG를 자족 운용할 수 있습니다. 외부 임베딩 API 의존이 없는지만 확인하세요. ([07 §7.5](../docs/07-production-operations.md#75-에어갭폐쇄망))

## A1.2 용어

| 용어 | 설명 |
|------|------|
| RAG | Retrieval-Augmented Generation — 검색으로 찾은 근거를 프롬프트에 넣어 생성 |
| Chunk | 임베딩·검색 단위로 쪼갠 문서 조각 |
| Embedding | 텍스트를 벡터로 변환한 수치 표현 |
| pgvector | PostgreSQL 벡터 검색 확장 (DSM(Data Services Manager) 9.1 제공) |
| top-k | 검색에서 가져올 상위 청크 수 |
| Reranking | 1차 검색 후보를 정밀 모델로 재정렬 |
| Hybrid search | 키워드(BM25) + 벡터 검색 결합 |
| Faithfulness | 답변이 검색 근거에만 충실한 정도(환각의 반대) |
| Knowledge Base | Agent Builder가 검색에 사용하는 인덱싱된 문서 집합 |
| Agent Builder | PAIS의 노코드/로우코드 RAG 앱 빌더 |
| Artifact Mirroring Tool | 에어갭 아티팩트 미러링 |

## A1.3 엔드투엔드 도입 체크리스트

```
인덱싱
- 문서 로딩·메타데이터(출처·접근등급) 정규화
- 청킹 전략·크기 결정(256–512 + 오버랩에서 시작)
- 임베딩 모델 선택(질문·문서 동일), pgvector 차원 일치
- 인덱스(HNSW/IVFFlat)·거리 연산자 결정
검색·추론
- top-k·메타데이터 권한 필터 결합
- (필요 시) 하이브리드·리랭킹
- "근거 없음" 폴백 임계 설정
- 시스템 프롬프트 가드 + temperature 낮춤
- 출처 진실원 = 실제 검색 청크 메타데이터
앱·운영
- 오케스트레이션 계층 분리
- 인가를 검색 필터에서 적용
- 후속 질문 재작성, 멀티턴 세션
- 골든셋(답 없음 포함) + 회귀 CI
- 트레이싱·폴백률·검색점수 관측
- 캐시 무효화 ↔ 재인덱싱 연동
- (해당 시) Artifact Mirroring Tool 에어갭 자족성 점검
```

## A1.4 참고 자료

- [VMware Private AI Service API 레퍼런스 (Broadcom Developer)](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)
- [VMware Private AI Foundation with NVIDIA 9.1 (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)
- [Private AI Services Detailed Design (Broadcom TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-9-0-and-later/9-1/design/design-library/private-ai-platform-detailed-design/private-ai-services.html)
- [DSM 9.1 — 모던 데이터베이스와 Private AI (VMware Cloud Foundation Blog)](https://blogs.vmware.com/cloud-foundation/2026/05/05/vmware-data-services-manager-9-1-automating-the-modern-databases-that-drive-ai-and-private-cloud/)
- [Building GenAI Agents on VCF with Private AI Services (VMware Cloud Foundation Blog)](https://blogs.vmware.com/cloud-foundation/2025/08/26/vmware-private-ai-services-demo/)
- 시리즈 형제 가이드: [① 인프라](../../01-infra/README.md) · [② VectorDB](../../02-vectordb/README.md) · [③ 서빙 API](../../03-serving-api/README.md)

---
[← 이전: 07 프로덕션 운영](../docs/07-production-operations.md) · [목차](../README.md)
