"""
generation/generator.py — One generated output per call.
Input: ContentPlan + canonical_text of cited facts (NEVER raw source).
Output: GeneratedOutput with Claim objects carrying fact_ids.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from app.core.schemas import (
    SourceOfTruth, ContentPlan, GeneratedOutput,
    GeneratedSection, Claim,
)
from app.core.ids import generate_claim_id
from app.generation.llm import call as llm_call
from app.security.spotlight import build_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)

_CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_key": {"type": "string"},
                    "claims": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "claim_id": {"type": "string"},
                                "text": {"type": "string"},
                                "fact_ids": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["claim_id", "text", "fact_ids"],
                        }
                    },
                    "raw_text": {"type": "string"},
                },
                "required": ["section_key", "claims"],
            }
        }
    },
    "required": ["sections"],
}


def generate(
    plan: ContentPlan,
    sot: SourceOfTruth,
    model: str | None = None,
) -> GeneratedOutput:
    """Generate one output constrained strictly to the locked SoT."""
    sot_map = {f.fact_id: f for f in sot.facts}

    # Build source context from only the cited facts (never raw source text)
    context_parts = []
    for section in plan.sections:
        for fid in section.fact_ids:
            fact = sot_map.get(fid)
            if fact:
                context_parts.append(f"[{fid}] {fact.canonical_text}")

    source_context = "\n".join(context_parts)

    instruction = (
        f"You are generating the '{plan.output_format}' section of a document.\n"
        f"Audience: {plan.audience}. Tone: {plan.tone}. "
        f"Detail level: {plan.detail_level}. Language: {plan.language}.\n"
        f"Generate ONLY from the provided facts. Each claim MUST cite its fact_ids.\n"
        f"Do NOT introduce any information not present in the facts below.\n"
        f"Sections to generate: {[s.section_key for s in plan.sections]}\n"
    )

    prompt = build_prompt(instruction, source_context)
    messages = [{"role": "user", "content": prompt}]

    response = llm_call(messages=messages, output_schema=_CLAIM_SCHEMA, model=model)

    # Parse response into typed objects
    sections_out: list[GeneratedSection] = []
    for sec_data in response.get("sections", []):
        claims = [
            Claim(
                claim_id=c.get("claim_id") or generate_claim_id(),
                section_key=sec_data["section_key"],
                text=c["text"],
                fact_ids=c.get("fact_ids", []),
            )
            for c in sec_data.get("claims", [])
        ]
        sections_out.append(GeneratedSection(
            section_key=sec_data["section_key"],
            claims=claims,
            raw_text=sec_data.get("raw_text", ""),
        ))

    return GeneratedOutput(
        output_id=str(uuid.uuid4()),
        job_id=plan.job_id,
        session_id=plan.session_id,
        output_format=plan.output_format,
        plan_id=plan.plan_id,
        lock_hash=plan.lock_hash,
        sections=sections_out,
        language=plan.language,
        generation_model=model or "default",
        generated_at=datetime.utcnow(),
    )
