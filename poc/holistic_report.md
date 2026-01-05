# Alloy全体検証レポート

**実行日時**: 2026-01-05 22:15:00

**モデル**: `poc/intermediates/holistic_system.als`

## ⚠️ Output Conflict (Defect 3)

**判定**: VIOLATION_FOUND

**検出された問題**: Consistency Verification Failed.
Run command `ConsistencyViolation` found an instance where conflicting outputs occur.

### 詳細解説

## 1. 検出された不具合 (Defect Description)
- **現象**：`Error` 状態において、システムが**2つの異なる出力**を同時に要求しました。
    - **ルール1**: `Rule_Emergency` -> `LED_RED_BLINK` (赤点滅)
    - **ルール2**: `Rule_TaskAssign` -> `LED_BLUE_ROTATE` (青回転)
- **シナリオ**:
    - Step 5: システムは `Error` 状態。
    - Event: `CMD_TASK_ASSIGN` が受信された。
    - 結果: `Rule_Emergency`（状態がErrorなら適用）と `Rule_TaskAssign`（CMD受信なら適用）の両方の条件が満たされ、LED出力が競合した。

## 2. 要件定義書の課題 (Issues in Requirements)
- **ルールの排他制御不足**: 個別の出力要件は記述されているが、「ある優先順位（例：Error時は緊急停止信号を優先）」などの調停ルールが存在しない。
- **適用条件の重複**: `Rule_TaskAssign` が「状態を問わずコマンド受信で適用」と解釈できる記述になっており、`Error` 状態での禁止事項が含まれていない。

## 3. 修正提案 (Proposed Fixes)
- **優先順位の定義**: `Error` 状態は最高優先度とし、他の操作コマンド（移動指示など）による出力を無効化する。
- **ガード条件の追加**: `Rule_TaskAssign` の適用条件に `State != Error` を追加する。

---

## ⚠️ DeadlockFree

**判定**: VIOLATION_FOUND

**検出された問題**: Counterexample found. The model has a flaw.

### 詳細解説

## 1. 検出された不具合 (Defect Description)  
- **現象**：ステップ 0〜9 がすべて **Diagnostic** 状態のまま変化せず、イベントも出力も発生しません。  
- **結果**：`Diagnostic` は **EndStates（Idle・SafeMode・Maintenance）** に含まれないため、システムは「次の遷移が存在しない」状態に陥り、**Deadlock（停止）** が発生しています。  

## 2. 要件定義書の課題 (Issues in Requirements)  
1. **Diagnostic 状態からの復帰条件が未定義**  
   - 現行の遷移表では `Diagnostic → Idle` は *Event_Switch_Auto* が発生したときだけと記載されています。  
   - しかし、診断モードは自律的に完了することが想定される（例：診断完了タイムアウト、内部診断完了シグナル）。この条件が要件に記載されていないため、外部からのスイッチが来ない限りシステムは永久に Diagnostic に留まります。  

2. **EndState の定義が不完全**  
   - `Diagnostic` が「作業が完了したら自動的に終了すべき」状態であるにも関わらず、EndStates に含められていません。  
   - そのため、DeadlockFree の検証で「非 EndState で遷移が無い」ケースがエラーとして検出されます。  

## 3. 修正提案 (Proposed Fixes)

| 修正箇所 | 具体的な追加・修正内容 |
|----------|----------------------|
| **3.1 State Transition - Diagnostic** | <ul><li>**新規イベント** `Event_Diagnostic_Complete` を定義。</li><li>遷移条件を追加: <br>「Diagnostic 状態で `Event_Diagnostic_Complete` が観測されたら、次の状態は Idle とする」</li></ul> |
| **3.2 EndState 定義** | <ul><li>`EndStates` に `Diagnostic` を追加し、**Idle・SafeMode・Maintenance・Diagnostic** が正常終了可能な状態であることを明示。</li></ul> |
| **3.3 要件記述例** | <pre>3.1.2 Diagnostic → Idle<br>条件: システム内部で診断が正常に完了したことを示す `Event_Diagnostic_Complete` が発生したとき。<br>アクション: 状態を Idle に遷移し、LED_GREEN_ON を点灯。</pre> |
| **3.4 安全性補足** | <ul><li>診断完了イベントが発生しないまま長時間滞留した場合のフォールバックとして、**タイムアウト**（例：30 秒）で自動的に `Event_Diagnostic_Complete` を生成する旨を要件に追記。</li></ul> |
| **3.5 テストケース更新** | <ul><li>Diagnostic → Idle の遷移が正しく機能するシナリオをテストケースに追加。</li><li>DeadlockFree 検証で `Diagnostic` が EndState として扱われることを確認。</li></ul> |

### まとめ  
- **Diagnostic 状態の自動復帰条件** と **EndState の範囲** が抜けていたことが、システムが停止する根本原因です。  
- 上記の「イベント追加」「遷移条件明示」「EndState 拡張」の3点を要件定義書に反映すれば、Deadlock が解消され、システムは診断完了後に正常に Idle へ戻ります。  

---

## ⚠️ Reachable

**判定**: VIOLATION_FOUND

**検出された問題**: Counterexample found. The model has a flaw.

### 詳細解説

## 1. 検出された不具合 (Defect Description)  
- **症状**：モデル実行時に **Diagnostic** 状態が 1 つも現れませんでした（`Reachable` アサーションが失敗）。  
- **トレース**：全 10 ステップとも **L_Verify** というサブステートにとどまり、状態・イベント・出力が変化しません。  
- **結果**：要件書で「Diagnostic は手動切替で遷移できる」と記載されているものの、システムは **Diagnostic** に到達できないまま停止します。  

## 2. 要件定義書の課題 (Issues in Requirements)  
| 項目 | 問題点 | 影響 |
|------|--------|------|
| **2.1 State Transition – Loading 系列** | `L_Approach / L_Handshake / L_Transfer / L_Verify` から次の状態への遷移が要件に記載されていない。 | これらのサブステートに入ったまま止まってしまい、上位状態 **Loading** から **Moving**、ひいては **Idle** へ進めない。 |
| **2.2 Reachability – Diagnostic** | 「Idle → Diagnostic は `Event_Switch_Manual` が発生したとき」とだけ記載されているが、**Idle** に到達する経路が実質的に欠如している。 | **Diagnostic** が到達不可能になる根本原因となっている。 |
| **2.3 Event Coverage** | `Event_Load_Complete` など、Loading 系列の完了を示すイベントが **Loading → Moving** の遷移にだけ使用され、サブステートからの遷移が未定義。 | サブステートで止まったままイベントが無視され、システムが「スタック」状態になる。 |

## 3. 修正提案 (Proposed Fixes)

### 修正箇所 1 – 2.3 State Transition – Loading 系列  
**対象**：要件定義書 第 **3章 2.2.1** 「Loading 状態遷移」  
**追加・修正内容**  

| 現行記述 | 修正後記述 |
|----------|------------|
| *Loading* → *Moving* は `Event_Load_Complete` が観測されたとき | **サブステートからの遷移を明示**<br>1. `L_Approach` → `L_Handshake` : `Event_Handshake_Complete`<br>2. `L_Handshake` → `L_Transfer` : `Event_Transfer_Start`<br>3. `L_Transfer` → `L_Verify` : `Event_Transfer_Complete`<br>4. `L_Verify` → **Loading** : `Event_Verify_OK`<br>5. **Loading** → **Moving** : `Event_Load_Complete` |
| - | **例外**：`Event_Load_Failure` が発生した場合は **Error** へ遷移。 |

### 修正箇所 2 – 2.1 State Transition – Idle への到達経路  
**対象**：要件定義書 第 **2章 1.1** 「システム起動シーケンス」  
**追加・修正内容**  

- **Booting → Idle** の遷移条件に **`Event_Init_Complete` が必ず発生する** ことを明記。  
- **Loading 完了後** の遷移を **Loading → Idle**（荷物が無い場合）または **Loading → Moving**（次の搬送指示がある場合）として記述し、**Idle** が必ず取得できるようにする。  

### 修正箇所 3 – 2.2 Reachability – Diagnostic  
**対象**：要件定義書 第 **4章 3.4** 「診断モード」  
**追加・修正内容**  

- 「**Idle** 状態で `Event_Switch_Manual` が受信されたとき、**Diagnostic** に遷移する」だけでなく、**Idle** が **必ず** 到達可能であることを前提条件として明記。  
- 具体的に、**Idle** への到達経路は以下のいずれかで保証されることを追記：  
  1. `Booting → Idle`（起動完了）  
  2. `Loading → Idle`（荷物なしで作業完了）  
  3. `Moving → Idle`（搬送完了）  
  4. `Charging → Idle`（充電完了）  

### 修正箇所 4 – 2.4 Conflict の防止（補足）  
**対象**：要件定義書 第 **5章 1.2** 「出力制御」  
**追加・修正内容**  

- 出力ルールの **適用条件** が **状態** と **コマンド** の両方を組み合わせて記述するように変更し、**同一ステップで複数の条件が同時に成立しない** ことを保証する。例：  
  - `Rule_Emergency` の条件は **`Error` 状態** **かつ** `CMD_EMERGENCY_STOP` が受信されたとき、**それ以外の状態では適用しない**。  

---

### まとめ  
1. **Loading 系列のサブステートから上位状態への遷移** を明示し、ステップが L_Verify に止まらないようにする。  
2. **Idle への到達経路** を要件に明記し、起動後・作業完了後に必ず Idle に戻れることを保証する。  
3. **Diagnostic への遷移条件** を、Idle が到達可能であることを前提に記述し、Reachable 失敗を防止する。  
4. **出力ルールの競合防止** を条件の組み合わせで明確化し、将来的な出力矛盾を回避する。  

これらの修正を要件定義書に反映すれば、モデル検証で指摘された「Diagnostic が到達できない」問題は解消され、システム全体の状態遷移が期待通りに動作するようになります。

---

## ⚠️ Deterministic

**判定**: VIOLATION_FOUND

**検出された問題**: Counterexample found. The model has a flaw.

### 詳細解説

## 1. 検出された不具合 (Defect Description)  
- **現象**：`Loading` 状態で `Event_Load_Complete` と `Event_Critical_Error` が同時に発生した場合、次の遷移先が定まりません。  
- **結果**：同一の開始状態と観測されたイベント集合に対して、システムが **2 つ以上の次状態** を選択できるため、**決定性 (Deterministic) が破られています**。  

## 2. 要件定義書の課題 (Issues in Requirements)  
| 項目 | 問題点 |
|------|--------|
| **遷移条件の記述** | 「遷移条件が満たされたときは必ず遷移する」ことが明記されていない。結果として、条件が満たされても「ステップが変わらない（stutter）」が許容され、二重の選択肢が生まれる。 |
| **自己ループ（ステイ）ルールの欠如** | 「何も起こらないときは現在の状態に留まる」ことを示す自己ループ条件が定義されていないため、ツールは暗黙的に「変化しない」ケースも遷移として受け取ってしまう。 |
| **排他性の保証** | 「同一ソース状態・同一イベント集合に対して複数の遷移先が存在しない」ことが要件として記載されていない。 |

## 3. 修正提案 (Proposed Fixes)

### 修正箇所  
- **4.2 State Transition – General Rules**  
- **4.3 State Transition – Individual State Tables**  

### 追加・修正すべき内容  

1. **遷移の必須実行を明示**  
   ```
   4.2.1 すべての遷移規則は「条件が成立したら必ず遷移する」ことを前提とする。  
   条件が成立したステップにおいて、現在の状態を維持（ステイ）することは許可しない。
   ```

2. **自己ループ（ステイ）を明示的に定義**  
   ```
   4.2.2 「何も起こらない」ことを表す自己ループは、以下の形式で明示的に記述する。  
   - ソース状態 S とイベント集合が、どの遷移規則にも一致しない場合に限り、次ステップも S とする。  
   - 例:  S = Loading, events = {Event_Arrived_Pickup} のときは、Loading → Loading は許可しない（Loading → Moving が唯一の有効遷移）。
   ```

3. **排他性（唯一性）ルールの追加**  
   ```
   4.2.3 同一ソース状態と同一イベント集合に対して、複数の遷移先が定義されてはいけない。  
   - すべての遷移表は「ソース状態 × イベント集合 → 1 つのターゲット状態」の 1 対 1 マッピングであることを保証する。  
   - 例外として、自己ループは「イベント集合が空」または「全遷移条件が不成立」のみ許可する。
   ```

4. **具体的な遷移表の修正例（Loading 状態）**  
   - **現行**  
     ```
     Loading -> Moving   when Event_Load_Complete
     ```
   - **修正後**  
     ```
     Loading -> Moving   when Event_Load_Complete
     Loading -> Loading  when (no Event_Load_Complete)   // 明示的に「何も起こらない」場合のみ許可
     ```
   - これにより、`Event_Load_Complete` が無いときは自己ループが唯一の遷移となり、`Event_Load_Complete` があるときは必ず `Moving` へ遷移することが保証されます。

5. **テスト・検証指針の追記**  
   ```
   5.1 変更後の遷移表に対して、決定性（Deterministic）チェックを必ず実施し、同一開始状態・同一イベント集合から複数の次状態が導出されないことを確認する。
   ```

---

**まとめ**  
- 現行要件では「条件が満たされたときに必ず遷移する」ことが暗黙の前提となっていないため、ツールは「変化しない」ケースも許容し、決定性が失われました。  
- 上記の **「遷移必須実行」「自己ループの明示」「排他性」** を要件に明記すれば、同一条件下で複数の次状態が生じることはなくなり、決定的なシステム動作が保証されます。
