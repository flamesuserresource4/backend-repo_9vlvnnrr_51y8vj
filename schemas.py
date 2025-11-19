"""
Database Schemas for Personalized Calendar App

Each Pydantic model represents a MongoDB collection. Collection name is the lowercase class name.
"""
from pydantic import BaseModel, Field
from typing import Optional, List

class CalendarPage(BaseModel):
    month: int = Field(..., ge=1, le=12, description="Month number 1-12")
    image_url: Optional[str] = Field(None, description="URL path to uploaded image for this month")
    note: Optional[str] = Field(None, description="Optional note shown on the page")

class Calendar(BaseModel):
    title: str = Field(..., description="Calendar title")
    year: int = Field(..., ge=1900, le=3000)
    start_month: int = Field(1, ge=1, le=12)
    style: str = Field("classic", description="Visual style key")
    pages: List[CalendarPage] = Field(default_factory=list, description="List of pages by month")
    owner: Optional[str] = Field(None, description="Optional owner identifier")
