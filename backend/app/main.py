from __future__ import annotations

import asyncio
from datetime import date
from io import BytesIO
import logging
from typing import Annotated


from fastapi import Depends, File, UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl,Field
from app.matching import calculate_match, extract_skills

from app.config import settings
from app.auth import get_current_user, router as auth_router
from app.database import SessionLocal
from app.models import JobRecord, ResumeUploadLimit, User


logger = logging.getLogger(__name__)
MAX_RESUME_UPLOADS_PER_DAY = 3


def html_to_text(value: str) -> str:
    return BeautifulSoup(value, "html.parser").get_text(
        " ",
        strip=True,
    )


def cache_jobs(jobs: list[Job]) -> None:
    try:
        with SessionLocal() as session:
            for job in jobs:
                statement = insert(JobRecord).values(
                    provider="searchapi",
                    provider_job_id=job.id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    description=job.description,
                    apply_url=str(job.apply_url),
                )

                statement = statement.on_conflict_do_update(
                    constraint="uq_jobs_provider_job_id",
                    set_={
                        "title": statement.excluded.title,
                        "company": statement.excluded.company,
                        "location": statement.excluded.location,
                        "description": statement.excluded.description,
                        "apply_url": statement.excluded.apply_url,
                        "fetched_at": statement.excluded.fetched_at,
                    },
                )

                session.execute(statement)

            session.commit()

    except SQLAlchemyError:
        logger.exception("Unable to cache live job results")


def record_resume_upload(user_id: int) -> bool:
    today = date.today()

    with SessionLocal() as session:
        statement = insert(ResumeUploadLimit).values(
            user_id=user_id,
            upload_date=today,
            upload_count=1,
        )

        statement = statement.on_conflict_do_update(
            constraint="uq_resume_upload_user_date",
            set_={
                "upload_count": ResumeUploadLimit.upload_count + 1,
            },
            where=(
                ResumeUploadLimit.upload_count
                < MAX_RESUME_UPLOADS_PER_DAY
            ),
        ).returning(ResumeUploadLimit.upload_count)

        updated_count = session.execute(statement).scalar_one_or_none()
        session.commit()

    return updated_count is not None


class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str
    description: str
    apply_url: HttpUrl

class MatchRequest(BaseModel):
    resume_text:str=Field(
        min_length=20,
        max_length=50_000
    )
    job_description:str=Field(
        min_length=10,
        max_length=50_000,
    )

class MatchResult(BaseModel):
    match_score:int
    matching_skills: list[str]
    missing_skills:list[str]


class ResumeResult(BaseModel):
    text: str
    skills: list[str]

app = FastAPI(
    title="JobMatch",
    version="0.3.0",
)

app.include_router(auth_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


async def fetch_searchapi_results(
    keyword: str,
    location: str,
) -> dict:
    parameters = {
        "engine": "google_jobs",
        "q": keyword,
        "location": location,
        "gl": "in",
        "hl": "en",
        "api_key": settings.searchapi_api_key,
    }

    timeout = httpx.Timeout(
        connect=10.0,
        read=30.0,
        write=10.0,
        pool=10.0,
    )

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                "https://www.searchapi.io/api/v1/search",
                params=parameters,
            )
            response.raise_for_status()
            provider_data = response.json()

            if provider_data.get("error"):
                raise HTTPException(
                    status_code=502,
                    detail=provider_data["error"],
                )

            return provider_data

    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "provider_status": error.response.status_code,
                "provider_message": error.response.text[:500],
            },
        ) from error

    except httpx.TimeoutException as error:
        raise HTTPException(
            status_code=504,
            detail="A connection to SearchApi timed out.",
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not connect to SearchApi: "
                f"{type(error).__name__}"
            ),
        ) from error


@app.get("/api/jobs", response_model=list[Job])
async def search_jobs(
    _current_user: Annotated[User, Depends(get_current_user)],
    keyword: str = Query(
        default="software developer",
        max_length=100,
    ),
    location: str = Query(
        default="India",
        max_length=100,
    ),
):
    clean_keyword = keyword.strip() or "software developer"
    clean_location = location.strip() or "India"

    if "india" not in clean_location.lower():
        clean_location = f"{clean_location}, India"

    provider_data = await fetch_searchapi_results(
        clean_keyword,
        clean_location,
    )

    jobs: list[Job] = []

    for item in provider_data.get("jobs", []):
        apply_url = item.get("apply_link") or item.get("sharing_link")

        if not apply_url:
            continue

        jobs.append(
            Job(
                id=str(item.get("id") or apply_url),
                title=item.get(
                    "title",
                    "Untitled job",
                ),
                company=item.get(
                    "company_name",
                    "Company not listed",
                ),
                location=item.get(
                    "location",
                    clean_location,
                ),
                description=html_to_text(
                    item.get("description")
                    or "No description provided."
                ),
                apply_url=apply_url,
            )
        )

    await asyncio.to_thread(cache_jobs, jobs)

    return jobs
@app.post("/api/match",response_model=MatchResult)
def match_resume_to_job(
    request: MatchRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
):
    result=calculate_match(
        resume_text=request.resume_text,
        job_description=request.job_description,
    )

    return MatchResult(**result)

@app.post(
    "/api/resume/extract",
    response_model=ResumeResult,
)
async def extract_resume(
    current_user: Annotated[User, Depends(get_current_user)],
    resume: UploadFile = File(...),
):
    if resume.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF resumes are accepted.",
        )

    maximum_size = 5 * 1024 * 1024
    file_data = await resume.read(maximum_size + 1)

    if len(file_data) > maximum_size:
        raise HTTPException(
            status_code=413,
            detail="The PDF must be 5 MB or smaller.",
        )

    try:
        reader = PdfReader(BytesIO(file_data))

        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Password-protected PDFs are not supported.",
            )

        extracted_text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        ).strip()

    except PdfReadError as error:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        ) from error

    if len(extracted_text) < 20:
        raise HTTPException(
            status_code=422,
            detail=(
                "No readable text was found. "
                "The PDF may be a scanned image."
            ),
        )

    upload_allowed = await asyncio.to_thread(
        record_resume_upload,
        current_user.id,
    )

    if not upload_allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                "Daily resume upload limit reached. "
                "You can upload up to 3 PDFs per day."
            ),
            headers={"Retry-After": "86400"},
        )

    return ResumeResult(
        text=extracted_text,
        skills=sorted(extract_skills(extracted_text)),
    )
