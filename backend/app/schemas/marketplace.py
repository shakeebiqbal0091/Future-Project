from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, constr


class MarketplaceAgent(BaseModel):
    id: str
    name: str
    description: str
    category: str
    price: float
    rating: float
    reviews: int
    author: str
    created_at: datetime
    version: int
    compatible: bool
    installed: bool
    tools: List[str]
    requirements: List[str]

    class Config:
        from_attributes = True


class MarketplaceAgentList(BaseModel):
    agents: List[MarketplaceAgent]
    total: int
    page: int
    size: int


class AgentInstallationRequest(BaseModel):
    agent_id: str


class AgentInstallationResponse(BaseModel):
    message: str
    agent_id: str
    installed_at: datetime


class MarketplaceSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = None
    price_range: Optional[str] = None
    page: int = 1
    size: int = 12


class MarketplaceSearchResponse(BaseModel):
    results: List[MarketplaceAgent]
    total: int
    page: int
    size: int
    query: str
    filters: Dict[str, Any]


class FeaturedAgentsRequest(BaseModel):
    count: int = 8


class FeaturedAgentsResponse(BaseModel):
    agents: List[MarketplaceAgent]
    featured_count: int


class AgentCategory(BaseModel):
    id: str
    name: str
    count: int


class MarketplaceCategoriesResponse(BaseModel):
    categories: List[AgentCategory]
    total_categories: int