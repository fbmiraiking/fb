from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.product import (
    ProductCategory,
    ReviewStatus,
    StandardProductRelationType,
)
from app.models.standard import StandardStatus


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    parent_id: int | None = Field(default=None, serialization_alias="parentId")
    aliases: list[str] = Field(default_factory=list)

    @classmethod
    def from_category(cls, category: ProductCategory) -> "ProductSummary":
        return cls(
            id=category.id,
            name=category.name,
            description=category.description,
            parent_id=category.parent_id,
            aliases=sorted(alias.alias for alias in category.aliases),
        )


class ProductSearchResponse(BaseModel):
    query: str
    total: int
    limit: int
    offset: int
    items: list[ProductSummary]


class ProductStandardItem(BaseModel):
    id: int
    standard_no: str = Field(serialization_alias="standardNo")
    standard_name: str = Field(serialization_alias="standardName")
    status: StandardStatus
    effective_date: date | None = Field(default=None, serialization_alias="effectiveDate")
    expiry_date: date | None = Field(default=None, serialization_alias="expiryDate")
    relation_type: StandardProductRelationType = Field(
        serialization_alias="relationType"
    )
    review_status: ReviewStatus = Field(serialization_alias="reviewStatus")


class ProductStandardsResponse(BaseModel):
    product: ProductSummary
    current: list[ProductStandardItem]
    upcoming: list[ProductStandardItem]
    historical: list[ProductStandardItem]
    related: list[ProductStandardItem]
