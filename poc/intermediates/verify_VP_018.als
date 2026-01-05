module VerifyLDSGuard

open util/ordering[Step] as ord
open util/integer

// ---------- States ----------
abstract sig State {}
one sig Moving, Paused extends State {}
// (other states omitted as they are irrelevant for this property)

// ---------- Steps (trace) ----------
sig Step {
    state    : one State,
    distance : one Int   // scaled: 1.0 m = 10, 1.2 m = 12
}

// ---------- Initial condition ----------
fact Init {
    ord/first.state    = Moving
    ord/first.distance = 20   // > 1.2 m, arbitrary start
}

// ---------- Helper predicates ----------
pred lowCond[s: Step]  { s.distance < 10 }   // < 1.0 m
pred highCond[s: Step] { s.distance > 12 }   // > 1.2 m

// steps between s0 and s1 (inclusive)
fun between[s0, s1: Step]: set Step {
    s0.*ord/next & (ord/nexts[s0] + s1)
}

// ---------- Guard duration checks ----------
pred lowFor[s: Step] {
    some s0: Step |
        s0 in s.^ord/prev and               // s0 is an ancestor of s
        # (between[s0, s]) >= 3 and          // at least 3 consecutive steps (≈300 ms)
        all t: Step | t in between[s0, s] implies lowCond[t]
}

pred highFor[s: Step] {
    some s0: Step |
        s0 in s.^ord/prev and
        # (between[s0, s]) >= 20 and         // at least 20 consecutive steps (≈2000 ms)
        all t: Step | t in between[s0, s] implies highCond[t]
}

// ---------- Property to verify ----------
assert LDS_Guard {
    all s: Step |
        let n = ord/next[s] | some n implies (
            (s.state = Moving and n.state = Paused)  implies (lowCond[s] and lowFor[s])
            and
            (s.state = Paused and n.state = Moving) implies (highCond[s] and highFor[s])
        )
}

// ---------- Check command ----------
check LDS_Guard for 30 Step, 5 Int