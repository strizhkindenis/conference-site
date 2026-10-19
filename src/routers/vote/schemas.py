from fastapi import UploadFile
from pydantic import BaseModel, Field

from src.routers.user.schemas import UserContext

from .models import VoteCandidate


class VoteFormContext(UserContext):
    selected: int | None = None
    reports: list[VoteCandidate] = []


class VoteForm(BaseModel):
    code: str
    candidate_id: int


class VoteAdminContext(UserContext):
    all_cnt: int
    voted_cnt: int
    image: str
    participants: list[VoteCandidate] = []
    candidates: list[VoteCandidate] = []
    selected_user_ids: list[int] = []


class CodesForm(BaseModel):
    codes_file: UploadFile


class CandidateForm(BaseModel):
    name: str = Field(min_length=1)
    work_name: str = Field(min_length=1)
