from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base, Course, Prereq, PrereqType

DB_PATH = Path(__file__).parent / "data" / "courses.db"
DB_URL = f"sqlite:///{DB_PATH}"

_engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def _ensure_tables() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(_engine)


_ensure_tables()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="UCSD Prereq Graph API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/courses")
def list_courses(
    department: str | None = None,
    q: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Course)
    if department:
        stmt = stmt.where(Course.department == department.upper())
    if q:
        like = f"%{q.upper()}%"
        stmt = stmt.where((Course.code.like(like)) | (Course.title.like(like)))
    stmt = stmt.order_by(Course.code).limit(limit)
    return [c.to_dict() for c in db.scalars(stmt)]


@app.get("/api/courses/{code}")
def get_course(code: str, db: Session = Depends(get_db)) -> dict:
    course = db.get(Course, code.upper())
    if not course:
        raise HTTPException(status_code=404, detail=f"Course {code} not found")
    return course.to_dict()


@app.get("/api/courses/{code}/prereqs")
def get_prereqs(code: str, db: Session = Depends(get_db)) -> dict:
    code = code.upper()
    course = db.get(Course, code)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course {code} not found")
    edges = db.scalars(
        select(Prereq).where(Prereq.course_code == code).order_by(Prereq.group_id, Prereq.id)
    ).all()
    groups: dict[int, list[dict]] = {}
    for e in edges:
        groups.setdefault(e.group_id, []).append(
            {
                "required": e.required_course_code,
                "type": e.prereq_type.value,
            }
        )
    return {
        "code": course.code,
        "title": course.title,
        "raw_prereq_text": course.raw_prereq_text,
        "notes": course.notes,
        "groups": [{"group_id": gid, "members": members} for gid, members in sorted(groups.items())],
    }


@app.get("/api/courses/{code}/unlocks")
def get_unlocks(code: str, db: Session = Depends(get_db)) -> list[dict]:
    code = code.upper()
    rows = db.scalars(
        select(Prereq)
        .where(Prereq.required_course_code == code)
        .where(Prereq.prereq_type == PrereqType.AND)
        .order_by(Prereq.course_code)
    ).all()
    seen: set[str] = set()
    out: list[dict] = []
    for r in rows:
        if r.course_code in seen:
            continue
        seen.add(r.course_code)
        c = db.get(Course, r.course_code)
        if c:
            out.append({"code": c.code, "title": c.title, "department": c.department})
    return out


@app.get("/api/departments")
def list_departments(db: Session = Depends(get_db)) -> list[str]:
    rows = db.execute(select(Course.department).distinct().order_by(Course.department)).all()
    return [r[0] for r in rows]
