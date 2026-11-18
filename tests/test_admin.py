from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin import repo
from app.admin.models import Admin
from app.admin.service import grant_admin
from app.auth.models import User
from app.auth.schemas import UserRegister
from app.auth.service import register_user
from app.auth.states import UserRole
from app.core.errors import ConflictError


@pytest.fixture
def session(client: TestClient) -> Iterator[Session]:
    # The client fixture rolls everything back after the test
    with client.app.state.session_factory() as session:  # type: ignore[attr-defined]
        yield session


def make_user(session: Session, student_id: str) -> User:
    return register_user(
        session,
        UserRegister(
            student_id=student_id,
            email=f"{student_id}@example.com",
            phone_number="0912345678",
            password="correct-horse-battery",
        ),
    )


def test_grant_admin_sets_the_role_and_adds_the_profile(session: Session) -> None:
    first = make_user(session, "admin0001")
    second = make_user(session, "admin0002")

    root = grant_admin(session, first, display_name="  Root Admin  ")
    granted = grant_admin(session, second, display_name="Ops", granted_by=first)

    assert first.role is UserRole.ADMIN
    assert second.role is UserRole.ADMIN
    assert root.display_name == "Root Admin"
    assert root.granted_by_id is None
    assert root.created_at is not None
    assert granted.granted_by_id == first.id

    session.expire_all()  # read back from the database, not the identity map
    profile = repo.get_by_user_id(session, second.id)
    assert profile is not None
    assert profile.user.student_id == "admin0002"
    assert profile.granted_by is not None
    assert profile.granted_by.student_id == "admin0001"


def test_a_user_has_at_most_one_admin_profile(session: Session) -> None:
    user = make_user(session, "admin0001")
    grant_admin(session, user, display_name="Root Admin")

    with pytest.raises(ConflictError):
        grant_admin(session, user, display_name="Again")

    # The database enforces it too, not only the service
    session.add(Admin(user_id=user.id, display_name="Duplicate"))
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_customers_have_no_admin_profile(session: Session) -> None:
    customer = make_user(session, "990000001")
    assert customer.role is UserRole.CUSTOMER
    assert repo.get_by_user_id(session, customer.id) is None


def test_deleting_users_keeps_the_table_consistent(session: Session) -> None:
    granter = make_user(session, "admin0001")
    grantee = make_user(session, "admin0002")
    grant_admin(session, granter, display_name="Root Admin")
    grant_admin(session, grantee, display_name="Ops", granted_by=granter)
    grantee_id = grantee.id

    # The granter's account goes away: the other admin keeps their profile
    session.execute(delete(User).where(User.id == granter.id))
    session.commit()
    session.expire_all()
    profile = repo.get_by_user_id(session, grantee_id)
    assert profile is not None
    assert profile.granted_by_id is None

    # The admin's own account goes away: the profile goes with it
    session.execute(delete(User).where(User.id == grantee_id))
    session.commit()
    assert session.scalar(select(Admin).where(Admin.user_id == grantee_id)) is None
