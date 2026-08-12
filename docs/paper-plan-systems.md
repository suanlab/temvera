# 시스템 논문 실행 계획 — Auditable Bitemporal Agent Memory

> 기준일: 2026-07-16 · 목표: **시스템 논문**, 자원 **API-only(GPU 없음)**,
> 인간 연구 **protocol-only 유지(D-009)**.
> **Target venue: COLM 2027** (2026-08-13 결정 D-013; ICLR에서 전환).
> 5인 리뷰 시뮬레이션 결과 ICLR 예상 채택 8–10% vs COLM 40–50% — 학습 기여가
> 없어 venue 반론이 어떤 수정으로도 사라지지 않음. 차선: NeurIPS D&B.
> ICLR 9월 마감이 해제되어, 리뷰가 찾아낸 프로토콜 결함을 그대로 안고 제출할
> 압박이 사라짐.

## 0. ICLR 10주 역산 일정 (압축 범위)

10주는 공격적이다. 범위를 ICLR 심사에 필수적인 것으로 좁힌다.

| 주차 | 기간 | 산출 | 게이트 |
|---|---|---|---|
| W1–3 | 07/16–08/05 | **E1 본실험**: Mem0 + per-query transaction-time replay + ≥5 seeds × 2–3 scales; **E3 purge 완전성** 잔존 스캔; Zep/Graphiti 어댑터(가능하면) | ≥5 seeds 봉인, Mem0 발산 통계 확정 |
| W4–5 | 08/06–08/19 | E2 NL 워크로드 확정 + (여유 시)LoCoMo/LongMemEval subset E7; 검색 스토리(E-016/E-050) 마감 | 외적타당성 or 명시적 defer |
| W5–7 | 08/20–09/02 | **E6 집중 related work**(전면 PRISMA 아님 — 핵심 경쟁자 1차소스 검증 완결) + 결과 동결·오류분석 | 모든 주장 근거 연결 |
| W7–9 | 09/03–09/16 | 논문 전문 작성, 내부 리뷰, 그림/표, 재현 부록 | 초안 완성 |
| W9 | 09/17–09/24 | 폴리시·abstract(9/19)·full(9/24) 제출 | 투고 |

**ICLR 프레이밍 이동:** 데이터관리 어휘 → **경험적 벤치마크 + 검증가능 substrate +
실배포 시스템 발산 측정**으로 리드. "왜 ML 문제인가"(장기 에이전트의 stale-belief·
망각·감사)를 서론에서 명확히.

**압축으로 defer:** 전면 PRISMA(→집중 related work), E7(여유 시만), per-query
replay 대규모(→중간 규모), RQ4 인간연구/DOI(D-009 유지). 상세는 아래.

### ICLR 리스크(정직)
Zep/Graphiti 어댑터·대규모 replay가 10주에 안 들어오면: **Mem0(per-query replay,
다중 seed) 확정 + Zep/Graphiti는 소스수준 의미론 대조**로 후퇴(plan §6 위험표대로),
E7는 defer. 이 후퇴선에서도 C-A/C-B/검색/강건성은 성립한다.

---

> (이하 원래 6개월 계획 — ICLR 압축 시 위 W1–9 게이트가 우선한다.)
> 이 문서는 [systematic-research-plan.md](./systematic-research-plan.md)의
> WP0·WP3를 시스템 논문 궤도로 구체화한 실행판이다. 성능·신규성 문장은
> 실행·재현·통계 검증 전까지 가설이며, 모든 신규 결과는 evidence-ledger에
> E-049부터 행을 추가한다.

---

## 1. 프레이밍과 방어 가능한 주장 집합

프로젝트의 정직한 상태(선점된 신규성 다수, 음성 결과 보존)를 감안해, 논문은
**개별 기제의 신규성이 아니라 "독립 검증 가능한 시간 정확성·삭제/감사 의미론을
실제 배포 시스템과 동일 예산에서 측정한 결과"** 를 기여로 삼는다.

### 주장하지 않는 것 (선점됨 — 반증 근거)
- git-native / 감사가능 메모리 최초 (Springdrift, E-009)
- confidence 감쇠 기제 자체 (Springdrift, E-009)
- 최초의 절차생성 judge-free 망각 벤치 (ForgetEval, E-005)
- temporal graph 필드·필터 신규성 (Graphiti, E-024)
- belief revision 일반 (MnemeBrain/mnemosy — 소스 미검증, 주장 보류)

### 주장하는 것 (동일 예산에서 측정되는 결합)
- **C-A. 검증된 bitemporal 정확성**: valid×transaction 두 축의 `as-of` 정답을
  독립 SQLite oracle로 교차검증(E-042/E-044). 외부 시스템(Mem0/Zep)이 stale-state·
  as-of에서 **어디서 갈라지는지**를 실측한다.
- **C-B. 삭제/purge 완전성 (헤드라인 차별점)**: purge 후 파생 저장소(벡터·그래프·
  history)의 잔존 여부를 시스템별로 측정. Temvera는 JSONL 잔존을 정직 보고 +
  crypto-purge 프로파일 제시(E-033/D-006). 대조: Mem0 best-effort 정리(E-025),
  Graphiti 물리 삭제(E-024), Hindsight orphan→backfill(E-032).
- **C-C. provenance→action 게이팅**: write 수용과 action 활성화 분리(E-017),
  서명자 침해 시 실패까지 정직 보고(E-023).
- **C-D. 재현 가능한 통합 하네스**: 봉인된 실행·검증기·데이터 카드.

---

## 2. 크리티컬 실험 계획 (갭 해소)

| ID | 실험 | 해소 갭 | 자원 | 신규 산출 |
|---|---|---|---|---|
| **E1** | 외부 시스템 **동일 예산 재현**: Mem0(`633b035`)·Zep/Graphiti(`20a6728`)에 동일 이력 주입 → as-of/current 질의 → oracle 정답 대비 exact/stale 채점 | 외부 재현 전무 (최대 갭) | API(고정 백본·temp 0), GPU 불필요 | E-049+ |
| **E2** | **자연어 워크로드 어댑터**: 생성 이력을 대화 턴으로 렌더링(정답 상태와 분리). E1 입력이자 BM25 구조어 약점(E-043) 해소 | 외적 타당성·NL 부재 | 없음(결정론) | 렌더러 + 봉인 |
| **E3** | **purge 완전성 교차 측정**: purge/delete 후 각 시스템 파생 저장소 잔존 스캔 | C-B 실측 | E1과 공유 | E-050+ |
| **E4** | **learned 밀집검색 베이스라인 복구**: fastembed(ONNX·CPU)로 bge-small 다운로드, hard vector-synonym + NL 워크로드 평가 | E-038 제외 항목 | CPU만 | E-051+ |
| **E5** | **강건성 확장**: grid를 3→10 seeds, contradiction-density·churn 축 추가(E-043/E-044가 지목한 미래 축) | 3 seeds·2 프로파일 한계 | 없음(결정론) | E-052+ |
| **E6** | **WP0 문헌검토 완료**: ACL/ACM DL/IEEE/USENIX/OpenReview/arXiv 검색식·날짜·중복제거 CSV, 2차 스크리닝, PRISMA flow | 단독 스크리닝 한계 | 없음 | prior-art matrix |
| **E7*** | 외부 공개 대화셋 외적 타당성(LoCoMo / LongMemEval, 라이선스 허용 시 subset) | 전부 합성 | API(리더·판정) | 선택 |

\* E7은 6개월 여유 시 착수. LongMemEval은 GPT-4o judge를 쓰므로 **결정론 retrieval
지표와 judged QA를 분리**해 보고하고 judge 모델을 명시한다(E-036).

**범위 밖(자원 제약):** A-MemGuard/MemIncept 완전 재현은 GPU·checkpoint 필요
(E-034) → 보안은 결정론 기제 연구 + 소스 수준 대조로 한정, SOTA 방어 우위 주장 안 함.
RQ4 인간 연구는 protocol-only 유지 → planted-fault 생성기·프로토콜·채점기를
**설계/아티팩트 기여**로 프레이밍하고 실증은 명시적 future work.

### E1 프로토콜 통제 (필수)
- 고정 백본 LLM 1종, temperature 0, 프롬프트·토크나이저·검색 토큰 예산 동일.
- 각 외부 시스템 API 응답 트랜스크립트를 봉인 저장(캐시)해 재현·감사 가능하게 함.
- ≥3 seeds, 조건 내 bootstrap 95% CI, 다중비교 보정 사전 지정.
- retrieval recall과 리더 답 정확도 분리(evaluation-plan §experimental controls).
- 원자적 purge를 못 하는 시스템은 "이력 제공 ≠ 파생물 원자 삭제"로 구분 채점.

---

## 3. 6개월 일정과 결정 게이트

| 기간 | 산출 | 게이트 |
|---|---|---|
| **M1** | E6 착수, E2 렌더러, E1 하네스 스캐폴딩, 결정 D-010·D-011 기록 | **G1**: 렌더러가 oracle 정답으로 결정론적 round-trip; Mem0 1종 end-to-end ingest→query 성공 |
| **M2–M3** | E1(Mem0+Zep/Graphiti) + E3(purge 완전성) + E4(learned) | **G2**: 외부 시스템 ≥2종 동일예산 봉인 재현 완료, 지표별 오류분석 |
| **M3–M4** | E5(grid 확장) + E6 완료(PRISMA) + (여유 시)E7 | **G3**: 확장 grid bootstrap CI + prior-art matrix 완결 |
| **M4–M5** | 결과 동결, 주장→근거 매핑 확정, 보안 기제 연구 정리 | **G4**: 모든 기여 문장에 ledger ID·최근접 선행·측정 실험 연결 |
| **M5–M6** | 논문 작성, 내부 리뷰, 아티팩트 패키징·DOI(카메라레디 시 D-009 해제 제안), 투고 | 투고 |

**첫 논문 최소 단위:** E1·E2·E3·E4·E5·E6. E1이 실패(외부 재현 불가)하면 성능
포장 대신 "opaque store 대비 검증 가능성" 한계와 수정 consistency model을 결과로
보고하고, 프레이밍을 재현성·측정 연구로 후퇴한다(범위 재설정).

---

## 4. 실험 → 주장 → 논문 섹션 매핑

| 주장 | 근거(기존/신규) | 논문 섹션 |
|---|---|---|
| C-A 검증된 bitemporal 정확성 | E-042/E-044(기존) + **E1** | Results §RQ1 |
| C-B purge/삭제 완전성 | E-024/E-025/E-032/E-033(기존) + **E3** | Results §headline |
| 검색·감쇠 기제 식별성 | E-016/E-014/E-022(기존) + **E4** | Results §retrieval |
| 외적 타당성 | **E2**(+선택 **E7**) | Setup + Results |
| C-C provenance-action 게이팅 | E-017/E-023(기존) | Results §security(정직한 실패 포함) |
| 강건성 | **E5** | Results §robustness |
| 관련연구 방어선 | **E6** | Related Work |
| 재현성 | E-045/E-047(기존) | Artifact |

---

## 5. 논문 구조 (English, systems track)

1. **Introduction** — valid-vs-transaction time, revision, purge, audit의 문제 정의;
   Springdrift/ForgetEval/Graphiti/Mem0/Hindsight 대비 정직한 포지셔닝.
2. **Related Work** — E6의 prior-art matrix.
3. **Design** — event ledger, dual substrate(git + SQLite oracle), disposable
   projections, purge/crypto-purge, provenance-action gate (source: architecture.md).
4. **Experimental Setup** — generator, NL renderer(E2), identical-budget protocol,
   baselines(내부 + 외부 시스템), metrics, seeds/CI.
5. **Results** — RQ1 정확성 + 외부 divergence / purge 완전성(headline) / 검색·감쇠 +
   learned / 외적 타당성 / 보안 기제 + 정직한 실패.
6. **Negative Results & Limitations** — E-014/E-022/E-023 등 보존(프로젝트 강점).
7. **Artifact & Reproducibility**.

---

## 6. 위험 등록부 (이 범위)

| 위험 | 완화 |
|---|---|
| 외부 시스템이 API-only에서 완전 재현 실패 | Mem0(가장 API-friendly) 우선 확보; Zep는 필요 시 소스 수준 의미론 대조로 보완하고 정직 기록 |
| API 비용·비결정성 | temp 0, 응답 캐시·봉인, judge 분산 별도 보고, 백본·커밋 고정 |
| LongMemEval judge=GPT-4o 혼입 | 결정론 retrieval과 judged QA 분리, judge 모델 명시(E-036) |
| purge 비교가 시스템별 의미 차이로 불공정 | "이력 vs 원자 삭제" 축을 사전 정의해 동일 기준 채점 |
| 선점(scooped) | 결합·측정 프레이밍으로 방어, 개별 기제 주장 포기 |

---

## 7. 기록할 신규 결정 (사용자 승인 필요)

- **D-010 (제안)** — 외부 시스템 재현을 위한 LLM API 사용 및 응답 트랜스크립트
  봉인 보관을 승인한다. 비공개·라이선스 위반 데이터는 포함하지 않으며 제3자
  시스템 소스는 재배포하지 않는다. (D-009의 "외부 시스템 미실행" 범위를 API-only로
  한정 해제)
- **D-011 (제안)** — learned 밀집검색 베이스라인용 공개 임베딩 모델(예: bge-small)
  다운로드를 승인한다(CPU/ONNX, GPU 불필요). (D-009의 learned-model 유예 해제)
- **D-009 잔여** — 공개 DOI/아카이브는 카메라레디 단계에서 별도 승인 시 해제.

---

## 8. 진행 로그 (loop)

- **2026-07-16 · iter1 (G1 착수):** E2 자연어 렌더러(`src/temvera/nl_workload.py`)와
  E1 외부 비교 하네스 스캐폴딩(`src/temvera/external_harness.py`) 구현. 결정론적
  값-부분문자열 채점기 + 이벤트-인지 레퍼런스 어댑터 2종(`OracleMemorySystem`
  1/1/0, `LatestValueSystem` 시간맹목 열화)로 하네스 식별성 검증. `temvera
  external-smoke --seed 17` → oracle exact 1.0 / latest 0.542, stale 0.458.
  신규 테스트 8건 통과, 전체 `pytest`·`ruff check .` 통과. D-010/D-011 기록.
  **G1 판정:** 렌더러 결정론 round-trip ✓, 레퍼런스 시스템 end-to-end ingest→query ✓
  (실제 외부 어댑터 Mem0/Zep는 D-010 하 API 확보 시 drop-in).
- **2026-07-16 · iter2 (E5 완료):** 강건성 grid 확장 —
  `experiments/configs/lifecycle-grid-robust.json`, 3 profiles(+high_churn) × 3
  entities × 3 revisions × **10 seeds** × 6 systems = 1620 rows,
  `experiments/runs/lifecycle-grid-robust-v1` 봉인·검증(valid). Oracle exact/recall/
  stale = 1/1/0 (90개 조건 전부, 조건별 CI가 10 seeds 기반). high_churn에서
  베이스라인 추가 열화(append_only exact 0.255/stale 0.662). ledger E-049 추가.
  E-044의 3 seeds/2 프로파일 한계 해소.
- **2026-07-16 · iter3 (E4 완료):** learned 벡터 베이스라인 복구. bge-small(MIT,
  CPU/ONNX) 다운로드 후, alias 테이블에 없는 10개 동의어쌍에서
  `src/temvera/synonym_eval.py` + `temvera vector-synonym-compare` →
  hashing recall@1 **0.0** vs learned **1.0**. E-038의 learned 제외 항목 해소.
  신규 테스트 3건(오프라인 hashing + network-guarded learned). ledger E-050 추가.
  부수 발견: artifact tamper 검증 flaky(E-051, 릴리스 하드닝 게이트로 이관).
- **2026-07-16 · iter4 (논문 스켈레톤):** `docs/paper-draft.md`를 시스템 논문
  전체 구조(§5)로 재정비. 확정 결과(E-016/E-044/E-049/E-050) 결과 섹션 배선,
  API 의존 섹션(E1 외부재현·purge 완전성, E2/E7 외적타당성)은 **PENDING (D-010)**
  으로 명시.

### 자동 실행 구간 종료 (loop paused 2026-07-16)

오프라인·CPU 가능 항목은 모두 완료·검증했다: E2 렌더러, E1 하네스, E4 learned,
E5 강건성 grid, 논문 스켈레톤, D-010/D-011. 남은 항목은 **사용자 자원/판단 필요**
로 자동 진행 불가:

| 항목 | 차단 사유 | 필요 조치 |
|---|---|---|
| **E1/E2/E7 외부 재현** | LLM API 키 없음(env 미설정). mem0ai 설치는 가능하나 추출에 키 필요. | 사용자가 API 키 제공 → Mem0/Zep 어댑터 작성·실행. Mem0 v2.x는 E-025의 `633b035`(0.1.x)와 커밋 상이 — 핀 버전 재확정 필요. |
| **E6 문헌검토** | 1차 소스 검증 필요한 대규모 작업. 얕은 WebSearch는 AGENTS.md 위반. | 전용 deep-research 세션 또는 academic-researcher 에이전트, 검색식·PRISMA 로그. |
| **RQ4 인간연구 / DOI** | D-009로 보류. | 별도 승인. |
| **E-051 tamper flaky** | 릴리스 하드닝 게이트로 이관. | envelope 무결성 검증으로 수정. |

### loop 재개 후: E1 파일럿 (2026-07-16)

사용자가 OpenAI API 키 제공 → E1 착수. Mem0 `0.1.118`(OSS `Memory`, gpt-4o-mini,
text-embedding-3-small) 어댑터(`mem0_adapter.py`) + 봉인 러너(`external_experiment.py`)
+ `external-mem0` CLI 구현. 결과(E-052, 봉인·검증):

- **방법론 발견:** 합성 토큰(`entity-000`,`place-38`)이 임베더에서 붕괴 →
  Mem0가 엔티티조차 구분 못함(v1 valid_time 0.167). `naturalize_events`(단사
  relabel, oracle 정확성 불변 검증)로 v2에서 exact **0.231→0.462**, 실패의 절반이
  토큰화 혼입임을 분리.
- **본질 발산:** v2 잔여 실패는 transaction_as_of/valid_time(현재상태만 반환)·
  expiry_boundary(만료 사실 abstain 실패, abstention 0.0)에 집중. oracle은 동일
  주입에서 exact 1.0.
- 버그 수정: CLI 함수-지역 `import seal_run`이 `main()` 전체에서 seal_run을
  지역변수화 → lifecycle-grid/operation-suite 봉인 `UnboundLocalError` 유발할 수
  있었음. 제거.

**E1 남은 것(파일럿→본실험):** per-query transaction-time replay, 다중 seed·규모,
Zep/Graphiti 어댑터. 전체 101 테스트·ruff 통과.

### E1 본실험 착수 (2026-07-17)

- **효율적 replay 재설계:** transaction time 단조성 → forward-checkpoint replay
  (턴을 recorded_at 순 전진 주입, 각 transaction_at에서 질의). 셀당 O(턴) 호출로
  reset 없이 정확한 transaction-time 의미론. 러너 adapter-agnostic 재작성
  (`external_experiment.py`), 오프라인 테스트 3건(oracle 양 모드 exact, 전진주입
  1회/턴, call projection) 통과.
- **Mem0 대규모 grid 실행 중:** 8 seeds × 3 scales × 2 profiles = 48 cells,
  per-query replay, gpt-4o-mini. 사전 call projection ~1837 ingest/~1833 search
  → **~$1–2**(승인 ~$30–60 대비 여유; forward-checkpoint 효율 덕). 백그라운드
  실행(PID 3588112), 완료 시 분석·ledger 기록 예정.
- **Graphiti 차단(인프라):** graphiti-core 0.29.2의 유일한 서버리스 백엔드 **Kuzu가
  손상**(3개 버그: driver `_database` 미설정, edge FTS 인덱스 `edge_name_and_fact`
  미생성, cosine-only 경로도 FTS 호출) + Graphiti가 Kuzu를 deprecated로 표기.
  유지보수 백엔드(Neo4j/FalkorDB)는 서버 필요하나 Docker 데몬 권한 거부.
  → 사용자에게 Neo4j 기동 or 소스수준 대조 fallback 결정 요청. 어댑터
  (`graphiti_adapter.py`)는 작성 완료, Neo4j 확보 시 배선·실행.

### E1 Mem0 grid 결과 확정 (E-053, 2026-07-17)

`external-mem0-grid-v1` 봉인·검증(48 cells). **헤드라인:** 동일 이력에서 Mem0는
transaction-time 범위 현재질의는 잘하나(transaction_as_of **0.949**) 과거
valid-time(**0.346**)·expiry(**0.062**)·**purge(0.121)** 에서 실패 — 즉 삭제·만료
사실을 반환(C-B 삭제완전성 직접 증거). oracle 1.0. 규모↑ 시 Mem0 열화
(0.70→0.52, 8-seed 95% CI). backbone gpt-4o-mini/Mem0 0.1.118. E-052 파일럿 대체.

**Graphiti 재개(사용자 Neo4j 선택):** 어댑터에 Neo4j 백엔드 배선 완료
(env `NEO4J_URI/USER/PASSWORD` 또는 config), `run_graphiti_comparison` +
`external-graphiti` CLI + 소규모 grid config(3 seeds×2 scales×1 profile) 준비.
Kuzu 경로는 손상 명시하고 Neo4j 필수. 전체 테스트·ruff 통과.

### Graphiti 결과 확정 (E-054, 2026-07-17)

Docker 권한 불가 → **rootless JDK21 + Neo4j 5.26 tarball 직접 기동**(bolt 7687).
Graphiti grid(`external-graphiti-grid-v1`, 6 cells) 봉인·검증. **핵심 대조 —
두 가지 다른 실패 양식:**
- **Mem0**(E-053): 현재상태로 병합 → 과거를 *잊음*. transaction_as_of 0.949지만
  valid_time 0.346.
- **Graphiti**(E-054): temporal edge *보존* → recall 0.873지만 valid-time 필터
  미적용으로 stale+current 동시 반환 → exact 0.224, stale 0.561.
- **Oracle**: 두 축 모두 적용 → 1.0.
- 둘 다 expiry/purge abstain 실패(C-B).

**공정성 후속 완료 (E-055):** Graphiti native `valid_at` 필터를 적용해 재실행
(`external-graphiti-filtered-v1`, 봉인·검증). 결과는 **개선이 아니라 악화**:
exact 0.224→0.031, recall 0.873→0.049, stale 0.561→0.960.
원인(Cypher 직접 진단, 80 edges): 대체된 edge 26/80이 `invalid_at` **미설정**
→ stale이 영구히 필터 통과; dated invalidation 54건 중 4건은 모순
(`invalid_at <= valid_at`) → 정답 edge 배제. 빈 답변은 10.4%뿐이라 abstain이
아니라 *오답 선택*이 손실 원인. `created_at`/`expired_at`은 벽시계 주입시각
(2026)이라 as-of 표현 불가 → replay로 강제(공정). `valid_at` NULL 0/80이므로
필터가 부당하게 엄격하지 않음. **교란:** 추출기가 gpt-4o-mini —
상위 모델이면 메타데이터가 나아질 수 있어 "현 파이프라인 기본값"의 한계로 한정.

→ **논문 메시지 강화:** temporal *필드* 보유 ≠ temporal *정확성*.

### 오염 사고와 정정 (2026-07-17)

**사고:** Graphiti cell `group_id`가 실행 간 재사용되는데 Neo4j `reset()`이 그룹을
비우지 않아, 나중 실행이 이전 실행 엣지가 남은 그래프에 질의(셀당 36 episodes,
정상 12). **E-055와 1차 gpt-4o 결과 무효** → ledger에 `superseded — invalid
measurement`로 철회하고 원본 수치는 provenance로 보존. default 실행(E-054)은
최초라 무오염.
**수정:** `reset()`에 group 단위 DETACH DELETE + config `graphiti_group_prefix`로
이중 격리. Neo4j 직접 조회로 12 episodes/cell 검증.

**정정된 결과 (E-057, 무오염):** 필터는 "전부 악화"가 아니라 **정밀도↑/recall↓**
트레이드오프 — exact 0.224→0.318, stale 0.561→0.360, recall 0.873→0.318.
그러나 핵심 범주는 여전히 실패: valid_time 0.093, expiry 0.067, purge 0.306.

**E-058 (교란 제거):** gpt-4o 추출로 교체해도 valid_time 0.111→0.111,
expiry 0.000→0.000 **불변**(purge는 오히려 하락). 천장은 추출기 품질이 아니라
**아키텍처**(transaction-time 축 부재, `invalid_at` 미설정)임을 확정.

### E1+E3 최종 상태
Mem0(48 cells)·Graphiti(default/filtered/gpt-4o, 격리 검증)·purge 잔존 스캔까지
완료. 헤드라인 C-A/C-B 모두 실측 근거 확보. 남은 것: E6 문헌검토, 규모 확대,
E7 외적타당성.

**E1 현황:** Mem0(48 cells)·Graphiti(6 cells) 2종 외부시스템 동일조건 확정.
남은 것: (a) temporally-filtered Graphiti, (b) purge 파생저장소 잔존 스캔(E3),
(c) 규모 확대. 헤드라인 C-A/C-B 성립.
