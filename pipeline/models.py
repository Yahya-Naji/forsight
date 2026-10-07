"""Pydantic contracts — the SYMBOLIC layer's schema.
The LLM extractor must emit objects that validate against these,
or the output is rejected. Mirrors supabase/migrations 001-002."""
from typing import Literal, Optional
from pydantic import BaseModel, Field

Pillar = Literal["CYBERSECURITY", "AI", "ELECTRONIC_WARFARE", "PROCUREMENT"]
EnvLayer = Literal["UAE", "REGIONAL", "GLOBAL"]
EvidenceClass = Literal["A", "B", "C", "D"]
Confidence = Literal["LOW", "MEDIUM", "MEDIUM_HIGH", "HIGH"]
Steep = Literal["Social", "Technological", "Economic", "Environmental", "Political"]

# Per-pillar entity-type catalogs (extraction may only use these)
ENTITY_TYPES: dict[str, list[str]] = {
    "CYBERSECURITY": ["threat_actor", "cyber_threat", "attack_surface", "defence_system",
                      "control", "standard", "supplier_dependency", "cyber_incident",
                      "uae_sector", "mission_assurance_requirement"],
    "AI": ["ai_capability", "ai_model", "dataset_asset", "tevv_gate",
           "human_control_boundary", "adversarial_threat", "compute_dependency"],
    "ELECTRONIC_WARFARE": ["spectrum_band", "ew_capability", "emitter_profile",
                           "link_dependence", "pnt_mode", "reprogramming_right",
                           "deconfliction_constraint"],
    "PROCUREMENT": ["acquisition_mechanism", "contract_right", "sovereignty_assessment",
                    "industrial_capability", "refresh_cycle", "export_control_constraint",
                    "localisation_program"],
}

class EvidenceCandidate(BaseModel):
    """What the extractor emits for each claim found in a document."""
    claim: str = Field(min_length=20, max_length=500)
    env_layer: EnvLayer
    steep: list[Steep] = Field(min_length=1)
    pillar: Pillar
    topic_id: str                      # must exist in topics table (checked in extract.py)
    question_id: Optional[str] = None
    quote_span: str = Field(min_length=10, max_length=400,
                            description="verbatim words from the document supporting the claim")
    ew_hook: str = Field(default="", max_length=200,
                         description="verbatim words inside quote_span that tie the claim "
                                     "to the topic's EW functions; checked in extract.py")
    # NOTE: class + confidence are NOT here on purpose — the rules engine assigns them.

class AttrPair(BaseModel):
    """One entity attribute.

    A free-form `dict` cannot be expressed in a strict JSON Schema — structured
    outputs require `additionalProperties: false` on every object — so entity
    attributes travel as typed key/value pairs and are folded into jsonb on
    insert.
    """
    key: str
    value: str


class EntityCandidate(BaseModel):
    pillar: Pillar
    entity_type: str
    name: str
    attrs: list[AttrPair] = []

    def attrs_dict(self) -> dict:
        return {a.key: a.value for a in self.attrs}

class ExtractionResult(BaseModel):
    evidence: list[EvidenceCandidate] = []
    entities: list[EntityCandidate] = []
