#!/usr/bin/env python3
"""
SAT Question Generator — FastAPI backend
Run locally:  uvicorn main:app --reload
Deploy:       Railway / Render / any VPS with Python 3.10+
"""
from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import sat_question_generator as sat

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SAT Question Generator API",
    version="1.0.0",
    description="Generate SAT-style practice questions with difficulty scoring.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production if needed
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Serve the static frontend from /static
app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Response schemas (Pydantic mirrors the dataclass)
# ---------------------------------------------------------------------------
class QuestionOut(BaseModel):
    question_id: int
    section: str
    skill: str
    prompt: str
    choices: dict[str, str]
    correct_answer: str
    explanation: str
    difficulty_score: int
    difficulty_label: str


class GenerateResponse(BaseModel):
    count: int
    section: str
    order: str
    questions: List[QuestionOut]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root():
    """Serve the HTML frontend."""
    return FileResponse("static/index.html")


@app.get("/api/questions", response_model=GenerateResponse, summary="Generate SAT questions")
def generate_questions(
    count: int = Query(default=5, ge=1, le=30, description="Number of questions (1–30)"),
    section: Literal["mixed", "math", "verbal"] = Query(default="mixed"),
    order: Literal["hardest", "easiest"] = Query(default="hardest"),
    seed: Optional[int] = Query(default=None, description="Optional seed for reproducibility"),
):
    """
    Generate *count* SAT-style questions for the given *section*, ranked by
    difficulty in the requested *order*.
    """
    try:
        generator = sat.SATQuestionGenerator(seed=seed)
        questions = generator.generate(count=count, section=section)
        ranked = sat.rank_questions(questions, order=order)
        return GenerateResponse(
            count=len(ranked),
            section=section,
            order=order,
            questions=[QuestionOut(**q.to_dict()) for q in ranked],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/health", summary="Health check")
def health():
    return {"status": "ok"}
