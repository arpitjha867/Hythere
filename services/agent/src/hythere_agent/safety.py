from __future__ import annotations

from dataclasses import dataclass

DISTRESS_PATTERNS = (
    "kill myself",
    "suicide",
    "end my life",
    "marna chahta",
    "marna chahti",
    "khud ko maar",
    "jeene ka mann nahi",
    "zinda nahi rehna",
)


@dataclass(slots=True)
class DistressResource:
    name: str | None
    contact: str | None
    region: str | None


@dataclass(slots=True)
class DistressAssessment:
    triggered: bool
    notice: str | None


def assess_distress(text: str, resource: DistressResource) -> DistressAssessment:
    lowered = text.lower()
    if not any(pattern in lowered for pattern in DISTRESS_PATTERNS):
        return DistressAssessment(triggered=False, notice=None)
    contact_bits = [bit for bit in [resource.name, resource.contact, resource.region] if bit]
    contact_text = " | ".join(contact_bits) if contact_bits else "verified local emergency or crisis support"
    notice = (
        "Main emergency service ya therapist nahin hoon. Agar tum abhi unsafe feel kar rahe ho, "
        f"please turant {contact_text} ya kisi trusted person se contact karo."
    )
    return DistressAssessment(triggered=True, notice=notice)
