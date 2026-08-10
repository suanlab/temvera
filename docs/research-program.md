# 통합 연구 프로그램 계획 — Git-Native Auditable Agent Memory

> 2026-07-15 · 이름충돌 조사에서 드러난 **컨셉 경쟁자 7건**을 반영해 T11·T1·T12를 하나의 논지로 재정의한 마스터 플랜.
> 관련 문서: [연구 지도](./ai-memory-research-agenda.md) · [선행연구 조사](./ai-memory-related-work.html) · [T11 제안서](./proposal-T11-belief-revision-memory.md) · [T1 제안서](./proposal-T1-memory-lifecycle-benchmark.md)

> **2026-07-15 검증 경고:** Springdrift 원문은 append-only memory와
> git-backed recovery를 이미 명시한다([evidence E-009](./evidence-ledger.md)).
> 따라서 아래 C1의 “최초”, “경쟁자 전부 DB”, “무선행” 표현은 반증됐으며
> 신규성 근거로 사용하면 안 된다. 최신 실행안은
> [체계적 연구 계획서](./systematic-research-plan.md)를 따른다.

---

## 0. 무엇이 바뀌었나 (정직한 재평가)

이름 조사 과정에서 **우리 연구와 직접 겹치는 활성 프로젝트/논문**이 나왔다. 이는 두 제안서의 일부 "최초" 주장을 선점한다.

| 경쟁자 | 무엇인가 | 선점하는 우리 주장 | 근거 |
|---|---|---|---|
| **Springdrift** | 에이전트 메모리에 `c_t=c_0·2^(−t/h)` **반감기 confidence 감쇠** | T11의 "감쇠 confidence 기제" 자체 | arXiv 2604.04660 |
| **mnemosy.ai** | 상용 "Cognitive Memory OS", confidence-tiered belief + **모순해소 통합** | T11의 "믿음개정+confidence" 조합 | mnemosy.ai |
| **MnemeBrain** | TMS + Belnap logic + **AGM belief revision** for agents | T11의 belief-revision 이론 앵글 | mnemebrain.ai |
| **Eywa** | provenance-grounded LTM (evidence→signals→beliefs→provenance graph) | T11/T12의 "프로비넌스 믿음 저장소" | arXiv 2605.30771 |
| **deeplethe/lethe — ForgetEval** | "잊도록 만든 AI 메모리" + **망각 벤치마크**(supersession·decay·amnesia·purge·drift) | **T1의 "최초 망각/생애주기 벤치" 주장** | github.com/deeplethe/lethe |
| **AI Ledger / AI Commit Ledger** | **git-native** append-only AI provenance/거버넌스 | T12의 "git-native 프로비넌스" 프레이밍 | github.com/ai-ledger · arXiv/RG 2026 |
| **UnluckyMycologist68/palimpsest** | **마크다운 기반** 계층적 LLM 컨텍스트 연속성 | T11의 "마크다운 메모리" 표면 | github repo |

**결론:** "감쇠 confidence"(Springdrift), "망각 벤치마크"(ForgetEval), temporal hybrid memory(Hindsight/Graphiti), poisoning attack/defense(MINJA·MemIncept·A-MemGuard)는 모두 활성 선행영역이다. Temvera는 개별 기능의 신규성이 아니라 exact bitemporal oracle, rebuild/purge 검증, provenance-action trace를 동일 궤적에서 측정하는 조합을 가설로 검증한다.

> **확인 상태:** ForgetEval의 seeded generation·deterministic substring scorer와 Springdrift의 append-only·Git-backed recovery는 1차 소스에서 확인했다(E-005, E-009, E-013). 나머지 novelty 주장은 체계적 검토와 외부 재현 전까지 잠정이다.

---

## 1. 통합 논지 (One Thesis)

> **"canonical event log와 인간이 읽는 projection을 분리하고, 두 시간축·삭제 계보·provenance-action trace를 독립 oracle과 결정론적 재구축으로 검증한다."**

이 결합의 존재 여부와 실질적 효용은 아직 가설이다. Hindsight, Graphiti, Springdrift, ForgetEval, MemLineage와 같은 예산·fixture에서 측정되는 차이만 기여로 남긴다.

---

## 2. 재정의된 기여 (Contributions)

각 기여를 "그것이 이기는 경쟁자"와 "현재 novelty 상태"와 함께 명시한다.

### C1 — Git-as-Bitemporal-Ledger 기질 (신규성 미확정)
git 이벤트와 명시적 valid time으로 **as-of 질의·프로비넌스 감사·인간 diff/PR 리뷰**를 제공하고, 그 정확성을 relational bitemporal oracle과 비교한다.
- **가장 가까운 대상:** Springdrift는 append-only memory와 git-backed recovery를 이미 제공한다.
- **상태:** 가설 — 차별점은 git 사용 자체가 아니라 bitemporal 의미론의 정확성, 결정론 검증, 인간 감사 효율로 제한한다.

### C2 — 감쇠 계층 비교 (음성 결과)
감쇠 confidence를 **검색 랭킹이 아니라 믿음-상태 전이**에 두어야 한다는 통제 실험. vstash의 부정결과(랭킹 감쇠→NDCG 하락)를 긍정 설계로 전환.
- **이기는 대상:** Springdrift(감쇠는 있으나 배치 선택을 실증 안 함)
- **상태:** 초기 가설 반증 — 384-cell 합성 grid에서 상태 감쇠가 랭크 감쇠를 지배하지 못했다(E-014). 외부 데이터 없이 일반 우위를 주장하지 않는다.

### C3 — Judge-Free 생애주기 벤치마크 (중간, 재프레이밍 필요)
exact bitemporal state와 operation trace를 계산하는 연산수준 벤치이며 ForgetEval 호환 결과를 함께 보고한다.
- **가장 가까운 대상:** ForgetEval은 이미 절차생성·judge-free 5범주를 제공하고, Mem2ActBench는 dynamic memory evolution과 tool use를 함께 평가한다.
- **상태:** 차이는 `as-of` transaction/valid-time 정답, rebuild/purge 검증, provenance-action trace로 제한한다. 신규성 확정 문구는 사용하지 않는다.

### C4 — 파일 저장소 프로비넌스 방어 (가설)
프론트매터를 **집행 지점**으로 삼아 권위 인식 검색·행동 게이팅과 위조/프로비넌스 세탁을 평가한다.
- **이기는 대상:** AI Ledger(거버넌스 표준이지 authority-gated 검색 아님)·Eywa(프로비넌스 그래프이지 파일/보안평가 아님)
- **상태:** 미확정 — MemLineage, A-MemGuard, MINJA, MemIncept와 동일 공격 예산으로 비교하기 전 독자성·효과 우위를 주장하지 않는다.

### C5 — 오픈소스 통합 레퍼런스 하네스 (기여물)
Temvera 위에 C1–C4를 통합한 재현가능 하네스. "불투명 저장소가 못 하는 인간참여형 감사가능 메모리"의 실증체.

---

## 3. 세 트랙 → 하나의 프로그램

| 트랙 | 구 제안 | 재정의된 역할 | 산출 |
|---|---|---|---|
| **A. 기질·시스템** | T11 | git-native 감사가능 믿음개정 메모리 (C1+C2) | 시스템 논문 |
| **B. 평가** | T1 | judge-free 생애주기 벤치 + judge 타당성 (C3) | 벤치 논문 |
| **C. 보안** | T12 | 프론트매터 프로비넌스 방어 (C4) | 보안 논문 or A에 병합 |

**통합 방식:** B가 A의 평가 하네스이자 독립 기여. A는 B로 자기 검증. C는 A의 프론트매터 스키마(`source.authority`)를 보안으로 확장. 하나의 아티팩트(C5)가 셋을 잇는다.

---

## 4. 구체 작업 분해 & 일정

### Phase 0 — 선행연구 잠금 (2주) · **최우선**
- [x] ForgetEval 원문/코드 정독: deterministic top-k substring scorer와 seeded procedural generation을 확인하고 C3를 재정의했다(E-005, E-013).
- [x] Springdrift 원문/코드 정독: append-only JSONL, git recovery, read-time decay와 평가 fallback 문제를 확인했다(E-009, E-040).
- [ ] mnemosy.ai·MnemeBrain·Eywa·AI Ledger 기술문서 확인 → C1/C4 차별점 문장 확정.
- [x] 두 제안서 related-work에 가장 가까운 시스템과 반증 근거를 편입했다.
- **산출:** "방어가능 novelty 확정본" 1페이지.

### Phase 1 — 벤치마크 먼저 (Track B, 6주) · 저위험 선행
학습 불필요·경쟁자 대비 가장 빨리 방어선 확보. C3.
- 엔티티-속성 상태기계·유효기간 생성기·결정론 검증기.
- ForgetEval 5범주 + write/merge/contradiction/temporal-validity 축 구현(ForgetEval을 부분집합으로 재현해 상호운용 입증).
- judge 타당성 슬라이스(judge-vs-계산정답 CI).

### Phase 2 — 기질·시스템 (Track A, 8주) C1+C2
- 프론트매터 스키마 + Ingest/Reconfirm/Supersede/Decay 연산자 + git 로그 어댑터.
- **핵심 실험 C2:** 감쇠를 (i)믿음상태 vs (ii)검색랭킹에 둔 두 구성 통제 대조.
- **핵심 실험 C1:** git 히스토리만으로 as-of 질의 정확도 vs 전용 bitemporal DB.

### Phase 3 — 경쟁자 대비 평가 (4주)
- Phase 1 벤치로 A를 Springdrift식(감쇠-only)·Zep·Mem0·mnemosy.ai식 베이스라인과 비교.
- stale-fact 사용률·abstention·as-of·감사가능성 지표.

### Phase 4 — 보안 (Track C, 6주) C4
- 프론트매터 authority 게이팅 + 위조/세탁 공격 구현 + MINJA 대비 평가.

### Phase 5 — 작성·릴리스 (4주/트랙별)
- Paper 1(벤치) → Paper 2(시스템+C2) → Paper 3(보안) 또는 2에 병합.

---

## 5. 통합 평가 설계

| 축 | 베이스라인(경쟁자 포함) | 지표 |
|---|---|---|
| 생애주기(C3) | Mem0·Zep·Letta·LangMem·**ForgetEval 셋**·raw LC·RAG | 연산별 정확도·FAMA·judge-vs-계산정답 CI |
| 기질/감쇠(C1·C2) | append-only·LWW·**Springdrift식 감쇠-랭킹**·Zep(boolean)·**mnemosy식 belief** | stale-fact율↓·abstention↑·as-of 정확도·감사 커버리지 |
| 보안(C4) | TMA-NM·MemLineage·미집행 프론트매터 | 주입성공률↓·위조탐지·행동게이팅 정확도 |

---

## 6. 위험 등록부 (경쟁자 인지)

| 위험 | 심각도 | 완화 |
|---|---|---|
| **선점(scooped)** — Springdrift/ForgetEval가 먼저 확장 | 높음 | 기질+평가+보안 **결합**으로 방어; 개별 기제 주장 포기; Phase 0·1로 빠르게 선점 회피. |
| ForgetEval가 이미 judge-free·절차생성이면 C3 약화 | 중 | Phase 0에서 확인; 그럴 경우 C3를 "judge 타당성 메타연구 + 연산 축 확장"으로 축소하고 무게를 C1/C2/C4로 이동. |
| "파일이라 SOTA 정확도 안 남" | 중 | 목표는 정확도 1위가 아니라 **감사가능·인간참여·판정신뢰의 Pareto 우위**; 동일 백본 통제. |
| 이름 미확정 | 낮음 | §8 참조; 코인드 네임 검증 후 확정, 그 전엔 코드네임 "Temvera-BR". |

---

## 7. 제안서에 편입할 선행연구 (related-work 추가분)

두 제안서에 아래를 정식 인용·차별화로 추가한다.

- **T11에 추가:** Springdrift(2604.04660, 감쇠기제 선행 — 우리는 기질·배치로 차별), mnemosy.ai(상용 belief OS — 인간감사로 차별), MnemeBrain(AGM/TMS — 파일/git로 차별), Eywa(2605.30771, 프로비넌스 LTM — 파일/보안으로 차별), UnluckyMycologist68/palimpsest(마크다운 컨텍스트 — 감쇠·bitemporal 없음).
- **T1에 추가:** deeplethe/lethe **ForgetEval**(망각벤치 선행 — 우리는 judge-free·절차생성·연산확장·judge타당성으로 차별; 5범주를 부분집합으로 포함).
- **T12에 추가:** AI Ledger/AI Commit Ledger(git-native provenance — 우리는 authority-gated 검색·위조공격·MINSA평가로 차별).

---

## 8. 이름 (미결)

6개 후보 전부 충돌(Mnemosyne/Lethe/Ledger/Half-Life/Palimpsest CROWDED~TAKEN, CREED만 MINOR). 특히 **Lethe는 ForgetEval의 deeplethe/lethe와 직접 충돌**이라 절대 회피. 코인드 후보(**Pentimento**/Recension/Doxa/Credal) 검증 후 확정. 확정 전 코드네임 **Temvera-BR**(Belief Revision).

---

## 9. 살아남는 novelty 체크리스트 (정직판)

- ⚠️ **git-as-bitemporal-ledger 기질** — Springdrift가 인접 선행이므로 정확한 의미론과 비교 실험으로만 차별 가능.
- ❌ **감쇠 상태가 랭킹 감쇠보다 우월** — 초기 grid에서 반증(E-014).
- ⚠️ **파일 저장소 프로비넌스 방어 + 위조공격** — 인접 공격·방어선과 동일 조건 비교 전 미확정.
- ⚠️ **judge 타당성 메타연구(메모리 연산 특화)** — 전체 문헌 검토 전 미확정.
- ⚠️ **인간 diff/PR 리뷰 효율** — protocol만 준비됐고 참가자 결과 없음.
- ⚠️ **감쇠 confidence 기제 자체** — Springdrift 선점, 주장하지 말 것.
- ⚠️ **"최초 망각/절차생성 judge-free 벤치"** — ForgetEval 선점; 주장하지 않는다.
- ⚠️ **belief revision 일반** — MnemeBrain/mnemosy 활성, 기질로만 차별.
