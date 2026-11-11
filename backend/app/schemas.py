from datetime import date
from typing import List, Literal, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class CaptionOptions(BaseModel):
    """How subtitles are generated and drawn. Defaults match the original look."""

    enabled: bool = True

    # --- Transcription ---
    language: Optional[str] = None  # None = let Whisper detect it
    model: Literal["tiny", "base", "small", "medium", "large"] = "base"
    max_words: Optional[int] = Field(None, ge=1, le=20)  # words per caption; None = full sentence

    # --- Text ---
    font_name: str = "Arial Unicode MS"
    font_size: int = Field(12, ge=4, le=72)
    bold: bool = False
    italic: bool = False
    uppercase: bool = False

    # --- Colors (#RRGGBB) ---
    colors: List[str] = Field(default=["#FFFF00", "#FF7F00", "#FFFFFF"], min_length=1)  # cycled per caption
    outline_color: str = Field("#000000", pattern=HEX_COLOR)
    outline_width: float = Field(2, ge=0, le=10)
    shadow: float = Field(0, ge=0, le=10)
    background: bool = False  # solid box behind the text
    background_color: str = Field("#000000", pattern=HEX_COLOR)

    # --- Placement ---
    position: Literal["top", "middle", "bottom"] = "bottom"
    margin_v: int = Field(80, ge=0, le=250)

    @field_validator("colors")
    @classmethod
    def _check_colors(cls, colors):
        import re
        for color in colors:
            if not re.match(HEX_COLOR, color):
                raise ValueError(f"'{color}' is not a #RRGGBB color")
        return colors

    @field_validator("font_name")
    @classmethod
    def _clean_font(cls, name):
        # Commas would break the ASS style line
        return name.replace(",", " ").strip() or "Arial Unicode MS"


class ScheduleOptions(BaseModel):
    """When clips go public. One clip per time slot, rolling over to the next day."""

    enabled: bool = True  # False = publish as soon as the upload finishes
    timezone: str = "UTC"  # the web UI fills in the browser's timezone
    start_date: Optional[date] = None  # None = tomorrow
    time_slots: List[str] = Field(default_factory=list)  # HH:MM; at least one is needed to schedule

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, name):
        try:
            ZoneInfo(name)
        except Exception:
            raise ValueError(f"'{name}' is not a known timezone")
        return name

    @field_validator("time_slots")
    @classmethod
    def _check_slots(cls, slots):
        import re
        for slot in slots:
            if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", slot):
                raise ValueError(f"'{slot}' is not a HH:MM time")
        return slots


class UploadOptions(BaseModel):
    """What gets sent to YouTube with each clip."""

    enabled: bool = True
    title: str = ""
    description: str = ""
    hashtags: List[str] = Field(default_factory=list)
    hashtags_in_title: bool = True
    number_clips: bool = False  # append "Part N" when a video yields several clips
    category_id: str = "22"
    privacy: Literal["private", "unlisted", "public"] = "private"  # used when not scheduled
    schedule: ScheduleOptions = Field(default_factory=ScheduleOptions)
    delete_after_upload: bool = True

    @field_validator("hashtags")
    @classmethod
    def _clean_hashtags(cls, hashtags):
        cleaned = []
        for tag in hashtags:
            tag = "".join(tag.split()).lstrip("#")
            if tag and f"#{tag}" not in cleaned:
                cleaned.append(f"#{tag}")
        return cleaned


class GradingOptions(BaseModel):
    """Score each clip with Claude and upload only the best ones."""

    enabled: bool = False  # needs an Anthropic API key
    top_n: int = Field(3, ge=1, le=100)  # how many of the best clips to upload


class PipelineOptions(BaseModel):
    """Which processing steps run and how."""

    clip_seconds: int = Field(60, ge=5, le=180)
    vertical: bool = True  # pad horizontal clips to 1080x1920
    remove_silent: bool = True
    max_silence_seconds: float = Field(5.0, ge=0)
    captions: CaptionOptions = Field(default_factory=CaptionOptions)
    grading: GradingOptions = Field(default_factory=GradingOptions)
    upload: UploadOptions = Field(default_factory=UploadOptions)
