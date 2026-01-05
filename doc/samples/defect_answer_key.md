# AGVフリート管理システム - 意図的欠陥一覧 (Answer Key)

本ドキュメントは、サンプル要件定義書 (`01_agv_core_logic.md`, `02_agv_communication.md`, `03_agv_hardware_safety.md`) に意図的に埋め込まれた欠陥（ヌケ・モレ・矛盾）の正解データです。
自動検出ツールの検証や、レビュー演習の答え合わせに使用してください。

---

## 1. 01_agv_core_logic.md (コアロジック)

### Defect 1: Dead End (状態の袋小路)
- **箇所**: `4.2.14. Error -> SafeMode`
- **内容**: `SafeMode` へ遷移する条件（低電圧かつ通信切断）は定義されているが、**`SafeMode` から脱出する遷移（復帰条件）が一切定義されていない**。
- **現象**: この状態に入ると、システムはDeep Sleepし通信も途絶えるため、外部コマンドでの復帰も不可能となり、完全に動作不能（文鎮化）になる。
- **分類**: Graph (Dead End) / Priority: High

### Defect 2: Missing Else (条件網羅漏れ)
- **箇所**: `5.2. 交差点制御・分岐ロジック (Req.Nav.005)`
- **内容**: 分岐方向として `LEFT`, `RIGHT`, `STRAIGHT` の3パターンしか定義されていない。
- **現象**: 以下のケースで挙動未定（Undefined Behavior）となる。
    - 指示データが破損して `NULL` や `UNKNOWN` になった場合。
    - 運用上ありえる `STOP` や `U_TURN` コマンドが来た場合。
    - T字路で物理的に直進できないのに `STRAIGHT` が指示された場合。
- **分類**: LLM (Missing Else) / Priority: High

---

## 2. 02_agv_communication.md (通信プロトコル)

### Defect 3: Conflicting Outputs (出力競合)
- **箇所**: `2.2.5. CMD_EMERGENCY_STOP` と `2.2.4. CMD_TASK_ASSIGN`
- **内容**: 「非常停止（赤点滅）」と「タスク受注（青回転）」のLED表示優先順位が定義されていない。
- **現象**: 非常停止ボタンが押されている（あるいはコマンド受信した）状態で、サーバーから新規タスクが割り当てられると、実装によってはLEDが「青（稼働中）」に上書きされる恐れがある。周囲の安全確認を誤認させる危険な欠陥。
- **分類**: Graph/Rule (Conflicting Outputs) / Priority: High

### Defect 4: Unstated Side Effects (副作用の未定義)
- **箇所**: `3.2. 交差点・排他制御フロー`
- **内容**: 交差点リソースの取得(`REQ_ACQUIRE`)と解放(`REQ_RELEASE`)の対において、**「交差点内でAGVが故障停止した場合」の解放ルール**が記述されていない。
- **現象**: 故障車がリソースを握ったままになるため、他の全AGVが交差点に進入できず、システム全体がデッドロックする。
- **分類**: Graph (Resource Leak / Side Effects) / Priority: High

---

## 3. 03_agv_hardware_safety.md (ハードウェア・安全)

### Defect 5: Orphan States (孤立機能)
- **箇所**: `5.1. 診断モード (Req.Maint.001)` と `Part 1: 4.2.1. Booting -> Idle`
- **内容**: Part 3では「起動時に特定操作で診断モードへ」とあるが、Part 1のメインステートマシン (`Booting`) では「自己診断Passなら無条件で `Idle` へ」と書かれており、診断モードへの分岐パスが存在しない。
- **現象**: 実装者がPart 1の図だけを見て実装すると、診断モードに入るコードが到達不能（Dead Code）になる。あるいはPart 3を見て実装するとPart 1の仕様と矛盾が発生する。
- **分類**: Graph (Orphan Node / Reachability) / Priority: High

### Defect 6: Timing Violation (タイミング制約違反)
- **箇所**: `2.3. 速度監視ロジック (Req.Safe.005)`
- **内容**: 「100ms以内に停止」という要求に対し、構成要素の遅延合計（エンコーダ平均化+リレー動作など）を見積もると明らかに270ms以上かかる。
- **現象**: 物理的に実現不可能な要求仕様となっている。設計段階での計算ミス。
- **分類**: Graph/Math (Timing Violation) / Priority: Medium

---
