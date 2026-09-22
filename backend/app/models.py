from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobRecord(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_job_id",
            name="uq_jobs_provider_job_id",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(
        String(50),
        default="searchapi",
    )
    provider_job_id: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(300), index=True)
    company: Mapped[str] = mapped_column(String(300), index=True)
    location: Mapped[str] = mapped_column(String(300), index=True)
    description: Mapped[str] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ResumeUploadLimit(Base):
    __tablename__ = "resume_upload_limits"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "upload_date",
            name="uq_resume_upload_user_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            name="fk_resume_upload_limits_user_id_users",
            ondelete="CASCADE",
        ),
        index=True,
    )
    upload_date: Mapped[date] = mapped_column(Date)
    upload_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )
