module VerifyErrorDeadEnd

// ---------- States ----------
abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused,
        Error, Maintenance, SafeMode, L_Approach, L_Handshake,
        L_Transfer, L_Verify extends State {}

// ---------- Events ----------
abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected,
        Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete,
        Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge,
        Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

// ---------- Transitions ----------
sig Transition {
    src: one State,
    tgt: one State,
    ev : one Event
}

// Transition instances (only a subset needed for the property)
one sig T_Booting_Idle extends Transition {} {
    src = Booting and tgt = Idle and ev = Event_Init_Complete
}
one sig T_Idle_Moving extends Transition {} {
    src = Idle and tgt = Moving and ev = Event_Transport_Order
}
one sig T_Moving_Paused extends Transition {} {
    src = Moving and tgt = Paused and ev = Event_Obstacle_Detected
}
one sig T_Paused_Moving extends Transition {} {
    src = Paused and tgt = Moving and ev = Event_Obstacle_Cleared
}
one sig T_Moving_Loading extends Transition {} {
    src = Moving and tgt = Loading and ev = Event_Arrived_Pickup
}
one sig T_Loading_Moving extends Transition {} {
    src = Loading and tgt = Moving and ev = Event_Load_Complete
}
one sig T_Moving_Unloading extends Transition {} {
    src = Moving and tgt = Unloading and ev = Event_Arrived_Dropoff
}
one sig T_Unloading_Idle extends Transition {} {
    src = Unloading and tgt = Idle and ev = Event_Unload_Complete
}
one sig T_Idle_Charging extends Transition {} {
    src = Idle and tgt = Charging and ev = Event_Go_Charge
}
one sig T_Idle_ChargingLow extends Transition {} {
    src = Idle and tgt = Charging and ev = Event_Low_Battery
}
one sig T_Charging_Idle extends Transition {} {
    src = Charging and tgt = Idle and ev = Event_Charge_Complete
}
one sig T_Idle_Error extends Transition {} {
    src = Idle and tgt = Error and ev = Event_Critical_Error
}
one sig T_Error_Maintenance extends Transition {} {
    src = Error and tgt = Maintenance and ev = Event_Switch_Manual
}
one sig T_Error_SafeMode extends Transition {} {
    src = Error and tgt = SafeMode and ev = Event_NetLoss_LowBat
}

// ---------- Resources ----------
abstract sig Resource {}
one sig ChargingStation, IntersectionNode, RFIDNode,
        WiFiChannel, MotorDriver, EmergencyStopCircuit extends Resource {}

// ---------- Assertion ----------
assert VerificationProperty {
    // There exists at least one transition whose source is Error
    some t: Transition | t.src = Error
}

check VerificationProperty for 15 State, 20 Transition, 15 Event, 6 Resource