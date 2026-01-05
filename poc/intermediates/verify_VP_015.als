module VerifyIntersectionNode

open util/ordering[Step] as ord

sig AGV {}
one sig IntersectionNode {}

sig Step {
    holder: IntersectionNode -> lone AGV,
    request: AGV -> set IntersectionNode,
    release: AGV -> set IntersectionNode
}

/* 初期状態: 何も保持・要求・解放していない */
fact Init {
    no ord/first.holder
    no ord/first.request
    no ord/first.release
}

/* 排他制御: 各 IntersectionNode は同時に 0 または 1 AGV しか保持できない */
fact MutualExclusion {
    all s: Step, r: IntersectionNode | lone s.holder[r]
}

/* 要求があり、かつリソースが空の場合は 1 つの要求者に割り当てる */
fact Grant {
    all s: Step | let n = ord/next[s] | some n implies {
        all a: AGV, r: IntersectionNode |
            (a->r in s.request and
             no s.holder[r] and
             no b: AGV - a | b->r in s.request) implies
                n.holder[r] = a
    }
}

/* 保持者が解放要求したら次のステップでリソースは空になる */
fact Release {
    all s: Step | let n = ord/next[s] | some n implies {
        all a: AGV, r: IntersectionNode |
            (a->r in s.release) implies
                no n.holder[r]
    }
}

/* 何も要求・解放が無い場合は保持状態を維持する */
fact Hold {
    all s: Step | let n = ord/next[s] | some n implies {
        all r: IntersectionNode |
            (no a: AGV | a->r in s.request or a->r in s.release) implies
                n.holder[r] = s.holder[r]
    }
}

/* 検証: どのステップでも同一 IntersectionNode を複数の AGV が同時に保持しない */
assert ExclusiveAccess {
    all s: Step, r: IntersectionNode | lone s.holder[r]
}
check ExclusiveAccess for 5 Step, 3 AGV, 1 IntersectionNode, 5 Int