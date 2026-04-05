from typing import List, Optional
from pydantic import BaseModel, Field

class Defect(BaseModel):
    location: str = Field(..., description="Specific location of the defect")
    description: str = Field(..., description="Technical description of the defect")
    rics_reference: Optional[str] = Field(None, description="Reference to RICS standards or section")
    risk_rating: int = Field(..., ge=1, le=3, description="RICS Condition Rating (1, 2, or 3)")
    remedial_action: str = Field(..., description="Recommended repair or further investigation")

class ForensicAnalysisResult(BaseModel):
    defects: List[Defect]
    general_observation: Optional[str] = Field(None, description="General summary of the inspected area")
    
    # Metadata for the pipeline to use later
    processed_model: str = "gemini-3-flash-preview"
