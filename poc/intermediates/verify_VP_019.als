module VerifyErrorToMaintenance

open util/ordering[Step] as ord

-- States
abstract sig State {}
one sig Error, Maintenance extends State {}

-- Events
abstract sig Event {}
one sig Event_Switch_Manual extends Event {}

-- Step (trace element)
sig Step {
    curState: one State,
    evs: set Event
}

/* Initial step */
fact Init {
    ord/first.curState = Error
    no ord/first.evs
}

/* Transition rule: Error -> Maintenance allowed only when manual switch event occurs */
fact TransitionRule {
    all s: Step | let n = ord/next[s] | some n implies {
        (s.curState = Error and Event_Switch_Manual in s.evs) implies n.curState = Maintenance
    }
}

/* No other constraints on state changes (minimal model) */
assert VerificationProperty {
    all s: Step | let n = ord/next[s] | some n implies {
        (s.curState = Error and Event_Switch_Manual in s.evs) implies n.curState = Maintenance
    }
}
check VerificationProperty for 5 Step, exactly 1 Error, exactly 1 Maintenance, exactly 1 Event_Switch_Manual