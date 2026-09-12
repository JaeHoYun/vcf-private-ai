# VCF 9.1 Private AI 보안과 거버넌스 통합 가이드

> **이 가이드를 읽기 전에** — 임베딩, 벡터, 토큰, RAG, 쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> VMware Cloud Foundation(VCF) 9.1 기반 Private AI(PAIF/PAIS) 플랫폼을 **착수 청사진, 위협 모델, 격리, 접근통제, 공급망, 데이터 거버넌스, 앱 가드레일, 감사, 에이전트 거버넌스**의 한 권으로 묶는 보안 통합 레퍼런스

[① 인프라](../01-infra/README.md), [② 데이터](../02-vectordb/README.md), [③ 서빙](../03-serving-api/README.md), [④ RAG](../04-rag/README.md) 각 편에 흩어져 있던 보안 주제(NSX/vDefend 격리, OIDC, MCP 승인 게이트, Artifact Mirroring Tool 에어갭, 문서 ACL, 프롬프트 인젝션 방어 등)를 **다층 방어 한 장의 그림**으로 통합하고, 각 통제의 **검증 방법**까지 함께 제시합니다.

본 문서는 새 컴포넌트를 소개하지 않습니다. 형제 가이드에서 만든 것을 **보안과 거버넌스 관점**으로 다시 꿰며, 세부 구현은 해당 가이드로 링크합니다.

> **VCF Private AI 가이드 시리즈 — ⑤ 보안과 거버넌스**, 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md), 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 기반 버전 (Source of Truth)

> 본 가이드는 **보안과 거버넌스 관점**에 집중하며, 엔진과 컴포넌트 버전은 단정하지 않고 형제 가이드의 버전 단일 기준 문서를 기준선으로 삼습니다 → [① README 버전표](../01-infra/README.md#기반-버전-source-of-truth). 모든 수치는 작성 시점(2026-06) 기준이고 2026-09에 VCF 9.1.1 / PAIS 3.0을 반영했으며, 적용 전 공식 문서로 재확인하시기 바랍니다.

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation / PAIF | 9.1.1 | 9.1 GA 2026-05, 9.1.1 GA 2026-09 |
| Private AI Services (PAIS) | 3.0 | Agent Builder, Data Indexing(RAG), MCP Tools Registry, Artifact Mirroring Tool. 3.0에서 API 토큰, BYO TLS 인증서, 원격 클라우드 모델 추가 |
| vDefend (Add-on) | 9.1 | 분산 방화벽과 IDS/IPS |
| PostgreSQL / pgvector (DSM 9.1.1) | 16.8 / 0.8.0 | PAIS 검증 조합 (②) |

## 문서 구성

착수 문서(00)에서 전체 그림과 순서를 잡은 뒤, 플랫폼을 **위협 식별 → 격리 → 접근통제 → 공급망 → 데이터 → 앱 → 감사** 순으로 방어하고, 마지막(08)에서 행위자로서의 에이전트를 다룹니다. 각 문서는 끝에 해당 영역 통제의 **검증 방법**을 담습니다.

| 순서 | 문서 | 내용 |
|------|------|------|
| 00 | [어디서부터 시작하나: 보안 청사진과 첫 90일](docs/00-where-to-start.md) | 요청 경로 위의 통제 지점 한 장, 90일 로드맵, 게이트별 최소 보안 세트, 준비물 워크시트, 흔한 실수 |
| 01 | [위협 모델과 보안 아키텍처 전경](docs/01-threat-model.md) | AI 파이프라인 공격면, 다층 방어 계층, 책임 분담, OWASP, ATLAS 매핑 |
| 02 | [네트워크, 테넌트, GPU 격리](docs/02-network-tenant-isolation.md) | NSX VPC/마이크로세그, vDefend, MIG, 네임스페이스 강격리 |
| 03 | [ID, 인증, 접근통제](docs/03-identity-access.md) | OIDC/RBAC, API 게이트웨이, MCP 도구 승인 게이트, 시크릿 |
| 04 | [에어갭, 공급망, 모델 출처](docs/04-airgap-supply-chain.md) | Artifact Mirroring Tool, Harbor, 모델 서명, 스캔, SBOM |
| 05 | [데이터 거버넌스와 프라이버시](docs/05-data-governance.md) | 문서 ACL 동기화, 검색단 인가, PII, 보존과 잔존 |
| 06 | [앱 계층 가드레일](docs/06-app-guardrails.md) | 프롬프트 인젝션/출력 방어, 도구 사용 안전(④ 브리지) |
| 07 | [감사, 로깅, 사고대응 + 컴플라이언스 체크리스트](docs/07-audit-compliance.md) | 추적성, 모델 행위 관측, 섀도 AI 후보 탐지, 사고대응, 한국 규제 매핑, 통제 검증 총괄(C-01–C-18과 게이트) |
| 08 | [에이전트 보안 거버넌스](docs/08-agent-governance.md) | 에이전트 위협 ASI01–10, 비인간 신원, 자율성 상한과 위험 등급 매트릭스, 레지스트리, MCP 도구 공급망과 도구 오염, 샌드박스, 킬스위치, 도구 게이트웨이, 레드팀 |

## 빠른 시작

- **"보안 때문에 전체를 어떻게 설계하고 어디서부터 시작하나"** → [00 어디서부터 시작하나](docs/00-where-to-start.md)
- **"전체 그림부터"** → [01 위협 모델과 보안 아키텍처](docs/01-threat-model.md)
- **"멀티테넌트/계열사 격리가 고민"** → [02 격리](docs/02-network-tenant-isolation.md) + [03 접근통제](docs/03-identity-access.md)
- **"규제 대응과 감사 준비"** → [07 감사와 컴플라이언스 체크리스트](docs/07-audit-compliance.md)
- **"플랫폼 밖에서 쓰이는 AI(섀도 AI)를 어떤 신호로 찾나"** → [07 7.2.3절](docs/07-audit-compliance.md) + [08 8.4절 레지스트리](docs/08-agent-governance.md)
- **"RAG 앱이 인젝션에 안전한가"** → [06 앱 가드레일](docs/06-app-guardrails.md)
- **"에이전트에 도구와 쓰기 권한을 주려는데 무엇을 통제하나"** → [08 에이전트 보안 거버넌스](docs/08-agent-governance.md)

서비스 하나를 출시하는 앱 팀의 준비물과 점검표는 [앱 가이드 12 서비스 보안 준비와 가드레일](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/12-service-security.md)에, 전사 거버넌스 운영 모델과 국내 규제 일정은 [AX 방법론 10](https://github.com/JaeHoYun/enterprise-ax-methodology/blob/main/docs/10-governance.md)과 [부록 A2](https://github.com/JaeHoYun/enterprise-ax-methodology/blob/main/appendix/A2-kr-regulatory-timeline.md)에 있습니다. 이 가이드는 플랫폼 통제의 정본이고, 그 둘은 이 가이드를 참조합니다.

## 참고 자료

각 문서는 본문에 1차 출처(Broadcom TechDocs, NVIDIA 공식 문서, OWASP Top 10 for LLM Applications, NIST AI RMF/CSF, MITRE ATLAS 등)를 인라인으로 표기합니다. 보안 통제의 적용 전에는 해당 공식 문서로 최신 사양을 재확인하시기 바랍니다.

## 라이선스

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). 자유롭게 활용하시되 출처를 표기해 주세요. `출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/05-security`

## 면책

**비공식 문서** — Broadcom, NVIDIA 등 벤더의 공식 입장을 대변하지 않습니다. 본문의 보안 설정, 통제, 검증 절차는 **예시**이며 릴리스와 환경마다 달라지므로, 적용 직전 공식 문서로 확인하시기 바랍니다. 규제와 컴플라이언스 항목은 일반 범주로만 다루며 특정 규제기관과 기업과 무관합니다. 언급된 제품명과 상표는 각 소유자의 자산입니다.
