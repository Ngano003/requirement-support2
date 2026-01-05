module VerifyChargingStation

open util/ordering[Step] as ord

// ---------- Signatures ----------
sig AGV {}

one sig ChargingStation {}

abstract sig State {}
one sig Idle, Charging extends State {}

sig Step {
    agvState: AGV -> one State,
    holder: lone AGV          // AGV that currently occupies the charging station
}

// ---------- Facts ----------
fact Init {
    // initial step: all AGVs idle, station free
    all a: AGV | ord/first.agvState[a] = Idle
    no ord/first.holder
}

// Mutual exclusion: at most one AGV holds the station
fact MutualExclusion {
    all s: Step | lone s.holder
}

// Consistency between holder and AGV state
fact HolderStateConsistency {
    all s: Step | 
        (some s.holder => (let a = s.holder | s.agvState[a] = Charging)) and
        (all a: AGV | s.agvState[a] = Charging => s.holder = a)
}

// Transition rules
fact Transitions {
    all s: Step | let n = ord/next[s] | some n implies {
        // If station was free, an AGV may start charging
        (no s.holder) implies {
            // either stay unchanged
            (all a: AGV | n.agvState[a] = s.agvState[a]) and no n.holder
            // or one AGV moves to Charging and becomes holder
            or
            (some a: AGV |
                n.agvState[a] = Charging and
                n.holder = a and
                s.agvState[a] = Idle
            )
        }
        // If station was occupied, holder must stay holder and remain Charging
        (some s.holder) implies {
            let a = s.holder |
                n.holder = a and
                n.agvState[a] = Charging and
                (all b: AGV - a | n.agvState[b] = s.agvState[b])
        }
    }
}

// ---------- Assertions ----------
assert ExclusiveCharging {
    all s: Step | lone a: AGV | s.agvState[a] = Charging
}

assert ChargingGrant {
    all s: Step, n: Step | n = ord/next[s] => (
        all a: AGV |
            (n.agvState[a] = Charging and s.agvState[a] = Idle) implies no s.holder
    )
}

// ---------- Checks ----------
check ExclusiveCharging for 5 Step, 3 AGV, 5 Int
check ChargingGrant for 5 Step, 3 AGV, 5 Int