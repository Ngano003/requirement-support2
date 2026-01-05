module VerifyLHandshake

abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused,
        Error, Maintenance, SafeMode, L_Approach, L_Handshake,
        L_Transfer, L_Verify extends State {}

fun trans: State -> set State {
    Booting->Idle +
    Idle->Moving +
    Moving->Paused +
    Paused->Moving +
    Moving->Loading +
    Loading->Moving +
    Moving->Unloading +
    Unloading->Idle +
    Idle->Charging +               // Event_Go_Charge / Event_Low_Battery
    Charging->Idle +
    Error->Maintenance +
    Maintenance->Idle +
    Error->SafeMode +
    (State - Error) -> Error       // wildcard src to Error for critical error
}

assert L_HandshakeHasSuccessor {
    some t: State | t in trans[L_Handshake]
}

check L_HandshakeHasSuccessor for 14 State