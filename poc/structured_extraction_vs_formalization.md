# 構造化抽出 (Structured Extraction) と 形式化 (Formalization) の違い

自然言語の仕様書を自動検証するプロセスにおいて、この2つは明確に異なるステップです。
一言で言えば、**「整理（構造化）」** と **「翻訳（形式化）」** の違いです。

---

## 1. 概念的な違い

| ステップ | 役割 | 出力イメージ | 主な作業 |
| :--- | :--- | :--- | :--- |
| **構造化抽出**<br>(Extraction) | 曖昧な自然言語から、**要素と関係性**を取り出して整理する。 | JSON, テーブル, リスト<br>（中間解釈） | **「読み解く」**<br>主語・述語の特定、条件の洗い出し、タグ付け。 |
| **形式化**<br>(Formalization) | 整理された情報を、**数学的な論理式やコード**に変換する。 | Alloy, TLA+, Pythonコード<br>（実行可能モデル） | **「書き下す」**<br>厳密な構文へのマッピング、論理演算子への変換。 |

---

## 2. 具体例で見るプロセス

以下の仕様記述を例にします。

> **仕様書原文**:
> 「AGVのバッテリー残量が20%を下回ったら、作業中であっても即座に充電ステーションへ向かわなければならない。ただし、緊急停止ボタンが押されている場合はその場に留まること。」

### Step 1: 構造化抽出 (Structured Extraction)
ここでやることは、文章を「データ」にすることです。LLMが得意なのはこのフェーズです。
まだAlloyの文法などは意識しません。

**出力結果 (JSONイメージ):**

```json
{
  "trigger_events": [
    {
      "name": "LowBattery",
      "condition": "Battery Level < 20%"
    },
    {
      "name": "EmergencyStop",
      "condition": "E-Stop Button == ON"
    }
  ],
  "actions": [
    {
      "name": "GoToCharging",
      "priority": "High"
    },
    {
      "name": "StayPut",
      "priority": "Critical"
    }
  ],
  "rules": [
    {
      "if": "LowBattery AND NOT EmergencyStop",
      "then": "GoToCharging"
    },
    {
      "if": "EmergencyStop",
      "then": "StayPut"
    }
  ]
}
```

**ポイント**:
- 「作業中であっても」という文言は、ルール上は「現在の状態に関わらず (Global Check)」という意味だと解釈して整理します。
- 「留まる」を行動として抽出します。

---

### Step 2: 形式化 (Formalization)
整理されたデータを、Alloyというツールの文法（シグネチャ、ファクト、述語）に変換します。
ここは厳密なルール支配の世界です。

**出力結果 (Alloyコード):**

```alloy
sig AGV {
    battery: Int,
    e_stop: Bool,
    state: State
}

// ルールの形式化
fact TransitionRules {
    all agv: AGV |
        // E-Stopが優先される論理
        (agv.e_stop = True) implies (agv.state' = agv.state) // StayPut
        else
        // バッテリー低下時の遷移
        (agv.battery < 20) implies (agv.state' = Charging)
}
```

**ポイント**:
- JSONの `"if": "LowBattery AND NOT EmergencyStop"` を `else` 構造や `implies` に変換します。
- 変数名や型（`Int`, `Bool`）を決定します。

---

## 3. なぜ分ける必要があるのか？

いきなり「原文 -> Alloy」と変換しようとすると、LLMは混乱します。

1.  **品質精度の向上**:
    - 「日本語の解釈ミス」なのか「Alloyの文法ミス」なのかを切り分けられます。
    - 構造化データ（JSON等）の段階であれば、人間がパッと見て「あ、条件が1個抜けてる」と指摘・修正するのが簡単です（Alloyコードをレビューするより遥かに楽です）。

2.  **汎用性**:
    - 一度「構造化データ」にしてしまえば、そこから出力先をAlloyに変えたり、Pythonのテストコードに変えたり、ドキュメントの表に変えたりすることが容易になります。

3.  **複雑性の分割**:
    - 構造化抽出は「読解力（文系脳）」、形式化は「論理構築力（理系脳）」を使います。LLMへのプロンプトも分けたほうが、それぞれのタスクに特化でき、精度が上がります。
