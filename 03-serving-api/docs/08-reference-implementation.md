# 08 — 레퍼런스 구현

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 아래 코드는 **최소 동작 예제**입니다. 경로·인증·필드는 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 제품 내 Sample Code로 확인 후 적용하세요. `{fqdn}`, `<...>` 는 환경값으로 치환합니다.

앞 문서들의 내용을 **실제로 호출하는 코드**로 모았습니다. 핵심 메시지는 변하지 않습니다. **`base_url`만 사내 PAIS로 바꾸면 됩니다.**

---

## 8.1 curl — 가장 빠른 확인

```bash
# 공통 변수
BASE="https://{fqdn}/api/v1/compatibility/openai/v1"
TOKEN="<access-token>"   # 발급 방법은 05 참조

# 1) 사용 가능한 모델 확인
curl -s "$BASE/models" -H "Authorization: Bearer $TOKEN"

# 2) 채팅 완성 (Model Endpoint, 상태 비저장)
curl -s -X POST "$BASE/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"model":"<completion-model-id>",
       "messages":[{"role":"user","content":"한 문장으로 자기소개 해줘"}],
       "max_tokens":128}'

# 3) 에이전트 호출 (RAG·세션 자동)
curl -s -X POST "$BASE/agents/hr-assistant/chat/completions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"연차 휴가는 며칠인가요?"}]}'
```

---

## 8.2 OpenAI Python SDK — base_url만 교체

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://{fqdn}/api/v1/compatibility/openai/v1",
    api_key="<access-token>",   # OIDC Bearer 토큰 (05 참조)
)

# (A) 단순 추론 — Model Endpoint
resp = client.chat.completions.create(
    model="<completion-model-id>",
    messages=[{"role": "user", "content": "분기 매출을 3줄로 요약해줘"}],
    temperature=0.2,
)
print(resp.choices[0].message.content)
print(resp.usage)   # prompt/completion/total tokens → 운영 로깅(07)

# (B) 스트리밍
for chunk in client.chat.completions.create(
        model="<completion-model-id>",
        messages=[{"role": "user", "content": "사내 보안 정책 핵심 5가지"}],
        stream=True):
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

> 기존에 외부 LLM API용으로 짜둔 코드라면, 위에서 바뀐 것은 `base_url`·`api_key`·`model` 세 가지뿐입니다. 호출 구조는 동일합니다.

---

## 8.3 에이전트 호출 — RAG를 직접 안 짜는 경우

에이전트의 OpenAI 호환 경로는 `agents/{id}` 하위에 놓입니다. 호출 방법은 두 가지입니다. SDK의 `base_url`을 에이전트 경로까지 포함하도록 지정하거나, 전체 경로를 직접 호출하면 됩니다.

```python
import httpx

BASE = "https://{fqdn}/api/v1/compatibility/openai/v1"
headers = {"Authorization": "Bearer <access-token>", "Content-Type": "application/json"}

r = httpx.post(
    f"{BASE}/agents/hr-assistant/chat/completions",
    headers=headers,
    json={"messages": [{"role": "user", "content": "출장비 정산 기한은?"}]},
)
data = r.json()
print(data["choices"][0]["message"]["content"])
print("세션:", data.get("session_id"))            # 다음 턴에 이어 붙이면 맥락 유지
print("출처:", data.get("index_context_info"))    # 답변 근거 문서 → UI에 표시
```

> 응답의 `session_id`·`index_context_info`가 Model Endpoint 대비 추가되는 핵심입니다([04.4](04-agent-rag-api.md#44-에이전트-채팅--post-agentsidchatcompletions)).

---

## 8.4 LangChain — 기존 자산 재사용 (패턴 2)

기존 LangChain RAG 코드가 있다면, LLM과 임베딩의 `base_url`만 사내 PAIS로 바꾸면 됩니다.

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

BASE = "https://{fqdn}/api/v1/compatibility/openai/v1"

llm = ChatOpenAI(
    base_url=BASE, api_key="<access-token>",
    model="<completion-model-id>", temperature=0.2,
)
embeddings = OpenAIEmbeddings(
    base_url=BASE, api_key="<access-token>",
    model="<embedding-model-id>",
)
# 이후 체인·리트리버는 기존 코드 그대로. 추론·임베딩만 사내로 이동.
```

> 멀티홉·리랭킹 등 고급 검색이나 특수 벡터 DB가 필요할 때 이 패턴(서빙은 PAIS, RAG는 코드)을 씁니다. 표준 Q&A라면 8.3의 Agent API가 더 간단합니다.

---

## 8.5 백엔드 중계(BFF, Backend For Frontend) 최소 골격

프론트엔드가 PAIS를 직접 부르지 않도록, 백엔드가 토큰을 들고 중계합니다([05.3](05-auth-and-gateway.md#53-토큰-운영--만료갱신보관)).

```python
# FastAPI 예시 — 토큰은 서버에서만, 프론트는 이 엔드포인트만 호출
from fastapi import FastAPI
from openai import OpenAI
import os

app = FastAPI()
client = OpenAI(
    base_url="https://{fqdn}/api/v1/compatibility/openai/v1",
    api_key=os.environ["PAIS_TOKEN"],   # Secret에서 주입, 코드에 하드코딩 금지
)

@app.post("/chat")
def chat(body: dict):
    # 여기서 앱 사용자 인증·권한·로깅·필터링을 수행(Gateway가 대신 안 해줌 → 05.4)
    resp = client.chat.completions.create(
        model=os.environ["MODEL_ID"],
        messages=body["messages"],
    )
    return {"content": resp.choices[0].message.content,
            "usage": resp.usage.model_dump()}   # 사용량 로깅 → 부서별 비용 배분(쇼백, 07.1)
```

---

## 8.6 엔드투엔드 체크리스트 (PoC → 프로덕션)

```
- 토큰 발급 경로 확인        env.json → IdP 토큰 발급 (05)
- 모델 목록 호출 성공         GET /models 200 OK
- 단순 추론 성공             chat/completions 응답·usage 확인
- (RAG 필요 시) KB·인덱스 구성  data-sources→KB→index→indexing (04)
- 에이전트 호출·출처 확인      agents/{id}/chat/completions, index_context_info (04)
- 스트리밍 동작 확인          stream=true, TTFT 체감 (03.5)
- 백엔드 중계 구조            토큰 서버 보관, 프론트 비노출 (05.3)
- 관측성                    usage 로깅, OTel 트레이스 수신 검증 (07)
- 보안                      TLS, 인증/인가, (MCP 시) 승인·읽기우선 (06)
- 모델 버전 관리             ConfigMap 분리, 카나리·롤백 경로 (07.5)
```

---

## 엔드포인트 전체 치트시트

**OpenAI 호환 인터페이스** — `https://{fqdn}/api/v1/compatibility/openai/v1`

| 동작 | 메서드·경로 |
|------|------------|
| 모델 목록 | `GET /models` |
| 임베딩 생성 | `POST /embeddings` |
| 채팅 완성 | `POST /chat/completions` |
| 에이전트 목록/생성 | `GET` / `POST /agents` |
| 에이전트 조회/수정/삭제 | `GET` / `POST` / `DELETE /agents/{id}` |
| 에이전트 채팅 | `POST /agents/{id}/chat/completions` |

**컨트롤 플레인** — `https://{fqdn}/api/v1/control`

| 동작 | 메서드·경로 |
|------|------------|
| 데이터 소스 | `POST /data-sources`, `POST /data-sources/test-connection`, `DELETE /data-sources/{id}` |
| 지식베이스 | `POST` / `GET /knowledge-bases`, `POST /knowledge-bases/{id}/data-sources`, `DELETE /knowledge-bases/{id}` |
| 인덱스 | `POST /knowledge-bases/{id}/indexes`, `POST .../indexes/{id}/indexings`, `GET .../active-indexing`, `POST .../search` |
| MCP | `POST /mcp-servers`, `GET /mcp-servers/tools`, `POST /mcp-servers/{id}/tools/{tid}/approval` |

> 위 경로·필드는 작성 시점 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/) 기준입니다. PAIS 버전에 따라 변경될 수 있으니 적용 직전 공식 레퍼런스로 확인하시기 바랍니다.

---

①②③ 흐름이 ④ RAG로 이어집니다. 인프라([①](../../01-infra/README.md)) → 데이터([②](../../02-vectordb/README.md)) → 서빙(③ 본 가이드) → 통합 RAG([④](../../04-rag/README.md)).

---

[← 이전: 07 관측성·운영](07-observability-ops.md) · [목차](../README.md)
