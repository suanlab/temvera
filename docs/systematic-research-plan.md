# 체계적 연구 계획서 — 감사가능한 시간 인식 에이전트 메모리

> 기준일: 2026-07-15  
> 상태: 승인된 로컬 범위의 WP1–WP5 완료. WP0는 단독 스크리닝 한계를
> 보존하고, 외부 동일예산 재현은 자원 부재로 미채택, 인간 연구는
> protocol-only, learned 모델과 공개 DOI는 D-009에 따라 보류한다.
> 성능·신규성 주장은 제한된 fixture 밖에서는 가설이다.

## 1. 연구 목표와 범위

Temvera의 목표는 에이전트가 장기간 축적한 사실을 **언제 알았고(transaction time), 언제 참이었으며(valid time), 무엇을 근거로 현재 믿는지** 재현 가능하게 관리하는 것이다. 연구의 중심 질문은 다음과 같다.

> 파일과 git으로 구현한 감사가능 메모리가 전용 저장소와 같은 시간적 정확성을 제공하면서, 갱신·망각·오염·인간 수정에서 더 나은 검증 가능성을 제공하는가?

초기 연구는 모델 학습이나 대규모 벡터 인프라를 제외한다. 상태 전이, 시간 질의, provenance, 삭제 계보와 결정론적 평가를 우선 구현한다.

## 2. 선행 연구와 확인된 공백

### 평가와 시간적 갱신

- [LongMemEval](https://arxiv.org/abs/2410.10813)은 정보 추출, 다중 세션 추론, 시간 추론, 지식 갱신, 기권을 평가한다. 따라서 이 능력들의 도입 자체는 신규 기여가 아니다.
- [LoCoMo](https://arxiv.org/abs/2402.17753)는 최대 35개 세션의 장기 대화와 시간·인과 의존성을 다룬다. 다만 자연어 응답 중심이라 개별 메모리 연산의 정답 상태를 직접 검사하기 어렵다.
- [LongMemEval-V2](https://arxiv.org/abs/2605.12493)는 환경 경험과 파일 기반 coding-agent memory를 포함한다. 공개 코드·라이선스 확인 전 수치는 잠정 근거로만 사용한다.
- [Scale-Conditioned Evaluation](https://arxiv.org/abs/2605.07313)은 무관 세션 증가와 호출 예산에 따라 메모리 신뢰성이 달라짐을 제기한다. 고정 크기 평균점수만으로 확장성을 주장하지 않는다.

### 감사가능성, 망각, 보안

- [Springdrift](https://arxiv.org/abs/2604.04660)는 append-only memory, 감사 추적, git-backed recovery를 이미 결합한다. 그러므로 “최초의 git-native 감사 메모리” 주장은 폐기한다. 남은 비교점은 bitemporal 질의의 정확성, 명시적 개정 의미론, 결정론적 검증, 인간 리뷰 효율이다.
- Springdrift commit `19b52b9`의 AGPL 라이선스와 experiment-5를 확인했다. Ollama가 없으면 스크립트가 오류 대신 0 벡터로 계속 실행되어 committed embedding 결과와 다른 점수를 만들며, Python decay 검사는 Gleam 구현을 직접 호출하지 않는다(E-040). 따라서 이 실행은 환경 실패 경로와 공식 확인용일 뿐 동일 예산 시스템 재현으로 세지 않는다.
- Zep의 공개 구현 [Graphiti](https://github.com/getzep/graphiti/tree/20a6728fbda9fb257ebf84584c2ccf37801a7cf9)는 temporal knowledge graph에서 `created_at`, `valid_at`, `invalid_at`, `expired_at`와 각 필드의 검색 필터를 이미 제공한다. 따라서 temporal graph나 시간 필드 자체를 신규성으로 주장하지 않는다. `remove_episode`는 관련 그래프 요소를 물리 삭제하므로, Temvera와의 비교는 과거 transaction-time 재현과 삭제 계보의 완전성을 동일 fixture에서 측정해야 한다.
- [Mem0](https://github.com/mem0ai/mem0/tree/633b0353422ff7634f8ec72daa4d1aed9e224983)는 현재 벡터 레코드를 갱신·삭제하면서 별도 SQLite history에 이전값, 새값, 연산, 시간을 기록한다. 엔티티 projection 정리는 비치명적 best-effort이므로, “이력 제공”과 “파생물까지 원자적으로 삭제”를 구분해 비교한다. 논문의 자체 보고 성능과 graph variant는 아직 재현 결과로 사용하지 않는다.
- [Hindsight](https://github.com/vectorize-io/hindsight/tree/15499870151bc381d29ed307aa8610764fdbb378)는 fact/belief 분리, temporal entity graph, lexical·vector·graph·temporal retrieval뿐 아니라 invalidation archive, observation/mental-model history, audit log, derived-record 삭제 정리까지 결합한다. 소스 migration은 과거 document re-ingest가 orphan observation을 남긴 결함과 후속 backsweep을 보존한다. 따라서 감사·삭제 계보 기능의 존재는 신규성이 아니며, 동일 failure injection에서 원자성·완전성·복구를 측정해야 한다.
- [Mem2ActBench](https://aclanthology.org/2026.acl-long.370/)는 dynamic memory evolution과 tool use를 함께 평가한다. 따라서 operation/action 평가 자체를 신규성으로 주장하지 않고, Temvera의 차이는 두 시간축의 exact state, rebuild/purge completeness, provenance-action trace로 제한한다.
- 공식 ACL 페이지는 Mem2ActBench 코드·데이터 저장소를 링크하지만 2026-07-16 현재 해당 GitHub URL은 404이고 clone도 실패했다(E-046). 공개 커밋·라이선스·scorer를 고정하기 전에는 외부 실행 베이스라인으로 세지 않는다.
- A-MemGuard와 MemIncept는 각각 consensus/dual-memory 방어와 cooperative stealth injection을 제시한다. 고정된 위협 예산에서 이들과 비교하기 전 signed provenance fixture의 우위를 주장하지 않는다.
- A-MemGuard commit `dd92f7f`의 MIT 라이선스와 실행 경로를 확인했다. 다만 AgentPoison 계열 데이터, 외부 checkpoint, 대형 GPU 의존성, API/local LLM이 필요하므로 published ASR·utility는 미재현 상태다. Experience-following artifact commit `4dc29e3`은 AgentDriver patch와 수동 데이터·API 설정만 제공하고 자체 라이선스가 없어 재배포하지 않는다.
- ForgetEval commit `b6053b7`의 생성기·채점기·MIT 라이선스를 확인했다. 이 벤치는 이미 seeded template generation과 deterministic top-k substring scoring으로 supersession, release/decay, amnesia, purge, drift를 다룬다. 따라서 “최초의 procedural judge-free lifecycle benchmark” 주장은 반증됐다. Temvera의 비교 가능 차이는 exact bitemporal state, `as-of` 정답, operation trace, current-tree 밖의 잔존 사본까지 포함하는 purge 검증으로 제한한다.
- [MINJA](https://arxiv.org/abs/2503.03704)는 질의만으로 영속 메모리를 오염시킬 수 있음을 보인다. [MemLineage](https://arxiv.org/abs/2605.14421)는 cryptographic provenance와 lineage 기반 action gating을 제안하므로 필수 보안 베이스라인 후보이다.

확인된 연구 공백은 개별 기능의 존재가 아니라, 동일한 생성 상태 궤적에서 **시간 정답성, 생애주기 연산, 공격 활성화, 인간 감사 비용을 함께 비교하는 재현 가능한 실험**이다. 이 공백 역시 체계적 문헌 검토 완료 전에는 가설로 취급한다.

## 3. 연구 질문과 반증 조건

| 질문 | 사전등록 가설 | 주요 반증 조건 |
|---|---|---|
| RQ1 시간 정답성 | git 이벤트와 명시적 valid time으로 relational bitemporal oracle과 같은 `as-of` 결과를 낸다. | 생성 이력의 어떤 정상 클래스에서 상태가 불일치한다. |
| RQ2 개정·망각 | 상태 수준 supersede/expiry가 rank-decay보다 stale-fact 사용을 줄이되 Evidence Recall@K를 덜 훼손한다. | recall 손실이 같거나 stale 사용률이 개선되지 않는다. |
| RQ3 보안 | 출처 검증과 lineage-aware action gate가 무방어 대비 공격 활성화를 낮춘다. | 동등 utility에서 ASR의 신뢰구간이 겹치거나 삭제 계보가 끊긴다. |
| RQ4 감사성 | provenance-linked diff가 불투명 저장소의 관리 UI보다 오류 탐지·복구 시간을 단축한다. | 시간·정확도·부수 변경 중 사전 지정한 우위가 없다. |

## 4. 연구 방법

### WP0 — 체계적 문헌 검토와 novelty lock (2주)

검색원은 ACL Anthology, ACM DL, IEEE Xplore, USENIX, OpenReview, arXiv로 고정한다. 검색식, 검색일, 중복 제거, 포함·제외 사유를 CSV로 남긴다. 포함 기준은 (a) 영속 agent memory, (b) 시간 갱신/망각, (c) provenance·poisoning, (d) operation-level evaluation 중 하나를 구현하거나 평가한 2020년 이후 1차 자료이다. 두 명이 독립 스크리닝하는 것이 이상적이며, 단독 수행 시 10% 재검토와 결정 로그를 남긴다. ForgetEval과 Springdrift는 코드·커밋·실행 환경까지 확인한다.

**종료 기준:** 모든 기여 문장에 ledger ID, 가장 가까운 선행 연구, 차이가 측정되는 실험이 연결된다. 검색하지 않은 영역을 “문헌 전무”로 표현하지 않는다.

### WP1 — 결정론적 lifecycle oracle (4주)

엔티티-속성 이벤트 생성기와 relational bitemporal oracle을 만든다. `ingest`, `reconfirm`, `supersede`, `expire`, `purge`, `as_of`를 seed 고정 상태 궤적으로 생성한다. 자연어 렌더링과 정답 상태를 분리하고, 모든 연산에 property-based 또는 fixture test를 둔다.

### WP2 — 최소 Temvera substrate (4주)

typed Python API, append-only event schema, Markdown/YAML projection, git transaction adapter, rebuildable lexical index만 구현한다. git은 원장의 유일한 근거로 가정하지 않고 canonical event log와 투영 결과의 byte-level 재구축을 검증한다. 벡터 검색은 exact·lexical baseline 이후에만 추가한다.

### WP3 — 비교 평가 (5주)

베이스라인은 recent/full context, BM25, append-only, last-write-wins, relational bitemporal oracle, Springdrift/ForgetEval 호환 어댑터(재현 가능할 때)로 구성한다. 동일 입력, 모델, 검색 토큰 예산을 사용한다.

주 지표는 exact state accuracy, stale/superseded use rate, Evidence Recall@K, abstention calibration, provenance coverage, purge completeness이다. 규모(세션 수), churn, contradiction density, 공격 비율을 독립 축으로 변화시킨다. 확률적 단계는 최소 3 seeds와 bootstrap 95% CI를 보고하고, 다중 비교 보정을 사전 지정한다.

### WP4 — 보안과 인간 감사 연구 (4주)

MINJA형 query-only injection, forged front matter, provenance laundering, derived-record persistence를 threat model로 고정한다. 무방어, 서명/출처 검증, lineage gate를 비교해 write acceptance와 downstream ASR을 분리한다. 인간 평가는 planted fault를 사용하며 오류 탐지율, 수정 시간, unintended edits를 측정한다. 참여자가 있으면 사전 동의와 데이터 최소화를 적용한다.

## 5. 재현성·데이터 관리

- 데이터, 모델, 프롬프트, seed, Python/OS 및 의존성 버전을 manifest에 고정한다.
- 개발/검증/최종 테스트를 분리하고 최종 테스트 튜닝을 금지한다.
- raw output은 `experiments/runs/`에 불변 저장하며 수동 수정하지 않는다.
- 공개 데이터마다 버전, URL, license, checksum을 기록한다. 비공개 대화와 재배포 불가 데이터는 포함하지 않는다.
- 삭제는 원본뿐 아니라 projection, index, cache, 평가 파생물까지 lineage로 검증한다.
- 릴리스 전 `pytest`와 `ruff check .`를 통과시키고, 실패·음성 결과도 보고한다.

## 6. 일정, 산출물, 의사결정 게이트

| 주차 | 산출물 | 게이트 |
|---|---|---|
| 1–2 | PRISMA식 검색 로그, prior-art matrix, 갱신된 ledger | 방어 가능한 기여가 없으면 범위 재설정 |
| 3–6 | 생성기, oracle, 결정론 테스트 | oracle 불일치 0건 |
| 7–10 | 최소 substrate와 rebuild 검증 | 모든 lifecycle 연산과 삭제 계보 통과 |
| 11–15 | 고정 프로토콜 비교 결과와 오류 분석 | 베이스라인 3종 이상 완전 재현 |
| 16–19 | 보안·감사 연구, artifact package, 논문 초안 | 주장별 근거·반증·CI 연결 |

첫 논문의 최소 단위는 WP0–WP3이다. RQ1이 실패하면 성능 포장 대신 git projection의 한계와 수정된 consistency model을 결과로 보고한다. RQ2–RQ4가 실패해도 음성 결과를 보존하고, 검색 최적화나 외부 서비스 도입으로 목표를 바꾸지 않는다.

## 7. 예상 기여(가설)

1. bitemporal oracle로 검증되는 재구축 가능한 agent-memory substrate.
2. 오염 저항형 lifecycle 생성기와 operation-level deterministic scorer.
3. 규모·churn·예산 조건을 명시한 비교 프로토콜.
4. provenance에서 행동과 삭제 파생물까지 이어지는 보안·감사 평가.

이 네 항목은 구현·재현·통계 검증 전까지 예상 기여이며 신규성 확정 문장이 아니다.
