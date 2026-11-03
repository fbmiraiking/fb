from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.requirement import RequirementType
from app.models.standard import StandardStatus
from app.schemas.vision import VisionAnalysisResponse
from app.services.requirement_verification_service import (
    VERIFICATION_DISCLAIMER,
    RequirementCheckStatus,
)


class StandardMatchItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    standard_no: str = Field(serialization_alias="standardNo")
    standard_name: str = Field(serialization_alias="standardName")
    status: StandardStatus
    status_label: str = Field(serialization_alias="statusLabel")
    publish_date: date | None = Field(default=None, serialization_alias="publishDate")
    effective_date: date | None = Field(default=None, serialization_alias="effectiveDate")
    expiry_date: date | None = Field(default=None, serialization_alias="expiryDate")
    relation_type: str = Field(serialization_alias="relationType")
    is_historical: bool = Field(serialization_alias="isHistorical")


class DetectedStandardItem(StandardMatchItem):
    replaced_by: list[StandardMatchItem] = Field(
        default_factory=list,
        serialization_alias="replacedBy",
    )
    latest_current: list[StandardMatchItem] = Field(
        default_factory=list,
        serialization_alias="latestCurrent",
    )
    notice: str


class RelatedStandardsResponse(BaseModel):
    current: list[StandardMatchItem]
    upcoming: list[StandardMatchItem]
    historical: list[StandardMatchItem]
    other: list[StandardMatchItem]


class MatchedCategoryItem(BaseModel):
    id: int
    name: str
    description: str | None = None
    parent_id: int | None = Field(default=None, serialization_alias="parentId")
    aliases: list[str] = Field(default_factory=list)
    score: float
    matched_terms: list[str] = Field(
        default_factory=list,
        serialization_alias="matchedTerms",
    )


class RequirementCheckItem(BaseModel):
    requirement_id: int = Field(serialization_alias="requirementId")
    chapter: str
    requirement_type: RequirementType = Field(
        serialization_alias="requirementType"
    )
    requirement_text: str = Field(serialization_alias="requirementText")
    verification_method: str = Field(serialization_alias="verificationMethod")
    status: RequirementCheckStatus
    status_label: str = Field(serialization_alias="statusLabel")
    image_checkable: bool = Field(serialization_alias="imageCheckable")
    evidence: list[str]
    message: str


class StandardVerificationItem(BaseModel):
    standard_id: int = Field(serialization_alias="standardId")
    standard_no: str = Field(serialization_alias="standardNo")
    standard_name: str = Field(serialization_alias="standardName")
    status: StandardStatus
    status_label: str = Field(serialization_alias="statusLabel")
    effective_date: date | None = Field(default=None, serialization_alias="effectiveDate")
    replacement_standards: list[StandardMatchItem] = Field(
        default_factory=list,
        serialization_alias="replacementStandards",
    )
    latest_current: list[StandardMatchItem] = Field(
        default_factory=list,
        serialization_alias="latestCurrent",
    )
    lifecycle_notice: str = Field(serialization_alias="lifecycleNotice")
    requirements: list[RequirementCheckItem]
    observed_count: int = Field(serialization_alias="observedCount")
    partial_count: int = Field(serialization_alias="partialCount")
    not_observed_count: int = Field(serialization_alias="notObservedCount")
    external_check_count: int = Field(serialization_alias="externalCheckCount")
    summary: str


class VisionMatchResponse(BaseModel):
    image_analysis: VisionAnalysisResponse = Field(serialization_alias="imageAnalysis")
    detected_standards: list[DetectedStandardItem] = Field(
        serialization_alias="detectedStandards"
    )
    related_standards: RelatedStandardsResponse = Field(
        serialization_alias="relatedStandards"
    )
    image_stored: bool = Field(default=False, serialization_alias="imageStored")
    matched_categories: list[MatchedCategoryItem] = Field(
        default_factory=list,
        serialization_alias="matchedCategories",
    )
    unmatched_visible_standard_numbers: list[str] = Field(
        default_factory=list,
        serialization_alias="unmatchedVisibleStandardNumbers",
    )
    standard_verification: list[StandardVerificationItem] = Field(
        default_factory=list,
        serialization_alias="standardVerification",
    )
    verification_notice: str = Field(
        default=VERIFICATION_DISCLAIMER,
        serialization_alias="verificationNotice",
    )
