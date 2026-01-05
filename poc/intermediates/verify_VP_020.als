module VerifyErrorToSafeMode

open util/ordering[Step] as ord
open util/integer

abstract sig State {}
one sig Error, SafeMode extends State {}

abstract sig Resource {}
one sig WiFiChannel extends Resource {}

sig Step {
    state : one State,
    rssi  : one Int,
    soc   : one Int
}

// Initial step (arbitrary)
fact Init {
    ord/first.state = Error
    ord/first.rssi  = -85
    ord/first.soc   = 10
}

// Transition rule (only the property of interest is asserted)
assert SafeModeTransition {
    all s: Step | let n = ord/next[s] | some n implies
        (s.state = Error and n.state = SafeMode) implies
            (s.rssi < -80 and s.soc < 15)
}

check SafeModeTransition for 5 Step, 5 Int, exactly 1 WiFiChannel