import enum

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RequirementType(str, enum.Enum):
    VISUAL = "VISUAL"
    LABEL = "LABEL"
    DOCUMENT = "DOCUMENT"
    LAB_TEST = "LAB_TEST"
    MEASUREMENT = "MEASUREMENT"


class StandardRequirement(Base):
    """One verification requirement extracted from a standard.

    The requirement type decides how far an image may be used: only VISUAL and
    LABEL items can be assisted by image analysis. DOCUMENT items need
    certificates, LAB_TEST items need laboratory work, and MEASUREMENT items
    need reliable instrument readings.
    """

    __tablename__ = "standard_requirement"
    __table_args__ = {
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_0900_ai_ci",
    }

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    standard_id: Mapped[int] = mapped_column(
        ForeignKey("standard.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chapter: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_type: Mapped[RequirementType] = mapped_column(
        Enum(
            RequirementType,
            name="requirement_type",
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
        index=True,
    )
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    verification_method: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<StandardRequirement id={self.id} standard={self.standard_id} "
            f"chapter={self.chapter!r} type={self.requirement_type!r}>"
        )
