module VerifyLApproach

/* ---------- Signatures ---------- */
abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused,
        Error, Maintenance, SafeMode, L_Approach, L_Handshake,
        L_Transfer, L_Verify extends State {}

abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected,
        Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete,
        Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge,
        Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat
        extends Event {}

sig Transition {
    src : one State,
    tgt : one State,
    ev  : one Event,
    cond: one String
}

/* ---------- Transition Instances ---------- */
one sig T_Booting_Idle extends Transition {}
one sig T_Idle_Moving extends Transition {}
one sig T_Moving_Paused extends Transition {}
one sig T_Paused_Moving extends Transition {}
one sig T_Moving_Loading extends Transition {}
one sig T_Loading_Moving extends Transition {}
one sig T_Moving_Unloading extends Transition {}
one sig T_Unloading_Idle extends Transition {}
one sig T_Idle_Charging_Order extends Transition {}
one sig T_Idle_Charging_LowBat extends Transition {}
one sig T_Charging_Idle extends Transition {}
one sig T_Error_Maintenance extends Transition {}
one sig T_Maintenance_Idle extends Transition {}
one sig T_Error_SafeMode extends Transition {}

fact TransitionDefinitions {
    T_Booting_Idle.src = Booting and
    T_Booting_Idle.tgt = Idle and
    T_Booting_Idle.ev  = Event_Init_Complete and
    T_Booting_Idle.cond = "All POST modules PASS"

    T_Idle_Moving.src = Idle and
    T_Idle_Moving.tgt = Moving and
    T_Idle_Moving.ev  = Event_Transport_Order and
    T_Idle_Moving.cond = "SOC > 20% AND current position known"

    T_Moving_Paused.src = Moving and
    T_Moving_Paused.tgt = Paused and
    T_Moving_Paused.ev  = Event_Obstacle_Detected and
    T_Moving_Paused.cond = "LDS distance < 1.0m for >= 300ms"

    T_Paused_Moving.src = Paused and
    T_Paused_Moving.tgt = Moving and
    T_Paused_Moving.ev  = Event_Obstacle_Cleared and
    T_Paused_Moving.cond = "LDS distance > 1.2m for >= 2000ms"

    T_Moving_Loading.src = Moving and
    T_Moving_Loading.tgt = Loading and
    T_Moving_Loading.ev  = Event_Arrived_Pickup and
    T_Moving_Loading.cond = "RFID tag read AND stop position error <= ±10mm"

    T_Loading_Moving.src = Loading and
    T_Loading_Moving.tgt = Moving and
    T_Loading_Moving.ev  = Event_Load_Complete and
    T_Loading_Moving.cond = "Load sensor ON"

    T_Moving_Unloading.src = Moving and
    T_Moving_Unloading.tgt = Unloading and
    T_Moving_Unloading.ev  = Event_Arrived_Dropoff and
    T_Moving_Unloading.cond = "Stop position error <= ±10mm"

    T_Unloading_Idle.src = Unloading and
    T_Unloading_Idle.tgt = Idle and
    T_Unloading_Idle.ev  = Event_Unload_Complete and
    T_Unloading_Idle.cond = "Load sensor OFF"

    T_Idle_Charging_Order.src = Idle and
    T_Idle_Charging_Order.tgt = Charging and
    T_Idle_Charging_Order.ev  = Event_Go_Charge and
    T_Idle_Charging_Order.cond = "Charging station available (FMS confirmed)"

    T_Idle_Charging_LowBat.src = Idle and
    T_Idle_Charging_LowBat.tgt = Charging and
    T_Idle_Charging_LowBat.ev  = Event_Low_Battery and
    T_Idle_Charging_LowBat.cond = "Charging station available (FMS confirmed)"

    T_Charging_Idle.src = Charging and
    T_Charging_Idle.tgt = Idle and
    T_Charging_Idle.ev  = Event_Charge_Complete and
    T_Charging_Idle.cond = "SOC > 95%"

    T_Error_Maintenance.src = Error and
    T_Error_Maintenance.tgt = Maintenance and
    T_Error_Maintenance.ev  = Event_Switch_Manual and
    T_Error_Maintenance.cond = "Physical switch changed to MANUAL"

    T_Maintenance_Idle.src = Maintenance and
    T_Maintenance_Idle.tgt = Idle and
    T_Maintenance_Idle.ev  = Event_Switch_Auto and
    T_Maintenance_Idle.cond = "All error flags cleared"

    T_Error_SafeMode.src = Error and
    T_Error_SafeMode.tgt = SafeMode and
    T_Error_SafeMode.ev  = Event_NetLoss_LowBat and
    T_Error_SafeMode.cond = "WiFi RSSI < -80dBm AND SOC < 15%"
}

/* ---------- Wildcard transition to Error (any src) ---------- */
fact WildcardToError {
    all s: State | some t: Transition |
        t.src = s and t.tgt = Error and t.ev = Event_Critical_Error
}

/* ---------- Assertion ---------- */
assert L_Approach_has_outgoing {
    some t: Transition | t.src = L_Approach
}

check L_Approach_has_outgoing for 5 State, 5 Event, 30 Transition, 5 Int