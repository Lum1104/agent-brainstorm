# schemas.py
# This file contains the Pydantic models for structured data validation.

from typing import List
from pydantic import BaseModel, Field

class Persona(BaseModel):
    """A single expert persona for brainstorming."""
    role: str = Field(description="The professional role of the persona.")
    goal: str = Field(description="The primary objective of this persona in the brainstorming session.")
    backstory: str = Field(description="A brief history of the persona's experience and perspective.")

class PersonaList(BaseModel):
    """A list of expert personas."""
    personas: List[Persona]

class TopIdea(BaseModel):
    """Represents a single top idea selected from the brainstorming session."""
    title: str = Field(description="The concise title of the idea.")
    description: str = Field(description="A detailed description of the idea.")

class TopIdeasList(BaseModel):
    """A list of the top 3 ideas after evaluation."""
    top_ideas: List[TopIdea]
