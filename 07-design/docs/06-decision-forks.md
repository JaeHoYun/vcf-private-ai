# 06 — 설계 결정 카탈로그

[← 목차로](../README.md)

이 문서는 이 가이드의 **모든 설계 결정을 한 장에 색인**합니다. 각 결정의 빠른 권고 트리거를 보고 상세 문서로 이동하세요. 결정을 내린 뒤에는 아래 **설계 결정 기록(ADR)** 템플릿으로 **선택과 근거를 남겨** 추적 가능하게 합니다. (약어·기술 용어 풀이는 [A1 용어집](../appendix/A1-reference.md)을 참조하세요.)

> 본 문서의 수치·동작은 작성 시점(2026-06) VCF 9.1 / PAIF 9.1 / PAIS 2.1 기준이며, 적용 전 공식 문서로 재확인하시기 바랍니다.

---

## 6.1 결정 색인 (12건)

**D1–D12** 는 아래 12개 설계 결정에 붙인 식별 번호입니다. 이 가이드 전체에서 각 결정을 이 번호로 가리킵니다.

| ID | 결정 | 경로 | 빠른 권고 트리거 | 상세 |
|----|------|------|-----------------|------|
| D1 | VCF 토폴로지 | 표준(기본) vs 통합(비권고) | 표준이 기본 — 통합은 최소 VCF용이라 Private AI 비권고 | [03](03-compute-gpu-topology.md) |
| D2 | GPU 공유 | MIG vs 타임슬라이싱 vs 패스스루 | 멀티테넌트 추론 → MIG / dev 가변부하 → 타임슬라이싱 / 대형 단일 → 패스스루 | [03](03-compute-gpu-topology.md) |
| D3 | 서빙 배치 | VKS vs DLVM | 프로덕션·다수 모델 → VKS / PoC·단일 → DLVM | [03](03-compute-gpu-topology.md) |
| D4 | 서빙 방식 | PAIS Runtime vs NIM vs 자가 vLLM | 표준 운영 → PAIS / 최고 성능·지원 → NIM / 최신 OSS → 자가 | [03](03-compute-gpu-topology.md) |
| D5 | 네트워킹 | NSX 오버레이·VPC vs 물리 VLAN | 셀프서비스·마이크로세그 → 오버레이 / 기존 VLAN·단순 → VLAN | [04](04-network-storage-availability.md) |
| D6 | 로드밸런서 | AVI vs 내장 L4 vs 서드파티 | 프로덕션 L7·WAF → AVI / 단순 L4 → 내장 / 특수 → 서드파티 | [04](04-network-storage-availability.md) |
| D7 | 스토리지 | vSAN vs 외장(NFS·FC·vVol) | 그린필드·HCI → vSAN / 기존 SAN·NAS → 외장 | [04](04-network-storage-availability.md) |
| D8 | VectorDB | DSM pgvector vs 외부 전용 | 표준 RAG → pgvector / 초대규모·전용 ANN → 외부 | [04](04-network-storage-availability.md) |
| D9 | 가용성·DR | 단일 vs stretched vs 멀티사이트 | 비핵심 → 단일 / 무중단 메트로 → stretched / 지역재해 → 멀티사이트 | [04](04-network-storage-availability.md) |
| D10 | 테넌시 격리 | soft vs hard | 신뢰 내부팀 → soft / 규제·외부 → hard | [05](05-tenancy-security.md) |
| D11 | Identity | 내장 vs 외부 IdP | 소규모 → 내장 / 기업 SSO·규제 → 외부 페더레이션 | [05](05-tenancy-security.md) |
| D12 | 에어갭 수준 | 완전 vs 프록시 vs 온라인 | 국가·방산 규제 → 완전 / 일반 기업 → 프록시 / 저민감 → 온라인 | [05](05-tenancy-security.md) |

## 6.2 결정 요인에서 영향받는 결정으로

요구사항(결정 요인)이 어떤 결정을 좌우하는지 정리합니다. 결정 요인 수집은 [01 설계 프로세스](01-design-process.md)에서 다룹니다.

| 결정 요인 | 강하게 미는 결정 |
|---------|-----------------|
| 규제·데이터 주권 | D12 에어갭 · D10 테넌시 · D11 Identity |
| 기존 물리망 투자 | D5 네트워킹 · D6 로드밸런서 |
| 기존 SAN·NAS 자산 | D7 스토리지 |
| 예산·최소 호스트 | D1 토폴로지 · D2 GPU 공유 |
| 성능·지연 SLO | D2 GPU 공유 · D4 서빙 방식 · D9 가용성 |
| 운영 스킬셋 | D3 서빙 배치 · D5 네트워킹 · D8 VectorDB |
| 무중단·연속성 | D9 가용성·DR · D2 GPU 공유(패스스루 HA 제약) |

## 6.3 설계 결정 기록(ADR) 템플릿

**설계 결정 기록(ADR, Architecture Decision Record)** 은 결정 하나를 "무엇을, 왜 그렇게 정했는지" 짧게 남기는 한 장짜리 기록입니다. 시간이 지나거나 담당자가 바뀌어도 "왜 이렇게 설계했나"에 답할 수 있게 합니다. 결정마다 아래 형식으로 한 건씩 남깁니다. 양식은 가벼워야 실제로 쓰입니다.

```
결정 기록 NNN: [결정 제목] (예: D7 스토리지)
- 날짜 / 작성자:
- 맥락: 어떤 요구·제약 때문에 결정이 필요했나
- 선택: 채택한 경로 (예: 외장 NFS)
- 대안: 검토했으나 버린 경로와 이유
- 결과·트레이드오프: 이 선택으로 감수하는 것
- 재검토 트리거: 무엇이 바뀌면 이 결정을 다시 본다
```

---
[← 이전: 05 설계 결정 — 멀티테넌시·보안 설계](05-tenancy-security.md) · [목차](../README.md) · [다음: 07 설계 리뷰 체크리스트와 검증 관문 →](07-design-review.md)
