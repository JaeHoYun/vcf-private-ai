# VCF 9.1 Private AI 사이징·용량·비용(TCO) 가이드

> **이 가이드를 읽기 전에** — 임베딩·벡터·토큰·RAG·쿠버네티스(VKS) 같은 용어가 낯설다면, 먼저 [VCF Private AI 입문 (Primer)](../00-foundations/README.md)에서 기초 어휘를 잡으시길 권합니다. 이 가이드는 그 개념들을 이미 아는 것으로 전제합니다.

> VMware Cloud Foundation(VCF) 9.1 기반 Private AI(PAIF: Private AI Foundation / PAIS: Private AI Services) 플랫폼을 **워크로드·GPU·VKS 클러스터 사이징부터 용량 계획·TCO**까지 한 권으로 다루는 정량 설계 레퍼런스

"GPU 몇 장이, 노드·클러스터를 어떻게 구성해, 얼마에 필요한가"에 답합니다. 프로덕션 배포는 VKS(vSphere Kubernetes Service) 기준이며, 워크로드를 자원 → 노드 → 클러스터 → 비용으로 환산하는 워크시트와, 추정치를 실측으로 보정하는 절차를 제공합니다.

이 가이드는 **사이징·용량·TCO의 단일 기준 문서**입니다. 전반 아키텍처·구축은 [① 인프라](../01-infra/README.md), 데이터는 [② VectorDB](../02-vectordb/README.md), 서빙은 [③ 서빙 API](../03-serving-api/README.md), RAG는 [④ RAG](../04-rag/README.md), 보안은 [⑤ 보안·거버넌스](../05-security/README.md)를 참조하고, 여기서는 정량 사이징·비용에 집중합니다.

> **VCF Private AI 가이드 시리즈 — ⑥ 사이징·용량·비용** · 7부작 중 한 편입니다. [전체 7개 보기 — 시리즈 허브](../README.md) · 상위 전략 [AX 방법론](https://github.com/JaeHoYun/enterprise-ax-methodology)

---

## 기반 버전 (Source of Truth)

> 본 가이드는 **정량 사이징·비용**에 집중하며, 엔진·컴포넌트 버전은 단정하지 않고 형제 가이드의 버전 단일 기준 문서를 기준선으로 삼습니다 → [① README 버전표](../01-infra/README.md#기반-버전-source-of-truth). 모든 수치는 작성 시점(2026-06) 기준이며 적용 전 공식 문서·견적으로 재확인하시기 바랍니다.

| 구분 | 버전 | 비고 |
|------|------|------|
| VMware Cloud Foundation / PAIF | 9.1 | GA 2026-05 |
| Private AI Services (PAIS) | 2.1 | Agent Builder, Model Runtime, MCP, Artifact Mirroring Tool |
| VKS (vSphere Kubernetes Service) | VCF 9.1 동반 | DRA 기반 GPU 스케줄링, 스케일 상향 |
| PostgreSQL / pgvector (DSM: Data Services Manager 9.1) | 16.8 / 0.8.0 | PAIS 검증 조합 (②) |

> 본 가이드의 사이징 수치(GPU 메모리·처리량·노드 수 등)는 모두 **어림 기준이며 환경·릴리스별로 달라집니다. 적용 전 반드시 벤치마크·부하시험으로 실측 보정**하시기 바랍니다. 비용·라이선스 단가는 단정하지 않으며 공식 견적·구독 조건으로 확인하셔야 합니다.

## 독자별 빠른 경로

사이징은 임원·기획자·아키텍트·인프라 담당이 서로 다른 깊이로 보는 주제입니다. 처음이라면 [00 오리엔테이션](docs/00-orientation.md)(선수지식·용어집·개념 미니맵)부터 보세요.

| 독자 | 권장 시작점 |
|------|-------------|
| 임원/의사결정자 | [E0 임원 브리프(요약 문서)](docs/E0-executive-brief.md) → [07.6 손익분기](docs/07-tco-cost-model.md#76-퍼블릭-gpu-클라우드-vs-온프레미스-paif-비교-프레임) |
| IT기획자 | [부록 A2 입력 환산](appendix/A2-inputs-and-defaults.md) → [08 전 과정 예제](docs/08-reference-scenario.md) → [07 TCO](docs/07-tco-cost-model.md) → [부록 A3 견적](appendix/A3-rfq-quote-checklist.md) |
| 개발자/아키텍트 | [01 방법론](docs/01-sizing-methodology.md) → [02 GPU](docs/02-gpu-sizing.md)·[03 컴퓨트](docs/03-compute-memory-sizing.md) → [04 클러스터](docs/04-vks-cluster-sizing.md) |
| 인프라 담당 | [04 클러스터](docs/04-vks-cluster-sizing.md) → [05 스토리지·네트워크](docs/05-storage-network-sizing.md) → [06 용량 계획](docs/06-capacity-planning.md) |

## 문서 구성

워크로드를 **자원 → 노드 → 클러스터 → 비용**으로 환산하는 사이징 생애주기 순서입니다. 각 문서는 끝에 추정치를 검증하는 **검증·실측 방법**을 담습니다.

| 순서 | 문서 | 내용 |
|------|------|------|
| 00 | [오리엔테이션](docs/00-orientation.md) | 독자별 경로, 선수지식 체크, 개념 미니맵, 미니 용어집 |
| E0 | [임원 브리프(요약 문서)](docs/E0-executive-brief.md) | 의사결정 지점, 손익분기 개념, 비용 구조, 임원 체크리스트 |
| 01 | [사이징 방법론과 워크로드 분류](docs/01-sizing-methodology.md) | 워크로드 분류, 입력값 체크리스트, 사이징 절차, 추정→실측 원칙 |
| 02 | [GPU 사이징](docs/02-gpu-sizing.md) | 모델→VRAM(가중치·KV캐시), 처리량→GPU 수·Replica, vGPU/MIG/DirectPath 용량 함의 |
| 03 | [컴퓨트·메모리 사이징](docs/03-compute-memory-sizing.md) | 노드 vCPU/RAM, CPU 추론(llama.cpp), 임베딩/리랭커, Replica 환산 |
| 04 | [VKS 클러스터 사이징과 인프라](docs/04-vks-cluster-sizing.md) | 컨트롤 플레인·노드 풀·GPU 노드 풀, 오토스케일, 스케일 한도, 단일 vs 다중 클러스터 |
| 05 | [스토리지·네트워크 용량 사이징](docs/05-storage-network-sizing.md) | vSAN, Harbor 모델 레지스트리, 벡터 인덱스 용량(②), NSX 대역폭 |
| 06 | [용량 계획과 운영](docs/06-capacity-planning.md) | 모니터링 지표, 증설 트리거, Reservation/쿼터 용량, PoC→프로덕션 로드맵 |
| 07 | [TCO와 비용 모델](docs/07-tco-cost-model.md) | 라이선스·HW·운영비 분해, 비용 산정 워크시트, 퍼블릭 vs 온프레미스 비교 프레임 |
| 08 | [레퍼런스 시나리오(전 과정 예제)](docs/08-reference-scenario.md) | 입력→GPU→노드→클러스터→스토리지→TCO를 한 시나리오로 끝까지 |
| 09 | [역방향 시나리오(공급 제약)](docs/09-reverse-sizing-scenario.md) | 고정 GPU→가용 용량→적재→할당 상한→잔여/증설, 08의 반대 방향 |

### 부록 (자립성 보조)

| 부록 | 문서 | 내용 |
|------|------|------|
| A1 | [1차 가정치 레퍼런스](appendix/A1-first-order-reference.md) | **예산 추정 전용** 처리량·동시성·KV·임베딩·콜드스타트 출발 숫자(출처·경고 포함) |
| A2 | [입력값 환산·기본값·모델 선택](appendix/A2-inputs-and-defaults.md) | 사용자 수→동시성 환산, 워크로드 프리셋, SLA 기본값, 모델 선택 1차 가이드 |
| A3 | [견적 요청(RFQ) 체크리스트](appendix/A3-rfq-quote-checklist.md) | 단가 칸을 채우려면 무엇을 물어야 하나(라이선스·HW·시설·기록 양식) |

### 계산 도구

| 도구 | 내용 |
|------|------|
| [계산 워크북(xlsx)](worksheet/) | 입력만 바꾸면 GPU·노드·스토리지·TCO 골격이 수식으로 자동 산출되는 스프레드시트 |

## 빠른 시작

- **"어디서부터 사이징하나"** → [01 사이징 방법론](docs/01-sizing-methodology.md)
- **"입력만 바꿔 바로 계산하고 싶다"** → [계산 워크북(xlsx)](worksheet/)
- **"입력값을 어떻게 정하나(사용자 수만 있다)"** → [부록 A2 입력값 환산](appendix/A2-inputs-and-defaults.md)
- **"GPU 몇 장 필요한가"** → [02 GPU 사이징](docs/02-gpu-sizing.md)
- **"이미 GPU가 있다 — 그걸로 무엇을 얼마나(역방향)"** → [01 사이징 방법론](docs/01-sizing-methodology.md) §1.7
- **"구매 전 예산 추정 출발 숫자가 필요하다"** → [부록 A1 1차 가정치](appendix/A1-first-order-reference.md)
- **"처음부터 끝까지 한 예제로 보고 싶다"** → [08 레퍼런스 시나리오](docs/08-reference-scenario.md)
- **"이미 GPU가 있다 — 역방향을 끝까지 예제로"** → [09 역방향 시나리오](docs/09-reverse-sizing-scenario.md)
- **"프로덕션 클러스터를 어떻게 짜나"** → [04 VKS 클러스터 사이징](docs/04-vks-cluster-sizing.md)
- **"얼마나 드나"** → [07 TCO와 비용 모델](docs/07-tco-cost-model.md)

## 참고 자료

각 문서는 본문에 1차 출처(Broadcom TechDocs·VCF 블로그, NVIDIA, vLLM 등)를 인라인으로 표기합니다. 사이징·비용 수치는 적용 전 공식 문서·견적과 실측으로 반드시 재확인하시기 바랍니다.

## 라이선스

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). 자유롭게 활용하시되 출처를 표기해 주세요. `출처: https://github.com/JaeHoYun/vcf-private-ai/tree/main/06-sizing-cost`

## 면책

**비공식 문서** — Broadcom·NVIDIA 등 벤더의 공식 입장을 대변하지 않습니다. 본문의 사이징 수치는 **어림 기준이며 환경·릴리스별로 달라지므로 반드시 실측으로 보정**해야 합니다. 비용·라이선스 단가는 단정하지 않으며 공식 견적·구독 조건으로 확인하셔야 합니다. 벤더가 발표한 TCO 절감 수치는 best-case(up to) 값으로 워크로드·사용률에 따라 달라집니다. 언급된 제품명·상표는 각 소유자의 자산입니다.
