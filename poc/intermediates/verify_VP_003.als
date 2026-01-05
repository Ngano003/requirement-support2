module VerifyMovingTransition

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

fact Transitions {
    some t1: Transition | t1.src = Booting   && t1.tgt = Idle      && t1.ev = Event_Init_Complete && t1.cond = "All POST modules PASS"
    some t2: Transition | t2.src = Idle      && t2.tgt = Moving    && t2.ev = Event_Transport_Order && t2.cond = "SOC > 20% AND current position known"
    some t3: Transition | t3.src = Moving    && t3.tgt = Paused    && t3.ev = Event_Obstacle_Detected && t3.cond = "LDS distance < 1.0m for >= 300ms"
    some t4: Transition | t4.src = Paused    && t4.tgt = Moving    && t4.ev = Event_Obstacle_Cleared && t4.cond = "LDS distance > 1.2m for >= 2000ms"
    some t5: Transition | t5.src = Moving    && t5.tgt = Loading   && t5.ev = Event_Arrived_Pickup && t5.cond = "RFID tag read AND stop position error <= ±10mm"
    some t6: Transition | t6.src = Loading   && t6.tgt = Moving    && t6.ev = Event_Load_Complete && t6.cond = "Load sensor ON"
    some t7: Transition | t7.src = Moving    && t7.tgt = Unloading && t7.ev = Event_Arrived_Dropoff && t7.cond = "Stop position error <= ±10mm"
    some t8: Transition | t8.src = Unloading && t8.tgt = Idle      && t8.ev = Event_Unload_Complete && t8.cond = "Load sensor OFF"
    // additional transitions can be added similarly
}

abstract sig Resource {}
one sig ChargingStation extends Resource {}

assert MovingHasOutgoing {
    some t: Transition | t.src = Moving
}

check MovingHasOutgoing for 15 State, 15 Event, 10 Transition, 2 Resource, 5 Int