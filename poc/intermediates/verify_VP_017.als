module VerifyMotorDriverExclusion

open util/ordering[Step] as ord

sig AGV {}

sig MotorDriver {
    owner: one AGV
}

sig Step {
    holder: MotorDriver -> lone AGV
}

// 初期状態: いずれの MotorDriver も保持されていない
fact Init {
    no ord/first.holder
}

// 所有者以外が保持できないことを強制
fact OwnerExclusivity {
    all s: Step, d: MotorDriver |
        (some s.holder[d]) implies s.holder[d] = d.owner
}

// 検証: すべてのステップで MotorDriver は所有者か未保持である
assert VerificationProperty {
    all s: Step, d: MotorDriver |
        no s.holder[d] or s.holder[d] = d.owner
}

check VerificationProperty for 5 Step, 3 AGV, 3 MotorDriver, 5 Int