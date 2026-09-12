# 05 — 인증과 게이트웨이

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)를 참조하세요.
> 인증 방식은 PAIS 버전과 배포 구성에 따라 달라질 수 있으므로, 적용 전 [공식 API 레퍼런스](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)와 제품 내 Sample Code로 확인하시기 바랍니다.

API는 "어떻게 호출하느냐"만큼 "누가 호출하느냐"가 중요합니다. PAIS API Gateway 앞에서 인증이 어떻게 이뤄지는지 정리합니다.

---

## 5.1 두 가지 인증 패턴

PAIS API에 접근하는 방식은 공식 자료에서 **세 가지**가 확인됩니다. 용도가 다르므로 구분해서 씁니다.

| 패턴 | 무엇 | 어디서 확인됨 | 적합 |
|------|------|--------------|------|
| **① OIDC Bearer 토큰** (주) | OIDC로 발급받은 액세스 토큰을 `Authorization: Bearer`로 전달 | 공식 PAIS API 레퍼런스 | 일반 앱과 서비스의 표준 호출 |
| **② mTLS** (보조) | 클라이언트 인증서(상호 TLS)로 신원 증명, API 키는 형식상 채우는 값(실제 인증에 쓰이지 않음) | Open WebUI 연동 사례(프록시 구성) | 서비스-서비스/프록시 연동, 인증서 기반 환경 |
| **③ API 토큰** (3.0부터) | VCF Automation 계정 또는 PAIS 로컬 계정이 발급한 장기 토큰을 같은 `Authorization: Bearer` 헤더로 전달 | 공식 문서(Generate API Tokens) | 다른 PAIS 인스턴스의 공유 모델 접근, VCF Consumption CLI 실행, IdP 없이 도는 무인 클라이언트 |

> **앱 코드에서는 ① OIDC Bearer 토큰**을 기본으로 생각하면 됩니다. ②는 Open WebUI처럼 게이트웨이/프록시를 앞에 두고 인증서로 신원을 보증하는 배포 패턴입니다. ③은 인스턴스 사이를 잇거나 CLI를 돌릴 때 필요한 수단이며, 일반 앱 호출을 ①에서 ③으로 바꿀 이유는 없습니다(5.6절). 어느 쪽을 쓸지는 조직의 PAIS 배포와 보안 구성에 따릅니다.

---

## 5.2 OIDC Bearer 토큰 — 획득과 사용

PAIS는 인스턴스에 설정된 **OIDC Identity Provider(IdP)** 로부터 토큰을 받습니다.

**① OIDC 설정 확인** — 인스턴스의 OIDC 구성(토큰 엔드포인트, client-id, scope)은 다음에서 조회합니다.

```
GET https://{fqdn}/env.json
```

**② 토큰 발급** — 공식 레퍼런스의 파이썬 예시는 OAuth2 Resource Owner Password 방식(사용자명 + API 토큰)을 보여줍니다.

```python
import httpx_auth

oidc_auth = httpx_auth.OAuth2ResourceOwnerPasswordCredentials(
    token_url="<IdP token endpoint>",   # env.json에서 확인
    client_id="<OIDC client-id>",       # env.json에서 확인
    scope="<OIDC scopes>",
    username="<username>",
    password="<api_token>",
)
```

**③ 호출** — 발급받은 액세스 토큰을 모든 요청 헤더에 넣습니다.

```
Authorization: Bearer <access-token>
```

```
인증 흐름 요약

  앱 ──① env.json 조회─────────────▶ PAIS  (OIDC 설정 획득)
  앱 ──② 토큰 발급 요청────────────▶ IdP   (username + api_token)
  앱 ◀── access_token ───────────── IdP
  앱 ──③ API 호출(Bearer token)────▶ API Gateway ─▶ Model Runtime
```

> 위 발급 방식(Resource Owner Password)은 공식 레퍼런스 예시 기준입니다. 조직에 따라 **서비스 계정 + 클라이언트 자격증명(Client Credentials)** 등 다른 OIDC 그랜트를 쓰도록 구성했을 수 있습니다. 실제 그랜트 타입과 scope는 PAIS/IdP 구성에 맞춰 확인하세요.

---

## 5.3 토큰 운영 — 만료, 갱신, 보관

| 항목 | 권장 |
|------|------|
| **만료** | 액세스 토큰은 만료 시간이 있습니다. 만료 전 선제 갱신 로직을 구현하세요. |
| **보관 위치** | 토큰과 자격증명은 **백엔드에서만** 다루고 프론트엔드에 노출하지 마세요. |
| **시크릿 관리** | `client_secret`, `api_token`은 Secret 저장소(예: K8s Secret)로 관리, 코드와 이미지에 하드코딩 금지. |
| **최소 권한** | 토큰의 권한과 scope를 호출에 필요한 최소로 제한하세요(네임스페이스 경계 활용). |
| **회전(rotation)** | 자격증명은 정기적으로 회전하고, 유출 시 즉시 폐기와 재발급 절차를 둡니다. |

> 프론트엔드(브라우저/모바일)에서 PAIS를 **직접** 호출하지 마세요. 토큰이 클라이언트에 노출됩니다. 항상 **백엔드(BFF, Backend For Frontend)가 중계**하고, 백엔드에서 토큰을 관리하고 주입하는 구조를 권장합니다.

---

## 5.4 API Gateway가 해주는 것 / 안 해주는 것

| Gateway가 제공 | 앱이 책임 |
|---------------|----------|
| 요청 인증(토큰 검증) | 사용자 로그인과 세션(앱 자체 인증) |
| 모델과 에이전트 호출 인가 | 비즈니스 권한(누가 어떤 기능을 쓰는지) |
| 복제본 간 로드밸런싱 | 호출량 제어(앱 측 큐잉과 백프레셔) |
| 단일 진입 URL 제공 | 재시도, 타임아웃, 서킷브레이커 |

> Gateway는 **PAIS 자원에 대한** 인증과 인가를 담당하지, **앱 사용자에 대한** 인증을 대신하지 않습니다. "이 사람이 이 메뉴를 쓸 수 있는가"는 앱이 결정하고, "이 토큰이 이 모델을 호출할 수 있는가"는 Gateway가 결정합니다.

---

## 5.5 레이트리밋, 쿼터, 로드밸런싱, 복제본

이 절은 "**호출량이 몰릴 때 무엇이 막아주고, 무엇을 앱이 책임지는가**"를 정리합니다. 결론부터: **로드밸런싱과 리소스 쿼터는 플랫폼이, 호출 빈도(rate) 제어는 상당 부분 앱이** 책임집니다.

**① 로드밸런싱과 스케일링 (Gateway/플랫폼 제공)**

- **로드밸런싱** — 같은 모델의 여러 복제본에 Gateway가 요청을 분산합니다. 앱은 복제본 수를 몰라도 됩니다.
- **스케일링** — 트래픽 증가는 복제본 증설로 흡수합니다. 복제본은 GPU를 점유하므로 비용과 직결됩니다 → [07 운영](07-observability-ops.md).

**② 리소스 쿼터 (네임스페이스 경계)**

- PAIS는 VCF Automation의 **네임스페이스 단위 리소스 쿼터**(GPU, 복제본 한도) 위에서 동작합니다([02.8](02-serving-api-architecture.md#28-멀티테넌시와-네임스페이스-경계)). 즉 한 네임스페이스가 무한정 자원을 점유하지 못하도록 **용량 상한**이 걸립니다. 다만 이는 "초당 요청 수(RPS)"를 직접 제한하는 **API 레이트리밋과는 다른 축**입니다 — 용량(capacity) 통제이지 호출 빈도(rate) 통제가 아닙니다.

**③ API 레이트리밋 — 현황과 보완**

- **게이트웨이 측 레이트리밋 현황** — 작성 시점([PAIS 릴리스 노트](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)) 기준, PAIS API Gateway가 **사용자/토큰별 요청 속도 제한(per-key rate limit)** 을 표준 기능으로 노출한다는 점은 공식 문서에서 명시 확인되지 않습니다. 따라서 외부 LLM SaaS처럼 "분당 토큰/요청 한도"가 게이트웨이에서 보장된다고 **가정하지 마세요**. (정책 제공 여부는 PAIS 버전과 배포 구성에 따라 다를 수 있으므로 적용 직전 공식 레퍼런스로 확인 필요.) 2026-08 Explore에서 프롬프트 라우팅과 사용자 단위 토큰 제한과 OpenID Connect 기반 앱 인가를 갖춘 AI Gateway가 발표됐지만 PAIS 3.0 릴리스 노트에는 없는 향후 기능이므로([① 00 0.7.4절](../../01-infra/docs/00-whats-new.md)), 이 절의 결론은 그대로입니다. 한편 서드파티 AI 게이트웨이(멀티 LLM 라우팅, 토큰 귀속과 레이트리밋, 팀별 예산 상한, 응답 캐시)를 VCF의 VKS 위에서 검증한 사례가 2026-08에 공개됐습니다([Solo.io agentgateway와 kagent, VCF 블로그](https://blogs.vmware.com/cloud-foundation/2026/08/07/running-solo-io-enterprise-agentgateway-and-kagent-on-vmware-cloud-foundation/), [TrueFoundry AI Gateway](https://www.truefoundry.com/blog/truefoundry-ai-gateway-on-vmware-cloud-foundation)). 두 사례 모두 참조 아키텍처는 작성 중이고 PAIS 엔드포인트를 백엔드로 썼는지는 밝히지 않았으므로, 게이트웨이 계층을 PAIS 앞에 별도로 둘지는 조직의 요건(여러 팀의 차지백, 토큰 예산, 모델 혼용 라우팅)에 따라 판단합니다.
- **혼잡 시 신호** — 용량을 초과하면 요청은 `429`(속도 초과/큐 포화), `503`(복제본 기동 중, 일시 과부하)으로 반환될 수 있습니다. 앱은 이를 **지수 백오프로 재시도**해야 합니다([03.9 에러 처리](03-openai-compatible-endpoints.md#39-에러-처리와-재시도)).
- **앱 측 보호(필수 보완)** — 게이트웨이 레이트리밋에 의존할 수 없으므로, 폭주 트래픽으로부터 백엔드와 GPU를 보호하는 1차 방어선은 **앱**입니다. 다음을 권장합니다.
  - **동시성 제한** — 백엔드에서 PAIS로 나가는 동시 요청 수에 상한(세마포어/커넥션 풀)을 둡니다.
  - **클라이언트 측 레이트리밋** — 사용자/테넌트별 요청 속도를 앱이 토큰버킷 등으로 제한합니다.
  - **타임아웃과 서킷브레이커** — AI 응답은 초 단위로 길어질 수 있어 타임아웃이 특히 중요합니다. 연속 실패 시 서킷을 열어 폭주를 차단합니다.
  - **백프레셔/큐잉** — 처리 한도를 넘는 요청은 큐잉하거나 즉시 거절(`429` 반환)해 GPU 포화를 막습니다.

> **요약** — PAIS는 **로드밸런싱과 용량 쿼터**를 제공하지만, **"초당 몇 건까지"를 게이트웨이가 끊어준다는 보장은 현재 명시되어 있지 않습니다.** 그러므로 호출 빈도 제어와 과부하 방지는 **앱 측 보호로 반드시 보완**하시기 바랍니다. 게이트웨이 레이트리밋 정책이 향후 제공/변경될 수 있으니 적용 직전 공식 문서로 재확인하세요.

---

## 5.6 API 토큰 (PAIS 3.0부터)

3.0은 OIDC 액세스 토큰과 별개로 **API 토큰**을 도입했습니다. 계정이 직접 발급하는 장기 토큰이며, 세 가지 일에 쓰입니다. 다른 PAIS 인스턴스에서 서빙 중인 공유 모델에 접근할 때, VCF Automation 네임스페이스에서 VCF Consumption CLI 명령을 실행할 때, 그리고 PAIS API 자체에 인증할 때입니다. 공식 문서는 외부 OIDC 공급자가 발급한 토큰으로는 다른 인스턴스의 모델에 접근할 수 없다고 명시하므로, 인스턴스 간 연결에는 이 토큰이 사실상 유일한 수단입니다.

| 항목 | 내용 |
|------|------|
| 발급 주체 두 가지 | VCF Automation 계정은 조직 설정의 API Tokens 화면에서, PAIS 로컬 계정은 PAIS UI의 계정 메뉴에서 발급 |
| 토큰 형식 | VCF Automation 계정 `vcfa-<org>-<값>`, 로컬 계정 `pais-<인증공급자>-<값>` (UI로 만든 로컬 계정은 `pais-sc-<값>`) |
| 사용 방법 | `Authorization: Bearer <토큰>` 헤더. OIDC 액세스 토큰과 같은 자리 |
| 전제 | 인스턴스 설정에서 API 토큰 발급이 켜져 있어야 함. UI로 PAIS를 활성화하면 기본으로 꺼져 있는 알려진 이슈가 있으므로 활성화 뒤 확인 |
| 만료와 회수 | 공식 문서가 만료 기간과 회수 절차를 명시하지 않음(확인 필요). 장기 토큰이므로 조직 정책으로 회전 주기와 폐기 절차를 정해 두어야 함 |

**어디에 쓰고 어디에 쓰지 않나**

- 인스턴스 간 공유 모델 연결(consumer가 provider를 호출)과 CLI 자동화에는 API 토큰을 씁니다.
- 일반 앱의 사용자 요청 경로는 그대로 ① OIDC 액세스 토큰(5.2절)을 씁니다. API 토큰은 사용자 신원을 담지 않으므로, 앱이 사용자별 권한을 구분해야 하는 경로에 API 토큰 하나를 공유하면 감사 추적이 끊깁니다.
- API 토큰은 시크릿입니다. 5.3절의 보관 원칙(백엔드에서만, Secret 저장소, 하드코딩 금지)이 그대로 적용됩니다.

거버넌스 관점의 수명과 회전 기준은 [⑤ 03 3.3절](../../05-security/docs/03-identity-access.md)에서 다룹니다. ([근거: Generate API Tokens for VCF Automation or Local Private AI Services Accounts](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-1/what-is-private-ai-services/generate-api-tokens-for-local-accounts.html))

---

## 5.7 게이트웨이 계층 설계 — 3계층 모델과 현 시점 선택지

5.4절과 5.5절은 PAIS 내장 게이트웨이가 무엇을 하고 무엇을 하지 않는지를 밝혔습니다. 이 절은 "그럼 무엇으로 대신하나"에 답합니다. 팀 하나가 앱 하나를 올릴 때는 5.5절의 앱 측 보호로 충분하지만, 여러 사업부가 같은 플랫폼을 쓰는 순간 차지백, 팀별 토큰 예산, 온프레미스와 클라우드 모델 혼용, 공용 가드레일이 필요해지고, 이것을 앱마다 재구현하는 구조는 오래가지 못합니다. 그래서 게이트웨이를 **별도 계층**으로 설계합니다.

### 5.7.1 3계층 모델과 책임 매트릭스

| 계층 | 담당 | 구현 후보 |
|------|------|-----------|
| **0계층 경계** | 조직 인증(SSO), WAF, TLS 종단, VIP, 전역 L7 레이트리밋 | Avi Load Balancer([⑦ 04 4.2절](../../07-design/docs/04-network-storage-availability.md)), 또는 조직이 이미 보유한 API 관리 플랫폼 |
| **1계층 AI 게이트웨이** | 키와 팀별 토큰 예산과 쿼터, 비용 귀속, 온프레미스와 클라우드 모델 라우팅과 폴백, 모델 별칭, 시맨틱 캐시, 가드레일 훅, 프롬프트와 응답 로깅, MCP 정책 | 오픈소스 또는 상용 AI 게이트웨이(5.7.3절), 향후 Broadcom AI Gateway([① 00 0.7.4절](../../01-infra/docs/00-whats-new.md)) |
| **2계층 PAIS 서빙 게이트웨이** | PAIS 자원의 인증과 인가, 복제본 로드밸런싱, 모델명 라우팅, mTLS, 원격 모델 라우트(`InferenceGatewayRoute`) | PAIS 내장(5.4절, [02 2.6절](02-serving-api-architecture.md)) |

계층이 겹치면 정책도 겹칩니다. 0계층과 1계층이 모두 레이트리밋을 걸면 어느 쪽이 먼저 끊는지 아무도 모르게 됩니다. 그래서 기능마다 담당 계층을 하나로 고정합니다.

| 기능 | 0계층 | 1계층 | 2계층 | 앱 |
|------|:---:|:---:|:---:|:---:|
| 조직 사용자 인증(SSO) | 담당 | | | 사용자 세션 |
| 서비스 인증과 PAIS 자원 인가 | | | 담당 | |
| 요청 단위 레이트리밋(RPS) | 전역 상한 | 키와 팀 단위 | | 1계층 없으면 앱 |
| 토큰 예산과 차지백 | | 담당 | | 1계층 없으면 앱이 usage 집계 |
| 모델 라우팅과 폴백 | | 담당(별칭) | 복제본과 원격 라우트 | 1계층 없으면 앱 설정 |
| 캐시 | | 응답과 시맨틱 캐시 | 엔진의 프리픽스 캐싱 | 1계층 없으면 앱 |
| 가드레일 | WAF(L7) | 훅(선택) | | 입력 분류기와 출력 필터는 앱이 기본 담당([⑤ 06](../../05-security/docs/06-app-guardrails.md)) |
| 요청 로깅과 추적 | 접근 로그 | 프롬프트와 응답 로그 | LLM 트레이싱(07) | 앱 레벨 지표 |

트래픽 평면도 셋으로 나뉩니다. **north-south**(앱 → LLM)는 1계층의 본령이고, **east-west**(에이전트 → 도구와 MCP, 에이전트 사이)는 도구별 인가와 세션 지속과 감사가 필요한 다른 평면이며 AgentMinder(별도 제품, 2026-08-31 GA)와 Avi 32.1.1의 MCP 로드밸런싱이 이 자리를 겨냥합니다. **클러스터 내부 inference gateway**(모델 인식 라우팅, Kubernetes Gateway API Inference Extension)는 2계층에 해당하지만, PAIS 내장 게이트웨이가 KV 캐시나 프리픽스 인식 스케줄링을 하는지는 문서화되어 있지 않습니다.

### 5.7.2 현 시점 선택지 네 가지

| 선택지 | 적합 조건 | 감수할 것 |
|--------|-----------|-----------|
| (1) PAIS 내장 + 앱 측 보호(5.5절) | 단일 테넌트나 소수 팀, 차지백 불필요, OIDC 인증과 모델 교체 투명성과 기본 토큰 추적으로 충분 | Broadcom AI Gateway의 시점이 미공개. 임시로 Avi L7 레이트리밋과 WAF, 토큰 회전, VCF Operations 메트릭 |
| (2) 오픈소스 AI 게이트웨이를 지금 도입 | 여러 사업부의 차지백, 팀별 토큰 예산, 온프레미스와 클라우드 모델 혼용 라우팅, MCP 거버넌스, 공용 가드레일이 당장 필요 | 게이트웨이가 단일 장애점. 레플리카, 상태 저장소 HA, 비상 시 PAIS 직결 우회 경로를 설계 |
| (3) 기존 API 관리 플랫폼 확장 | Apigee, Kong, Azure API Management, Layer7 같은 플랫폼이 이미 인증과 개발자 포털과 감사의 정본 | 토큰 단위 한도(요청 수가 아닌), 스트리밍 청크의 토큰 집계, MCP 프록시, 온프레미스 런타임 여부를 먼저 확인 |
| (4) 결합 | 대기업의 기본값. 0계층 기존 플랫폼이나 Avi + 1계층 AI 게이트웨이 + 2계층 PAIS | 위의 책임 매트릭스를 문서로 고정해 이중 정책 방지 |

서드파티 AI 게이트웨이를 VCF의 VKS 위에서 검증한 공개 사례는 5.5절에 적은 두 건(2026-08)이며, 참조 아키텍처는 작성 중입니다.

### 5.7.3 온프레미스와 에어갭에서의 후보 선정 기준

후보를 고를 때 다섯 가지를 먼저 봅니다. (1) SaaS 컨트롤플레인에 의존하지 않고 완전 자체 호스팅이 되는가. (2) 이미지와 Helm 차트를 Artifact Mirroring Tool이나 Harbor로 미러링할 수 있는가. (3) OpenAI 호환 패스스루와 모델 별칭을 지원하는가. (4) OpenTelemetry GenAI 시맨틱 컨벤션으로 추적을 내보내는가. (5) Kubernetes Gateway API나 Inference Extension과 정합해 향후 이식이 쉬운가(Avi의 AKO가 Gateway API를 지원하므로 개념이 맞물립니다).

작성 시점(2026-09) 기준으로 이 기준을 통과하는 오픈소스 후보는 Agent Router(구 Envoy AI Gateway, Apache 2.0, Agentic AI Foundation 산하), agentgateway와 kgateway(Apache 2.0, CNCF Sandbox), LiteLLM(MIT에 상용 Enterprise 기능 분리), Apache APISIX의 AI 플러그인입니다. 반대로 관리형 컨트롤플레인이 필수인 제품(예: Kong AI Gateway 2.0의 Konnect 의존)이나 SaaS 전용 게이트웨이는 폐쇄망에서 성립하지 않거나 오프라인 모드를 따로 확인해야 합니다. 이 가이드는 어느 후보도 실측하지 않았으므로, 선정은 조직의 운영 역량(Envoy 계열은 Envoy 운영 경험, LiteLLM은 PostgreSQL 의존과 메모리 관리)과 함께 PoC로 확인하십시오. 시맨틱 캐시는 온프레미스 임베딩(PAIS Infinity 엔드포인트 활용 가능)과 Redis나 pgvector가 필요하고, 가드레일 모델도 내부에 두어야 합니다.

### 5.7.4 배치와 운영

1계층은 GPU가 없는 별도 VKS 네임스페이스(또는 VPC)에 레플리카 2 이상으로 두고 Avi VIP 뒤에 놓습니다. PostgreSQL이나 Redis 같은 상태 저장 의존성은 HA 범위에 포함합니다. PAIS는 zone 수준 HA가 없으므로 모델 엔드포인트 레플리카 2 이상과 짝을 맞춥니다. vDefend 분산 방화벽으로 앱 클러스터, 게이트웨이, 모델 클러스터, 벡터 DB 사이를 기본 거부로 나눕니다([⑤ 02](../../05-security/docs/02-network-tenant-isolation.md)). 원격 클라우드 모델로의 라우팅은 NSX egress 명시 허용이 전제이며 폐쇄망에서는 성립하지 않고, 반출 통제는 [⑤ 05 5.6절](../../05-security/docs/05-data-governance.md)을 따릅니다. 논리 배치도는 [⑦ 04 4.2절](../../07-design/docs/04-network-storage-availability.md)에 있습니다.

### 5.7.5 전환 원칙 — 나중에 싸게 바꾸기

어느 선택지를 고르든 다음을 지키면 Broadcom AI Gateway가 나왔을 때 1계층을 교체하거나 축소하는 비용이 작습니다.

1. 앱은 PAIS가 이미 노출하는 OpenAI 호환 `/v1` 계약만 바라보고 게이트웨이 고유 SDK나 헤더에 의존하지 않습니다.
2. 모델 이름은 게이트웨이의 별칭 계층으로 고정해 백엔드 교체가 앱에 보이지 않게 합니다.
3. 텔레메트리는 OpenTelemetry GenAI 시맨틱 컨벤션으로 통일해 PAIS 트레이싱과 한 파이프라인에 모읍니다. 컨벤션이 아직 안정 상태가 아니므로 스키마 변경을 흡수할 수집 계층을 둡니다.
4. 라우팅 설정은 가능한 한 Gateway API 자원(HTTPRoute, InferencePool)으로 표현합니다.
5. Broadcom AI Gateway 출시 시 점검표 — 키와 팀 예산과 차지백, 시맨틱 캐시, 가드레일 훅, MCP 정책, 클라우드 모델 라우팅, OpenTelemetry 호환. 충족되는 항목은 1계층에서 걷어내고, 부족한 항목은 1계층에 남깁니다.

앱 팀이 이 계층들을 어떻게 소비하는지(온보딩, 별칭, 예산, 절감)는 [앱 가이드 05 플랫폼 소비](https://github.com/JaeHoYun/vcf-private-ai-apps/blob/main/docs/05-platform-consumption.md)에서 다룹니다.

---

[← 이전: 04 에이전트와 RAG API](04-agent-rag-api.md) | [목차](../README.md) | [다음: 06 MCP 도구 API →](06-mcp-tools-api.md)
