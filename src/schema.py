from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class Constraint(BaseModel):
    """制約: システムに対する制約条件 (例: 応答時間 < 50ms)"""
    id: str = Field(..., description="制約の一意なID")
    description: str = Field(..., description="制約の内容")
    type: str = Field(..., description="制約の種類 (ex: performance, safety, resource)")

class Output(BaseModel):
    """成果: システムのアクションや出力 (例: LED点灯, モーター回転)"""
    id: str = Field(..., description="出力の一意なID")
    description: str = Field(..., description="出力の内容")
    target_entity_id: Optional[str] = Field(None, description="出力先の実体ID")
    conflict_group: Optional[str] = Field(None, description="排他制御グループID (例: 'motor_arm_action'). 同一グループの出力は同時実行不可。")

class Trigger(BaseModel):
    """トリガー: 状態遷移を引き起こすイベント (例: ボタン押下、タイムアウト)"""
    id: str = Field(..., description="トリガーの一意なID")
    description: str = Field(..., description="トリガーの内容")
    source_entity_id: Optional[str] = Field(None, description="トリガー発生元実体ID")

class Transition(BaseModel):
    """遷移: ある状態から別の状態への移動"""
    trigger_id: str = Field(..., description="遷移を引き起こすトリガーID")
    target_state_id: str = Field(..., description="遷移先の状態ID")
    output_ids: List[str] = Field(default_factory=list, description="遷移に伴う出力IDリスト")
    constraint_ids: List[str] = Field(default_factory=list, description="適用される制約IDリスト")

class State(BaseModel):
    """状態: 実体が取りうる状態 (例: 待機中, ロック中)"""
    id: str = Field(..., description="状態の一意なID")
    name: str = Field(..., description="状態名")
    description: str = Field("", description="状態の説明")
    transitions: List[Transition] = Field(default_factory=list, description="この状態からの遷移リスト")

class Entity(BaseModel):
    """主格: システムを構成する要素 (例: ユーザー, コントローラー)"""
    id: str = Field(..., description="実体の一意なID")
    name: str = Field(..., description="実体名")
    type: str = Field(..., description="実体の種類 (ex: user, hardware, software)")
    states: List[State] = Field(default_factory=list, description="この実体が持つ状態リスト")

class SystemRequirements(BaseModel):
    """システム要件全体"""
    project_name: str
    entities: List[Entity]
    global_constraints: List[Constraint] = Field(default_factory=list, description="システム全体にかかる制約")
    defined_outputs: List[Output] = Field(default_factory=list, description="システム内で定義された全出力リスト")
    unbound_triggers: List[Trigger] = Field(default_factory=list, description="エンティティに紐付かないグローバルトリガー定義")
