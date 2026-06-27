# 03 — ID·인증·접근통제

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [vcf-private-ai-series](../../README.md)

이 문서는 VCF 9.1 / PAIF 9.1 / PAIS 2.1 기반 사설 AI 플랫폼에서 "누가(사람·서비스·에이전트) 무엇에 접근할 수 있는가"를 통제하는 거버넌스 관점을 다룹니다. 모델 추론 API, 에이전트, MCP 도구, 지식 베이스(KB)는 모두 동일한 ID 체계 위에서 권한이 평가되어야 하며, 한 곳이라도 통제가 끊기면 전체 신뢰 경계가 무너집니다.

서빙 계층의 인증 구현 절차(API 키 발급 화면, 게이트웨이 설정 단계 등)는 [③ 서빙 가이드](../../03-serving-api/README.md)에서 다룹니다. 본 문서는 그 위에서 "정책을 어떻게 설계하고 강제·검증할 것인가"라는 거버넌스 층위에 집중합니다.

---

## 3.1 ID 모델: 인간 사용자와 서비스 ID의 분리

사설 AI 플랫폼에서 가장 먼저 정리해야 할 것은 ID의 종류를 구분하는 일입니다. 사람과 자동화된 클라이언트는 인증 방식·수명주기·책임 추적 방식이 다르므로 같은 자격증명을 공유해서는 안 됩니다.

VCF 9.x는 vSphere, NSX, VCF Operations, VCF Automation 전반에 걸친 통합 SSO를 제공하며, Okta·Ping Identity·Microsoft Entra ID 같은 외부 OIDC/SAML IdP와 연동됩니다. 이 통합 ID 소스를 사용하면 공유 로컬 자격증명 의존을 줄이고 더 세분화된 접근통제를 적용할 수 있습니다([Bringing Modern Identity to VCF 9, Broadcom VCF Blog](https://blogs.vmware.com/cloud-foundation/2026/02/18/bringing-out-of-the-box-modern-identity-to-your-infrastructure-with-vmware-cloud-foundation-9-0/)).

PAIS API는 OIDC를 인가 기반으로 사용하며, 대화형 클라이언트는 **Authorization Code with PKCE** 흐름으로 토큰을 받습니다([VMware Private AI Service API, Broadcom Developer Portal](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)).

| ID 유형 | 대표 주체 | 인증 방식 | 자격증명 수명 |
|---|---|---|---|
| 인간 사용자 | VI Admin, MLOps, 앱 개발자, 감사자 | OIDC(Authorization Code + PKCE) + MFA | 세션 단위, 단기 토큰 |
| 서비스 ID(M2M) | 백엔드 앱, 배치 작업 | OAuth2 Client Credentials | 단기 액세스 토큰, 회전 |
| 에이전트 런타임 | Agent Builder 에이전트 | 네임스페이스 귀속 ID + 승인된 도구 스코프 | 위임된 단기 토큰 |

> 거버넌스 원칙: 인간용 흐름(PKCE+MFA)과 서비스용 흐름(Client Credentials)을 절대 섞지 마세요. 사람이 만든 개인 토큰으로 무인 자동화를 돌리면 퇴사·역할 변경 시 추적·회수가 끊깁니다.

신원 보증 수준은 NIST SP 800-63 프레임워크(IAL/AAL/FAL)를 기준선으로 잡습니다. 운영자·관리자 같은 고위험 역할은 AAL2(MFA) 이상, 프로덕션 모델 변경 같은 최고위험 작업은 AAL3(하드웨어 인증기, 검증자 위장 저항) 적용을 권고합니다([NIST SP 800-63-4](https://pages.nist.gov/800-63-4/sp800-63.html)).

---

## 3.2 RBAC: 역할 정의와 최소 권한

통합 SSO 위에서 역할 기반 접근통제(RBAC)를 설계합니다. 핵심은 "직무에 필요한 최소 범위"만 부여하고, 역할 간 직무 분리(SoD)를 강제하는 것입니다. 특히 운영 권한과 감사 권한은 반드시 분리되어야 부정 변경의 자기 은폐를 막을 수 있습니다.

| 역할 | 책임 | 부여 권한(예시) | 명시적 차단 |
|---|---|---|---|
| VI Admin | 인프라·워크로드 도메인 운영 | GPU-Accelerated Workload Domain 구성, 네임스페이스 생성 | 모델 가중치 직접 열람, KB 콘텐츠 변경 |
| MLOps | 모델 배포·런타임 운영 | 모델 갤러리 배포, Model Runtime 스케일링, API 게이트웨이 정책 | IdP/SSO 설정 변경, 감사 로그 삭제 |
| 앱 개발자 | 에이전트·앱 구축 | Agent Builder 사용, 승인된 도구·KB 소비 | MCP 서버 신규 등록 승인, 인프라 변경 |
| 감사자 | 통제·로그 검증 | 로그·구성·권한 부여 내역 읽기 전용 | 모든 쓰기·실행·삭제 |

VCF SSO와 vCenter Server Linking을 사용하면 워크로드 도메인 전반의 구성을 일관되게 관리하면서, 공통 ID 소스로 더 세분화된 접근통제를 구현할 수 있습니다([10 VCF 9 Enhancements, Broadcom VCF Blog](https://blogs.vmware.com/cloud-foundation/2025/09/18/10-vmware-cloud-foundation-9-enhancements-simplifying-your-day-2-operations/)).

PAIS의 Agent Builder·KB·도구 소비는 VCF Automation의 **네임스페이스** 단위로 가용성이 결정되므로, 네임스페이스 경계를 RBAC의 1차 격리 단위로 삼는 것이 효과적입니다([Adding MCP Servers, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities.html)).

> 거버넌스 원칙: 역할은 "할 수 있는 것"의 화이트리스트로 정의하고, 위 표의 "명시적 차단" 열처럼 고위험 작업은 별도로 부인(deny)을 명문화합니다. 권한 부여는 만료가 있는 임시 부여를 기본으로 하고, 영구 부여는 예외 승인 대상으로 관리합니다.

---

## 3.3 API 접근통제: OpenAI 호환 게이트웨이와 토큰 수명주기

PAIS는 OpenAI API와 호환되는 인터페이스를 제공하며, API 게이트웨이가 모델 엔드포인트로 들어오는 요청의 인증·인가와 부하 분산을 담당합니다([Private AI Services New in VCF 9.0, Broadcom VCF Blog](https://blogs.vmware.com/cloud-foundation/2025/06/19/private-ai-services-new-in-vmware-private-ai-foundation-with-nvidia-in-vcf-9-0/)).

모든 API 요청은 `Authorization: Bearer <access-token>` 헤더에 단기 액세스 토큰을 실어 보내며, 이 토큰은 OIDC를 통해 발급됩니다([VMware Private AI Service API, Broadcom Developer Portal](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)). OIDC 디스커버리 구성은 PAIS 인스턴스의 `https://<fqdn>/env.json`에서 확인할 수 있습니다(상세 흐름은 ③ 서빙 가이드 참조).

```bash
# OpenAI 호환 모델 목록 호출 — Bearer 액세스 토큰 필수
curl 'https://pais.local/api/v1/compatibility/openai/v1/models' \
  --header 'Authorization: Bearer <access-token>'
```

서비스 계정(무인 클라이언트)은 OAuth2 **Client Credentials** 그랜트로 자기 자격증명을 토큰과 교환합니다. 이 그랜트는 RFC 6749 4.4절에 정의된 M2M 인증 표준으로, 사용자 개입이 없고 응답에 리프레시 토큰을 포함하지 않습니다. 클라이언트는 필요할 때마다 자격증명으로 새 토큰을 받습니다([RFC 6749 §4.4](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4), [OAuth.net Client Credentials](https://oauth.net/2/grant-types/client-credentials/)).

| 자격증명 | 발급 대상 | 권장 수명 | 회수·회전 |
|---|---|---|---|
| 인간 액세스 토큰 | 사용자 세션 | 분–1시간(단기) | 만료 + IdP 세션 종료 |
| 서비스 액세스 토큰 | 서비스 계정 | 분–1시간(단기) | 만료 시 재발급, 리프레시 없음 |
| 클라이언트 시크릿 | 서비스 계정 등록 | 정책상 정기 회전 | 노출 의심 시 즉시 폐기·재발급 |

API 게이트웨이 정책은 OWASP API Security Top 10(2023)을 점검표로 삼습니다. 특히 API1:2023(BOLA)과 API2:2023(Broken Authentication)이 최우선입니다. 객체 ID를 받는 모든 엔드포인트는 호출자가 그 객체에 대한 권한이 있는지 객체 수준 인가를 검증해야 하고, 토큰은 발급자·대상(audience)·만료·서명·키 ID 같은 클레임을 전부 검증해야 합니다([OWASP API1:2023 BOLA](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/), [OWASP API Security Project](https://owasp.org/www-project-api-security/)).

마이크로서비스 간 통신은 PAIS 내부에서 mTLS로 상호 인증됩니다. 즉 클라이언트→게이트웨이 구간은 Bearer 토큰, 서비스↔서비스 구간은 mTLS라는 이중 경계를 유지합니다([VMware Private AI Service API, Broadcom Developer Portal](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/)).

> 거버넌스 원칙: 장수 토큰·정적 API 키 공유를 금지하고, 단기 토큰 + 시크릿 회전을 표준으로 둡니다. 토큰이 단기이므로 누출되더라도 피해 범위가 그 수명 안으로 한정됩니다.

---

## 3.4 에이전트·MCP 접근통제: 도구 등록·승인 게이트

에이전트는 사람보다 빠르게, 그리고 자율적으로 도구를 호출합니다. 따라서 "어떤 도구가 플랫폼에 들어오는가"와 "누가 그 도구를 호출할 수 있는가"를 분리해 통제하는 것이 에이전트 거버넌스의 핵심입니다.

PAIS는 MCP(Model Context Protocol) 서버에 연결하고, 그 서버가 제공하는 도구 중 **승인된 도구 목록**(approved tools)만 Agent Builder의 에이전트에서 사용하도록 합니다([Adding MCP Servers, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities.html)).

승인 게이트의 동작은 도구의 출처에 따라 다릅니다.

| 도구 출처 | 등록·승인 동작 | 거버넌스 함의 |
|---|---|---|
| REX 도구(데이터 인덱싱·검색 내부 생성) | 생성 시 자동 승인 | 플랫폼 내부 신뢰 경계 안 |
| 외부 MCP 서버 도구 | 명시적 승인 필요 | 외부 능력 유입에 대한 통제 지점 |

REX 도구는 생성 시 자동 승인되지만, 외부 MCP 서버의 도구는 명시적 승인을 거쳐야 합니다([Adding MCP Servers, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities.html)). 이 차이는 외부에서 들어오는 능력을 사람이 한 번 검토하는 통제 지점이 됩니다.

도구 갤러리(Tool Gallery)에서는 각 도구의 제공 MCP 서버, 현재 사용 중인 에이전트, 입력·출력 스키마를 포함한 전체 설명을 확인할 수 있습니다([Explore MCP Tools, Broadcom TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities/exploring-the-mcp-tools-avaiable-in-your-namespace.html)). 도구는 네임스페이스 범위에서 동작하므로, 승인·소비 권한도 네임스페이스 경계를 따릅니다.

거버넌스 관점에서 권장하는 도구 권한 계층은 다음과 같습니다.

- 등록(register): 외부 MCP 서버 연결과 도구 노출 — VI Admin/플랫폼 운영 책임자.
- 승인(approve): 노출된 외부 도구를 사용 가능 목록으로 전환 — 직무 분리상 등록자와 다른 승인자 권장.
- 소비(consume): 승인된 도구를 에이전트에 결합 — 앱 개발자(해당 네임스페이스 내).

KB(지식 베이스) 접근도 같은 원칙입니다. KB는 Google Drive·Confluence·SharePoint·S3 등 데이터 소스에 연결되어 벡터 DB에 인덱싱되며, PAIS 인스턴스의 네임스페이스에 귀속됩니다([Building GenAI Agents with PAIS, Broadcom VCF Blog](https://blogs.vmware.com/cloud-foundation/2025/08/26/vmware-private-ai-services-demo/)). 따라서 원본 데이터 소스의 접근 권한과 KB 소비 권한이 일치하도록 매핑하지 않으면, 에이전트를 통해 권한 없는 사용자가 민감 데이터를 우회 열람할 수 있습니다.

> 거버넌스 원칙: "에이전트가 가진 권한 = 그 에이전트를 호출하는 사람의 권한"이 아닐 수 있습니다. 에이전트가 위임받은 도구·KB 스코프가 호출자 권한을 초과하지 않도록 설계하고(권한 상승 방지), 도구별 최소 스코프와 승인 이력을 추적 가능하게 보관하세요.

---

## 3.5 시크릿 관리: 모델·DB 자격증명과 키 회전

AI 플랫폼은 모델 레지스트리 접근 토큰, 벡터 DB·관계형 DB 자격증명, 외부 데이터 소스(SharePoint·S3 등) 연결 비밀, MCP 서버 인증 정보 등 다양한 시크릿을 다룹니다. 이들이 평문 설정·코드·이미지에 박히면 단일 유출로 전체가 무너집니다.

| 시크릿 유형 | 사용처 | 회전 기준 |
|---|---|---|
| 모델 레지스트리 자격증명 | 모델 갤러리·런타임 배포 | 정기 + 인력 변동 시 |
| 벡터 DB / DB 자격증명 | 데이터 인덱싱·검색(RAG) | 정기 + 노출 의심 시 즉시 |
| 데이터 소스 연결 비밀 | KB 인덱싱 커넥터 | 소스 정책에 종속, 정기 회전 |
| OAuth2 클라이언트 시크릿 | 서비스 계정 M2M | 정기 회전, 누출 시 즉시 폐기 |

거버넌스 기준선은 다음과 같습니다.

- 시크릿은 코드·이미지·로그에 두지 않고 전용 비밀 저장소에서만 주입합니다.
- 모든 시크릿은 소유자·용도·만료를 가진 인벤토리로 관리하고, 만료 없는 시크릿을 예외로 취급합니다.
- 회전은 정기 일정 + 트리거(인력 변동, 노출 의심, 사고 대응) 기반으로 수행합니다. 클라이언트 시크릿은 노출 의심 시 즉시 폐기·재발급합니다([OAuth.net Client Credentials](https://oauth.net/2/grant-types/client-credentials/)).
- 단기 토큰을 기본으로 하여, 회전 누락이 있어도 누출 시 피해 범위가 그 수명 안으로 한정됩니다([OWASP API Security Project](https://owasp.org/www-project-api-security/)).

> 확인 필요: PAIS 2.1이 내장 비밀 저장소를 제공하는지, 외부 KMS/Vault 연동을 전제로 하는지는 배포 토폴로지에 따라 다를 수 있어 공식 배포 문서로 별도 확인이 필요합니다.

---

## 3.6 검증 방법

아래 점검 항목으로 ID·인증·접근통제 통제가 설계대로 강제되는지 검증합니다. 각 항목은 합격 기준(통과/실패)을 명확히 두고 정기 회귀로 반복합니다.

| # | 검증 항목 | 방법 | 합격 기준 |
|---|---|---|---|
| 1 | OIDC 흐름 분리 | 인간 로그인은 PKCE+MFA, 서비스는 Client Credentials로만 토큰 발급되는지 확인 | 교차 사용 0건 |
| 2 | 토큰 인가 검증 | 만료·잘못된 audience·변조 서명 토큰으로 게이트웨이 호출 | 모두 401/403 거부 |
| 3 | BOLA 점검 | 사용자 A 토큰으로 사용자 B 소유 객체(모델·KB·에이전트) 접근 시도 | 객체 수준 인가로 차단 |
| 4 | RBAC 최소 권한 | 앱 개발자 계정으로 MCP 등록 승인·인프라 변경 시도 | 권한 부족으로 거부 |
| 5 | 직무 분리 | 감사자 계정으로 쓰기·삭제 시도 | 모두 거부, 읽기만 허용 |
| 6 | MCP 승인 게이트 | 미승인 외부 MCP 도구를 에이전트에 결합 시도 | 승인 전 사용 불가 |
| 7 | 도구 스코프 추적 | 도구 갤러리에서 도구별 사용 에이전트·승인 이력 확인 | 추적 체인 누락 0건 |
| 8 | KB 권한 일치 | 원본 데이터 소스 권한 없는 사용자가 에이전트로 해당 KB 질의 | 우회 열람 불가 |
| 9 | mTLS 내부 통신 | 마이크로서비스 간 통신 캡처로 상호 TLS 적용 확인 | 평문·단방향 TLS 0건 |
| 10 | 시크릿 회전 | 시크릿 인벤토리의 만료·회전 이력 점검 | 만료 없는 시크릿 0건(예외 승인 제외) |

권장 검증 주기: 항목 2·3·4·5·6은 변경 시마다(CI/CD 게이트), 1·7·8·9는 분기, 10은 회전 정책 주기에 맞춰 수행합니다. 모든 검증 결과는 감사자가 읽기 전용으로 열람 가능해야 하며, 통제 실패는 [01 위협 모델](01-threat-model.md)의 위험 항목과 추적 가능하게 연결합니다.

검증 결과의 근거가 되는 정의·동작은 다음 공식 출처에 묶입니다.

- 인증·인가 표준: [RFC 6749 §4.4](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4), [NIST SP 800-63-4](https://pages.nist.gov/800-63-4/sp800-63.html), [OWASP API Security Top 10 (2023)](https://owasp.org/www-project-api-security/)
- 플랫폼 동작: [VMware Private AI Service API](https://developer.broadcom.com/xapis/vmware-private-ai-service-api/latest/), [Adding MCP Servers (TechDocs)](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/adding-mcp-servers-for-real-time-data-access-and-specialized-ai-capabilities.html)

---

[← 이전: 02 네트워크·테넌트·GPU 격리](02-network-tenant-isolation.md) · [목차](../README.md) · [다음: 04 에어갭·공급망·모델 출처 →](04-airgap-supply-chain.md)
