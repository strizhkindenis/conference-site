from enum import StrEnum, auto
from typing import Annotated

from pydantic import BaseModel, model_validator
from sqlmodel import JSON, Column, Field, SQLModel, UniqueConstraint


class ReportFormType(StrEnum):
    fundamental = auto()
    applied = auto()
    classical = auto()
    nonlinear = auto()


class ReportType(StrEnum):
    original = auto()
    scipop = auto()


class ReportForm(BaseModel):
    form_type: ReportFormType = Field(default=ReportFormType.fundamental)

    report_name: str | None = None
    report_type: ReportType = Field(default=ReportType.original)

    @model_validator(mode="after")
    def normalize_legacy_form_type(self):
        if self.form_type == ReportFormType.classical:
            self.form_type = ReportFormType.fundamental
        elif self.form_type == ReportFormType.nonlinear:
            self.form_type = ReportFormType.applied
        return self

    flag_bio_phys: bool = False
    flag_comp_sci: bool = False
    flag_math_phys: bool = False
    flag_med_phys: bool = False
    flag_nano_tech: bool = False
    flag_general_phys: bool = False
    flag_solid_body: bool = False
    flag_space_phys: bool = False

    file_id: int | None = None


class UserRole(StrEnum):
    admin = auto()
    basic = auto()
    participant = auto()
    viewer = auto()


class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("email", name="uq_user_email"),)

    id: int = Field(default=None, primary_key=True)
    email: str = Field(default=None, nullable=False)
    password: str = Field(default=None, nullable=False)
    role: UserRole = Field(
        default=UserRole.basic,
        nullable=False,
        sa_column_kwargs={"server_default": UserRole.basic},
    )

    name: Annotated[str | None, Field(default=None, nullable=True)]
    surname: Annotated[str | None, Field(default=None, nullable=True)]
    patronymic: Annotated[str | None, Field(default=None, nullable=True)]
    organization: Annotated[str | None, Field(default=None, nullable=True)]
    year: Annotated[int | None, Field(default=None, nullable=True)]
    contact: Annotated[str | None, Field(default=None, nullable=True)]

    form: Annotated[
        ReportForm | None,
        Field(default=None, sa_column=Column(JSON, nullable=True)),
    ]
