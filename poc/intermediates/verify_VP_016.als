module VerifyRFIDNode

open util/ordering[Step] as ord

sig AGV {}
sig RFIDNode {}

sig Step {
    reads: RFIDNode -> set AGV
}

fact Init {
    no ord/first.reads
}

assert ConcurrentRead {
    some s: Step | some n: RFIDNode | some disj a1, a2: AGV |
        a1 in s.reads[n] and a2 in s.reads[n]
}

check ConcurrentRead for 5 Step, 3 AGV, 2 RFIDNode, 5 Int