module HolisticSystem

open util/ordering[Step] as ord

// ------------------------------------------------------------
// Signatures
// ------------------------------------------------------------

// Time step
sig Step {
    state    : one State,
    occupies : set Resource,          // resources occupied in this step
    events   : set Event,            // events/commands observed in this step
    outputs  : set Output            // outputs produced in this step
}

// Top‑level states (including sub‑states)
abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging,
        Paused, Error, Maintenance, SafeMode,
        L_Approach, L_Handshake, L_Transfer, L_Verify,
        Diagnostic extends State {}

// Events / Commands (both internal events and external commands)
abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order,
        Event_Obstacle_Detected, Event_Obstacle_Cleared,
        Event_Arrived_Pickup, Event_Load_Complete,
        Event_Arrived_Dropoff, Event_Unload_Complete,
        Event_Go_Charge, Event_Low_Battery,
        Event_Charge_Complete, Event_Critical_Error,
        Event_Switch_Manual, Event_Switch_Auto,
        Event_NetLoss_LowBat,
        CMD_MOVE, CMD_PAUSE, CMD_RESUME,
        CMD_TASK_ASSIGN, CMD_EMERGENCY_STOP,
        CMD_CHANGE_MODE,
        EVT_POS_UPDATE, EVT_TASK_RESULT,
        REQ_ACQUIRE_RESOURCE, RES_GRANT_RESOURCE,
        REQ_RELEASE_RESOURCE extends Event {}

// Resources that require exclusive access
abstract sig Resource {}
one sig ChargingStation, Intersection, LED_Indicator, MotorPowerRelay extends Resource {}

// Outputs (LED patterns, motor control, etc.)
abstract sig Output {}
one sig LED_GREEN_ON, LED_BLUE_ROTATE, LED_YELLOW_BLINK,
        LED_RED_BLINK, Motor_Enable, Motor_Disable extends Output {}

// Requirement rules linking conditions to required outputs
abstract sig Requirement {
    condition : set State + Event,   // when this rule applies
    action    : one Output           // required output
}

// ------------------------------------------------------------
// Helper sets
// ------------------------------------------------------------
let EndStates = Idle + SafeMode + Maintenance

// ------------------------------------------------------------
// Transition predicate
// ------------------------------------------------------------
pred transition[s, n: Step] {
    // 1. Booting -> Idle
    (s.state = Booting and Event_Init_Complete in n.events and n.state = Idle) or

    // 2. Idle -> Moving
    (s.state = Idle and Event_Transport_Order in n.events and n.state = Moving) or

    // 3. Moving -> Paused
    (s.state = Moving and Event_Obstacle_Detected in n.events and n.state = Paused) or

    // 4. Paused -> Moving
    (s.state = Paused and Event_Obstacle_Cleared in n.events and n.state = Moving) or

    // 5. Moving -> Loading
    (s.state = Moving and Event_Arrived_Pickup in n.events and n.state = Loading) or

    // 6. Loading -> Moving
    (s.state = Loading and Event_Load_Complete in n.events and n.state = Moving) or

    // 7. Moving -> Unloading
    (s.state = Moving and Event_Arrived_Dropoff in n.events and n.state = Unloading) or

    // 8. Unloading -> Idle
    (s.state = Unloading and Event_Unload_Complete in n.events and n.state = Idle) or

    // 9. Idle -> Charging (command or low battery)
    (s.state = Idle and (Event_Go_Charge in n.events or Event_Low_Battery in n.events) and n.state = Charging) or

    // 10. Charging -> Idle
    (s.state = Charging and Event_Charge_Complete in n.events and n.state = Idle) or

    // 11. Global -> Error (critical error)
    (Event_Critical_Error in n.events and n.state = Error) or

    // 12. Error -> Maintenance
    (s.state = Error and Event_Switch_Manual in n.events and n.state = Maintenance) or

    // 13. Maintenance -> Idle
    (s.state = Maintenance and Event_Switch_Auto in n.events and n.state = Idle) or

    // 14. Error -> SafeMode
    (s.state = Error and Event_NetLoss_LowBat in n.events and n.state = SafeMode) or

    // 15. Idle -> Diagnostic (manual switch)
    (s.state = Idle and Event_Switch_Manual in n.events and n.state = Diagnostic) or

    // 16. Diagnostic -> Idle
    (s.state = Diagnostic and Event_Switch_Auto in n.events and n.state = Idle)
}

// ------------------------------------------------------------
// Facts
// ------------------------------------------------------------

// Consecutive steps must either follow a defined transition or stutter (no change)
fact StepProgression {
    all s: Step - ord/last |
        let n = ord/next[s] |
        transition[s, n] or
        (n.state = s.state and n.occupies = s.occupies and n.events = s.events and n.outputs = s.outputs)
}

// Every step must have at most one instance of each exclusive resource
fact ResourceExclusivity {
    all s: Step | all r: Resource | lone (s.occupies & r)
}

// Sample requirement rules (used by NoConflictingOutputs)
// Concrete Requirement Rules (Defect 3 Reproduction)
// 1. Emergency Rule: Error or Stop command -> Red Blink
one sig Rule_Emergency extends Requirement {}
fact {
    Rule_Emergency.condition = Error + CMD_EMERGENCY_STOP
    Rule_Emergency.action = LED_RED_BLINK
}

// 2. Moving Rule: Moving state -> Blue Rotate
one sig Rule_Moving extends Requirement {}
fact {
    Rule_Moving.condition = Moving
    Rule_Moving.action = LED_BLUE_ROTATE
}

// 3. Task Assignment Rule: Task Assign command -> Blue Rotate
// This conflicts with Rule_Emergency if Task Assign happens during Error/Stop
one sig Rule_TaskAssign extends Requirement {}
fact {
    Rule_TaskAssign.condition = CMD_TASK_ASSIGN
    Rule_TaskAssign.action = LED_BLUE_ROTATE
}

// 4. Idle Rule: Idle state -> Green On
one sig Rule_Idle extends Requirement {}
fact {
    Rule_Idle.condition = Idle
    Rule_Idle.action = LED_GREEN_ON
}

// ------------------------------------------------------------
// Assertions
// ------------------------------------------------------------

assert DeadlockFree {
    all s: Step |
        (s.state !in EndStates) implies (some n: Step | transition[s, n] and n != s)
}

assert Reachable {
    all st: State | some s: Step | s.state = st
}

assert ResourceSafety {
    all s: Step | all r: Resource | lone (s.occupies & r)
}

assert Deterministic {
    all s: Step | all n1, n2: Step |
        (transition[s, n1] and transition[s, n2]) implies n1 = n2
}

pred ConsistencyViolation {
    some s: Step |
        some disj r1, r2: Requirement |
            (s.state in r1.condition and s.state in r2.condition) and r1.action != r2.action
}

// ------------------------------------------------------------
// Checks
// ------------------------------------------------------------
run ConsistencyViolation for 10 Step