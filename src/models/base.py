"""
Base models for RestDelBot 5.0
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class RestDelBotBaseModel(BaseModel):
    """Base model with common fields and optimizations"""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        # Performance optimizations
        validate_assignment = True
        use_enum_values = True
        populate_by_name = True  # заменено с allow_population_by_field_name
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SessionStatus(str, Enum):
    """Session status enumeration"""
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class OrderStatus(str, Enum):
    """Order status enumeration"""
    DRAFT = "draft"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
