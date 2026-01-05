module VerifyChargingTransition

open util/ordering[Step] as ord
open util/integer

// ---------- States ----------
abstract sig State {}
one sig Idle, Charging extends State {}

// ---------- Events ----------
abstract sig Event {}
one sig Event_Charge_Complete extends Event {}

// ---------- Resources ----------
one sig ChargingStation {}

// ---------- AGV ----------
sig AGV {
    soc: one Int   // 0 .. 100 (scaled)
}

// ---------- Steps (trace) ----------
sig Step {
    agv: one AGV,
    st : one State,
    holder: lone ChargingStation
}

// ---------- Initial condition ----------
fact Init {
    ord/first.st = Idle
    no ord/first.holder
}

// ---------- Resource exclusivity ----------
fact ExclusiveChargingStation {
    all s: Step | lone s.holder
    all s: Step | s.st = Charging implies some s.holder
}

// ---------- Transition rule ----------
pred canLeaveCharging[s, n: Step] {
    s.st = Charging and
    n.st = Idle and
    s.agv.soc > 95 and
    n.holder = none
}

// Allow staying in the same state when no transition occurs
fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies {
        (canLeaveCharging[s, n]) or (n.st = s.st and n.holder = s.holder)
    }
}

// ---------- Assertion: Charging has at least one outgoing transition ----------
assert ChargingHasTransition {
    all s: Step | s.st = Charging implies
        (some n: Step | n = ord/next[s] and canLeaveCharging[s, n])
}

check ChargingHasTransition for 5 Step, 2 AGV, 1 ChargingStation, 7 Int