from enum import StrEnum, auto
from typing import Annotated

from sqlmodel import Column, Enum, Field, SQLModel, String, UniqueConstraint


class Reports(StrEnum):
    a = auto()
    b = auto()
    c = auto()
    d = auto()
    e = auto()
    f = auto()
    g = auto()
    h = auto()
    i = auto()
    j = auto()
    k = auto()
    l = auto()


class VoteCandidate(SQLModel, table=True):
    id: Annotated[int | None, Field(default=None, primary_key=True)]
    user_id: Annotated[int | None, Field(default=None, unique=True)]
    name: Annotated[str, Field(sa_column=Column(String(200), nullable=False))]
    work_name: Annotated[
        str, Field(sa_column=Column(String(500), nullable=False))
    ]
    deleted: bool = Field(default=False, nullable=False)


class Vote(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("code", name="uq_vote_code"),)

    id: Annotated[int | None, Field(default=None, primary_key=True)]
    code: Annotated[
        str,
        Field(sa_column=Column(String(50), nullable=False)),
    ]
    report: Annotated[
        Reports | None,
        Field(
            default=None,
            sa_column=Column(Enum(Reports), nullable=True),
        ),
    ]
    candidate_id: int | None = Field(
        default=None, foreign_key="votecandidate.id"
    )
