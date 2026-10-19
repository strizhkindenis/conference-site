import base64
import io
from typing import Annotated

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import HTMLResponse
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

from src.db import Session
from src.depends import TemplateRenderer
from src.routers.auth.depends import CurrentUser, CurrentUserOrNone
from src.routers.user.models import User, UserRole

from .models import Vote, VoteCandidate
from .repo import CandidateRepository, VoteRepository
from .schemas import VoteAdminContext, VoteForm, VoteFormContext

vote_router = APIRouter(prefix="/vote")


@vote_router.get("/", response_class=HTMLResponse)
async def get_vote(
    templates: TemplateRenderer,
    current_user: CurrentUserOrNone,
    session: Session,
):
    candidates = await CandidateRepository(session).get_all()
    return templates.render(
        "vote/index.jinja",
        VoteFormContext(current_user=current_user, reports=candidates),
    )


@vote_router.post("/", response_class=HTMLResponse)
async def post_vote(
    templates: TemplateRenderer,
    current_user: CurrentUserOrNone,
    session: Session,
    form: Annotated[VoteForm, Form()],
):
    candidates = await CandidateRepository(session).get_all()
    try:
        vote = await VoteRepository(session).update(
            form.code, form.candidate_id
        )
    except NoResultFound:
        return templates.render(
            "vote/index.jinja",
            VoteFormContext(
                current_user=current_user,
                reports=candidates,
                selected=form.candidate_id,
                error="Такого кода несуществует.",
            ),
        )

    return templates.render(
        "vote/index.jinja",
        VoteFormContext(
            current_user=current_user,
            reports=candidates,
            selected=vote.candidate_id,
            message="Голос учтен.",
        ),
    )


def get_vote_results_plot(
    votes: list[Vote], candidates: list[VoteCandidate]
) -> str:
    labels = [str(candidate.id) for candidate in candidates]
    counts = dict.fromkeys(labels, 0)
    for vote in votes:
        if vote.candidate_id is not None and str(vote.candidate_id) in counts:
            counts[str(vote.candidate_id)] += 1
    plt.bar(labels, [counts[label] for label in labels])
    plt.title("Результаты голосования")
    with io.BytesIO() as buf:
        plt.savefig(buf, format="jpeg")
        img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    plt.close()
    return f"data:image/jpeg;base64,{img_b64}"


async def get_vote_admin_context(
    session: Session, current_user: User, message: str | None = None
) -> VoteAdminContext:
    votes = await VoteRepository(session).get()
    candidates = await CandidateRepository(session).get_all(
        include_deleted=True
    )
    result = await session.execute(
        select(User)
        .where(User.role == UserRole.participant)
        .order_by(User.surname)
    )
    participants = list(result.scalars().all())
    return VoteAdminContext(
        current_user=current_user,
        message=message,
        image=get_vote_results_plot(votes, candidates),
        all_cnt=len(votes),
        voted_cnt=sum(vote.candidate_id is not None for vote in votes),
        participants=[
            VoteCandidate(
                id=user.id,
                user_id=user.id,
                name=f"{user.surname or ''} {user.name or ''}".strip()
                or user.email,
                work_name=(
                    user.form.get("report_name") or ""
                    if isinstance(user.form, dict)
                    else user.form.report_name
                    if user.form
                    else "Без названия"
                ),
            )
            for user in participants
        ],
        candidates=candidates,
        selected_user_ids=[
            candidate.user_id
            for candidate in candidates
            if candidate.user_id is not None
        ],
    )


@vote_router.get("/admin", response_class=HTMLResponse)
async def get_admin(
    templates: TemplateRenderer, current_user: CurrentUser, session: Session
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return templates.render(
        "vote/admin.jinja", await get_vote_admin_context(session, current_user)
    )


@vote_router.post("/admin", response_class=HTMLResponse)
async def post_admin(
    templates: TemplateRenderer,
    current_user: CurrentUser,
    session: Session,
    codes_file: Annotated[UploadFile | None, File()] = None,
    participant_ids: Annotated[list[int] | None, Form()] = None,
    selection_submit: Annotated[str | None, Form()] = None,
    arbitrary_name: Annotated[str, Form()] = "",
    arbitrary_work_name: Annotated[str, Form()] = "",
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    messages = []
    if codes_file is not None and codes_file.filename:
        codes = (await codes_file.read()).decode("utf8").split()
        vote_repo = VoteRepository(session)
        await vote_repo.delete_all()
        for code in codes:
            await vote_repo.create(code.strip())
        messages.append("Коды голосования перезаданы.")

    candidate_repo = CandidateRepository(session)
    selected_ids = set(participant_ids or [])
    result = await session.execute(
        select(User).where(
            User.role == UserRole.participant, User.id.in_(selected_ids)
        )
    )
    selected_users = list(result.scalars().all())
    candidates = [
        VoteCandidate(
            user_id=user.id,
            name=f"{user.surname or ''} {user.name or ''}".strip()
            or user.email,
            work_name=(
                user.form.get("report_name") or ""
                if isinstance(user.form, dict)
                else user.form.report_name
                if user.form
                else "Без названия"
            ),
        )
        for user in selected_users
    ]
    if selection_submit is not None:
        await candidate_repo.replace(candidates)
        messages.append("Кандидаты для голосования сохранены.")

    if arbitrary_name.strip() and arbitrary_work_name.strip():
        await candidate_repo.create(
            arbitrary_name.strip(), arbitrary_work_name.strip()
        )
        messages.append("Произвольный кандидат добавлен.")

    context = await get_vote_admin_context(
        session, current_user, " ".join(messages) or None
    )
    return templates.render("vote/admin.jinja", context)


@vote_router.post(
    "/admin/candidate/{candidate_id}", response_class=HTMLResponse
)
async def update_candidate(
    candidate_id: int,
    templates: TemplateRenderer,
    current_user: CurrentUser,
    session: Session,
    name: Annotated[str, Form()],
    work_name: Annotated[str, Form()],
    deleted: Annotated[str | None, Form()] = None,
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    candidate_repo = CandidateRepository(session)
    if deleted is not None:
        await candidate_repo.mark_deleted(candidate_id)
    else:
        if not name.strip() or not work_name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        await candidate_repo.update(
            candidate_id, name.strip(), work_name.strip()
        )
    context = await get_vote_admin_context(
        session, current_user, "Кандидат сохранен."
    )
    return templates.render("vote/admin.jinja", context)
