module VerifyLTransferDeadEnd

sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused, Error, Maintenance, SafeMode, L_Approach, L_Handshake, L_Transfer, L_Verify extends State {}

sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected, Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete, Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge, Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error, Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

sig Transition {
    src: one State,
    tgt: one State,
    ev:  one Event
}

fact TransitionSet {
    // listed transitions must exist
    some t: Transition | t.src = Booting   and t.tgt = Idle      and t.ev = Event_Init_Complete
    some t: Transition | t.src = Idle      and t.tgt = Moving    and t.ev = Event_Transport_Order
    some t: Transition | t.src = Moving    and t.tgt = Paused    and t.ev = Event_Obstacle_Detected
    some t: Transition | t.src = Paused    and t.tgt = Moving    and t.ev = Event_Obstacle_Cleared
    some t: Transition | t.src = Moving    and t.tgt = Loading   and t.ev = Event_Arrived_Pickup
    some t: Transition | t.src = Loading   and t.tgt = Moving    and t.ev = Event_Load_Complete
    some t: Transition | t.src = Moving    and t.tgt = Unloading and t.ev = Event_Arrived_Dropoff
    some t: Transition | t.src = Unloading and t.tgt = Idle      and t.ev = Event_Unload_Complete
    some t: Transition | t.src = Idle      and t.tgt = Charging  and t.ev = Event_Go_Charge
    some t: Transition | t.src = Idle      and t.tgt = Charging  and t.ev = Event_Low_Battery
    some t: Transition | t.src = Charging  and t.tgt = Idle      and t.ev = Event_Charge_Complete

    // no other transitions are allowed
    all t: Transition |
        (t.src = Booting   and t.tgt = Idle      and t.ev = Event_Init_Complete) or
        (t.src = Idle      and t.tgt = Moving    and t.ev = Event_Transport_Order) or
        (t.src = Moving    and t.tgt = Paused    and t.ev = Event_Obstacle_Detected) or
        (t.src = Paused    and t.tgt = Moving    and t.ev = Event_Obstacle_Cleared) or
        (t.src = Moving    and t.tgt = Loading   and t.ev = Event_Arrived_Pickup) or
        (t.src = Loading   and t.tgt = Moving    and t.ev = Event_Load_Complete) or
        (t.src = Moving    and t.tgt = Unloading and t.ev = Event_Arrived_Dropoff) or
        (t.src = Unloading and t.tgt = Idle      and t.ev = Event_Unload_Complete) or
        (t.src = Idle      and t.tgt = Charging  and t.ev = Event_Go_Charge) or
        (t.src = Idle      and t.tgt = Charging  and t.ev = Event_Low_Battery) or
        (t.src = Charging  and t.tgt = Idle      and t.ev = Event_Charge_Complete)
}

sig Resource {} // placeholder for resource definitions

assert LTransferHasOutgoing {
    some t: Transition | t.src = L_Transfer
}

check LTransferHasOutgoing for 13 State, 15 Event, 20 Transition, 5 Resource, 5 Int