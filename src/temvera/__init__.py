"""Temporal, provenance-aware memory research primitives."""

from .decay import (
    DecayCandidate,
    DecayCase,
    DecayResult,
    decay_smoke_cases,
    evaluate_decay,
)
from .generator import generate_histories, generate_lifecycle_suite
from .index import HashingVectorIndex, LexicalIndex
from .model import Authority, Belief, MemoryEvent, Operation
from .oracle import LifecycleOracle
from .protected_store import ProtectedEventStore
from .retrieval import MemoryPacket, MemoryPacketItem, build_packet
from .sqlite_oracle import SqliteBitemporalOracle
from .store import GitTransactionAdapter, JsonlEventStore

__all__ = [
    "Authority",
    "Belief",
    "DecayCandidate",
    "DecayCase",
    "DecayResult",
    "LifecycleOracle",
    "LexicalIndex",
    "MemoryEvent",
    "MemoryPacket",
    "MemoryPacketItem",
    "Operation",
    "ProtectedEventStore",
    "SqliteBitemporalOracle",
    "GitTransactionAdapter",
    "HashingVectorIndex",
    "JsonlEventStore",
    "generate_histories",
    "generate_lifecycle_suite",
    "build_packet",
    "decay_smoke_cases",
    "evaluate_decay",
]

__version__ = "0.0.1"
