module VerifyPausedTransition

// ---------- States ----------
abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused,
        Error, Maintenance, SafeMode,
        L_Approach, L_Handshake, L_Transfer, L_Verify extends State {}

// ---------- Events ----------
abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected,
        Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete,
        Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge,
        Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

// ---------- Resources ----------
abstract sig Resource {}
one sig ChargingStation, IntersectionNode, RFIDNode,
        WiFiChannel, MotorDriver, EmergencyStopCircuit extends Resource {}

// ---------- Transitions ----------
sig Transition {
    src: one State,
    tgt: one State,
    ev : one Event
}

// Explicit transition definitions
fact DefineTransitions {
    some t: Transition | t.src = Booting   and t.tgt = Idle        and t.ev = Event_Init_Complete
    some t: Transition | t.src = Idle      and t.tgt = Moving      and t.ev = Event_Transport_Order
    some t: Transition | t.src = Moving    and t.tgt = Paused      and t.ev = Event_Obstacle_Detected
    some t: Transition | t.src = Paused    and t.tgt = Moving      and t.ev = Event_Obstacle_Cleared
    some t: Transition | t.src = Moving    and t.tgt = Loading     and t.ev = Event_Arrived_Pickup
    some t: Transition | t.src = Loading   and t.tgt = Moving      and t.ev = Event_Load_Complete
    some t: Transition | t.src = Moving    and t.tgt = Unloading   and t.ev = Event_Arrived_Dropoff
    some t: Transition | t.src = Unloading and t.tgt = Idle        and t.ev = Event_Unload_Complete
    some t: Transition | t.src = Idle      and t.tgt = Charging    and t.ev = Event_Go_Charge
    some t: Transition | t.src = Idle      and t.tgt = Charging    and t.ev = Event_Low_Battery
    some t: Transition | t.src = Charging  and t.tgt = Idle        and t.ev = Event_Charge_Complete
    some t: Transition | t.src = Error     and t.tgt = Maintenance and t.ev = Event_Switch_Manual
    some t: Transition | t.src = Maintenance and t.tgt = Idle     and t.ev = Event_Switch_Auto
    some t: Transition | t.src = Error     and t.tgt = SafeMode   and t.ev = Event_NetLoss_LowBat
    // Wild‑card transition: any state can go to Error via Critical_Error
    all s: State | some t: Transition | t.src = s and t.tgt = Error and t.ev = Event_Critical_Error
}

// ---------- Property ----------
assert PausedHasOutgoing {
    some t: Transition | t.src = Paused
}

check PausedHasOutgoing for 14 State, 15 Event, 30 Transition, 6 Resource