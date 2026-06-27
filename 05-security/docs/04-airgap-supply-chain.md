# 04 — 에어갭·공급망·모델 출처

> 기반 버전은 [README 버전 기준 문서](../README.md#기반-버전-source-of-truth)을 참조하세요.
> 시리즈 인덱스: [시리즈 허브](../../README.md)

이 문서는 폐쇄망(에어갭) 환경에서 Private AI 워크로드를 운영할 때의 공급망 보안을 다룹니다. 모델·컨테이너·드라이버가 외부에서 어떻게 안전하게 반입되고, 출처(provenance)와 무결성이 어떻게 검증되며, 로컬 레지스트리(Harbor) 단계에서 어떤 통제가 걸리는지를 보안 관점으로 정리합니다. 인프라 구성 절차 자체는 ① 인프라 가이드([① 인프라](../../01-infra/README.md))의 Artifact Mirroring Tool·Harbor 서술을 참조하고, 본 문서는 그 위에 보안 통제를 얹습니다.

용어 주의: 본 문서의 에어갭 반입 도구는 Broadcom 공식 명칭 **"Artifact Mirroring Tool(아티팩트 미러링 도구)"** 으로 표기합니다. 운영 현장에서 "에어갭 모델/툴링 반입 도구" 등으로 풀어 부르기도 하나, 공식 산출물 기준 명칭은 Artifact Mirroring Tool이며 Private AI Services 2.1에서 도입되었습니다([Broadcom TechDocs — Private AI Services Release Notes](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-release-notes/vmware-private-ai-services-release-notes.html)).

---

## 4.1 에어갭 운영 모델: 외부 의존 차단과 단방향 반입

에어갭 환경의 핵심 전제는 "운영망은 외부 인터넷에 연결되지 않는다"는 것입니다. 따라서 모델·컨테이너 이미지·NVIDIA 드라이버/Operator·OS 패키지는 모두 **인터넷 연결 호스트에서 한 번 내려받아(stage), 검증한 뒤, 폐쇄망의 로컬 레지스트리(Harbor)로 단방향 반입**하는 흐름을 따릅니다. Private AI Services 2.1의 Artifact Mirroring Tool은 이 단방향 미러링을 표준화합니다([Broadcom TechDocs — Upload the Private AI Services Components to a Disconnected Environment](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html)).

Artifact Mirroring Tool이 인터넷 측에서 끌어오는(pull) 아티팩트 출처와 반입 대상은 다음과 같습니다([같은 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html)).

| 아티팩트 | 외부 출처 | 폐쇄망 반입 후 위치 | 보안 관점 |
| --- | --- | --- | --- |
| Private AI Services 패키지 | packages.broadcom.com | Harbor 프로젝트 | Broadcom 토큰 인증 필요 |
| NVIDIA GPU Operator Helm 차트 | helm.ngc.nvidia.com | Harbor 프로젝트 | NVIDIA AI Enterprise 라이선스 필요 |
| NVIDIA 컨테이너 이미지 | nvcr.io | Harbor 프로젝트 | 서명/스캔 대상 |
| Node Feature Discovery 차트·이미지 | GitHub, registry.k8s.io | Harbor 프로젝트 | 출처 고정·핀(pin) 권장 |
| Ubuntu 패키지 | archive.ubuntu.com | 로컬 apt 저장소 | `custom-repo.list`로 인덱싱 |

운영 흐름은 (1) 연결망에서 `docker login` 후 `vcf pais amt pull [YAML]`로 `pais-store` 디렉터리에 아티팩트를 적재 → (2) 물리적/검역 절차로 폐쇄망 측 머신에 전송 → (3) `vcf pais amt push [harbor-fqdn]/[project]`로 Harbor에 업로드입니다([같은 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/deploying-private-ai-foundation-with-nvidia/installing-and-configuring-private-ai-services/upload-the-private-ai-services-components-to-a-disconnected-environment.html)). 보안상 (2)와 (3) 사이의 **검역(quarantine) 구간**에서 서명·해시·스캔 검증을 강제하는 것이 핵심이며, 이 통제 없이 반입하면 에어갭이 제공하는 격리 효과가 사라집니다.

Harbor 자체를 에어갭에 처음 세울 때는 "부트스트랩 문제"가 있습니다. Harbor Supervisor Service를 띄우려면 컨테이너 이미지가 필요한데, 폐쇄망에는 그 이미지를 줄 레지스트리가 아직 없기 때문입니다. 해결책은 임시 부트스트랩 레지스트리(Bitnami Harbor OVA)를 먼저 띄워 이미지를 공급하고, 그 위에 운영용 Harbor Supervisor Service를 배포하는 2단계 방식입니다. 이미지 사전 적재에는 Carvel `imgpkg copy`로 tar 번들을 만들어 옮기는 절차가 사용됩니다([VCF Blog — Deploying Harbor Service in Air-Gapped VCF 9.0](https://blogs.vmware.com/cloud-foundation/2026/04/21/deploying-harbor-service-in-air-gapped-vmware-cloud-foundation-9-0/)).

---

## 4.2 모델 공급망: 출처·서명·무결성 검증

모델은 NVIDIA NGC 카탈로그, Hugging Face Hub, 기타 ML 카탈로그에서 **신뢰 소스에서만** 내려받아야 합니다([Broadcom TechDocs — Storing ML Models in VMware Private AI Foundation](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html)). 반입 모델은 Harbor(OCI 호환 레지스트리)를 모델 스토어로 삼는 Model Gallery 구조에 저장되며, 다음 계층으로 관리됩니다([같은 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html)).

| 계층 | 내용 | 무결성 의미 |
| --- | --- | --- |
| Project | 고유 이름·접근권한을 가진 Harbor 프로젝트 | RBAC 경계 |
| Model | 프로젝트 내 OCI 리포지터리 | 자산 단위 |
| Revision | 콘텐츠 다이제스트로 식별되는 **불변(immutable) 매니페스트** | 동일 데이터는 한 revision만 저장 → 변조 탐지 |
| File | 실제 모델 데이터가 담긴 OCI 레이어/블롭 | 다이제스트 기반 검증 |

업로드는 VCF Consumption CLI의 `vcf pais models push --modelName ... --modelStore ... --tag approved` 형태로 수행합니다([같은 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html)). 보안 관점에서 업로드 **이전**에 반드시 거쳐야 하는 인입 게이트는 다음과 같습니다([같은 TechDocs](https://techdocs.broadcom.com/us/en/vmware-cis/private-ai/foundation-with-nvidia/9-0/private-ai-foundation-9-x/what-is-private-ai-services/storing-ml-models-in-vmware-private-ai-foundation.html)).

1. **해시 검증** — 모델 파일의 해시 코드를 신뢰 소스가 공표한 체크섬과 대조해 무결성을 확인합니다.
2. **악성코드·역직렬화 공격 스캔** — pickle 등 역직렬화 기반 모델 포맷은 임의 코드 실행 위험이 있으므로 별도 스캔이 필요합니다. 가능하면 safetensors 등 안전 포맷을 우선합니다(확인 필요: 조직 표준 포맷 정책).
3. **추론 기능 테스트 및 성능·안전성 평가** — 격리 환경에서 동작과 안전성을 검증합니다.

출처(provenance) 보강: OWASP는 "현재 공개 모델에는 강한 출처 보증이 없다"는 점을 명시적 공급망 위험으로 지적합니다([OWASP Top 10 for LLM Applications 2025 — LLM03 Supply Chain](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)). 따라서 조직은 모델 출처를 **자체 서명·체크섬·서명된 메타데이터**로 보강하고, Revision 다이제스트와 `tag approved` 승인 흐름을 거버넌스 기록으로 남겨야 합니다. Model Gallery의 불변 Revision은 이 추적의 기술적 기준점 역할을 합니다.

---

## 4.3 컨테이너 공급망: 스캔·서명·SBOM·접근통제

컨테이너 이미지는 Harbor에서 스캔·서명·접근통제를 일괄 적용합니다. Harbor는 기본 스캐너로 Trivy를 내장하며, OS 패키지·애플리케이션 의존성·IaC 오구성 취약점을 탐지합니다([VCF Blog — Securing Your Software Supply Chain with Harbor](https://blogs.vmware.com/cloud-foundation/2026/01/30/securing-your-software-supply-chain-with-harbor/)).

| 통제 | Harbor 설정 | 보안 효과 |
| --- | --- | --- |
| Scan-on-push | 프로젝트의 "Automatically scan images on push" 활성화 | 반입 즉시 취약점 가시화 |
| 심각도 게이트 | "Prevent vulnerable images from running" + 임계값(Critical/High 등) | 임계 초과 이미지 pull 차단 |
| CVE 예외 | 프로젝트/시스템 CVE Allowlist(만료일 설정 가능) | 예외의 시간 제한 관리 |
| 콘텐츠 신뢰 | Cosign 또는 Notation을 필수 서명원으로 지정 | **서명 없는 이미지 pull 차단** |
| 불변 태그 | Immutable tag 규칙 | 운영 태그 덮어쓰기 방지 |
| 감사 로그 | push/pull·스캔결과·정책변경·접근 기록 | 추적성 확보 |

서명은 Sigstore의 cosign을 사용합니다. cosign은 이미지와 동일 레지스트리에 서명을 OCI 아티팩트로 저장하며, 다이제스트 기반 태그에 push합니다. keyless 서명은 단기 인증서를 OIDC 신원에 묶어(Fulcio 발급) 키 관리 부담을 줄입니다([Sigstore — Verifying Signatures](https://docs.sigstore.dev/cosign/verifying/verify/)). 폐쇄망에서는 공개 Sigstore 인스턴스 의존이 어려우므로, **키 기반 서명 또는 사내 Fulcio/Rekor 운영**을 검토합니다(확인 필요: 사내 투명성 로그 운영 여부). 검증 정책은 admission 단계에서 강제하는 것이 안전하며, Kyverno의 `verifyImages` 규칙으로 필수 서명·다이제스트 고정을 적용할 수 있습니다([Kyverno — Sigstore image verification](https://release-1-10-0.kyverno.io/docs/writing-policies/verify-images/sigstore/)).

SBOM은 "무엇이 들어있는가"를, SLSA provenance는 "변조되지 않았음"을 증명하여 상호 보완합니다([Practical DevSecOps — SLSA Framework Guide](https://www.practical-devsecops.com/slsa-framework-guide-software-supply-chain-security/)). SBOM 표준 포맷은 SPDX(Linux Foundation, ISO/IEC 5962:2021)와 CycloneDX(OWASP)이며, Harbor는 SBOM과 attestation 생성을 지원합니다([VCF Blog — Securing Your Software Supply Chain with Harbor](https://blogs.vmware.com/cloud-foundation/2026/01/30/securing-your-software-supply-chain-with-harbor/)). SLSA는 빌드 출처 보증 수준을 Level 1–3(이상)으로 정의하며, Level 3은 위조 불가능한(non-falsifiable) provenance를 요구합니다([SLSA Framework Guide](https://www.practical-devsecops.com/slsa-framework-guide-software-supply-chain-security/)).

접근통제: Harbor RBAC는 LDAP/Active Directory/OIDC와 연동되며, CI/CD 파이프라인에는 만료일과 범위가 제한된 **robot account**를 부여해 사람 자격증명 노출을 방지합니다([VCF Blog — Securing Your Software Supply Chain with Harbor](https://blogs.vmware.com/cloud-foundation/2026/01/30/securing-your-software-supply-chain-with-harbor/)). 프로젝트 단위로 RBAC·스캔정책·쿼터·태그보존 규칙이 독립 적용됩니다([WebSearch 종합 — Harbor 프로젝트 구조](https://blogs.vmware.com/cloud-foundation/2026/01/30/securing-your-software-supply-chain-with-harbor/)).

---

## 4.4 데이터·임베딩 오염(poisoning) 위협과 인입 검증

OWASP는 학습/임베딩 데이터의 악의적 조작을 LLM04:2025 "Data and Model Poisoning"으로 분류합니다(2025판에서 기존 "Training Data Poisoning"이 확장됨)([OWASP Top 10 for LLM Applications 2025](https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf)). 공급망 신뢰는 전이적(transitive)이어서, 모델 파일뿐 아니라 호스트의 인프라·CI/CD·접근통제·운영진까지 신뢰 대상에 포함됩니다([Indusface — OWASP LLM03 Supply Chain](https://www.indusface.com/learning/owasp-llm-supply-chain/)).

RAG/임베딩 파이프라인에서 특히 주의할 인입 지점과 통제는 다음과 같습니다.

| 위협 | 인입 지점 | 통제(요지) |
| --- | --- | --- |
| 학습/파인튜닝 데이터 오염 | 외부 데이터셋 반입 | 출처 검증·해시 고정·격리 검사 |
| 임베딩 코퍼스 오염 | RAG 소스 문서 반입 | 신뢰 소스 한정·콘텐츠 검증·변경 추적 |
| 의존 패키지 오염 | PyPI/Helm 등 | 핀(pin)·서명·SBOM·취약점 스캔 |
| 모델 호스트 측 변조 | NGC/Hugging Face 등 업스트림 | 해시 대조·역직렬화 스캔·승인 태깅 |

실제 사례로, Hugging Face의 CI/CD가 교차 테넌트 접근·모델 오염에 악용될 수 있었던 사례, 그리고 단일 오염 PyPI 패키지로 LLM 프록시 게이트웨이가 침해된 사례가 보고되었습니다([Confident AI — OWASP Top 10 2025 for LLM Applications](https://www.confident-ai.com/blog/owasp-top-10-2025-for-llm-applications-risks-and-mitigation-techniques)). 이는 "신뢰 소스에서만 반입"이 출처 확인의 시작일 뿐, 해시·서명·스캔 게이트가 함께 걸려야 함을 보여줍니다.

상세 데이터 거버넌스(데이터 분류·접근정책·보존·계보 관리 전반)는 본 문서 범위를 넘어가며, **본 시리즈의 05 데이터 거버넌스 문서**에서 다룹니다. 본 문서는 "오염된 데이터/임베딩이 폐쇄망 안으로 들어오지 못하게 하는 인입 검증"에 한정합니다.

---

## 4.5 검증 방법

아래 항목으로 4.1–4.4의 통제가 실제로 작동하는지 점검합니다. 명령·경로·정책 위치는 ① 인프라 가이드의 Artifact Mirroring Tool/Harbor 절차와 교차 확인하세요.

| 점검 항목 | 검증 방법 | 합격 기준 |
| --- | --- | --- |
| 외부 의존 차단 | 폐쇄망 노드에서 외부 레지스트리(nvcr.io 등) 직접 pull 시도 | 차단됨. 모든 pull은 Harbor 경유 |
| Artifact Mirroring Tool 미러링 무결성 | `vcf pais amt pull` 산출물(`pais-store`)의 다이제스트를 push 후 Harbor 매니페스트와 대조 | 다이제스트 일치 |
| 모델 해시 게이트 | 반입 모델 해시를 신뢰 소스 공표값과 대조 | 불일치 시 업로드 차단 |
| 모델 불변성 | 동일 모델 데이터 재push 시 Revision 수 | 신규 Revision 생성 안 됨(동일 다이제스트 1개) |
| 컨테이너 scan-on-push | 임의 취약 이미지 push | 스캔 자동 실행·결과 기록 |
| 심각도 게이트 | Critical/High 초과 이미지 pull 시도 | pull 차단(Allowlist 예외만 통과) |
| 콘텐츠 신뢰 | 서명 없는 이미지 pull 시도 | 차단됨 |
| 서명 검증 정책 | admission(Kyverno 등)에서 미서명/미고정 이미지 배포 시도 | admission 거부 |
| SBOM/attestation | 대표 이미지의 SBOM·attestation 존재 확인 | SPDX/CycloneDX 산출물 존재 |
| RBAC·robot account | robot account 권한 범위·만료일 확인 | 최소권한·만료 설정됨 |
| 감사 추적 | push/pull·정책변경 로그 조회 | 행위 추적 가능 |
| 데이터·임베딩 인입 | 미검증 데이터셋/문서 반입 시도 | 출처·해시 게이트에서 차단 |

검증 시 발견된 예외(예: CVE Allowlist 등록 항목)는 만료일과 사유를 거버넌스 기록으로 남기고, 근거→통제→증적의 추적체인이 끊기지 않도록 관리합니다. 불확실하거나 환경별로 달라지는 항목(사내 Fulcio/Rekor 운영, 모델 포맷 정책 등)은 "확인 필요"로 표기해 별도 확정 절차를 둡니다.

---

[← 이전: 03 ID·인증·접근통제](03-identity-access.md) · [목차](../README.md) · [다음: 05 데이터 거버넌스·프라이버시 →](05-data-governance.md)
