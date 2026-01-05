module VerifyPausedTransition

open util/ordering[Step] as ord
open util/integer

abstract sig State {}
one sig Moving, Paused extends State {}

abstract sig Event {}
one sig Event_Obstacle_Detected extends Event {}

sig Step {
    state: one State,
    event: lone Event,
    ldsDist: one Int,   // scaled: 0.1 m units (1.0 m = 10)
    ldsTimer: one Int   // ms
}

/* 初期条件: 任意のステップが条件を満たすことがある */
fact ConditionExists {
    some s: Step |
        s.state = Moving and
        s.event = Event_Obstacle_Detected and
        s.ldsDist <= 9 and          // < 1.0 m
        s.ldsTimer >= 300
}

/* 遷移規則 */
fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies {
        (s.state = Moving and
         s.event = Event_Obstacle_Detected and
         s.ldsDist <= 9 and
         s.ldsTimer >= 300) implies
            n.state = Paused
        else
            n.state = s.state
    }
}

/* 検証: 条件を満たす Moving 状態から必ず Paused へ遷移できること */
assert VerificationProperty {
    all s: Step |
        (s.state = Moving and
         s.event = Event_Obstacle_Detected and
         s.ldsDist <= 9 and
         s.ldsTimer >= 300) implies
            (let n = ord/next[s] | some n and n.state = Paused)
}

check VerificationProperty for 5 Step, 5 Int