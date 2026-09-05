from __future__ import annotations
from enum import Enum

class Audience(str, Enum):
    executive = "executive"
    technical = "technical"
    public    = "public"
    field     = "field"

class Tone(str, Enum):
    neutral = "neutral"
    formal  = "formal"
    urgent  = "urgent"
    plain   = "plain"

class Language(str, Enum):
    en = "en"
    hi = "hi"
    ta = "ta"

class DetailLevel(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"

class Objective(str, Enum):
    inform   = "inform"
    warn     = "warn"
    persuade = "persuade"
    instruct = "instruct"

class ContentStyle(str, Enum):
    narrative  = "narrative"
    bulleted   = "bulleted"
    analytical = "analytical"

class OutputFormat(str, Enum):
    advisory          = "advisory"
    executive_summary = "executive_summary"
    presentation      = "presentation"
    linkedin          = "linkedin"
    twitter_x         = "twitter_x"
    infographic       = "infographic"
    video_package     = "video_package"
