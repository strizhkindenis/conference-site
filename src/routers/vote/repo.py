from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select, update

from .models import Vote, VoteCandidate


class VoteRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_one(self, code: str) -> Vote:
        stmt = select(Vote).where(Vote.code == code)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_one_or_none(self, code: str) -> Vote | None:
        try:
            return await self.get_one(code)
        except NoResultFound:
            return None

    async def get(self) -> list[Vote]:
        result = await self._session.execute(select(Vote))
        return list(result.scalars().all())

    async def create(self, code: str) -> Vote:
        vote = Vote(code=code)
        self._session.add(vote)
        await self._session.flush()
        return vote

    async def update(self, code: str, candidate_id: int) -> Vote:
        candidate = await self._session.execute(
            select(VoteCandidate).where(
                VoteCandidate.id == candidate_id,
                VoteCandidate.deleted.is_(False),
            )
        )
        candidate.scalar_one()
        stmt = (
            update(Vote)
            .where(Vote.code == code)
            .values(candidate_id=candidate_id)
        )
        await self._session.execute(stmt)
        return await self.get_one(code)

    async def delete_all(self):
        await self._session.execute(delete(Vote))


class CandidateRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_all(
        self, include_deleted: bool = False
    ) -> list[VoteCandidate]:
        statement = select(VoteCandidate).order_by(VoteCandidate.id)
        if not include_deleted:
            statement = statement.where(VoteCandidate.deleted.is_(False))
        result = await self._session.execute(statement)
        return list(result.scalars().all())

    async def replace(self, candidates: list[VoteCandidate]) -> None:
        await self._session.execute(update(Vote).values(candidate_id=None))
        await self._session.execute(
            delete(VoteCandidate).where(VoteCandidate.user_id.is_not(None))
        )
        for candidate in candidates:
            self._session.add(candidate)
        await self._session.flush()

    async def create(self, name: str, work_name: str) -> VoteCandidate:
        candidate = VoteCandidate(name=name, work_name=work_name)
        self._session.add(candidate)
        await self._session.flush()
        return candidate

    async def delete_marked(self) -> None:
        marked = await self._session.execute(
            select(VoteCandidate.id).where(VoteCandidate.deleted.is_(True))
        )
        candidate_ids = list(marked.scalars().all())
        if candidate_ids:
            await self._session.execute(
                update(Vote).where(Vote.candidate_id.in_(candidate_ids)).values(
                    candidate_id=None
                )
            )
            await self._session.execute(
                delete(VoteCandidate).where(
                    VoteCandidate.id.in_(candidate_ids)
                )
            )

    async def get_one(self, candidate_id: int) -> VoteCandidate:
        result = await self._session.execute(
            select(VoteCandidate).where(VoteCandidate.id == candidate_id)
        )
        return result.scalar_one()

    async def update(
        self,
        candidate_id: int,
        name: str,
        work_name: str,
        deleted: bool = False,
    ) -> VoteCandidate:
        await self._session.execute(
            update(VoteCandidate)
            .where(VoteCandidate.id == candidate_id)
            .values(name=name, work_name=work_name, deleted=deleted)
        )
        result = await self._session.execute(
            select(VoteCandidate).where(VoteCandidate.id == candidate_id)
        )
        return result.scalar_one()
