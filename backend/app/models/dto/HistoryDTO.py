"""任务执行历史记录数据传输对象 (History DTO)。

专职负责规划与求解任务历史查询、详情审计的 HTTP API 请求/响应模型。
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TaskHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_type: str = Field(..., description="任务类型: ROUTING, GLOBAL_ROUTING, CLUSTERING, CLUSTER_SCHEDULE")
    save_type: Optional[str] = Field("AUTO", description="保存类型: MANUAL 或 AUTO")
    status: str = Field("SUCCESS", description="状态: PENDING, RUNNING, SUCCESS, FAILED")
    parameters: Optional[str] = Field(None, description="输入参数 JSON 字符串")
    result: Optional[str] = Field(None, description="输出结果 JSON 字符串")
    error_message: Optional[str] = Field(None, description="错误信息")


class TaskHistoryCreate(TaskHistoryBase):
    task_id: Optional[str] = None


class TaskHistoryResponse(TaskHistoryBase):
    id: int
    task_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
