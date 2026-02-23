from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    agent_type: str
    model: str
    parameters: Optional[dict] = None

class AgentCreate(AgentBase):
    pass

class AgentResponse(AgentBase):
    id: str
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    agent_id: str
    input_data: dict
    output_data: Optional[dict] = None
    status: Optional[str] = "pending"
    error_message: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class TaskResponse(TaskBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True