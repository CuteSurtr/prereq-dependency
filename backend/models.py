from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class PrereqType(StrEnum):
    AND = "AND"
    OR = "OR"
    COREQ = "COREQ"
    RECOMMENDED = "RECOMMENDED"


class Course(Base):
    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    department: Mapped[str] = mapped_column(String(10), index=True)
    units: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_prereq_text: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)

    prereqs: Mapped[list[Prereq]] = relationship(
        back_populates="course",
        foreign_keys="Prereq.course_code",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "department": self.department,
            "units": self.units,
            "description": self.description,
            "raw_prereq_text": self.raw_prereq_text,
            "notes": self.notes,
        }


class Prereq(Base):
    __tablename__ = "prereqs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(
        String(20), ForeignKey("courses.code"), index=True
    )
    group_id: Mapped[int] = mapped_column(Integer)
    required_course_code: Mapped[str] = mapped_column(String(20), index=True)
    prereq_type: Mapped[PrereqType] = mapped_column(SAEnum(PrereqType))

    course: Mapped[Course] = relationship(back_populates="prereqs", foreign_keys=[course_code])
