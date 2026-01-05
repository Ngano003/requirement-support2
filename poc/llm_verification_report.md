# LLM要件検証レポート

**実行日時**: 2026-01-05 22:48:09
**対象ファイル**: 01_agv_core_logic.md, 02_agv_communication.md, 03_agv_hardware_safety.md

## エグゼクティブサマリー
要件定義書に対し、状態の脱出欠如や条件未網羅、リソース解放漏れ、タイミング不整合など複数の欠陥を特定。特に SafeMode の出口未定義や速度監視のタイムライン違反は致命的で、修正が必須。

| Critical | Major | Minor | Total |
| :---: | :---: | :---: | :---: |
| 4 | 4 | 3 | 11 |

## 検出された欠陥一覧

### 🔴 [DEF-001] Dead Ends

**Severity**: Critical
**Location**: 4.2.14 SafeMode entry (State SafeMode) – No outgoing transition defined

**Description**:
SafeMode 状態への遷移は定義されているが、SafeMode から他の状態へ戻る遷移が全く記載されていない。バッテリが回復しても復帰できず、システムが永久停止する可能性がある。

**Recommendation**:
SafeMode から Idle へ復帰する条件と遷移（例: バッテリ > 20% かつ通信復帰）を明示し、復帰手順を実装する。

---

### 🔴 [DEF-002] Dead Ends

**Severity**: Critical
**Location**: 4.2.11 Global -> Error (State Error) – No generic recovery path

**Description**:
Error 状態はどの状態からでも遷移可能だが、Error から通常運転へ戻る一般的な遷移が記載されていない。手動スイッチで Maintenance に遷移するケースしかなく、ソフトウェアだけで復旧できない。

**Recommendation**:
Error から Idle へ復帰するフロー（例: エラーフラグクリア後の自動遷移）を追加し、手動介入不要のリカバリを提供する。

---

### 🟠 [DEF-003] Missing Else

**Severity**: Major
**Location**: 4.2.2 Idle -> Moving (Battery > 20% 条件)

**Description**:
Idle から Moving への遷移はバッテリ残量 >20% が必要とされているが、20% 以下の場合の動作が未定義。低バッテリ時にタスクが割り当てられた場合の挙動が不明。

**Recommendation**:
バッテリ ≤20% の場合は自動的に Charging へ遷移、またはタスク受入れを拒否するロジックを明記する。

---

### 🟠 [DEF-004] Missing Else

**Severity**: Major
**Location**: 4.2.6 Loading -> Moving (荷物センサー ON 条件)

**Description**:
荷物センサーが OFF のまま Loading から Moving へ遷移するケースが未定義。荷積み失敗時にシステムが無限に Loading に留まる恐れがある。

**Recommendation**:
荷物センサーが OFF の場合は Error (E_102) へ遷移し、リトライまたは手動介入フローを追加する。

---

### 🟠 [DEF-005] Missing Else

**Severity**: Major
**Location**: 4.2.10 Charging -> Idle (SOC > 95% 条件)

**Description**:
充電完了条件が SOC > 95% のみで、95% 以下での遷移が未定義。充電が途中で停止した場合に状態が停滞する可能性がある。

**Recommendation**:
SOC が 95% 未満の場合は Charging 状態に留まること、もしくはタイムアウトで Error へ遷移する旨を明記する。

---

### 🔵 [DEF-006] Orphan States

**Severity**: Minor
**Location**: 5.5 診断モード (Diagnostic Mode) – 5.1.5

**Description**:
診断モードへの遷移手順はハードウェアレベルで記載されているが、メインステートマシンからこのモードへ遷移するトリガーが存在しない。通常運転中に診断モードへ入れない。

**Recommendation**:
メインステートマシンに「Diagnostic」状態を追加し、Maintenance からの遷移や手動スイッチでの遷移を定義する。

---

### 🔵 [DEF-007] Conflicting Outputs

**Severity**: Minor
**Location**: 2.2.5 CMD_EMERGENCY_STOP と 4.2.2/4.2.5 の LED 制御

**Description**:
緊急停止コマンドは LED を RED_BLINK に設定するが、タスク実行中は LED が BLUE_ROTATE になる旨が規定されている。両方が同時に有効になると表示が競合し、オペレーターが状態を判断できない。

**Recommendation**:
LED 表示の優先順位を明示し、緊急停止時は全ての他の LED パターンを上書きすることを規定する。

---

### 🟠 [DEF-008] Unstated Side Effects

**Severity**: Major
**Location**: 3.1 交差点・排他制御フロー – REQ_ACQUIRE_RESOURCE / REQ_RELEASE_RESOURCE

**Description**:
リソース取得後にエラーやキャンセルが発生した場合、リソース解放 (REQ_RELEASE_RESOURCE) が必ず実行される保証が記載されていない。リソースがロックされたまま残り、他 AGV が交差点に進入できなくなるデッドロックのリスクがある。

**Recommendation**:
エラー発生時やタスク中止時に自動的に REQ_RELEASE_RESOURCE を送信するフローを追加し、FMS 側でもタイムアウト解放機構を実装する。

---

### 🔴 [DEF-009] Timing Violation

**Severity**: Critical
**Location**: 2.3 速度監視ロジック – Req.Safe.005

**Description**:
速度超過検知は 100 ms 以内に非常停止を作動させると規定されているが、センサ周期 50 ms、4サンプル移動平均で 200 ms の遅延、さらにリレー遮断遅延 20 ms が加わり、合計で 270 ms となり要件を満たさない。

**Recommendation**:
フィルタ遅延を削減する（例: 2サンプル平均）か、要求時間を 300 ms 以上に緩和し、ハードウェア側の遮断遅延を 20 ms 未満に改善する。

---

### 🔵 [DEF-010] Ambiguous Terms

**Severity**: Minor
**Location**: 3.1 用語定義 と 2.3 通信プロトコル – Task / Transport Order

**Description**:
「搬送指示」は Event_Transport_Order と CMD_TASK_ASSIGN の二つで表現されており、同一概念なのか別物なのかが不明瞭。ドキュメント全体で用語が統一されていない。

**Recommendation**:
「Task」または「Transport Order」のいずれかに統一し、用語集に明確な定義を追加する。

---

### 🔴 [DEF-011] Cycles

**Severity**: Critical
**Location**: 3.1 交差点・排他制御フロー – REQ_ACQUIRE_RESOURCE と 4.2.11 Global -> Error

**Description**:
AGV がリソース取得中に Critical Error が発生すると Error 状態へ遷移し、リソース解放が未定義になる。その結果、FMS がリソースを解放できず、他 AGV が待ち続けてデッドロックになる可能性がある。

**Recommendation**:
Error 状態遷移時に自動的に REQ_RELEASE_RESOURCE を送信するか、FMS が一定時間経過後にリソースを強制解放するロジックを追加する。

---

