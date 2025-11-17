"""
Database Schemas for Islamic Habit Tracker

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercase form of the class name (e.g., Habit -> "habit").
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date


class Habit(BaseModel):
    """
    Habits a user wants to track.
    Collection: "habit"
    """
    title: str = Field(..., description="Habit title, e.g., Fajr, Quran lesen")
    description: Optional[str] = Field(None, description="Short description")
    category: Optional[Literal[
        "gebet",
        "quran",
        "dhikr",
        "spenden",
        "wissen",
        "gesundheit",
        "sonstiges",
    ]] = Field("sonstiges", description="Habit category")
    frequency: Literal["daily", "weekly"] = Field(
        "daily", description="How often this habit is intended"
    )
    goal_per_period: int = Field(1, ge=1, le=1000, description="Target count per period")
    color: Optional[str] = Field(
        None,
        description="Optional color hex for UI cards (e.g., #16a34a)",
    )


class HabitEntry(BaseModel):
    """
    Completion records for a habit per day (or date within week).
    Collection: "habitentry"
    """
    habit_id: str = Field(..., description="Reference to Habit _id as string")
    entry_date: date = Field(..., description="Date of the entry (YYYY-MM-DD)")
    completed: bool = Field(True, description="Whether completed for this date")
    notes: Optional[str] = Field(None, description="Optional notes")
