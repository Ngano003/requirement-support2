あなたはAlloy形式手法のエキスパートです。
提供される要件定義書と構造化データに基づいて、システム全体を検証するための**単一のAlloyモデル**を生成してください。

## 入力データ
1. **要件定義書**: システムの挙動、状態遷移、リソース制約が記述されています。
2. **構造化データ (JSON)**: 抽出された状態、遷移、リソース、ガード条件のリストです。

## タスク
システム全体を網羅するAlloyモデル (`module HolisticSystem`) を作成し、以下の4つの包括的な検証を行えるようにしてください。

### 1. モデルの構造
- **Time/Step**: `util/ordering[Step]` を使用して時系列を表現してください。
- **State**: すべての状態（階層構造があれば `extends` を使用）を定義してください。
- **Resources**: `ChargingStation`, `IntersectionNode` などのリソースを定義し、StepごとにどのAGVが占有しているかを表現してください。
- **Transitions**: `pred transition[s, n: Step]` を定義し、状態遷移ルールをすべて記述してください。
    - トリガーイベントとガード条件を正確に反映してください。
    - 遷移が定義されていない場合は状態を維持する (`stuttering`) か、エラーとするか、ロジックに合わせて適切に処理してください。

### 2. 検証項目 (Assertions)
以下の4つの `assert` を必ず含めてください。

1.  **DeadlockFree**:
    -   「終了状態（IdleやSafeModeなど意図された停止状態）」以外のすべての到達可能な状態から、少なくとも1つの有効な遷移が存在すること。
    -   `all s: Step | (s.state !in EndStates) implies (some n: Step | transition[s, n] and n != s)`

2.  **Reachable**:
    -   定義されたすべての状態（Stateのサブシグネチャ）が、初期状態から一連の遷移を経て到達可能であること。
    -   `all st: State | some s: Step | s.state = st` (注: スコープ内で到達可能かチェック)

3.  **ResourceSafety**:
    -   排他制御が必要なリソース（ChargingStation, IntersectionNode, RFIDNodeなど）について、同一Stepで複数のAGV（またはプロセス）が同時に占有していないこと。
    -   `all s: Step, r: Resource | lone s.occupies.r`

4.  **Deterministic**:
    -   ある状態と入力（イベント/条件）に対して、可能な遷移先が常に一意であること。
    -   競合する遷移ルールが存在しないことを確認。

## 出力形式
Alloyコードのみを以下の形式で出力してください。解説は不要です。

```alloy
module HolisticSystem

open util/ordering[Step] as ord

// Signatures
...

// Facts
...

// Predicates
...

// Assertions
assert DeadlockFree { ... }
assert Reachable { ... }
assert ResourceSafety { ... }
assert Deterministic { ... }
assert NoConflictingOutputs { ... }

// Checks
check DeadlockFree for 10 Step, 5 Int
check Reachable for 10 Step
check ResourceSafety for 10 Step
check Deterministic for 10 Step
check NoConflictingOutputs for 10 Step
```

## 注意点
- **構文エラー回避**: シグネチャの定義漏れやスコープ設定に注意してください。
- **スコープ**: デフォルトで `10 Step` 程度を想定してください。
- **不明確な仕様**: 要件に明記がない部分は、Alloyモデル上で「任意の振る舞いを許容」するか、コメントで「仕様未定義」として明示的な制約を書かないようにしてください（過剰な制約を避ける）。

## 実装例 (Reference Implementation)
以下のパターンを **必ず** 採用してください。省略・簡略化は禁止です。

```alloy
// Output Definition
abstract sig Output {}
one sig LED_Red, LED_Blue, Motor_Stop extends Output {}

// Requirement Rules (Extracted from system_action)
sig Requirement {
    condition: set State + Event, // When this rule applies
    action: one Output            // Required output
}

// Conflict Detection Prediction
assert NoConflictingOutputs {
    all s: Step |
        all Disj r1, r2: Requirement |
            // If both rules apply in current state...
            (s.state in r1.condition and s.state in r2.condition) 
            implies 
            // ...actions must be consistent.
            r1.action = r2.action
}
```
