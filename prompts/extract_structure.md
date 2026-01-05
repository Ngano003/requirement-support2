あなたはソフトウェア要件の分析エキスパートです。
提供された要件定義書（Markdownテキスト）を読み、形式検証（Formal Verification）に使用するための「構造化データ」を抽出してください。

## タスク
要件定義書の記述を以下の4つの次元（Category）に分類し、JSONフォーマットで出力してください。

### 1. state_transition (動的次元)
- システムが持つ「状態 (State)」と、状態間の「遷移 (Transition)」を網羅的にリストアップしてください。
- 遷移のトリガーとなる「イベント (Event)」と、遷移に必要な「条件 (Guard)」を明記してください。

### 2. resource_concurrency (リソース次元)
- 複数の主体（AGV、ユーザーなど）が共有・競合する「リソース (Resource)」を特定してください。
- リソースの使用ルール（排他制御、優先順位、定員など）を記述してください。

### 3. logic_guard (論理次元)
- 状態遷移やリソースアクセスの条件となっている「数値的な閾値」や「複合条件」を抽出してください。
- 例: "Battery < 20%", "Timer > 60s"

### 4. data_relation (データ次元)
- システムが管理する主要なデータエンティティと、その関係性（親子関係、必須制約など）を記述してください。

### 5. system_action (出力・動作次元)
- システムが外部に対して行う「出力 (Output)」や「アクション (Action)」を抽出してください。
- 例: "LED: Red Blink", "Sound: Warning Beep", "Motor: Stop"
- そのアクションがトリガーされる「条件 (Condition)」や「イベント (Event)」を明記してください。これはDefect 3 (Conflicting Outputs) の検出に必須です。

## 出力フォーマット (JSON)
必ず以下のJSONスキーマに従って出力を行ってください。Markdownコードブロックは含めず、純粋なJSONのみを出力してください。

```json
{
  "state_transition": {
    "states": ["StateA", "StateB", ...],
    "events": ["Event1", "Event2", ...],
    "transitions": [
      {
        "src": "StateA",
        "tgt": "StateB",
        "event": "Event1",
        "condition": "Condition description"
      }
    ]
  },
  "resource_concurrency": {
    "resources": [
      {
        "name": "ResourceName",
        "description": "Description",
        "access_rules": ["Rule 1", "Rule 2"]
      }
    ]
  },
  "logic_guard": [
    {
      "category": "Battery",
      "condition": "SOC < 20%",
      "implication": "Must go to charge"
    }
  ],
  "data_relation": [
    {
      "entity": "EntityName",
      "constraints": ["Constraint 1"]
    }
  ],
  "system_action": [
    {
      "action": "LED_Red_Blink",
      "trigger": "Event_Critical_Error",
      "condition": "Error == Critical",
      "description": "Indicate critical error"
    }
  ]
}
```

## 入力要件書
{{requirement_text}}
