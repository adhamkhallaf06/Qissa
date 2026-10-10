from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

HEX_COLOR = r"^#[0-9a-fA-F]{6}$"


class CaptionOptions(BaseModel):
    """How subtitles are generated and drawn. Defaults match the original look."""

    enabled: bool = True

    # --- Transcription ---
    language: Optional[str] = "ar"  # None = let Whisper detect it
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


class PipelineOptions(BaseModel):
    """Which processing steps run and how."""

    clip_seconds: int = Field(60, ge=5, le=180)
    vertical: bool = True  # pad horizontal clips to 1080x1920
    remove_silent: bool = True
    max_silence_seconds: float = Field(5.0, ge=0)
    captions: CaptionOptions = Field(default_factory=CaptionOptions)
