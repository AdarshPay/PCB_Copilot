"""Curated component profile models (20–30 parts target)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from pcb_ai_circuit_ir.models import Constraint, EvidenceRef, FunctionalClass, Pin


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ComponentProfile(Model):
    manufacturer: str
    orderable_mpn: str
    functional_class: FunctionalClass
    symbol_ref: str
    footprint_ref: str
    pins: list[Pin] = Field(default_factory=list)
    absolute_maximum: list[Constraint] = Field(default_factory=list)
    recommended_operating: list[Constraint] = Field(default_factory=list)
    supply_domains: list[str] = Field(default_factory=list)
    required_support_components: list[str] = Field(default_factory=list)
    recommended_support_components: list[str] = Field(default_factory=list)
    boot_reset_config: list[str] = Field(default_factory=list)
    interface_characteristics: dict[str, str] = Field(default_factory=dict)
    approved_reference_circuits: list[str] = Field(default_factory=list)
    simulation_model_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)


__all__ = ["ComponentProfile"]
