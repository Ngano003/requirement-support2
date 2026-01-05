module VerifyBooting

open util/ordering[Step] as ord

abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused,
        Error, Maintenance, SafeMode, L_Approach, L_Handshake,
        L_Transfer, L_Verify extends State {}

abstract sig Resource {}
one sig ChargingStation extends Resource {}

sig Step {
    state: one State
}

/* 初期状態は Booting */
fact Init {
    ord/first.state = Booting
}

/* 遷移規則（必要最小限） */
pred transitionRule[s, n: Step] {
    (s.state = Booting   and n.state = Idle)          or
    (s.state = Idle      and n.state = Moving)        or
    (s.state = Moving    and n.state = Paused)        or
    (s.state = Paused    and n.state = Moving)        or
    (s.state = Moving    and n.state = Loading)       or
    (s.state = Loading   and n.state = Moving)        or
    (s.state = Moving    and n.state = Unloading)     or
    (s.state = Unloading and n.state = Idle)          or
    (s.state = Idle      and n.state = Charging)      or
    (s.state = Charging  and n.state = Idle)          or
    (s.state = Error     and n.state = Maintenance)  or
    (s.state = Maintenance and n.state = Idle)       or
    (s.state = Error     and n.state = SafeMode)     or
    /* 任意状態から Error への遷移（ワイルドカード） */
    (n.state = Error)
}

/* 各ステップの次ステップが存在すれば遷移規則を満たす */
fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies transitionRule[s, n]
}

/* 検証: Booting から少なくとも 1 つの遷移先が存在すること */
assert BootingHasSuccessor {
    all s: Step | s.state = Booting implies
        (some n: Step | n in s.*ord/next and n.state != Booting)
}

check BootingHasSuccessor for 5 Step, exactly 14 State, exactly 1 Resource, 5 Int