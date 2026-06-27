# 06 — MCP 도구 API

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 경로·필드는 [공식 PAIS API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/) 기준입니다.

PAIS 2.1은 에이전트가 **외부 데이터·도구(DB, ITSM(IT 서비스 관리 시스템), 메신저 등)** 를 표준 인터페이스(MCP)로 연동하도록 지원합니다. 이 문서는 그 연동을 **API로 등록·승인·통제**하는 방법을 다룹니다. MCP의 개념·거버넌스 원칙은 형제 가이드 [05](../../01-infra/docs/05-agents-mcp.md)에 자세하며, 여기서는 API에 집중합니다.

---

## 6.1 MCP란 (요약)

**MCP(Model Context Protocol)** 는 에이전트(LLM)와 외부 시스템을 잇는 표준 인터페이스입니다. 도구마다 커스텀 커넥터를 만들 필요 없이, 표준 프로토콜 하나로 다양한 시스템을 연결합니다.

```
        [ Agent (LLM) ]
              │  MCP (표준 프로토콜)
   ┌──────────┼───────────┬───────────┐
   ▼          ▼           ▼           ▼
  사내 DB   ITSM        코드/이슈    메신저
 (조회)    (티켓)       (조회)      (조회/전송)
```

> 연결 가능한 시스템의 정확한 목록·커넥터·버전은 적용 직전 [PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1.html)에서 확인하시기 바랍니다. (여기서는 특정 제품을 단정하지 않고 분류로 설명합니다.)

---

## 6.2 MCP 서버·도구 API

| 동작 | 메서드·경로 |
|------|------------|
| 외부 MCP 서버 등록 | `POST /control/mcp-servers` (`name`, `url`, `transport`) |
| 도구 목록 조회 | `GET /control/mcp-servers/tools` (`server` 필터: 서버 ID 또는 `built-in`) |
| 도구 승인/해제 | `POST /control/mcp-servers/{server-id}/tools/{tool-id}/approval` (`is_approved`) |

**흐름**

```
① 외부 MCP 서버 등록      POST /control/mcp-servers
        │                  { name, url, transport }
        ▼
② 서버가 노출하는 도구 조회  GET /control/mcp-servers/tools?server={id}
        │                  → 각 도구 { id, name, is_approved, mcp_server_id }
        ▼
③ 도구별 명시적 승인        POST .../tools/{tool-id}/approval { is_approved: true }
        │
        ▼
④ 에이전트에 승인된 도구 연결  (에이전트 생성/수정 시 tools[]에 추가 → 04)
```

> **승인(approval)이 별도 단계**라는 점이 핵심입니다. 서버를 등록한다고 모든 도구가 자동으로 에이전트에 노출되지 않습니다. `is_approved`를 명시적으로 켜야 사용 가능합니다 — 이것이 거버넌스의 1차 게이트입니다.

---

## 6.3 거버넌스 — 읽기 우선, 쓰기 신중

외부 도구·DB에 에이전트가 접근하는 순간 **보안 표면이 확장**됩니다. MCP API는 거버넌스를 전제로 설계되었으며, 최소한 다음을 정의해야 합니다.

| 거버넌스 축 | API/운영 통제점 | 권고 |
|------------|----------------|------|
| **연결 승인** | `mcp-servers` 등록 + 도구 `approval` | 관리자 승인제, 허용 목록(화이트리스트) |
| **권한 범위** | 도구별 읽기/쓰기 범위, 자격증명 scope | 최소 권한, read-only 우선, 서비스 계정 분리 |
| **네임스페이스 경계** | 어떤 네임스페이스 에이전트가 어떤 도구를 쓰는지 | DEV/PROD 분리, 민감 도구는 PROD 한정 |
| **인증** | 도구 자격증명 보관 | 비밀값(Secret) 관리, 정기 회전, 토큰 만료 |
| **감사** | 도구 호출 추적 | 모든 tool call 로깅(누가·언제·무엇을·결과) → [07](07-observability-ops.md) |
| **데이터 유출 방지** | 외부로 나가는 컨텍스트 통제 | 입출력 필터링, 개인식별정보(PII) 마스킹, 쓰기 승인 게이트 |

> **쓰기(Write) 작업 주의** — 티켓 생성·메시지 전송·DB 갱신처럼 **부수효과가 있는 도구**는 별도 승인 게이트·확인 절차를 두는 것을 강력히 권장합니다. 읽기 전용으로 시작해 점진적으로 권한을 확대하세요.

> **에어갭 환경** — 외부 반출이 불가한 환경에서는 MCP 연동 대상을 **내부 시스템(사내 DB·내부 ITSM)** 으로 한정하고, 외부 SaaS·외부 MCP 서버 등록을 차단합니다(Artifact Mirroring Tool(아티팩트 미러링 도구)로 미러링한 폐쇄망과 결합 → [근거: PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)).

---

## 6.4 도구 호출 동작 (런타임)

에이전트가 MCP 도구를 호출하는 일반 흐름입니다. **무엇을·언제·어떤 권한으로** 호출할지는 승인 정책과 시스템 지시(`instructions`)가 통제하며, LLM이 임의로 무제한 실행하지 않습니다.

```
사용자 질문 → ① LLM이 "도구 필요" 판단(tool call 결정)
            → ② 승인된 도구만, 권한 범위 내에서 호출
            → ③ 도구 결과를 컨텍스트로 주입
            → ④ (필요 시 지식베이스(KB) 문서와 종합) 최종 답변 + 출처
```

도구 호출 단계는 관측성으로 추적해야 합니다(호출된 도구·인자·결과·소요 시간) → [07 관측성](07-observability-ops.md).

---

## 6.5 에이전트 도구 설계 권장 사항

1. **읽기 우선, 쓰기 신중** — 부수효과 도구는 승인 게이트·시험 실행(dry-run)으로 시작.
2. **도구 최소화** — 한 에이전트에 도구가 너무 많으면 LLM의 도구 선택 정확도가 떨어집니다. 역할별로 분리.
3. **시스템 지시에 사용 규칙 명시** — "확실하지 않으면 도구를 호출하지 말 것", "민감 작업은 사용자 확인" 등.
4. **RAG vs 도구 역할 구분** — 사실·문서는 KB(RAG), 실시간·정형 데이터는 MCP 도구.
5. **거버넌스를 코드화(GitOps)** — `mcp-servers` 등록·`approval`·도구 연결을 IaC(코드형 인프라, Infrastructure as Code)로 관리해 재현·감사 가능하게.

---

[← 이전: 05 인증·게이트웨이](05-auth-and-gateway.md) · [목차](../README.md) · [다음: 07 관측성·운영 →](07-observability-ops.md)
