module VerifyUnloading

// ---------- Signatures ----------
abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused,
        Error, Maintenance, SafeMode, L_Approach, L_Handshake,
        L_Transfer, L_Verify extends State {}

abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected,
        Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete,
        Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge,
        Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

sig Transition {
    src : one State,
    tgt : one State,
    ev  : one Event
}

// ---------- Resources ----------
abstract sig Resource {}
one sig ChargingStation extends Resource {}

// ---------- Transition Facts ----------
fact Transitions {
    // Unloading -> Idle
    some t_unload : Transition |
        t_unload.src = Unloading and
        t_unload.tgt = Idle and
        t_unload.ev  = Event_Unload_Complete
    // (Other transitions omitted for brevity)
}

// ---------- Assertion ----------
assert UnloadingHasSuccessor {
    all s: State | s = Unloading implies
        some tr: Transition | tr.src = s
}

check UnloadingHasSuccessor for 5 State, 5 Event, 5 Transition, 2 Resource, 5 Int