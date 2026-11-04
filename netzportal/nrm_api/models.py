from datetime import date, datetime
from pydantic import BaseModel, Field


class Installation(BaseModel):
    id: str = Field(description="NRM order-product ID; identifies the application, not a physical site")
    application_number: str
    order_id: str
    order_number: str
    order_product_number: str
    product_id: str
    product_name: str
    request_type: str
    request_type_name: str
    status_code: str = Field(description="Unmodified NRM status, e.g. Zur_Korrektur")
    status: str = Field(description="NRM status name with underscores replaced by spaces")
    submitted_on: date | None
    location: str = Field(description="Installation address as supplied by NRM, including line breaks")
    applicant: str = Field(description="Applicant name and address as supplied by NRM")
    connection_taker: str
    division: str
    is_open: bool
    is_closed: bool
    is_assigned: bool
    unread_comments_count: int


class InstallationList(BaseModel):
    source: str = "NRM Netzportal / Meine NRM / Bestellungen / Alle"
    retrieved_at: datetime
    total: int
    installations: list[Installation]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
