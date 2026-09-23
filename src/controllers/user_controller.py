from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select, update

from src.controllers.file_controller import FileController, FileControllerDep
from src.db import Session
from src.routers.files.models import File
from src.routers.user.models import ReportForm, User, UserRole
from src.routers.user.schemas import UserForm


@dataclass
class UserNew:
    email: str
    hashed_password: str
    role: UserRole = UserRole.basic


@dataclass
class UserFilter:
    id: int | None = None
    email: str | None = None


class UserRepo:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user_new: UserNew) -> User:
        user = User(
            email=user_new.email,
            password=user_new.hashed_password,
            role=user_new.role,
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return User.model_validate(user)

    async def get_one(self, user_filter: UserFilter) -> User:
        stmt = select(User)
        if user_filter.id is not None:
            stmt = stmt.where(User.id == user_filter.id)
        if user_filter.email is not None:
            stmt = stmt.where(User.email == user_filter.email)
        result = await self._session.execute(stmt)
        user = result.scalar_one()
        return User.model_validate(user)

    async def get(self) -> list[User]:
        stmt = select(User)
        result = await self._session.execute(stmt)
        return [User.model_validate(user) for user in result.scalars().all()]

    async def update(self, user: User) -> User:
        stmt = (
            update(User).where(user.id == User.id).values(**user.model_dump())
        )
        await self._session.execute(stmt)
        return await self.get_one(UserFilter(id=user.id))

    async def delete(self, id: int):
        stmt = delete(User).where(User.id == id)
        await self._session.execute(stmt)


class UserController:
    def __init__(self, session: AsyncSession, file_controller: FileController):
        self._user_repo = UserRepo(session)
        self._file_controller = file_controller

    async def create(self, user_new: UserNew) -> User:
        return await self._user_repo.create(user_new)

    async def get_one(self, user_filter: UserFilter) -> User:
        user = await self.get_one_or_none(user_filter)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return user

    async def get_one_or_none(self, user_filter: UserFilter) -> User | None:
        try:
            return await self._user_repo.get_one(user_filter)
        except NoResultFound:
            return None

    async def get(self) -> list[User]:
        return await self._user_repo.get()

    async def update(self, user: User) -> User:
        return await self._user_repo.update(user)

    async def delete(self, id: int) -> User:
        user, file = await self.get_user_with_file(UserFilter(id=id))
        if user.role == UserRole.admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        if file is not None:
            await self._file_controller.delete(file.id)
        await self._user_repo.delete(id)
        return user

    async def get_user_file_or_none(self, user: User) -> File | None:
        if user.form and user.form.file_id is not None:
            return await self._file_controller.get_one_or_none(
                user.form.file_id
            )
        return None

    async def get_user_file(self, user: User) -> File:
        file = await self.get_user_file_or_none(user)
        if file is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        return file

    async def get_user_with_file(
        self, user_filter: UserFilter
    ) -> tuple[User, File | None]:
        user = await self.get_one(user_filter)
        file = await self.get_user_file_or_none(user)
        return user, file

    async def get_file(self, user: User, id: int) -> File:
        if user.role == UserRole.admin:
            return await self._file_controller.get_one(id)
        file = await self.get_user_file(user)
        if file.id != id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return file

    async def update_from_user_form(
        self,
        user_id: int,
        form: UserForm,
    ) -> tuple[User, File | None]:
        user = await self.get_one(UserFilter(id=user_id))
        report_form, file = await self.update_report_form(user, form)
        user = user.model_copy(
            update={
                "email": form.email,
                "role": form.role,
                "surname": form.surname,
                "name": form.name,
                "patronymic": form.patronymic,
                "organization": form.organization,
                "year": form.year,
                "contact": form.contact,
                "form": report_form,
            }
        )
        user = await self._user_repo.update(user)
        return user, file

    async def update_report_form(
        self, user: User, form: UserForm
    ) -> tuple[ReportForm | None, File | None]:
        file = await self.get_user_file_or_none(user)
        if form.role != UserRole.participant:
            if file is not None:
                await self._file_controller.delete(file.id)
            return None, None

        if form.report_file is not None and form.report_file.filename:
            if file is not None:
                await self._file_controller.delete(file.id)
            content = await form.report_file.read()
            file = File(
                name=form.report_file.filename,
                type=form.report_file.content_type,
                content=content,
            )
            file = await self._file_controller.create(file)

        report_form = ReportForm(
            form_type=form.form_type,
            report_name=form.report_name,
            report_type=form.report_type,
            flag_bio_phys=form.flag_bio_phys,
            flag_comp_sci=form.flag_comp_sci,
            flag_math_phys=form.flag_math_phys,
            flag_med_phys=form.flag_med_phys,
            flag_nano_tech=form.flag_nano_tech,
            flag_general_phys=form.flag_general_phys,
            flag_solid_body=form.flag_solid_body,
            flag_space_phys=form.flag_space_phys,
            file_id=file.id if file is not None else None,
        )

        return report_form, file


def get_user_controller(
    session: Session, file_controller: FileControllerDep
) -> UserController:
    return UserController(session, file_controller)


UserControllerDep = Annotated[UserController, Depends(get_user_controller)]
