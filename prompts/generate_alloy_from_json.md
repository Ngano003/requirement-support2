あなたは形式手法Alloyのエキスパートです。
提供された「要件の構造化データ（JSON）」と「検証観点（JSON）」を元に、検証可能なAlloy 6のモデルコードを生成してください。

## 目標
検証観点: **{{viewpoint_name}}**
説明: {{viewpoint_description}}

この観点を検証するために必要最小限のモデル（State, Resource, Logic）のみ定義し、検証時間を短縮してください。無関係な要素は定義しないでください。

## タスク
1. **必要な要素の定義**:
   - `state_transition` から、この観点に関連する State, Event, Transition を定義。
   - `resource_concurrency` から、この観点に関連する Resource を定義。
   - `logic_guard` から、条件ロジックを定義。

2. **検証式の作成**:
   - 指定された観点に対応する `assert` 文を作成してください。
   - コマンド名は `check VerificationProperty` としてください。

## 出力形式（厳守）
**重要**: 以下のルールを厳守してください:
1. 出力はMarkdownのコードブロック（```alloy ... ```）で囲む
2. **説明文は一切含めない**（コードブロックの外に説明を書かないこと）
3. コードブロックの中身は**純粋なAlloyコードのみ**
4. 出力例:
```alloy
module VerifyDeadEnd

open util/ordering[Step] as ord

sig State {}
// ... 純粋なAlloyコードのみ
check VerificationProperty
```


---

# Alloy 6 言語リファレンス (包括的ガイド)

以下はAlloy 6の完全な構文リファレンスです。コード生成時は必ずこのリファレンスに従ってください。

## 第1章: 基本構造

### 1.1 モジュール宣言
```alloy
module myModel           // オプション: ファイル先頭でモジュール名を宣言
```

### 1.2 コメント
```alloy
// 単一行コメント
-- 単一行コメント (代替構文)
/* 複数行
   コメント */
```

### 1.3 インポート
```alloy
open util/ordering[State]          // Stateに対する全順序を導入
open util/ordering[Time] as ord    // エイリアス付きでインポート
open util/integer                  // 整数演算を有効化
open util/boolean                  // ブール演算を有効化
open util/relation                 // リレーション操作ユーティリティ
```

---

## 第2章: シグネチャ (Signature)

### 2.1 基本シグネチャ
```alloy
sig Person {}                      // 空のシグネチャ
sig Student {}                     // 別の独立したシグネチャ
```

### 2.2 フィールド付きシグネチャ
```alloy
sig Person {
    name: one String,              // 必須フィールド (ちょうど1つ)
    age: one Int,                  // 整数フィールド
    friends: set Person,           // 0個以上のPersonの集合
    spouse: lone Person,           // 0または1つ
    children: some Person          // 1つ以上
}
```

### 2.3 多重度キーワード
| キーワード | 意味 | 例 |
|-----------|------|-----|
| `one`     | ちょうど1つ | `owner: one Person` |
| `lone`    | 0または1つ | `spouse: lone Person` |
| `some`    | 1つ以上 | `wheels: some Wheel` |
| `set`     | 0個以上 | `friends: set Person` |

### 2.4 継承とサブタイプ
```alloy
abstract sig Vehicle {}            // 抽象シグネチャ (直接インスタンス化不可)
sig Car extends Vehicle {}         // Vehicleを継承
sig Truck extends Vehicle {}       // Vehicleを継承
sig Motorcycle extends Vehicle {}  // Vehicleを継承

// one sig: シングルトン (ただ1つのアトムが存在)
one sig CEO extends Person {}      // CEOは常にちょうど1人

// 複数のシングルトンを一度に宣言
abstract sig Color {}
one sig Red, Green, Blue extends Color {}
```

### 2.5 シグネチャファクト (Signature Fact)
```alloy
sig Person {
    age: one Int
} {
    // このブロック内の制約は全Personインスタンスに適用される
    age >= 0
    age <= 150
}
```

---

## 第3章: リレーション (Relation)

### 3.1 リレーションの基本
```alloy
// フィールドは暗黙的にリレーションとなる
sig Person {
    father: lone Person,           // Person -> Person のバイナリリレーション
    children: set Person           // Person -> Person のバイナリリレーション
}
```

### 3.2 リレーションの参照
```alloy
// p が Person のインスタンスのとき
p.father                           // pの父 (Personまたはnone)
p.children                         // pの子供たち (Personの集合)

// 逆方向の参照
father.p                           // pを父とするPersonの集合
children.p                         // pを子とするPersonの集合

// 逆リレーション演算子 (~)
~father                            // father の逆リレーション (子 -> 親)
p.~father                          // pを父とするPersonの集合 (= father.p と同じ結果)
```

### 3.3 リレーション演算子
```alloy
// 結合 (Join) - ドット演算子
a.r                                // aからリレーションrを辿る
r.b                                // bに到達するリレーションrの始点集合

// 制限 (Restriction)
s <: r                             // ドメイン制限: sに含まれる要素から始まるrのみ
r :> s                             // レンジ制限: sに含まれる要素で終わるrのみ

// 上書き (Override)
r ++ s                             // rをsで上書き (sのドメインの要素はsの値を使う)

// 直積 (Cartesian Product)
A -> B                             // AとBの直積リレーション

// 合成 (Composition) 
// ドット演算子と異なり、中間の繋がりを保持
r . s                              // rとsの合成 (rの終点とsの始点が一致する組み合わせ)
```

### 3.4 閉包演算子
```alloy
^r                                 // 推移閉包 (1回以上rを辿る)
*r                                 // 反射推移閉包 (0回以上rを辿る)
```

例:
```alloy
sig Person {
    parent: set Person
}

// 先祖を表現
fun ancestors[p: Person]: set Person {
    p.^parent                      // parentを1回以上辿って到達できるPerson
}

// 自分自身を含む先祖
fun ancestorsOrSelf[p: Person]: set Person {
    p.*parent                      // parentを0回以上辿って到達できるPerson (自分自身を含む)
}
```

---

## 第4章: 論理式と述語

### 4.1 論理演算子
```alloy
not A                              // 否定
A and B                            // 論理積
A or B                             // 論理和
A implies B                        // 含意 (A => B と同じ)
A iff B                            // 同値 (A <=> B と同じ)
A => B                             // 含意 (代替構文)
A <=> B                            // 同値 (代替構文)
```

### 4.2 量化子 (Quantifiers)
```alloy
all x: Set | formula              // すべてのxについてformula が成り立つ
some x: Set | formula             // あるxについてformula が成り立つ
no x: Set | formula               // どのxについてもformula が成り立たない
lone x: Set | formula             // 高々1つのxについてformula が成り立つ
one x: Set | formula              // ちょうど1つのxについてformula が成り立つ

// 複数変数
all x: A, y: B | formula          // すべてのxとyについて
some x: A | some y: B | formula   // あるxについて、あるyについて

// 分離変数宣言
all disj x, y: Set | formula      // x != y であるすべての組み合わせについて
```

### 4.3 集合演算子
```alloy
A + B                              // 和集合 (union)
A & B                              // 積集合 (intersection)
A - B                              // 差集合 (difference)
```

### 4.4 集合比較
```alloy
A = B                              // 等しい
A != B                             // 等しくない
A in B                             // 部分集合 (AはBに含まれる)
A not in B                         // 部分集合でない

// 多重度判定
no A                               // Aは空集合
some A                             // Aは空でない
lone A                             // Aは0個または1個の要素
one A                              // Aはちょうど1個の要素
#A                                 // Aの要素数 (整数を返す)
```

### 4.5 述語 (Predicate)
```alloy
pred isAdult[p: Person] {
    p.age >= 18
}

pred married[p1, p2: Person] {
    p1.spouse = p2
    p2.spouse = p1
}

// 述語の呼び出し
isAdult[john]                      // ブラケット構文
john.isAdult                       // ドット構文 (第一引数がレシーバ)
```

### 4.6 関数 (Function)
```alloy
fun double[n: Int]: Int {
    n.plus[n]                      // または n.mul[2]
}

fun children[p: Person]: set Person {
    p.children
}

// 関数の呼び出し
double[5]                          // 結果: 10
children[john]                     // johnの子供の集合
```

---

## 第5章: ファクト (Fact)

### 5.1 基本ファクト
```alloy
fact {
    all p: Person | p not in p.^parent   // 自分自身の先祖になれない
}

fact NoSelfParent {
    no p: Person | p in p.parent         // 自分自身の親になれない
}
```

### 5.2 条件付きファクト
```alloy
fact MarriageSymmetry {
    all p1, p2: Person | p1.spouse = p2 implies p2.spouse = p1
}
```

---

## 第6章: アサーション (Assertion)

### 6.1 基本アサーション
```alloy
assert NoOrphans {
    all p: Person | some p.parent         // すべてのPersonには親がいる
}

assert AcyclicParent {
    no p: Person | p in p.^parent         // 親関係に循環がない
}
```

### 6.2 チェックコマンド
```alloy
check NoOrphans                           // デフォルトスコープでチェック
check NoOrphans for 5                     // すべてのsigを最大5個でチェック
check NoOrphans for 5 but 3 Person        // Personは最大3個
check NoOrphans for 5 but exactly 3 Person // Personはちょうど3個

// 複数のシグネチャに対するスコープ指定
check MyAssertion for 5 State, 3 AGV, 2 Resource, 5 Int
```

---

## 第7章: 整数演算 (Integer)

### 7.1 整数の基本
```alloy
// Intは組み込み型
sig Item {
    quantity: one Int
}
```

### 7.2 整数演算子
```alloy
// 比較演算子
a < b
a > b  
a <= b
a >= b
a = b
a != b

// 算術演算 (メソッド構文を使用)
a.plus[b]                          // a + b
a.minus[b]                         // a - b
a.mul[b]                           // a * b
a.div[b]                           // a / b (整数除算)
a.rem[b]                           // a % b (剰余)
a.abs                              // |a| (絶対値)
a.sign                             // 符号 (-1, 0, または 1)

// 中置演算子も使用可能
3.plus[4]                          // 7
3.minus[1]                         // 2
2.mul[3]                           // 6
```

### 7.3 整数のスコープ
```alloy
// ビット幅でスコープを指定 (値の範囲ではない！)
check MyAssertion for 5 Int        // 5ビット = -16 ～ 15 の範囲
check MyAssertion for 6 Int        // 6ビット = -32 ～ 31 の範囲
check MyAssertion for 7 Int        // 7ビット = -64 ～ 63 の範囲

// 警告: 以下は禁止
// check MyAssertion for 100 Int   // エラー! 100ビットは大きすぎる

// 推奨: 5～7ビットに収まるようモデル内の数値をスケーリングする
// 例: 100ms -> 10 tick, 1000m -> 10 unit
```

### 7.4 集合のカーディナリティ
```alloy
#Person                            // Personの要素数
#p.friends                         // pの友達の数
#(A + B)                           // AとBの和集合の要素数
```

---

## 第8章: util/ordering モジュール

### 8.1 基本的な使い方
```alloy
open util/ordering[State]          // Stateに全順序を導入

sig State {
    val: one Int
}
```

### 8.2 ordering が提供する関数と述語
```alloy
first                              // 最初の要素
last                               // 最後の要素
next[s]                            // sの次の要素 (存在しなければnone)
prev[s]                            // sの前の要素 (存在しなければnone)
nexts[s]                           // sより後のすべての要素
prevs[s]                           // sより前のすべての要素

// 使用例
first.val                          // 最初のStateのval値
s.next                             // sの次のState (存在しなければnone)
s.prev                             // sの前のState
```

### 8.3 orderingを使ったトレースモデル
```alloy
open util/ordering[Step] as ord

sig Step {
    state: one State,
    holder: lone Resource
}

// 初期条件
fact Init {
    ord/first.state = InitialState
    no ord/first.holder
}

// 遷移規則
fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies {
        // s から n への遷移条件を記述
        transitionRule[s, n]
    }
}

pred transitionRule[s, n: Step] {
    // 遷移のロジック
    n.state != s.state or n.holder != s.holder
}
```

### 8.4 エイリアス付きordering
```alloy
open util/ordering[Time] as timeOrd
open util/ordering[Event] as eventOrd

// 使い分け
timeOrd/first                      // 最初のTime
eventOrd/first                     // 最初のEvent
timeOrd/next[t]                    // tの次のTime
```

---

## 第9章: よくある間違いと修正

### 9.1 存在しないキーワード
```alloy
// ❌ 間違い: "contains" は存在しない
list contains item

// ✅ 正解: "in" を使う
item in list
```

### 9.2 範囲演算子の誤用
```alloy
// ❌ 間違い: Int に対して ".." は使えない
x in 1..5

// ✅ 正解: 比較演算子を使う
x >= 1 and x <= 5
```

### 9.3 リレーションのナビゲーション
```alloy
sig Step {
    waiting: AGV -> Intersection    // AGVがどのIntersectionを待っているか
}

// ❌ 間違い: waiting の定義と矛盾するアクセス
s.waiting[i]                       // i は Intersection だが、waiting の第一引数は AGV

// ✅ 正解: 正しい方向でアクセス
s.waiting[a]                       // a は AGV -> 対応する Intersection を取得
a.(s.waiting)                      // 同上
i.~(s.waiting)                     // i は Intersection -> 待っている AGV の集合
```

### 9.4 nextの使い方
```alloy
open util/ordering[Step] as ord

// ❌ 間違い: s.next だけでは動作しない場合がある
s.next

// ✅ 正解: ord/next[s] または s.(ord/next) を使う
ord/next[s]
let n = ord/next[s] | ...
```

### 9.5 ファクト内でのimplies
```alloy
// ❌ 間違い: implies の右辺が複数の制約を持つ時に括弧なし
all s: Step | condition implies
    constraint1
    constraint2

// ✅ 正解: 括弧で囲む
all s: Step | condition implies {
    constraint1
    constraint2
}
```

### 9.6 letの使い方
```alloy
// ✅ 正解: let を使って一時変数を定義
all s: Step | let n = ord/next[s] | some n implies {
    // n を使った制約
}
```

---

## 第10章: 完全なモデル例

### 10.1 リソース排他制御モデル
```alloy
open util/ordering[Step] as ord

sig AGV {}
sig Resource {}

sig Step {
    holder: Resource -> lone AGV,
    requester: AGV -> set Resource
}

// 初期状態: 誰もリソースを保持していない
fact Init {
    no ord/first.holder
}

// 排他制御: 各リソースは最大1つのAGVが保持
fact MutualExclusion {
    all s: Step, r: Resource | lone s.holder[r]
}

// 遷移: リソースが空なら要求者に割り当てる
fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies {
        all r: Resource, a: AGV |
            (r in a.(s.requester) and no s.holder[r]) implies n.holder[r] = a
    }
}

// 検証: デッドロックがないこと
assert NoDeadlock {
    all s: Step | some a: AGV, r: Resource |
        no s.holder[r] implies (
            some n: Step | n in s.*ord/next and some n.holder[r]
        )
}

check NoDeadlock for 5 Step, 3 AGV, 2 Resource, 5 Int
```

### 10.2 状態遷移モデル
```alloy
open util/ordering[Step] as ord

abstract sig State {}
one sig Idle, Moving, Loading, Error, SafeMode extends State {}

sig AGV {
    battery: Int
}

sig Step {
    agvState: AGV -> one State,
    agvBattery: AGV -> one Int
}

// 初期状態
fact Init {
    all a: AGV | ord/first.agvState[a] = Idle
    all a: AGV | ord/first.agvBattery[a] = 10   // スケーリングされた値
}

// バッテリー制約
fact BatteryConstraint {
    all s: Step, a: AGV | s.agvBattery[a] >= 0 and s.agvBattery[a] <= 10
}

// 遷移ルール
pred canMove[s: Step, a: AGV] {
    s.agvState[a] = Idle
    s.agvBattery[a] >= 2
}

fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies {
        all a: AGV | {
            // Idle -> Moving (バッテリー十分)
            (canMove[s, a]) implies {
                n.agvState[a] = Moving
                n.agvBattery[a] = s.agvBattery[a].minus[1]
            }
            // Low Battery -> Error
            (s.agvBattery[a] < 2 and s.agvState[a] != SafeMode) implies {
                n.agvState[a] = Error
            }
        }
    }
}

// SafeMode以外はデッドロックしない
assert NoDeadlockExceptSafeMode {
    all s: Step, a: AGV |
        s.agvState[a] != SafeMode implies (
            some n: Step | n in s.^ord/next and n.agvState[a] != s.agvState[a]
        )
}

check NoDeadlockExceptSafeMode for 6 Step, 2 AGV, 6 Int
```

---

## 入力データ: 構造化データ
{{structure_json}}
