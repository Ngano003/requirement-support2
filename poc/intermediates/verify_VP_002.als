module VerifyIdleTransition

abstract sig State {}
one sig Booting, Idle, Moving, Loading, Unloading, Charging, Paused, Error, Maintenance, SafeMode, L_Approach, L_Handshake, L_Transfer, L_Verify extends State {}

abstract sig Event {}
one sig Event_Init_Complete, Event_Transport_Order, Event_Obstacle_Detected, Event_Obstacle_Cleared, Event_Arrived_Pickup, Event_Load_Complete, Event_Arrived_Dropoff, Event_Unload_Complete, Event_Go_Charge, Event_Low_Battery, Event_Charge_Complete, Event_Critical_Error, Event_Switch_Manual, Event_Switch_Auto, Event_NetLoss_LowBat extends Event {}

sig Transition {
  src: one State,
  tgt: one State,
  ev:  one Event
}

// 必要な遷移を定義
fact Transitions {
  // Booting -> Idle
  some t1: Transition | t1.src = Booting and t1.tgt = Idle and t1.ev = Event_Init_Complete
  // Idle -> Moving
  some t2: Transition | t2.src = Idle and t2.tgt = Moving and t2.ev = Event_Transport_Order
  // Moving -> Paused
  some t3: Transition | t3.src = Moving and t3.tgt = Paused and t3.ev = Event_Obstacle_Detected
  // Paused -> Moving
  some t4: Transition | t4.src = Paused and t4.tgt = Moving and t4.ev = Event_Obstacle_Cleared
  // Moving -> Loading
  some t5: Transition | t5.src = Moving and t5.tgt = Loading and t5.ev = Event_Arrived_Pickup
  // Loading -> Moving
  some t6: Transition | t6.src = Loading and t6.tgt = Moving and t6.ev = Event_Load_Complete
  // Moving -> Unloading
  some t7: Transition | t7.src = Moving and t7.tgt = Unloading and t7.ev = Event_Arrived_Dropoff
  // Unloading -> Idle
  some t8: Transition | t8.src = Unloading and t8.tgt = Idle and t8.ev = Event_Unload_Complete
  // Idle -> Charging (order)
  some t9: Transition | t9.src = Idle and t9.tgt = Charging and t9.ev = Event_Go_Charge
  // Idle -> Charging (low battery)
  some t10: Transition | t10.src = Idle and t10.tgt = Charging and t10.ev = Event_Low_Battery
  // Charging -> Idle
  some t11: Transition | t11.src = Charging and t11.tgt = Idle and t11.ev = Event_Charge_Complete
  // Error -> Maintenance
  some t12: Transition | t12.src = Error and t12.tgt = Maintenance and t12.ev = Event_Switch_Manual
  // Maintenance -> Idle
  some t13: Transition | t13.src = Maintenance and t13.tgt = Idle and t13.ev = Event_Switch_Auto
  // Error -> SafeMode
  some t14: Transition | t14.src = Error and t14.tgt = SafeMode and t14.ev = Event_NetLoss_LowBat
}

// Idle状態から少なくとも1つの遷移先が存在することを検証
assert IdleHasOutgoing {
  some t: Transition | t.src = Idle
}

check IdleHasOutgoing for 20 Transition, 15 Event