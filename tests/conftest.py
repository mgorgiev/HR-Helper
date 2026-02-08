import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.deps import get_db, get_file_storage
from app.main import create_app
from app.models import Base
from app.storage.local import LocalFileStorage

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://hr_helper:hr_helper_dev@localhost:5432/hr_helper_test",
)

SAMPLE_DATA_DIR = Path(__file__).parent.parent / "sample_data" / "resumes"


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """Provide a transactional session that rolls back after each test."""
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(loop_scope="session")
async def client(db_session, tmp_path) -> AsyncGenerator[AsyncClient]:
    app = create_app()

    # Override DB dependency — yield the test session directly, no commit/rollback
    async def _override_get_db():
        yield db_session

    # Override file storage dependency to use temp directory
    storage = LocalFileStorage(str(tmp_path / "uploads"))

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_file_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", follow_redirects=True
    ) as ac:
        yield ac


@pytest.fixture
def tmp_upload_dir(tmp_path) -> Path:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


@pytest.fixture(scope="session")
def sample_pdf() -> Path:
    return SAMPLE_DATA_DIR / "sample_resume.pdf"


@pytest.fixture(scope="session")
def sample_docx() -> Path:
    return SAMPLE_DATA_DIR / "sample_resume.docx"


@pytest.fixture(scope="session")
def sample_txt() -> Path:
    return SAMPLE_DATA_DIR / "sample_resume.txt"


def make_candidate_payload(**overrides):
    """Helper to create a valid candidate payload with unique email."""
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": f"john.doe.{uuid.uuid4().hex[:8]}@example.com",
        "phone": "+1234567890",
        "status": "new",
    }
    data.update(overrides)
    return data


def make_job_payload(**overrides):
    """Helper to create a valid job payload."""
    data = {
        "title": "Software Engineer",
        "department": "Engineering",
        "description": "Build great software",
        "requirements": "Python, FastAPI, SQL",
        "location": "Remote",
        "employment_type": "full_time",
        "is_active": True,
    }
    data.update(overrides)
    return data
