入力とドラフトに基づいて、要件を明確にするための質問を生成してください。

入力:
{{input_text}}

ドラフト:
{{draft_requirements}}

ルール:
- 1つの質問につき1つの観点。
- 簡潔に。
- 以下のJSON形式で出力してください:
```json
[
  {
    "id": "q1",
    "category": "functional",
    "question": "質問文",
    "priority": "high",
    "context": "文脈"
  }
]
```
JSON配列のみを出力してください。
