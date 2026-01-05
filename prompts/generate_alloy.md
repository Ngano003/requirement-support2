あなたはソフトウェア要求仕様書から形式手法Alloyのコードを生成するエキスパートです。
以下の仕様書（Markdown形式）を読み、Alloy 6の構文でモデル化してください。

## タスク
1. 仕様書に記載されている「状態（State）」と「状態遷移（Transition）」をモデリングしてください。
2. 状態遷移におけるイベント（Event）も sig として定義してください。
3. 仕様書の「意図的な欠陥」セクションは**無視**し、記載されている仕様の通りにモデリングしてください。ただし、欠陥（Dead Endなど）が検出できるように、システムが満たすべき特性（安全性、活性など）を `assert` または `check` として定義してください。
   - 特に今回のケースでは「デッドロック（Dead End）がないこと」を確認したいです。
   - これにより、`NoDeadlock` チェックで反例（Dead End）が検出されるようにしてください。
   - `Reachable` などの補助関数を定義せず、単純に `all s: State` に対して遷移が存在するか確認する assert を作成してください。
   - 変数名とフィールド名が被らないように注意してください（例: `st` フィールドがあるなら変数名は `s` や `state` にする）。

## 出力形式
Alloyのコードのみを出力してください。Markdownのコードブロック（```alloy ... ```）で囲ってください。

## ヒント
- State, Event を abstract sig として定義し、具体的な状態やイベントを extends させてください。
- 時間概念を扱うために、util/ordering モジュールを使うか、StateをTimeに関連付ける一般的なイディオム（`sig State { transition: Event -> State }` など）を使用してください。今回はシンプルに `ordering[State]` を使うか、あるいは動的な振る舞いを `pred step[s, s': State, e: Event]` のように定義する方法が推奨されます。
- ここでは、Electrum Alloy（時間拡張）ではなく、標準的なAlloy 6で動的モデルを記述するスタイル（Trace idiom）を推奨します。
  - `sig State {}`
  - `var sig Current in State {}` (Alloy 6の `var` キーワードを使う場合)
  - または、従来の `util/ordering[Time]` を使い、 `sig State { ... }` がTimeごとに変化する形。
  
  **今回はAlloy 6の `var` 機能を使わず、伝統的なTraceスタイル（`util/ordering[Time]` または ステップ関数）で記述してください。**
  **重要: Alloy 6では `'` (プライム) はLTLの演算子です。変数名に（`s'` のように）アポストロフィを使用しないでください。代わりに `next_s` や `future_s` などを使ってください。**
  **例えば `pred step[s: State, e: Event, s': State]` はNGです。 `pred step[s: State, e: Event, next_s: State]` と書いてください。**
  **重要: Alloy 6では `next` はLTLの予約語です。`util/ordering` を使う場合は必ず `as ord` で別名を付け、`ord/next` や `ord/first` のようにアクセスしてください。**
  
  例:
  ```alloy
  open util/ordering[State] as ord
  
  // ...
  fact Trace {
      all s: State - ord/last | let s' = ord/next[s] | ...
  }
  ```
  
  abstract sig Event {}
  one sig EventA, EventB extends Event {}
  
  // 状態遷移の定義
  // ...
  ```
  
  あるいは、もっと単純にグラフ構造として検証するだけでも構いません（到達不能状態の検出など）。
  しかし、仕様書は「振る舞い」なので、初期状態から遷移を繰り返して到達できるかを確認するスタイルが良いでしょう。

## 仕様書
{{requirement_text}}
