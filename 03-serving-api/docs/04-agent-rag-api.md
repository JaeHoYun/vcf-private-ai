# 04 — 에이전트·RAG API

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 경로·필드는 [공식 PAIS API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/) 기준이며, 버전에 따라 변경될 수 있습니다.

[03](03-openai-compatible-endpoints.md)의 Model Endpoint가 "모델 1회 호출"이라면, **Agent API는 RAG·세션·도구를 묶어 한 번에 호출**합니다. 대부분의 문서 기반 Q&A 앱은 RAG 로직을 직접 구현하는 대신 이 API를 호출하는 편이 구현 분량이 적고 오류 가능성도 낮습니다.

---

## 4.1 RAG를 구성하는 리소스 4종

Agent가 문서 기반으로 답하려면, 그 뒤에 데이터 파이프라인 리소스가 있어야 합니다. PAIS는 이를 각각의 API 리소스로 노출합니다.

```
Data Source ──▶ Knowledge Base ──▶ Index ──▶ (검색) ──▶ Agent
 원천 데이터      논리적 묶음        임베딩·청크    의미 검색     RAG 응답
 (문서 위치)     (KB)              저장소         top_k         + 출처
```

| 리소스 | 역할 | 핵심 경로(컨트롤 플레인) |
|--------|------|------------------------|
| **Data Source** | 원천 데이터 연결 정의 | `/control/data-sources` |
| **Knowledge Base** | 데이터 소스를 묶는 논리 단위 | `/control/knowledge-bases` |
| **Index** | 청크·임베딩 색인 | `/control/knowledge-bases/{kb-id}/indexes` |
| **Agent** | 모델 + KB(+도구)를 묶은 호출 단위 | `/compatibility/openai/v1/agents` |

> OpenAI 호환 인터페이스(`/compatibility/openai/v1`)에는 **모델·에이전트 호출**이, 컨트롤 플레인(`/control`)에는 **데이터·인덱스·MCP(Model Context Protocol) 도구 관리**가 놓입니다. 호출(런타임) vs 관리(구성)의 분리로 이해하면 경로가 외워집니다.

---

## 4.2 데이터 소스 · 지식베이스 · 인덱스 (RAG 구성 API)

UI로 구성할 수도 있지만, GitOps·자동화를 위해 API로 구성하는 흐름을 정리합니다.

**① 데이터 소스 등록**

| 항목 | 값 |
|------|----|
| 연결 테스트 | `POST /control/data-sources/test-connection` (`origin_url`, `type`, `credentials`) |
| 생성 | `POST /control/data-sources` (`origin_url`, `name`, `type`, `credentials`) |

**② 지식베이스 생성·연결**

| 항목 | 값 |
|------|----|
| 생성 | `POST /control/knowledge-bases` (`name`, `data_origin_type`, `index_refresh_policy`) |
| 데이터 소스 연결 | `POST /control/knowledge-bases/{kb-id}/data-sources` (`data_source_id`) → 초기 상태 `NOT_INDEXED` |

**③ 인덱스 생성·색인**

| 항목 | 값 |
|------|----|
| 인덱스 생성 | `POST /control/knowledge-bases/{kb-id}/indexes` (`embeddings_model_endpoint`, `chunk_size`, `chunk_overlap`, `text_splitting`) |
| 색인 트리거 | `POST .../indexes/{index-id}/indexings` → 상태 `PENDING` |
| 진행 확인 | `GET .../indexes/{index-id}/active-indexing` → `PENDING`/`DONE` |

**④ 인덱스 직접 검색 (RAG 디버깅에 유용)**

| 항목 | 값 |
|------|----|
| 검색 | `POST .../indexes/{index-id}/search` (`text`, `top_k`, `similarity_cutoff`) |
| 응답 | `chunks[]`(`text`, `score`, `document_id`, `origin_name`, `metadata`) |

> `search`는 **Agent를 거치지 않고 검색 품질만 따로 점검**할 때 매우 유용합니다. 답이 이상하면 "검색이 문제인지(잘못된 청크가 올라옴) 생성이 문제인지(좋은 청크인데 답이 틀림)"를 이 엔드포인트로 분리 진단할 수 있습니다. 벡터 인덱스·청크 튜닝의 상세는 형제 가이드 [vectorDB 편](../../02-vectordb/README.md) 참조.

---

## 4.3 에이전트 CRUD

| 동작 | 메서드·경로 |
|------|------------|
| 목록 | `GET /compatibility/openai/v1/agents` (`limit`, `offset`, `order`) |
| 생성 | `POST /compatibility/openai/v1/agents` |
| 조회 | `GET /compatibility/openai/v1/agents/{agent-id}` |
| 수정 | `POST /compatibility/openai/v1/agents/{agent-id}` (부분 수정; 선택값 해제는 `null`) |
| 삭제 | `DELETE /compatibility/openai/v1/agents/{agent-id}` |

**생성 요청의 핵심 필드**

| 필드 | 의미 |
|------|------|
| `name`, `description` | 에이전트 식별·설명 |
| `model` | 사용할 Completion Model Endpoint |
| `instructions` | 시스템 지시(규칙·톤·제약) |
| `tools[]` | 연결할 도구 (`link_type`, `tool_id`) — KB·MCP 도구 → [06](06-mcp-tools-api.md) |
| `session_max_length` | 세션 최대 길이(대화 맥락 한도) |
| `session_summarization_strategy` | 맥락 초과 시 요약 전략 |
| `index_reference_format` | 출처(참조) 표기 형식 (예: `structured` 또는 `null`) |

```bash
curl -s -X POST 'https://{fqdn}/api/v1/compatibility/openai/v1/agents' \
  -H 'Authorization: Bearer <access-token>' -H 'Content-Type: application/json' \
  -d '{
    "name":"hr-assistant",
    "description":"사내 인사 규정 Q&A",
    "model":"<completion-model-id>",
    "instructions":"인사 규정 문서에 근거해서만 답하고, 모르면 모른다고 답한다.",
    "tools":[{"link_type":"knowledge_base","tool_id":"<kb-id>"}]
  }'
```

> 위 `tools`의 `link_type`·`tool_id` 값 형식은 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)의 스키마와 제품 내 Sample Code로 정확히 확인하세요. KB 연결과 MCP 도구 연결의 표기가 다를 수 있습니다.

---

## 4.4 에이전트 채팅 — `POST /agents/{id}/chat/completions`

에이전트를 호출하는 런타임 엔드포인트입니다. 형태는 `chat/completions`와 같지만, **RAG·세션이 자동으로 끼워집니다.**

| 항목 | 값 |
|------|----|
| 경로 | `POST /compatibility/openai/v1/agents/{agent-id}/chat/completions` |
| 요청 | `messages[]`, `temperature`, `max_tokens`, `stream` |
| 응답 | `id`, `object`, `model`, `choices[]`, `usage`, **`session_id`**, **`index_context_info`** |

```bash
curl -s -X POST 'https://{fqdn}/api/v1/compatibility/openai/v1/agents/hr-assistant/chat/completions' \
  -H 'Authorization: Bearer <access-token>' -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"연차 휴가는 며칠인가요?"}]}'
```

응답에서 Model Endpoint 대비 **추가되는 두 가지**:

| 추가 필드 | 의미 | 활용 |
|----------|------|------|
| `session_id` | PAIS가 관리하는 세션 식별자 | 다음 요청에 이어 붙이면 대화 맥락 유지 |
| `index_context_info` | 답변에 사용된 출처(검색된 문서/청크) | 답변 UI에 "근거 문서" 표시, 환각 검증 |

**두 번째 턴 — `session_id`를 이어 붙이기**

첫 응답에서 받은 `session_id`를 **후속 요청에 그대로 실어 보내면** PAIS가 이전 맥락을 이어받습니다. 앱은 이전 `messages`를 다시 누적할 필요 없이, **이번 턴의 사용자 발화만** 보내면 됩니다(Model Endpoint와의 결정적 차이).

전달 위치는 배포·버전에 따라 **요청 바디** 또는 **헤더**가 쓰일 수 있습니다. 두 방식 모두 예시로 제시하되, 적용 전 공식 레퍼런스로 정확한 위치를 확인하시기 바랍니다.

```bash
# 방식 A) 요청 바디에 session_id 포함 (두 번째 턴: 이번 발화만 전송)
curl -s -X POST 'https://{fqdn}/api/v1/compatibility/openai/v1/agents/hr-assistant/chat/completions' \
  -H 'Authorization: Bearer <access-token>' -H 'Content-Type: application/json' \
  -d '{
    "session_id":"<첫-응답에서-받은-session_id>",
    "messages":[{"role":"user","content":"그럼 반차도 연차에서 차감되나요?"}]
  }'
```

```bash
# 방식 B) 헤더로 session_id 전달 (바디는 이번 발화만)
curl -s -X POST 'https://{fqdn}/api/v1/compatibility/openai/v1/agents/hr-assistant/chat/completions' \
  -H 'Authorization: Bearer <access-token>' -H 'Content-Type: application/json' \
  -H 'x-pais-session-id: <첫-응답에서-받은-session_id>' \
  -d '{"messages":[{"role":"user","content":"그럼 반차도 연차에서 차감되나요?"}]}'
```

> **면책** — 위 `session_id`의 전달 위치(바디 필드명 `session_id` / 헤더명 `x-pais-session-id`)는 **예시**입니다. PAIS 버전에 따라 필드명·헤더명·전달 위치가 다를 수 있으므로, 적용 전 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 제품 내 Sample Code로 정확한 키를 확인하시기 바랍니다. `session_id`를 생략하면 매 요청이 **새 세션**으로 처리되어 맥락이 끊깁니다.

> **세션을 PAIS가 관리**하므로, 앱은 대화 이력을 직접 쌓지 않아도 됩니다(Model Endpoint와의 가장 큰 차이). 다만 사용자에게 보여줄 **대화 이력의 영구 저장**(감사·재현용)은 여전히 앱이 자체 DB에 남기는 것을 권장합니다 — PAIS 세션은 운영용 맥락이지 앱의 영구 기록이 아닙니다.

---

## 4.5 Model Endpoint API vs Agent API — 최종 선택표

| 상황 | 선택 |
|------|------|
| 표준 문서 Q&A·사내 챗봇(대다수) | **Agent API** (RAG·세션·출처 자동) |
| 멀티홉·리랭킹·Self-RAG 등 고급 검색 | Model Endpoint API + 직접 RAG |
| 기존 LangChain/LlamaIndex 자산 재사용 | Model Endpoint API (OpenAI 호환으로 연결) |
| 단순 요약·분류 등 RAG 불필요 | Model Endpoint API |
| 임베딩만 필요 | `embeddings` 엔드포인트 |

> 패턴 선택의 더 넓은 맥락(관리형 엔드투엔드 vs 커스텀 RAG)은 형제 가이드 [04](../../01-infra/docs/04-dev-scenarios.md)를 참조하세요. 본 가이드는 그중 **API 호출 계층**을 구체화합니다.

---

[← 이전: 03 OpenAI 호환 엔드포인트](03-openai-compatible-endpoints.md) · [목차](../README.md) · [다음: 05 인증·게이트웨이 →](05-auth-and-gateway.md)
