from pydantic import BaseModel, HttpUrl
from typing import Optional
from uuid import UUID


class CreateUser(BaseModel):
    name: str = "user"


class CreateEndpoint(BaseModel):
    name: str = "default"


class CreateDestination(BaseModel):
    url: HttpUrl
    method: str = "POST"
    secret_header_name: str = "X-Relay-Secret"
    secret_value: str = "change-me"


class EndpointOut(BaseModel):
    id: UUID
    name: str
    is_enabled: bool


class DestinationOut(BaseModel):
    id: UUID
    url: str
    method: str


class DeliveryOut(BaseModel):
    id: UUID
    status: str
    attempt: int
    last_http_status: Optional[int] = None
    last_error: Optional[str] = None
