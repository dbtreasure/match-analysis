from pydantic import BaseModel, Field


class ScoringEvent(BaseModel):
    timestamp_seconds: int = Field(description="Time in seconds from start of video when scoring change occurred")
    athlete: str = Field(description="Name of athlete who scored or lost points")
    points_change: int = Field(description="Points gained (positive) or lost (negative). Use 0 for advantages.")
    advantages_change: int = Field(description="Advantages gained. Use 0 for point changes.")
    action: str = Field(description="Brief description of the action (e.g. 'Takedown', 'Sweep', 'Guard pass')")
    ibjjf_rule: str = Field(description="IBJJF rule reference (e.g. 'Art. 5, Item 10')")
    running_score: str = Field(description="Score after this event (e.g. '2-4' or '2-4 (3 adv)')")


class MatchAnalysis(BaseModel):
    athlete_1_name: str = Field(description="Full name of first athlete")
    athlete_1_gi_color: str = Field(description="Gi color of first athlete")
    athlete_2_name: str = Field(description="Full name of second athlete")
    athlete_2_gi_color: str = Field(description="Gi color of second athlete")
    events: list[ScoringEvent] = Field(description="List of all scoring changes in chronological order")
    final_score: str = Field(description="Final score (e.g. '4-16')")
    winner: str = Field(description="Name of the winner")


class AnalysisRun(BaseModel):
    model: str = Field(description="Gemini model used")
    media_resolution: str = Field(description="Media resolution setting")
    video_file: str = Field(description="Video file analyzed")
    prompt: str = Field(description="Prompt used for analysis")
    analysis: MatchAnalysis = Field(description="The match analysis result")
