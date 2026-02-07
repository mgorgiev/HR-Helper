import asyncio
import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_db, get_file_storage
from app.main import create_app
from app.models import Base
from app.storage.local import LocalFileStorage

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://hr_helper:hr_helper_dev@localhost:5432/hr_helper_test",
)

SAMPLE_DATA_DIR = Path(__file__).parent.parent / "sample_data" / "resumes"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession]:
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session, tmp_path) -> AsyncGenerator[AsyncClient]:
    app = create_app()

    # Override DB dependency
    async def _override_get_db():
        yield db_session

    # Override file storage dependency to use temp directory
    storage = LocalFileStorage(str(tmp_path / "uploads"))

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_file_storage] = lambda: storage

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
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
