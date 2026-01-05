module VerifyChargingIdle

open util/ordering[Step] as ord
open util/integer

abstract sig State {}
one sig Idle, Charging extends State {}

sig AGV {
  soc: one Int
}

sig ChargingStation {}

sig Step {
  state: one State,
  soc: one Int,
  holder: lone AGV
}

// 初期条件（テスト用に SOC > 95 の Charging 状態から開始）
fact Init {
  ord/first.state = Charging
  ord/first.soc > 95
  no ord/first.holder
}

// 充電ステーションは同時に 1 AGV しか保持できない
fact MutualExclusion {
  all s: Step | lone s.holder
}

// 遷移規則：Charging かつ SOC > 95 のとき Idle へ遷移し、リソース解放
fact Transitions {
  all s: Step | let n = ord/next[s] | some n implies {
    (s.state = Charging and s.soc > 95) implies {
      n.state = Idle
      n.holder = none
    }
    (s.state != Charging or s.soc <= 95) implies {
      n.state = s.state
      n.soc = s.soc
      n.holder = s.holder
    }
  }
}

// 充電完了後は必ず Idle に遷移できることを検証
assert ChargingToIdleWhenSOCHigh {
  all s: Step | (s.state = Charging and s.soc > 95) implies
    some n: Step | n = ord/next[s] and n.state = Idle
}

check ChargingToIdleWhenSOCHigh for 5 Step, 2 AGV, 5 Int