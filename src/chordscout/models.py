"""Data models for chord progression segments, analysis results, and project files."""

from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


def format_timestamp(seconds: float, include_ms: bool = False) -> str:
    """Format seconds into MM:SS or MM:SS.ms string."""
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    secs = seconds % 60
    if include_ms:
        return f"{minutes:02d}:{secs:04.1f}"
    return f"{minutes:02d}:{int(secs):02d}"


@dataclass
class ChordSegment:
    """Represents a time-bounded chord segment."""

    start_time: float
    end_time: float
    chord: str
    confidence: float = 1.0
    is_user_edited: bool = False

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    @property
    def formatted_start(self) -> str:
        return format_timestamp(self.start_time, include_ms=True)

    @property
    def formatted_end(self) -> str:
        return format_timestamp(self.end_time, include_ms=True)

    @property
    def time_range_str(self) -> str:
        return f"{self.formatted_start} - {self.formatted_end}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "chord": self.chord,
            "confidence": round(self.confidence, 3),
            "is_user_edited": self.is_user_edited,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChordSegment:
        return cls(
            start_time=float(data["start_time"]),
            end_time=float(data["end_time"]),
            chord=str(data["chord"]),
            confidence=float(data.get("confidence", 1.0)),
            is_user_edited=bool(data.get("is_user_edited", False)),
        )


@dataclass
class AnalysisMetadata:
    """Metadata regarding the analyzed song file."""

    file_path: str
    file_name: str
    duration: float
    sample_rate: int
    tempo_bpm: Optional[float] = None
    key_estimate: Optional[str] = None
    tuning_offset_cents: float = 0.0
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisMetadata:
        return cls(**data)


@dataclass
class AnalysisResult:
    """Complete analysis outcome for a song."""

    metadata: AnalysisMetadata
    segments: list[ChordSegment] = field(default_factory=list)
    disclaimer: str = (
        "Initial algorithmic analysis -- verify against your ear. Complex jazz "
        "voicings, altered tunings, and dense mixes may require user adjustment."
    )

    def get_chord_at_time(self, time_sec: float) -> Optional[ChordSegment]:
        for seg in self.segments:
            if seg.start_time <= time_sec < seg.end_time:
                return seg
        if self.segments and time_sec >= self.segments[-1].start_time:
            return self.segments[-1]
        return None

    def unique_chords(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for seg in self.segments:
            if seg.chord and seg.chord != "N" and seg.chord not in seen:
                seen.add(seg.chord)
                result.append(seg.chord)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "metadata": self.metadata.to_dict(),
            "disclaimer": self.disclaimer,
            "segments": [seg.to_dict() for seg in self.segments],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisResult:
        meta = AnalysisMetadata.from_dict(data["metadata"])
        segments = [ChordSegment.from_dict(s) for s in data.get("segments", [])]
        disclaimer = data.get("disclaimer", "")
        return cls(metadata=meta, segments=segments, disclaimer=disclaimer)
