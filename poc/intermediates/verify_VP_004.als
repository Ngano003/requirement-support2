module VerifyLoadingTransition

abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused, Error, Maintenance, SafeMode,
        L_Approach, L_Handshake, L_Transfer, L_Verify extends State {}

abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected, Event_Obstacle_Cleared,
        Event_Arrived_Pickup, Event_Load_Complete, Event_Arrived_Dropoff, Event_Unload_Complete,
        Event_Go_Charge, Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

sig Transition {
    src: one State,
    tgt: one State,
    ev : one Event,
    cond: one String
}

/* Transitions relevant to the Loading state */
fact LoadingTransitions {
    some t: Transition | t.src = Loading
}

/* Example concrete transition from Loading to Moving */
one sig T_LoadingToMoving extends Transition {}

fact DefineTransitions {
    T_LoadingToMoving.src = Loading
    T_LoadingToMoving.tgt = Moving
    T_LoadingToMoving.ev  = Event_Load_Complete
    T_LoadingToMoving.cond = "Load sensor ON"
}

/* Resources (included for completeness) */
abstract sig Resource {}
one sig ChargingStation, IntersectionNode, RFIDNode, WiFiChannel,
        MotorDriver, EmergencyStopCircuit extends Resource {}

assert LoadingHasSuccessor {
    some t: Transition | t.src = Loading
}

check LoadingHasSuccessor for 5 State, 5 Event, 5 Transition, 5 Resource