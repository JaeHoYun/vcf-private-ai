# 01 — 위협 모델 및 보안 아키텍처 전경
> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

이 문서는 PAIF(Private AI Foundation) 9.1 / PAIS(Private AI Services) 2.1 기반 Private AI 플랫폼의 **위협 모델**과 **보안 아키텍처 전경**(landscape)을 정리합니다. 개별 통제의 상세 설계는 02–07 문서로 위임하며, 본 문서는 "무엇을 왜 방어하는가"를 파악하는 출발점입니다.

PAIF 9.1은 VCF(VMware Cloud Foundation) 9.1 위에 GPU 가속 컴퓨팅과 AI 중심 서비스를 얹은 플랫폼이며, AI 워크로드는 **GPU-Accelerated Workload Domain**(본 문서 약칭 PAIF Workload Domain)에 배치됩니다. Private AI Services는 이 도메인의 Supervisor 위에 설치되어 Model Gallery, Model Runtime, Vector Database, Data Indexing and Retrieval, AI Agent Builder 등을 제공합니다([Broadcom: Deploy a GPU-Accelerated Workload Domain](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/deploy-a-vi-workload-domain-in-vmware-cloud-foundation.html)).

## 1.1 보호 대상과 신뢰 가정

| 구분 | 보호 자산 | 손상 시 영향 |
|---|---|---|
| 데이터 | 학습/RAG 코퍼스, 임베딩 벡터, 프롬프트·응답 로그 | 기밀 유출, 추론 데이터 역추적 |
| 모델 | 가중치, 어댑터(LoRA), 모델 카드 | 모델 절취, 무결성 훼손, 백도어 |
| 플랫폼 | Supervisor, VKS 클러스터, GPU 자원 | 테넌트 격리 붕괴, 자원 탈취 |
| 자격증명 | 서비스 토큰, 레지스트리 키, MCP 자격 | 권한 상승, 측면 이동 |
| 가용성 | 추론 엔드포인트, GPU 풀 | 서비스 거부, 비용 폭증 |

신뢰 가정: 하이퍼바이저(ESX)와 vSphere 관리 평면은 신뢰 기반(root of trust)으로 두되, 그 위의 모든 테넌트·앱·외부 입력은 **기본 불신**(zero trust)으로 취급합니다.

## 1.2 AI 파이프라인 공격면 전수

데이터 인입 → 인덱싱(②) → 검색 → 서빙(③) → 에이전트/MCP → 앱의 각 단계에 고유 위협이 존재합니다. 분류 코드는 OWASP Top 10 for LLM Applications 2025를 따릅니다([OWASP GenAI](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)).

| # | 파이프라인 단계 | 주요 위협 | OWASP LLM / ATLAS 매핑 | 1차 방어 문서 |
|---|---|---|---|---|
| 1 | 데이터 인입 | 데이터·모델 포이즈닝, 오염 코퍼스 주입 | LLM04 / ATLAS Poison Training Data | 05 |
| 2 | 인덱싱(임베딩) | 벡터·임베딩 약점, 임베딩 역전, 교차테넌트 누수 | LLM08 / ATLAS RAG Poisoning | 05 |
| 3 | 검색(Retrieval) | 간접 프롬프트 인젝션(오염 문서), False RAG Entry | LLM01, LLM08 / ATLAS False RAG Entry Injection | 06 |
| 4 | 서빙(추론) | 민감정보 노출, 시스템 프롬프트 유출, 무한 소비 | LLM02, LLM07, LLM10 / ATLAS Model Inversion | 06 |
| 5 | 출력 처리 | 부적절 출력 처리(XSS/명령 주입 전이) | LLM05 / — | 06 |
| 6 | 에이전트·MCP | 과도한 권한(Excessive Agency), 도구 오남용 | LLM06 / ATLAS Multi-agent trust exploitation | 03, 06 |
| 7 | 공급망 | 모델·이미지·라이브러리 변조 | LLM03 / ATLAS AI Supply Chain Compromise | 04 |
| 8 | 앱·전체 | 오정보(환각) 전파, 감사 부재 | LLM09 / — | 06, 07 |

MITRE ATLAS는 2025–2026 갱신에서 RAG Poisoning, False RAG Entry Injection, LLM Prompt Crafting, AI Supply Chain Compromise 등 생성형 AI 공격기법을 대폭 확장했습니다(v5.1.0 기준 16 tactics / 84 techniques)([MITRE ATLAS](https://atlas.mitre.org/)).

## 1.3 다층 방어(Defense-in-Depth) 계층 모델

단일 통제에 의존하지 않고 계층별로 독립 방어선을 둡니다. 각 계층은 하위 계층이 뚫려도 상위 영향이 제한되도록 설계합니다.

| 계층 | 핵심 통제 | 대표 컴포넌트 | 상세 문서 |
|---|---|---|---|
| L1 물리/하이퍼바이저 | 부팅 무결성, GPU 격리, 호스트 강화 | ESX, vSphere, Secure Boot/vTPM | 01·03 |
| L2 네트워크 | 마이크로세그멘테이션, L7 검사, NDR | NSX, vDefend Distributed Firewall | 02 |
| L3 플랫폼 | 테넌트 격리, RBAC, 네임스페이스 | VKS, Supervisor, PAIF Services | 02·03 |
| L4 모델/데이터 | 무결성 서명, 암호화, 벡터 격리 | Model Gallery, Harbor, Vector DB | 04·05 |
| L5 앱/추론 | 입력 검증, 출력 처리, 가드레일 | AI Agent Builder, 게이트웨이 | 06 |
| L6 운영/감사 | 로깅, 탐지, 컴플라이언스 증빙 | VCF Operations, SIEM 연계 | 07 |

L2에서 vDefend Distributed Firewall은 하이퍼바이저에 내장된 소프트웨어 정의 L2-L7 스테이트풀 방화벽으로, 데이터센터 네트워크 재설계 없이 워크로드 NIC 단위 제로트러스트 마이크로세그멘테이션을 제공합니다([VMware vDefend Distributed Firewall](https://www.vmware.com/products/cloud-infrastructure/vdefend-distributed-firewall)).

## 1.4 신뢰 경계(Trust Boundary)와 테넌트 격리 개요

다음 경계를 넘는 데이터·제어 흐름은 모두 인증·인가·검사 대상입니다(상세 격리 설계는 [02-network-tenant-isolation.md](02-network-tenant-isolation.md)).

- 외부 사용자 ↔ 앱/게이트웨이: 인증·입력 검증 경계. 간접 인젝션 차단 지점.
- 앱 ↔ 추론 엔드포인트: 테넌트 토큰 검증, 레이트 리밋(LLM10).
- 테넌트 A ↔ 테넌트 B(계열사/사업부): 네트워크·네임스페이스·벡터 인덱스 격리. 교차 누수 금지.
- 워크로드 도메인 ↔ 관리 평면(vCenter/NSX): 관리 트래픽 분리, 운영자 권한 최소화.
- 플랫폼 ↔ 외부 레지스트리(NGC 등): 공급망 경계. 에어갭 환경은 단방향 미러링만 허용([04-airgap-supply-chain.md](04-airgap-supply-chain.md)).

PAIF는 에어갭 배치를 지원하며, Artifact Mirroring Tool(PAIS 2.1 신규)를 통해 GPU 모델 엔드포인트·에이전트를 포함한 전 기능을 외부 인터넷 없이 운용할 수 있습니다([Broadcom: Secure Private AI Part 2](https://blogs.vmware.com/cloud-foundation/2026/04/30/guide-to-secure-private-ai-with-broadcom-part-2/)).

## 1.5 책임 분담 모델

Private AI 보안은 단일 주체가 전담하지 않습니다. 계층별 책임 주체를 명확히 분리해야 통제 누락을 막을 수 있습니다.

| 책임 영역 | 플랫폼 제공(VCF/PAIF) | 플랫폼 운영자(인프라/보안팀) | 앱 개발자(데이터/MLOps) |
|---|---|---|---|
| 하이퍼바이저·GPU 격리 | 제공 | 패치·구성 적용 | — |
| 네트워크 세그멘테이션 | 엔진 제공(vDefend/NSX) | 정책 설계·적용 | 워크로드 태깅 |
| ID·RBAC | 인증 연동 제공 | 역할·최소권한 설계 | 서비스계정 위생 |
| 모델·이미지 공급망 | 레지스트리·서명 기능 | 미러링·승인 게이트 | 모델 출처 검증 |
| 데이터 거버넌스 | 암호화·벡터DB 제공 | 키·보존정책 | 코퍼스 분류·마스킹 |
| 앱 가드레일 | Agent Builder 프레임 | 가드레일 정책 표준 | 프롬프트·출력 검증 |
| 감사·컴플라이언스 | 로그 소스 제공 | SIEM·증빙 체계 | 앱 레벨 이벤트 발생 |

이 표는 NIST AI RMF의 Govern/Map/Measure/Manage 책임 배분 관점과 부합합니다([NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)).

## 1.6 위협 → 문서 매핑(커버리지 행렬)

본 시리즈가 OWASP LLM Top 10 전 항목을 어느 문서에서 다루는지 추적할 수 있도록 매핑합니다. 추적 체인이 끊기지 않게 신규 위협 발견 시 본 표를 갱신합니다.

| OWASP LLM 2025 | 위협 요지 | 주 담당 문서 | 보조 |
|---|---|---|---|
| LLM01 프롬프트 인젝션 | 직접/간접 입력으로 동작 변조 | 06 | 02, 05 |
| LLM02 민감정보 노출 | 응답·로그를 통한 기밀 유출 | 05 | 06, 07 |
| LLM03 공급망 | 모델·이미지·의존성 변조 | 04 | 03 |
| LLM04 데이터·모델 포이즈닝 | 오염 데이터로 무결성 훼손 | 05 | 04 |
| LLM05 부적절 출력 처리 | 출력의 하류 시스템 주입 | 06 | — |
| LLM06 과도한 권한 | 에이전트/MCP 권한 남용 | 03 | 06 |
| LLM07 시스템 프롬프트 유출 | 지시문·비밀 노출 | 06 | 07 |
| LLM08 벡터·임베딩 약점 | 인덱스 누수·역전·오염 | 05 | 02 |
| LLM09 오정보 | 환각·근거 없는 출력 | 06 | 07 |
| LLM10 무한 소비 | 자원 고갈·비용 폭증 | 06 | 02, 07 |

OWASP 2025 개정에서 시스템 프롬프트 유출(LLM07)과 벡터·임베딩 약점(LLM08)이 신규 진입했으며, 프롬프트 인젝션(LLM01)은 직접·간접 인젝션을 모두 포괄하도록 정의가 확장되었습니다([OWASP GenAI](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)). RAG 파이프라인을 다루는 앞 시리즈는 [vcf-rag-reference-architecture(시리즈 ④)](../../04-rag/README.md)를 참조하세요.

## 1.7 위협 우선순위화 관점

모든 위협을 동시에 막을 수는 없으므로, 자산 가치 x 발생 가능성 x 노출도로 우선순위를 둡니다.

- 즉시(P0): 교차테넌트 누수(LLM08), 공급망 변조(LLM03) — 격리·서명이 깨지면 피해가 비가역적.
- 단기(P1): 간접 프롬프트 인젝션(LLM01), 과도한 권한(LLM06) — RAG·에이전트 도입 시 노출면 급증.
- 지속(P2): 무한 소비(LLM10), 오정보(LLM09) — 가용성·신뢰도 저하, 운영 모니터링으로 흡수.

우선순위는 조직 데이터 민감도와 규제 환경(예: 금융·공공·제조)에 따라 재평가가 필요하며, "확인 필요" 항목은 단정하지 말고 PoC로 검증합니다.

## 1.8 검증 방법

본 문서의 전경 모델이 실제 환경에서 성립하는지 확인하는 절차입니다. 각 항목은 후속 문서의 상세 검증으로 연결됩니다.

1. **자산·경계 인벤토리 확인**: PAIF Workload Domain 및 Supervisor에 설치된 Private AI Services 목록을 확인합니다.
   ```bash
   kubectl get ns
   kubectl get supervisorservices -A        # Private AI Services 설치 여부
   ```
   기대값: Model Gallery / Runtime / Vector DB / Indexing / Agent Builder 중 활성 서비스가 인벤토리와 일치.

2. **L1 부팅 무결성**: ESX 호스트의 Secure Boot/TPM 증명 상태를 vCenter에서 확인합니다(미충족 호스트가 있으면 L1 신뢰 기반 가정 위반).
   - 체크포인트: 모든 GPU 호스트가 Attested 상태, GPU 격리 모드(MIG/passthrough) 정책과 일치.

3. **L2 세그멘테이션 적용 확인**: vDefend Distributed Firewall이 워크로드 NIC에 적용 중인지, 테넌트 간 기본 거부(default-deny)인지 확인합니다.
   - Security Segmentation Report로 미세그먼트(allow-any) 규칙 존재 여부 점검([vDefend](https://www.vmware.com/products/cloud-infrastructure/vdefend-distributed-firewall)).
   - 검증 테스트: 테넌트 A 워크로드에서 테넌트 B 추론 엔드포인트로 연결 시도 → 차단되어야 정상(상세는 [02](02-network-tenant-isolation.md)).

4. **L3 권한 최소화 확인**: 네임스페이스/서비스계정의 RBAC가 최소권한인지 점검합니다.
   ```bash
   kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>
   ```
   기대값: 에이전트/앱 계정이 GPU·시크릿·타 네임스페이스에 광범위 권한을 갖지 않음(LLM06 대비, 상세 [03](03-identity-access.md)).

5. **L4 공급망 신뢰 확인**: Harbor/Model Gallery에 등록된 모델·이미지가 승인·서명 경로로만 유입되는지, 에어갭 환경은 Artifact Mirroring Tool 단방향 미러링만 사용하는지 확인합니다(상세 [04](04-airgap-supply-chain.md)).

6. **커버리지 행렬 점검(테이블탑)**: 1.6 표의 OWASP LLM 10개 항목 각각에 대해 "담당 문서가 실제 통제를 명시하는가"를 검토하고, 미커버 항목이 0인지 확인합니다. 신규 위협(ATLAS 갱신 등) 발생 시 본 표에 행을 추가합니다.

7. **추적 체인 무결성**: 각 위협이 (위협 분류 → 방어 통제 → 검증 절차 → 감사 증빙[07])으로 끊김 없이 연결되는지 확인합니다. 끊긴 고리가 있으면 회귀 불합격으로 간주합니다([07-audit-compliance.md](07-audit-compliance.md)).

---

### 참고 출처
- [Broadcom TechDocs — Deploy a GPU-Accelerated Workload Domain](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/deploy-a-vi-workload-domain-in-vmware-cloud-foundation.html)
- [Broadcom VCF Blog — Secure Private AI with Broadcom (Part 2, Artifact Mirroring Tool/에어갭)](https://blogs.vmware.com/cloud-foundation/2026/04/30/guide-to-secure-private-ai-with-broadcom-part-2/)
- [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)
- [MITRE ATLAS](https://atlas.mitre.org/)
- [VMware vDefend Distributed Firewall](https://www.vmware.com/products/cloud-infrastructure/vdefend-distributed-firewall)
- [NIST AI RMF Core (Govern/Map/Measure/Manage)](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)

---

[목차](../README.md) · [다음: 02 네트워크·테넌트·GPU 격리 →](02-network-tenant-isolation.md)
