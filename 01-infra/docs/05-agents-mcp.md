# 05 — 에이전트·MCP·거버넌스 (9.1 신규)

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 이 문서는 **PAIS 2.1에서 새로 강화된 에이전트·외부 도구 연동(MCP)** 을 다룹니다. 9.0.x 가이드에는 없던 영역입니다.

단순 RAG Q&A를 넘어, 에이전트가 **외부 시스템(DB·이슈트래커·메신저·IT 서비스 관리(ITSM))을 직접 조회·실행**하고, 그 과정을 **거버넌스와 관측성**으로 통제하는 것이 9.1의 핵심 진전입니다.

---

## 5.1 Model Endpoint vs Agent (복습)

| 구분 | Model Endpoint | Agent |
|------|---------------|-------|
| 역할 | 단일 모델 API 노출 | RAG + 도구 사용 캡슐화 |
| 입력 | 프롬프트 | 사용자 질문 |
| 출력 | LLM 응답 | 응답 + 출처 + 세션 (+도구 실행 결과) |
| RAG | 미지원 | 지원 내장 |
| Knowledge Base | 미지원 | 지원 연결 |
| **외부 도구(MCP)** | 미지원 | 지원 **(9.1)** |
| 세션 관리 | 미지원 | 지원 |
| API | `/v1/chat/completions` | `/v1/agents/{name}/chat` |

> 대부분의 RAG 앱은 **Agent**가 간편합니다. 외부 시스템 연동까지 필요하면 9.1의 **MCP**가 정답입니다.

---

## 5.2 Agent 구성 요소 (9.1)

```
┌──────────────────────────── Agent ─────────────────────────────┐
│  System Prompt   규칙·톤·제약                                    │
│      +                                                          │
│  Model Endpoint  Llama 3.1 8B 등 (Temperature·Max Tokens)        │
│      +                                                          │
│  Knowledge Base  RAG 데이터 (Similarity Cutoff·Chunk 수)          │
│      +                                                          │
│  MCP Tools (9.1) 외부 데이터·도구 (DB·ITSM·메신저·코드)            │
│      +                                                          │
│  Session Config  Chat History·만료 시간                           │
│  ───────────────────────────────────────────────────────────   │
│  → REST API 자동 생성: POST /v1/agents/{name}/chat               │
└─────────────────────────────────────────────────────────────────┘
```

기본 RAG 설정(KB·프롬프트·세션)은 [문서 03 §3.4](03-workflows.md#34-phase-c-rag에이전트-구성)와 동일하며, 여기서는 **MCP 도구 연동**을 더합니다.

---

## 5.3 MCP(Model Context Protocol)란?

**MCP는 에이전트(LLM)와 외부 데이터·도구를 잇는 산업 표준 인터페이스**입니다. 9.0.x에서는 외부 시스템을 붙이려면 시스템마다 커스텀 커넥터/코드를 만들어야 했지만, 9.1의 PAIS 2.1은 **MCP 표준으로 커스텀 커넥터 없이** 연동합니다.

```
            [ 에이전트 (LLM) ]
                   │  MCP (표준 프로토콜)
        ┌──────────┼───────────┬───────────┬───────────┐
        ▼          ▼           ▼           ▼           ▼
     Oracle    MS SQL     ServiceNow    GitHub       Slack
   PostgreSQL  (DB)        (ITSM)       (코드/이슈)  (메신저)
```

> 비유하자면 MCP는 표준 포트와 같습니다. 도구마다 다른 케이블(커스텀 커넥터)을 만들 필요 없이, 하나의 표준 인터페이스로 다양한 시스템을 꽂습니다.

### 지원 연동 (PAIS 2.1)

| 분류 | 예시 시스템 | 활용 |
|------|------------|------|
| 데이터베이스 | Oracle, Microsoft SQL Server, PostgreSQL | 사내 정형 데이터 조회/집계 |
| ITSM/업무 | ServiceNow | 티켓 조회·생성, 워크플로우 |
| 개발 | GitHub | 코드/이슈/PR 조회 |
| 협업 | Slack | 메시지 조회·전송 |

> 위 목록은 Broadcom 발표 기준 대표 예시입니다. 지원 커넥터·버전의 정확한 목록은 적용 직전 [PAIS 2.1 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)에서 확인하시기 바랍니다.

### PAIS 2.1에서 추가된 MCP 운영 기능

PAIS 2.1은 MCP 연동에 **중앙 관리·자동 검색** 기능을 더했습니다.

| 기능 | 내용 |
|------|------|
| **Tool Gallery** | MCP 서버를 **중앙에서 등록·관리**하고 도구를 활성화하는 UI. "a tool gallery for centralized MCP server management and tool enablement" |
| **Knowledge Base의 MCP 노출 (KB-as-MCP-tool)** | Knowledge Base를 **MCP 도구로 노출**해, 앱 개발자가 컨텍스트 인식 에이전트를 구성. "exposes knowledge bases over MCP so that AI application developers can build context-aware agents" |
| **Agentic Retrieval** | Data Indexing & Retrieval이 **MCP 도구로 통합**되어, 에이전트가 *검색 수행 여부와 검색어를 스스로 결정*. "Data Indexing and Retrieval is integrated in Private AI Services as an MCP tool, allowing agents to decide whether to retrieve content from a knowledge base and what search term to use" |

> 위 세 기능은 [Broadcom TechDocs — Private AI Services 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html) 및 [MCP 도구 탐색 가이드](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/exploring-the-mcp-tools-avaiable-in-your-namespace.html) 기준입니다. 이로써 RAG 검색은 고정 파이프라인이 아니라 **에이전트가 도구 설명을 보고 호출 여부를 판단**하는 흐름으로 동작합니다(§5.4).

---

## 5.4 Tool-calling 동작 흐름

에이전트가 MCP 도구를 사용하는 일반 흐름:

```
사용자: "지난주 결함 티켓 수를 부서별로 알려줘"
   │
   ▼
① LLM이 의도 파악 → "ServiceNow 조회가 필요"하다고 판단(tool call 결정)
   │
   ▼
② MCP를 통해 ServiceNow 도구 호출 (거버넌스 정책 내 권한·범위 검증)
   │
   ▼
③ 도구 결과(티켓 데이터)를 LLM 컨텍스트로 주입
   │
   ▼
④ LLM이 결과 + (필요 시 KB 문서)를 종합해 최종 답변 생성
   │
   ▼
응답: "지난주 결함 티켓은 총 42건이며, 생산1팀 18건 … (출처: ServiceNow)"
```

핵심: **무엇을, 언제, 어떤 권한으로** 호출할지는 거버넌스 정책과 시스템 프롬프트가 통제합니다(§5.5). LLM이 임의로 무제한 실행하지 않습니다.

---

## 5.5 거버넌스 (가장 중요)

외부 도구·DB에 에이전트가 접근하는 순간, **보안 표면이 확장**됩니다. 9.1의 MCP는 거버넌스를 전제로 설계됐으며, 다음을 반드시 정의해야 합니다.

| 거버넌스 축 | 통제 내용 | 권고 |
|------------|----------|------|
| **연결 승인** | 어떤 MCP 도구를 플랫폼에 등록할지 | Platform/Org Admin 승인제, 화이트리스트 |
| **권한 범위** | 도구별 읽기/쓰기 범위, 접근 가능 데이터 | 최소 권한 원칙(read-only 우선), 서비스 계정 분리 |
| **네임스페이스 경계** | 어떤 네임스페이스의 에이전트가 어떤 도구를 쓰는지 | DEV/PROD 분리, 민감 도구는 PROD 제한 |
| **인증** | 도구 자격 증명 보관 | Secret 관리, 정기 갱신, 토큰 만료 |
| **감사** | 도구 호출 추적 | 모든 tool call 로깅(누가·언제·무엇을·결과) |
| **데이터 유출 방지** | 외부로 나가는 컨텍스트 통제 | 입출력 필터링, 개인식별정보(PII) 마스킹, 쓰기 작업 승인 게이트 |

> **쓰기(Write) 작업 주의:** ServiceNow 티켓 생성, Slack 전송, DB 갱신 등 **부수효과가 있는 도구**는 별도 승인 게이트·확인 절차를 두는 것을 강력히 권장합니다. 읽기 전용으로 시작해 점진적으로 권한을 확대하세요.

> **에어갭 환경:** 방산·금융·공공처럼 외부 반출이 불가한 환경에서는 MCP 연동 대상도 **내부 시스템(사내 PostgreSQL·내부 ITSM)** 으로 한정하고, Artifact Mirroring Tool(아티팩트 미러링 도구) 기반 폐쇄망 구성과 결합합니다 → [문서 06](06-production.md), [문서 08](08-industry.md).

---

## 5.6 에이전트 관측성 (LLM 트레이싱)

PAIS 2.1은 **OpenTelemetry(OTel) Collector 기반 LLM 트레이싱**을 제공합니다. 에이전트 호출이 RAG 검색·도구 호출·LLM 추론 등 여러 단계를 거치므로, 단계별 추적이 디버깅·성능·비용 분석의 핵심입니다.

| 추적 대상 | 확인 가능한 것 |
|----------|--------------|
| LLM 호출 | 토큰 사용량, 지연, 캐시 활용률 |
| RAG 검색 | 검색된 청크, Similarity 점수 |
| MCP 도구 호출 | 호출된 도구, 인자, 결과, 소요 시간 |
| 전체 트레이스 | 한 요청의 end-to-end 단계별 타임라인 |

> **알려진 이슈(PAIS 2.1):** 일부 환경에서 PAIS의 LLM 트레이스가 OpenTelemetry Collector에 표시되지 않을 수 있습니다(릴리스 노트 기재). 관측성 구성 시 트레이스 수신을 반드시 검증하세요.
>
> 모델·GPU 메트릭 대시보드와의 통합 운영은 [문서 06 §관측성](06-production.md)에서 다룹니다.

---

## 5.7 에이전트 설계 베스트 프랙티스

1. **읽기 우선, 쓰기 신중** — 부수효과 도구는 승인 게이트·드라이런으로 시작.
2. **도구 최소화** — 한 에이전트에 너무 많은 도구를 붙이면 LLM의 도구 선택 정확도가 떨어집니다. 역할별로 분리.
3. **시스템 프롬프트에 도구 사용 규칙 명시** — "확실하지 않으면 도구를 호출하지 말 것", "민감 작업은 사용자 확인" 등.
4. **RAG + 도구의 역할 구분** — 사실/문서는 KB(RAG), 실시간/정형 데이터는 MCP 도구.
5. **트레이싱 상시 활성화** — 환각·오작동·비용 급증을 단계별로 추적.
6. **거버넌스를 코드화(GitOps)** — 도구 등록·권한 정책을 IaC(Infrastructure as Code, 코드형 인프라)로 관리해 재현·감사 가능하게.

---

[← 이전: 04 개발 시나리오 및 AI 앱 개발](04-dev-scenarios.md) · [목차](../README.md) · [다음: 06 프로덕션 아키텍처 →](06-production.md)
