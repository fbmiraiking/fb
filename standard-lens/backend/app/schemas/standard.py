from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.standard import StandardStatus


class StandardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    standard_no: str
    normalized_no: str
    standard_name: str
    standard_type: str | None = None
    status: StandardStatus
    publish_date: date | None = None
    effective_date: date | None = None
    expiry_date: date | None = None
    standard_year: int | None = None
    source: str | None = None
    source_url: str | None = Field(default=None, description="官方标准链接")


class StandardDetail(StandardSummary):
    scope: str | None = None
    created_at: datetime
    updated_at: datetime


class StandardVersionItem(BaseModel):
    """One entry in a standard's version chain.

    Field names are serialized in camelCase for the frontend timeline.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    standard_no: str = Field(serialization_alias="standardNo")
    standard_name: str = Field(serialization_alias="standardName")
    status: StandardStatus
    publish_date: date | None = Field(default=None, serialization_alias="publishDate")
    effective_date: date | None = Field(default=None, serialization_alias="effectiveDate")
    expiry_date: date | None = Field(default=None, serialization_alias="expiryDate")
    standard_year: int | None = Field(default=None, serialization_alias="standardYear")
    is_historical: bool = Field(serialization_alias="isHistorical")
    is_current: bool = Field(serialization_alias="isCurrent")
    is_upcoming: bool = Field(serialization_alias="isUpcoming")


class StandardSearchResponse(BaseModel):
    query: str
    normalized_query: str | None = Field(
        default=None,
        description="查询可识别为标准号时的规范化结果",
    )
    total: int
    limit: int
    offset: int
    items: list[StandardSummary]
