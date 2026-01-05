module VerifyPausedToMoving

open util/ordering[Step] as ord
open util/integer

abstract sig State {}
one sig Paused, Moving extends State {}

sig Step {
    state: one State,
    ldsDist: one Int,
    timer: one Int
}

// 初期状態
fact Init {
    ord/first.state = Paused
    ord/first.ldsDist = 0
    ord/first.timer = 0
}

// タイマー更新（距離が閾値以上なら加算、そうでなければリセット）
fact TimerUpdate {
    all s: Step | let n = ord/next[s] | some n implies {
        (s.ldsDist > 120) implies n.timer = s.timer.plus[100]
        (not (s.ldsDist > 120)) implies n.timer = 0
        n.ldsDist = s.ldsDist
    }
}

// 状態遷移規則
fact Transition {
    all s: Step | let n = ord/next[s] | some n implies {
        (s.state != Paused) implies n.state = s.state
        (s.state = Paused) implies {
            (s.ldsDist > 120 and s.timer >= 2000) implies n.state = Moving
            (not (s.ldsDist > 120 and s.timer >= 2000)) implies n.state = Paused
        }
    }
}

// 目的：条件を満たすとき Paused → Moving が起こり得ることを示す
assert CanResumeMoving {
    some s: Step |
        let n = ord/next[s] |
        some n and
        s.state = Paused and
        n.state = Moving and
        s.ldsDist > 120 and
        s.timer >= 2000
}

check CanResumeMoving for 5 Step, 5 Int