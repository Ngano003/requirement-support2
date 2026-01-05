module VerifyMaintenanceOutgoing

open util/ordering[Step] as ord

-- States
abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused, Error, Maintenance,
        SafeMode, L_Approach, L_Handshake, L_Transfer, L_Verify extends State {}

-- Events
abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected,
        Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete,
        Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge,
        Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

-- Resources (minimal definition)
abstract sig Resource {}
one sig ChargingStation, IntersectionNode, RFIDNode, WiFiChannel,
        MotorDriver, EmergencyStopCircuit extends Resource {}

-- Transitions
sig Transition {
    src: one State,
    tgt: one State,
    ev : one Event
}

/* All allowed transitions (existence) */
fact TransitionInstances {
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
    -- wildcard transition to Error from any state
    all s: State | some t: Transition | t.src = s and t.tgt = Error and t.ev = Event_Critical_Error
}

/* Steps (trace) */
sig Step {
    state: one State
}

/* Initial step */
fact Init {
    ord/first.state = Booting
}

/* Transition consistency between consecutive steps */
fact StepTransitionRule {
    all s: Step | let n = ord/next[s] | some n implies
        some tr: Transition | tr.src = s.state and tr.tgt = n.state
}

/* Assertion: Maintenance state must have at least one outgoing transition */
assert MaintenanceHasOutgoing {
    all s: Step | s.state = Maintenance implies
        some n: Step | n = ord/next[s] and
            some tr: Transition | tr.src = Maintenance and tr.tgt = n.state
}

check MaintenanceHasOutgoing for 5 Step, exactly 14 State, exactly 15 Event, exactly 15 Transition, 5 Int