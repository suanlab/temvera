# 논문 제안서 — T11: 프로비넌스·믿음개정 마크다운 메모리

> **작업 제목:** *Git-Native Belief Revision: Decaying-Confidence, Bitemporal Memory on a Flat Markdown Store for LLM Agents*
> 유형: 시스템 + 알고리즘 · 위험도: 중 · Temvera 정체성 직결
> 작성일 2026-07-15 · 근거: [선행연구 조사](./ai-memory-related-work.html) T11 · **[통합 프로그램 계획](./research-program.md)**

> ⚠️ **선행연구 갱신(2026-07 충돌조사 반영) — novelty 재정의:** 이름 조사에서 **직접 경쟁자**가 드러나 아래 원 제안의 "감쇠 기제" 주장은 **선점**됐다. 반드시 [통합 프로그램 계획 §0·§2](./research-program.md) 기준으로 읽을 것.
> - **Springdrift** (arXiv 2604.04660): 에이전트 메모리에 `c_t=c_0·2^(−t/h)` 반감기 confidence 감쇠를 **이미 구현**. → §4.2의 감쇠 공식은 우리 기여가 **아님**.
> - **mnemosy.ai**: 상용 belief OS(confidence-tiered + 모순해소). **MnemeBrain**: AGM/TMS belief revision. **Eywa**(2605.30771): provenance-grounded LTM. → "belief revision + confidence" 조합은 활성 경쟁 영역.
> - **살아남는 방어선(이것만 주장):** ① **git-as-bitemporal-ledger 기질**(as-of·감사·diff/PR 무료 — 경쟁자 전부 벡터/그래프/DB), ② **감쇠 배치 실증**(믿음상태 vs 랭킹, vstash 부정결과의 긍정 전환), ③ **인간 감사가능성**. 기제가 아니라 **기질·배치·감사**로 차별.
> - **Phase 0 필수:** Springdrift의 저장 기질(파일/git 여부)을 원문 확인 후 ②의 대조를 확정.

---

## 1. 초록 (Pitch)

LLM 에이전트의 장기 메모리는 "무엇을 기억하는가"가 아니라 **"바뀌는 세계 속에서 무엇을 여전히 믿어야 하는가"**의 문제다. 현행 시스템은 사실을 append하거나 파괴적으로 덮어쓰며, 진부해진 정보를 조용히 계속 사용한다. 우리는 각 메모리를 **개정가능한 믿음(revisable belief)**으로 취급하는 경량 메모리 하네스를 제안한다. 각 믿음은 (event-time, ingestion-time) 이중 시간과 **재확인 없이는 감쇠하는 confidence**를 지니며, 모순은 파괴적 덮어쓰기가 아니라 **질의 시점 supersede(패자 보존)**로 해소된다. 핵심 통찰은 **git 커밋 히스토리 자체가 append-only bitemporal 로그**라는 것 — 별도 버전관리 인프라 없이 감사가능성을 무료로 얻는다. 모든 것은 평면 markdown + YAML 프론트매터 위에서 동작하여 인간이 읽고·diff하고·리뷰할 수 있다. LongMemEval·LOCOMO의 knowledge-update·temporal·abstention 하위셋에서 파괴적 덮어쓰기 및 그래프 기반 bitemporal 베이스라인(Zep) 대비 **stale-fact 사용률 감소와 abstention 정확도 향상**을 목표로 한다.

---

## 2. 문제 정의 & 동기

에이전트 메모리를 DB 관점에서 보면 정확성은 개별 레코드가 아니라 **상태 궤적(state trajectory)**에 달려 있다 (GEM, arXiv 2605.26252). 최근 연구(Memora/FAMA, ACL 2026 Findings)는 **존재 기반(memory-presence) 정확도가 성능을 과대평가**함을 보였다 — 폐기됐어야 할 메모리 사용을 벌하지 않기 때문이다. 즉 핵심 난제는 용량이 아니라 **변경 속의 일관·최신성 유지**다.

세 가지 구체적 실패가 반복된다:
1. **파괴적 갱신** — 사실이 바뀌면 옛 값을 덮어써 감사·롤백·근거 추적이 불가.
2. **비교할 상태 표현** — Graphiti는 `valid_at`, `invalid_at`, `expired_at`를 제공한다. confidence의 점진적 쇠퇴 지원 여부는 고정 소스에서 아직 완전 검증하지 않았으므로 부재로 단정하지 않고, 동일 fixture에서 boolean validity와 thresholded confidence를 비교한다.
3. **감쇠의 오배치** — 앞선 vstash 연구는 시간 감쇠를 **검색 랭킹 스코어에 직접 넣으면 NDCG가 오히려 하락**함을 보였다. 감쇠는 검색 계층이 아니라 **믿음 상태 계층**에 있어야 한다.

**왜 지금, 왜 파일 기반인가.** Springdrift가 이미 append-only·Git-backed agent memory를 제공하고 Hindsight와 Graphiti가 temporal hybrid/graph memory를 제공한다. 따라서 파일·Git·시간 필드 자체는 공백이 아니다. 검증할 차이는 canonical event log에서의 byte-level rebuild, 독립 relational oracle과의 `as-of` 동등성, declared projection 전체의 purge lineage, 그리고 인간 감사 비용이다.

---

## 3. 연구 질문 & 가설

- **RQ1** 연속 감쇠 confidence가 boolean 무효화(Zep식) 대비 stale-fact 사용을 줄이는가?
  - *H1:* 재확인 없는 믿음의 confidence를 시간 감쇠시키고 임계 미만이면 회수에서 강등하면, 파괴적/boolean 베이스라인 대비 stale-fact 응답률이 유의하게 감소한다.
- **RQ2** 감쇠를 **검색 스코어가 아니라 믿음 상태**에 두면 vstash가 보고한 NDCG 하락을 피하면서 abstention을 개선하는가?
  - *H2:* 감쇠를 회수 랭킹 가중이 아니라 supersede/expiry 상태 전이로 구현하면 검색 품질을 해치지 않고 "모른다/상충한다" 기권 정확도가 오른다.
- **RQ3** git 히스토리를 bitemporal 로그로 쓰면 별도 버전 저장 없이 "언제 참이었나 vs 언제 알았나" 질의(as-of)를 정확히 답할 수 있는가?
  - *H3:* 프론트매터 (valid_from/to, observed_at) + git blame/log만으로 시간여행 질의 정확도가 전용 bitemporal DB에 근접한다.

---

## 4. 제안 방법

### 4.1 데이터 모델 (프론트매터 스키마)
```yaml
---
id: <slug>
claim: "<사실 한 줄>"
valid_from: 2026-03-01        # event-time 시작 (언제 참이 됐나)
valid_to: null                # event-time 종료 (무효화 시각; null=현재 유효)
observed_at: 2026-03-02       # ingestion-time (언제 알았나)
confidence: 0.82              # 현재 믿음 강도
last_reconfirmed: 2026-06-10  # 마지막 재확인 시각
half_life_days: 90            # 감쇠 반감기 (사실 유형별)
supersedes: [old-slug]        # 이 믿음이 대체한 이전 믿음
superseded_by: null           # 이 믿음을 대체한 이후 믿음
source: {origin: user|tool|inference, authority: high|med|low}
---
<본문: 근거·맥락·[[관련 믿음]] 링크>
```
git 커밋 = ingestion-time 트랜잭션 로그. `superseded_by`로 패자 보존(파괴적 덮어쓰기 금지).

### 4.2 감쇠·개정 연산자 (GEM의 4연산자에 대응)
- **Ingest** — 새 믿음 파일 생성, confidence 초기화, 커밋.
- **Reconfirm** — 재관측 시 `last_reconfirmed` 갱신·confidence 부스트(감쇠 리셋).
- **Decay(질의시 지연 계산)** — `conf(t) = confidence · 2^(−(t − last_reconfirmed)/half_life)`; 임계 미만이면 회수에서 강등(삭제 아님).
- **Supersede** — 모순 탐지 시 이전 믿음에 `superseded_by` 설정·`valid_to` 마감, 신규 믿음 링크. 패자는 파일로 보존(git에도 영구 기록).
- **Retrieve(as-of)** — 질의 시각/유효시각 기준 가시 믿음만 반환, 감쇠 confidence로 랭킹 보정은 **하지 않고** 강등/기권에만 사용(H2).

### 4.3 모순 탐지
경량 LLM 추출로 (subject, relation, object) 정규화 후 동일 (subject, relation)에 상충 object 발생 시 supersede 트리거. 결정론적 경로(2606.01435 "Don't Ask the LLM to Track Freshness" 스타일)와 LLM 경로를 ablation.

---

## 5. 평가 설계

| 항목 | 내용 |
|---|---|
| **벤치마크** | LongMemEval(knowledge-update·temporal-reasoning·abstention 서브셋), LOCOMO(temporal·knowledge-update), 2606.01435 freshness 셋. T1 생애주기 벤치(자매 제안서)가 준비되면 연산수준 채점 추가. |
| **베이스라인** | ① append-only(감쇠·supersede 없음), ② 파괴적 last-writer-wins, ③ Zep/Graphiti(그래프 bitemporal·boolean 무효화), ④ Mem0, ⑤ Hindsight, ⑥ ablation: supersede-only(감쇠 off), decay-in-ranking(vstash식, H2 반례 검증). |
| **지표** | stale-fact 사용률↓, abstention 정확도↑(모름/상충 정답), knowledge-update 정확도, as-of 질의 정확도(H3), FAMA 스타일 망각 페널티, 토큰/지연 오버헤드. |
| **핵심 대조** | H2: 감쇠를 상태에 둘 때 vs 랭킹에 둘 때의 NDCG/abstention 차이(vstash 부정결과 재현·해소). |

---

## 6. 예상 기여

1. **평면 Markdown projection과 canonical event log의 검증 가능한 결합** — 독립 oracle·rebuild·purge 실험으로 기존 시스템과의 차이를 측정한다.
2. **감쇠의 올바른 계층 규명** — 검색 랭킹(실패)이 아니라 믿음 상태 전이(제안)라는 설계 원칙을 실증.
3. **git-as-bitemporal-log** — 버전관리 인프라 없이 as-of/감사를 얻는 저비용 패턴.
4. **인간 검사가능 메모리** — diff·PR 리뷰 가능한 에이전트 메모리(불투명 임베딩과 대조).

---

## 7. 위험 & 완화

| 위험 | 완화 |
|---|---|
| 반감기 `half_life`를 사실 유형별로 정하기 어려움 | 유형별 사전값 + 데이터 기반 학습(재확인 간격 분포에서 추정); 민감도 분석 포함. |
| 모순 탐지의 LLM 비결정성(21 vs 38 트리플 문제) | 결정론적 정규화 경로 병행·재현성 보고; supersede는 보수적(고확신 상충만) 트리거. |
| git 히스토리가 as-of DB만큼 질의 효율적이지 못함 | 프론트매터에 유효시각 색인 캐시; git은 감사·근거 추적용, 핫패스는 인덱스. |
| Zep 대비 "그래프 없이 되나" 반론 | 목표는 SOTA 정확도가 아니라 **경량·검사가능·감쇠**의 Pareto 우위; 동일 백본·설정 통제 벤치로 방어. |
| 벤치마크 자체보고 논쟁(LOCOMO) | 동일 모델·프롬프트로 모든 베이스라인 재실행; 자매 제안서 T1의 judge-free 지표 병행. |

---

## 8. 마일스톤 (약 6개월)

1. **M1 (4주)** 프론트매터 스키마·감쇠/supersede 연산자·git 로그 어댑터 구현(Temvera 위).
2. **M2 (6주)** 모순 탐지(결정론+LLM) 및 as-of 회수; 단위 평가.
3. **M3 (6주)** LongMemEval·LOCOMO 베이스라인 6종 재실행·주요 대조(H1–H3).
4. **M4 (4주)** ablation(감쇠 위치 H2, 반감기 민감도), 오버헤드 측정.
5. **M5 (4주)** 작성·오픈소스 릴리스(재현 스크립트).

---

## 9. 목표 발표처

- **주:** COLM, ACL/EMNLP(main 또는 Findings), NeurIPS D&B(벤치 병행 시).
- **시스템 앵글 강화 시:** CIDR(비전 페이퍼), VLDB(bitemporal·as-of 엄밀화 시 T8과 결합).
- **워크숍 선공개:** Agent memory / long-context 계열.

---

## 10. 자매 제안서와의 관계

- **T1(생애주기 벤치마크)** — 본 시스템의 **연산수준 평가 하네스**. T1이 먼저 서면 T11의 stale-fact/supersede/expiry를 judge-free로 채점 가능. 권장 순서: T1 → T11.
- **T12(프론트매터 프로비넌스 방어)** — 본 스키마의 `source.authority`를 보안 집행점으로 확장. T11의 자연스러운 후속.
- **T8(bitemporal MVCC)** — 다중 에이전트 동시쓰기로 확장 시 형식 보증을 제공하는 상위 시스템 계층.
