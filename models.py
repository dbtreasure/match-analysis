from typing import Literal

from pydantic import BaseModel, Field


class AthleteDescription(BaseModel):
    scoreboard_side: Literal["left", "right"] = Field(description="Which side of scoreboard overlay")
    athlete_number: Literal["1", "2"] = Field(description="1 for left, 2 for right")
    name: str = Field(description="Name as shown on scoreboard")
    gi_color: str = Field(description="Gi color: white, blue, or other")
    belt_indicator: str | None = Field(default=None, description="If same gi colors, belt tip color (yellow/green coral) to distinguish")
    physical_description: str = Field(description="Brief description: build, hair, distinguishing features")


class AthleteIdentification(BaseModel):
    athlete_1: AthleteDescription = Field(description="Athlete on LEFT side of scoreboard")
    athlete_2: AthleteDescription = Field(description="Athlete on RIGHT side of scoreboard")
    same_gi_color: bool = Field(description="True if both athletes wear same color gi")
    distinguishing_feature: str = Field(description="Primary way to tell athletes apart during match")


class ScoringEvent(BaseModel):
    timestamp_seconds: int = Field(description="Time in seconds from start of video when scoring change occurred")
    match_clock: str = Field(description="Time shown on match clock when event occurred (e.g. '8:45')")
    athlete: Literal["1", "2"] = Field(description="Which athlete scored: '1' for athlete on LEFT side of scoreboard, '2' for athlete on RIGHT side")
    points_change: int = Field(description="Points gained (positive) or lost (negative). Use 0 for advantages/penalties.")
    advantages_change: int = Field(description="Advantages gained (positive) or lost (negative). Use 0 for point/penalty changes.")
    penalties_change: int = Field(description="Penalties received (positive). Use 0 for point/advantage changes.")
    action: str = Field(description="Brief description of the action (e.g. 'Takedown', 'Sweep', 'Guard pass')")
    ibjjf_rule: str = Field(description="IBJJF rule reference (e.g. 'Art. 5, Item 10')")
    running_score: str = Field(description="Running points score after this event as 'athlete1-athlete2' (e.g. '2-4')")
    running_advantages: str = Field(description="Running advantages after this event as 'athlete1-athlete2' (e.g. '1-0')")
    running_penalties: str = Field(description="Running penalties after this event as 'athlete1-athlete2' (e.g. '0-1')")


class MatchAnalysis(BaseModel):
    athlete_1_name: str = Field(description="Full name of athlete 1 (LEFT side of scoreboard)")
    athlete_1_gi_color: str = Field(description="Gi color of athlete 1")
    athlete_2_name: str = Field(description="Full name of athlete 2 (RIGHT side of scoreboard)")
    athlete_2_gi_color: str = Field(description="Gi color of athlete 2")
    events: list[ScoringEvent] = Field(description="List of all scoring changes in chronological order")
    final_score: str = Field(description="Final score as 'athlete1-athlete2' (e.g. '4-16')")
    winner: Literal["0", "1", "2"] = Field(description="Winner: '1' for athlete 1, '2' for athlete 2, '0' for draw")


class AnalysisRun(BaseModel):
    model: str = Field(description="Gemini model used")
    media_resolution: str = Field(description="Media resolution setting")
    video_file: str = Field(description="Video file analyzed")
    prompt: str = Field(description="Prompt used for analysis")
    analysis: MatchAnalysis = Field(description="The match analysis result")
