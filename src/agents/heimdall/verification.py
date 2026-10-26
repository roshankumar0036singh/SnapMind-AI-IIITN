"""
src/agents/heimdall/verification.py
===================================
Evidence-driven event verification evaluator for Heimdall Gatekeeper.

Deterministic, generic evaluator that classifies an event proposition as:
  - 'real': verified by eligible pre-as-of evidence without unresolved contradiction.
  - 'rumour': asserted claim contradicted by stronger evidence, supported only
              by weak/corrected/retracted sources, or explained by an alternative cause.
  - 'unverifiable': insufficient eligible evidence in the corpus to confirm or contradict.

CRITICAL DESIGN PRINCIPLE:
No hardcoding of event names, document IDs, country names, titles, or dataset-specific phrases.
All evaluations are driven purely by extracted propositions, document metadata, tiers,
temporal boundaries, and semantic relationship matching.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Tier reliability weights
# ---------------------------------------------------------------------------
TIER_WEIGHTS: Dict[int, float] = {
    1: 1.0,  # Official government / authority / gazette / treaty registry
    2: 0.8,  # Commercial tracker / port logistics / customs / shipping registry
    3: 0.5,  # General news / industry reporting / market analysis
    4: 0.2,  # Social media / unverified commentary / message board
}

# ---------------------------------------------------------------------------
# Semantic Pattern Dictionaries (Generic across domains & event packs)
# ---------------------------------------------------------------------------

# Event types
DESTRUCTION_KEYWORDS = {
    "destroy", "destroyed", "destroys", "destruction", "demolish", "demolished",
    "bomb", "bombed", "blast", "blasted", "burn", "burned", "burnt", "sink", "sank", "sunk",
    "blown up", "levelled", "leveled", "flattened", "wipe out", "wiped out", "strike", "strikes",
    "missile", "shelling", "attack", "attacked", "demolition"
}

EXPIRY_KEYWORDS = {
    "expire", "expired", "expiry", "expiration", "terminate", "terminated", "termination",
    "lapse", "lapsed", "non-renewal", "not renewed", "end of agreement", "ended agreement",
    "cancel", "cancelled", "cancellation", "dissolve", "dissolved"
}

SHUTDOWN_KEYWORDS = {
    "closure", "closed", "close", "shut down", "shutdown", "halt", "halted", "block", "blocked",
    "blockade", "suspend", "suspended", "stoppage", "cease", "ceased", "bar", "barred", "ban", "banned"
}

LABOUR_KEYWORDS = {
    "strike", "walkout", "protest", "labour", "labor", "dockworker", "union action", "picket"
}

DISRUPTION_KEYWORDS = {
    "disrupt", "disrupted", "disruption", "collapse", "collapsed", "halt", "halted",
    "suspend", "suspended", "closure", "closed", "interruption", "stoppage"
}

SEVERITY_COMPLETE_KEYWORDS = {
    "complete", "completely", "total", "totally", "full", "fully", "entire", "entirely",
    "major", "catastrophic", "absolute", "all", "every", "flattened", "wholly"
}

SEVERITY_PARTIAL_KEYWORDS = {
    "partial", "partially", "reduced", "minor", "limited", "temporary", "some", "fractional"
}

# Contradiction indicators (affirms continuation, operational status, or intactness)
CONTRADICTION_INTACT_PATTERNS = [
    r"\bremain(?:ed|s)? open\b",
    r"\bopen and operat(?:ing|ional)\b",
    r"\bcontinu(?:ed|es|ing)? operat(?:ing|ions)\b",
    r"\boperat(?:ed|ing|ional|ions)? (?:normally|at reduced capacity|with delays|with minor delays)\b",
    r"\bundamaged\b",
    r"\bintact\b",
    r"\bno (?:physical |structural )?damage\b",
    r"\bno (?:strikes|attacks|missiles|explosions|casualties)\b",
    r"\brefut(?:es|ed)?\b",
    r"\bdeni(?:es|ed)?\b",
    r"\bnot destroyed\b",
    r"\bnot closed\b",
    r"\bnot (?:hit|bombed|struck)\b",
    r"\bships (?:delayed|rerouted|operating|continue operating)\b",
    r"\bberths? (?:active|accessible|open)\b",
    r"\bcustoms (?:processing )?continu(?:ed|es|ing)\b",
]

# Alternative explanation markers (explains disruption by different cause)
ALTERNATIVE_CAUSE_KEYWORDS = [
    ("labour strike", "labour dispute or dockworker action"),
    ("labor strike", "labour dispute or dockworker action"),
    ("dockworker strike", "dockworker union strike"),
    ("labour dispute", "labour dispute"),
    ("administrative expiry", "administrative non-renewal or expiration"),
    ("technical failure", "technical or mechanical failure"),
    ("bad weather", "weather disruption"),
    ("scheduled maintenance", "scheduled maintenance"),
    ("routine inspection", "routine regulatory inspection"),
    ("customs paperwork", "customs paperwork delay"),
    ("congestion", "logistical port congestion"),
]

# Rumour / unverified qualifiers
RUMOUR_QUALIFIERS = [
    r"\brumou?rs?\b",
    r"\buncorroborated\b",
    r"\bunconfirmed\b",
    r"\bsocial media\b",
    r"\bchatter\b",
    r"\bspeculat(?:ion|ive)\b",
    r"\balleg(?:ation|ed|edly)\b",
    r"\bdecoy\b",
    r"\bdebunked\b",
    r"\bunverified\b",
    r"\bfalse report\b",
    r"\bhoax\b",
    r"\bwithout evidence\b",
]


# ---------------------------------------------------------------------------
# Proposition Extraction
# ---------------------------------------------------------------------------

def extract_event_proposition(
    question: str,
    as_of_date: Optional[Any] = None,
    event_id: Optional[str] = None,
    hints: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract structured dimensions of the event proposition from the user question.
    Generic and free of hardcoded dataset references.
    """
    q_lower = question.lower()
    hints = hints or {}

    # 1. Time boundary
    time_boundary = ""
    date_match = re.search(r"\b(?:before|on or before|prior to|by|as of)\s+(\d{4}-\d{2}-\d{2})\b", question, re.IGNORECASE)
    if date_match:
        time_boundary = f"on_or_before_{date_match.group(1)}"
    elif as_of_date:
        time_boundary = f"on_or_before_{as_of_date}"
    else:
        time_boundary = "unbounded"

    # 2. Event type
    event_type = "disruption"
    if any(k in q_lower for k in DESTRUCTION_KEYWORDS):
        event_type = "physical_destruction"
    elif any(k in q_lower for k in EXPIRY_KEYWORDS) and any(w in q_lower for w in ["agreement", "treaty", "accord", "pact", "contract", "deal", "renewal", "expire", "expiry"]):
        event_type = "agreement_expiry"
    elif any(k in q_lower for k in SHUTDOWN_KEYWORDS) or "collapse" in q_lower:
        event_type = "operational_shutdown"
    elif any(k in q_lower for k in LABOUR_KEYWORDS):
        event_type = "labour_disruption"
    elif "fire" in q_lower:
        event_type = "fire_damage"
    elif "damage" in q_lower or "damaged" in q_lower:
        event_type = "infrastructure_damage"

    # 3. Cause
    cause = None
    cause_match = re.search(
        r"\b(?:caused by|due to|because of|following|from|by|after)\s+([a-zA-Z0-9_\- ]{3,40}?)"
        r"(?:\s+(?:before|prior|in|on|at|and|or|\.|\?|$))",
        question,
        re.IGNORECASE,
    )
    if cause_match:
        raw_cause = cause_match.group(1).strip()
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", raw_cause):
            cause = raw_cause.replace(" ", "_").lower()

    if not cause:
        if "military strike" in q_lower or "air strike" in q_lower or "missile strike" in q_lower or "strikes" in q_lower:
            cause = "military_strikes"
        elif "non-renewal" in q_lower or "not renewed" in q_lower or "without renewal" in q_lower:
            cause = "non_renewal"
        elif "labour strike" in q_lower or "worker strike" in q_lower:
            cause = "labour_action"
        elif "fire" in q_lower:
            cause = "fire"

    # 4. Severity
    severity = None
    if any(k in q_lower for k in SEVERITY_COMPLETE_KEYWORDS):
        severity = "complete_or_major"
    elif any(k in q_lower for k in SEVERITY_PARTIAL_KEYWORDS):
        severity = "partial"

    # 5. Subject & Location (Generic entity extraction from noun phrases)
    subject = hints.get("subject") or hints.get("event_name")
    location = hints.get("location")

    if not subject:
        cap_phrases = re.findall(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*)\b", question)
        skip_words = {"Did", "What", "When", "Where", "Why", "How", "Evaluate", "Was", "Were", "Is", "Are", "Has", "Have", "The", "Assess"}
        candidates = [p for p in cap_phrases if p not in skip_words and len(p) > 2]
        if candidates:
            subject = candidates[0]
            if len(candidates) > 1:
                location = candidates[1]
        else:
            noun_match = re.search(r"\b(?:port|terminal|facility|corridor|agreement|strait|canal|pipeline|rail(?:way)?)\b", q_lower)
            if noun_match:
                subject = noun_match.group(0).title()
            else:
                subject = "Disruption Event"

    # 6. Objects mentioned
    objects = []
    for obj_word in ["port", "terminal", "silos", "infrastructure", "ships", "vessels", "berths", "rail line", "pipeline", "grain terminal", "agreement", "corridor"]:
        if obj_word in q_lower:
            objects.append(obj_word)

    is_structured = bool(event_type != "disruption" or cause or objects or severity)

    return {
        "subject": str(subject),
        "event_type": event_type,
        "cause": cause,
        "object": objects,
        "severity": severity,
        "time_boundary": time_boundary,
        "location": location,
        "raw_claim": question,
        "structured": is_structured,
    }


# ---------------------------------------------------------------------------
# Evidence Role Classification
# ---------------------------------------------------------------------------

def classify_evidence_relationship(
    doc: Dict[str, Any],
    proposition: Dict[str, Any],
    as_of_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Classify a retrieved document's relationship to the specific event proposition.
    """
    doc_id = str(doc.get("doc_id") or doc.get("ref") or "UNKNOWN")
    tier_val = doc.get("reliability_tier", doc.get("tier", 3))
    try:
        tier = int(str(tier_val).replace("T", "").strip())
    except (ValueError, TypeError):
        tier = 3

    content = (doc.get("content") or doc.get("content_untrusted") or doc.get("summary") or "").strip()
    c_lower = content.lower()
    title = (doc.get("title") or "").strip()
    t_lower = title.lower()
    full_text = f"{t_lower} {c_lower}"

    pub_date_val = doc.get("pub_date") or doc.get("date")
    pub_date: Optional[date] = None
    if pub_date_val:
        if isinstance(pub_date_val, date):
            pub_date = pub_date_val
        elif isinstance(pub_date_val, str) and len(pub_date_val) >= 10:
            try:
                pub_date = date.fromisoformat(pub_date_val[:10])
            except ValueError:
                pass

    # 1. Unusable check (damaged, quarantined, injection flagged)
    if doc.get("is_damaged") or doc.get("usable") is False or doc.get("is_injection_attempt") or doc.get("quarantined"):
        return {
            "ref": doc_id,
            "role": "unusable",
            "reason": f"Document {doc_id} is damaged, quarantined, or flagged for security/injection.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": False,
        }

    # 2. Post-as-of check
    if as_of_date and pub_date and pub_date > as_of_date:
        return {
            "ref": doc_id,
            "role": "post_as_of",
            "reason": f"Document {doc_id} published on {pub_date}, after the as-of cut-off {as_of_date}.",
            "tier": tier,
            "date": str(pub_date),
            "usable": False,
        }

    # 3. Retraction check
    if doc.get("is_retracted") or any(r in full_text for r in ["retracts", "retraction", "hereby retracted", "withdrawn", "is withdrawn"]):
        return {
            "ref": doc_id,
            "role": "retraction",
            "reason": f"Document {doc_id} is formally retracted or withdraws a previous claim.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": False,
        }

    # 4. Correction check
    if doc.get("is_correction") or any(r in full_text for r in ["correction:", "correction notice", "erratum", "corrects previous report"]):
        return {
            "ref": doc_id,
            "role": "correction",
            "reason": f"Document {doc_id} issues a formal correction altering earlier reporting.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": True,
        }

    # 5. Contradiction check against the proposition
    prop_type = proposition.get("event_type", "")
    prop_cause = proposition.get("cause", "")
    prop_severity = proposition.get("severity", "")

    is_contradiction = False
    contra_reason = ""
    for pat in CONTRADICTION_INTACT_PATTERNS:
        match = re.search(pat, full_text)
        if match:
            if prop_type in ("physical_destruction", "fire_damage", "infrastructure_damage") or prop_severity == "complete_or_major":
                is_contradiction = True
                contra_reason = f"Document states facility/operations continued or remained intact ('{match.group(0)}')."
                break
            elif prop_type == "operational_shutdown" and any(k in pat for k in ["remain open", "operat", "processing"]):
                is_contradiction = True
                contra_reason = f"Document states operations remained open/active ('{match.group(0)}')."
                break

    if is_contradiction:
        return {
            "ref": doc_id,
            "role": "contradiction",
            "reason": contra_reason,
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": True,
        }

    # 6. Alternative explanation check
    for alt_phrase, alt_desc in ALTERNATIVE_CAUSE_KEYWORDS:
        if alt_phrase in full_text:
            if prop_cause and prop_cause not in alt_phrase.replace(" ", "_"):
                return {
                    "ref": doc_id,
                    "role": "alternative_explanation",
                    "reason": f"Document explains disruption via {alt_desc}, contradicting the alleged cause ({prop_cause}).",
                    "tier": tier,
                    "date": str(pub_date) if pub_date else None,
                    "usable": True,
                }
            elif prop_type in ("physical_destruction", "fire_damage"):
                return {
                    "ref": doc_id,
                    "role": "alternative_explanation",
                    "reason": f"Document attributes disruption to {alt_desc}, not physical destruction.",
                    "tier": tier,
                    "date": str(pub_date) if pub_date else None,
                    "usable": True,
                }

    # 7. Rumour check
    is_rumour_text = any(re.search(pat, full_text) for pat in RUMOUR_QUALIFIERS)
    if is_rumour_text or (tier >= 4 and any(k in full_text for k in DESTRUCTION_KEYWORDS)):
        return {
            "ref": doc_id,
            "role": "rumour_only",
            "reason": f"Document {doc_id} reports claim only as an unverified rumour, speculation, or Tier-4 post.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": True,
        }

    # 8. Direct support vs Partial support
    has_event_match = False
    if prop_type == "agreement_expiry":
        has_event_match = any(k in full_text for k in EXPIRY_KEYWORDS)
    elif prop_type in ("physical_destruction", "infrastructure_damage"):
        has_event_match = any(k in full_text for k in DESTRUCTION_KEYWORDS)
    elif prop_type == "operational_shutdown":
        has_event_match = any(k in full_text for k in SHUTDOWN_KEYWORDS) or any(k in full_text for k in ["collapse", "collapsed", "disrupt", "disruption", "closed completely"])
    elif prop_type == "labour_disruption":
        has_event_match = any(k in full_text for k in LABOUR_KEYWORDS)
    elif prop_type == "fire_damage":
        has_event_match = "fire" in full_text
    elif prop_type == "disruption":
        has_event_match = any(k in full_text for k in DISRUPTION_KEYWORDS)

    # Subject / Object match check
    prop_subj = (proposition.get("subject") or "").lower().strip()
    subj_tokens = [w for w in re.findall(r"\b[a-zA-Z0-9_\-]+\b", prop_subj) if len(w) > 2 and w not in {"the", "and"}]
    obj_tokens = proposition.get("object", [])
    
    has_subj_match = False
    if not subj_tokens and not obj_tokens:
        has_subj_match = True
    elif any(token.lower() in full_text for token in subj_tokens):
        has_subj_match = True
    elif any(obj.lower() in full_text for obj in obj_tokens):
        has_subj_match = True
    elif prop_type == "agreement_expiry" and "agreement" in full_text:
        has_subj_match = True

    if has_event_match and has_subj_match:
        if prop_cause:
            cause_words = prop_cause.replace("_", " ").split()
            cause_match = any(cw in full_text for cw in cause_words if len(cw) > 3)
            if not cause_match and prop_type == "physical_destruction":
                return {
                    "ref": doc_id,
                    "role": "partial_support",
                    "reason": f"Confirms disruption at subject, but does not confirm alleged cause ({prop_cause}).",
                    "tier": tier,
                    "date": str(pub_date) if pub_date else None,
                    "usable": True,
                }
        return {
            "ref": doc_id,
            "role": "direct_support",
            "reason": f"Directly confirms the occurrence of {prop_type} regarding {proposition.get('subject')}.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": True,
        }

    # 9. Partial support check (related disruption mentioned)
    if has_subj_match or any(k in full_text for k in ["disrupt", "delay", "decline", "halt", "volume", "imports", "exports", "expiry", "agreement"]):
        return {
            "ref": doc_id,
            "role": "partial_support",
            "reason": "Mentions related supply-chain disruption or trade activity, but does not confirm the specific claim.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": True,
        }

    # 10. Background check (explicitly marked EVENT_ID = NONE or general overview)
    eid = str(doc.get("event_id") or "").upper()
    if eid in ("NONE",) or "profile" in full_text or "baseline" in full_text or "background" in full_text:
        return {
            "ref": doc_id,
            "role": "background",
            "reason": f"Corpus background document {doc_id} providing general contextual reference, not proof of event occurrence.",
            "tier": tier,
            "date": str(pub_date) if pub_date else None,
            "usable": True,
        }

    return {
        "ref": doc_id,
        "role": "irrelevant",
        "reason": "Does not discuss the claimed event proposition.",
        "tier": tier,
        "date": str(pub_date) if pub_date else None,
        "usable": True,
    }


# ---------------------------------------------------------------------------
# Decision Evaluator & Scoring
# ---------------------------------------------------------------------------

def evaluate_verification_verdict(
    question: str,
    proposition: Dict[str, Any],
    as_of_date: Optional[date],
    retrieved_documents: List[Dict[str, Any]],
    document_metadata: Optional[Dict[str, Any]] = None,
    corrections: Optional[List[Any]] = None,
    retractions: Optional[List[Any]] = None,
    contradictions: Optional[List[Any]] = None,
    evidence_index: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    """
    Deterministically evaluate verification verdict (real, rumour, unverifiable)
    based on retrieved evidence, roles, source tiers, and contradiction scoring.
    """
    evidence_roles: List[Dict[str, Any]] = []

    direct_supports: List[Dict[str, Any]] = []
    partial_supports: List[Dict[str, Any]] = []
    contradictions_found: List[Dict[str, Any]] = []
    alternative_explanations: List[Dict[str, Any]] = []
    rumour_sources: List[Dict[str, Any]] = []
    corrections_found: List[Dict[str, Any]] = []
    retractions_found: List[Dict[str, Any]] = []
    post_as_of_docs: List[Dict[str, Any]] = []
    unusable_docs: List[Dict[str, Any]] = []
    background_docs: List[Dict[str, Any]] = []

    # Classify each document
    for doc in retrieved_documents:
        role_entry = classify_evidence_relationship(doc, proposition, as_of_date)
        evidence_roles.append(role_entry)
        role = role_entry["role"]

        if role == "direct_support":
            direct_supports.append(role_entry)
        elif role == "partial_support":
            partial_supports.append(role_entry)
        elif role == "contradiction":
            contradictions_found.append(role_entry)
        elif role == "alternative_explanation":
            alternative_explanations.append(role_entry)
        elif role == "rumour_only":
            rumour_sources.append(role_entry)
        elif role == "correction":
            corrections_found.append(role_entry)
        elif role == "retraction":
            retractions_found.append(role_entry)
        elif role == "post_as_of":
            post_as_of_docs.append(role_entry)
        elif role == "unusable":
            unusable_docs.append(role_entry)
        elif role == "background":
            background_docs.append(role_entry)

    # Direct support score calculation
    raw_support = 0.0
    for s in direct_supports:
        tier = s.get("tier", 3)
        w = TIER_WEIGHTS.get(tier, 0.3)
        raw_support += w

    # Penalties against support:
    retraction_penalty = 0.0
    if retractions_found:
        retraction_penalty = 0.8 * len(retractions_found)

    correction_penalty = 0.0
    if corrections_found:
        correction_penalty = 0.5 * len(corrections_found)

    # Contradiction score calculation
    raw_contradiction = 0.0
    for c in contradictions_found:
        tier = c.get("tier", 3)
        w = TIER_WEIGHTS.get(tier, 0.3)
        if tier <= 2:
            w += 0.3
        raw_contradiction += w

    for alt in alternative_explanations:
        tier = alt.get("tier", 3)
        w = TIER_WEIGHTS.get(tier, 0.3) * 0.8
        if tier <= 2:
            w += 0.2
        raw_contradiction += w

    # Bonus if contradiction comes from Tier 1/2 while support is only weak/rumour
    has_high_tier_contra = any(c.get("tier", 3) <= 2 for c in (contradictions_found + alternative_explanations))
    only_weak_support = len(direct_supports) == 0 or all(s.get("tier", 4) >= 4 for s in direct_supports)
    if has_high_tier_contra and (rumour_sources or only_weak_support):
        raw_contradiction += 0.5

    # Net scores bounded to [0.0, 1.0]
    support_score = max(0.0, min(1.0, raw_support - (retraction_penalty + correction_penalty)))
    contradiction_score = max(0.0, min(1.0, raw_contradiction))

    # Verdict Decision Policy
    verdict = "unverifiable"
    proposition_status = "insufficient"
    confidence = 0.0
    decision_basis = ""

    # Check for REAL
    has_strong_direct_support = any(s.get("tier", 3) <= 2 for s in direct_supports)
    if has_strong_direct_support and len(retractions_found) == 0 and contradiction_score < 0.3:
        verdict = "real"
        proposition_status = "confirmed"
        confidence = min(0.98, max(0.70, support_score))
        decision_basis = (
            f"Verified REAL: Strong direct confirmation from reliable pre-as-of sources "
            f"(support_score={support_score:.2f}) without material unresolved contradiction."
        )

    # Check for RUMOUR
    elif (contradiction_score >= 0.5 and (rumour_sources or only_weak_support or len(direct_supports) == 0)) or \
         (len(retractions_found) > 0 and len(direct_supports) == 0) or \
         (has_high_tier_contra and (rumour_sources or any(c in question.lower() for c in DESTRUCTION_KEYWORDS))):
        verdict = "rumour"
        proposition_status = "contradicted"
        confidence = min(0.95, max(0.65, contradiction_score))
        decision_basis = (
            f"Classified as RUMOUR/DECOY: Higher-reliability evidence contradicts the claim or provides "
            f"an alternative explanation (contradiction_score={contradiction_score:.2f}), "
            f"while positive support is weak, uncorroborated, or retracted."
        )

    # Otherwise UNVERIFIABLE
    else:
        verdict = "unverifiable"
        proposition_status = "insufficient"
        confidence = 0.2
        if post_as_of_docs and not direct_supports:
            decision_basis = "UNVERIFIABLE: Relevant documents are dated after the as-of cut-off date."
        elif unusable_docs and not direct_supports:
            decision_basis = "UNVERIFIABLE: Relevant documents in the corpus are damaged or quarantined."
        elif background_docs and not direct_supports:
            decision_basis = "UNVERIFIABLE: Corpus contains only general background documents without event occurrence reports."
        else:
            decision_basis = "UNVERIFIABLE: Insufficient eligible evidence in the corpus to confirm or contradict the claim."

    supporting_refs = [s["ref"] for s in direct_supports if s.get("tier", 4) <= 3]
    contradicting_refs = [c["ref"] for c in contradictions_found] + [a["ref"] for a in alternative_explanations]
    reasons = build_verification_reasons(
        verdict=verdict,
        proposition=proposition,
        proposition_status=proposition_status,
        direct_supports=direct_supports,
        contradictions=contradictions_found,
        alternative_explanations=alternative_explanations,
        rumour_sources=rumour_sources,
        corrections=corrections_found,
        retractions=retractions_found,
        post_as_of=post_as_of_docs,
        unusable=unusable_docs,
        background=background_docs,
        decision_basis=decision_basis,
    )

    unresolved_questions: List[str] = []
    if verdict == "real":
        unresolved_questions.append(
            "Event occurrence verified; specific sector trade volume exposure to be debated by Thor and Loki."
        )
    elif verdict == "unverifiable":
        unresolved_questions.append(
            "Corpus lacks eligible records confirming or refuting the event; judicial review or supplemental evidence required."
        )

    return {
        "verdict": verdict,
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "supporting_refs": supporting_refs,
        "contradicting_refs": contradicting_refs,
        "corrections": [c["ref"] for c in corrections_found],
        "retractions": [r["ref"] for r in retractions_found],
        "unresolved_questions": unresolved_questions,
        "proposition_status": proposition_status,
        "proposition": proposition,
        "evidence_roles": evidence_roles,
        "support_score": round(support_score, 2),
        "contradiction_score": round(contradiction_score, 2),
        "decision_basis": decision_basis,
    }


# ---------------------------------------------------------------------------
# Build Verification Reasons
# ---------------------------------------------------------------------------

def build_verification_reasons(
    verdict: str,
    proposition: Dict[str, Any],
    proposition_status: str,
    direct_supports: List[Dict[str, Any]],
    contradictions: List[Dict[str, Any]],
    alternative_explanations: List[Dict[str, Any]],
    rumour_sources: List[Dict[str, Any]],
    corrections: List[Dict[str, Any]],
    retractions: List[Dict[str, Any]],
    post_as_of: List[Dict[str, Any]],
    unusable: List[Dict[str, Any]],
    background: List[Dict[str, Any]],
    decision_basis: str,
) -> List[str]:
    """
    Format transparent, audit-ready verification reasons citing specific evidence roles.
    """
    reasons: List[str] = []

    if verdict == "real":
        reasons.append(
            f"The specific event proposition regarding '{proposition.get('subject', 'the event')}' "
            f"is directly confirmed by eligible pre-as-of sources."
        )
        for s in direct_supports[:3]:
            reasons.append(f"[{s['ref']}] (Tier {s.get('tier', 'N/A')}): {s.get('reason')}")
        if corrections:
            for c in corrections[:2]:
                reasons.append(f"[{c['ref']}]: Formal correction corroborates the non-renewal/verified state.")

    elif verdict == "rumour":
        if rumour_sources:
            reasons.append("The alleged claim is supported only by weak, uncorroborated, or rumour-level records.")
        if contradictions:
            reasons.append("Higher-reliability records contradict the claim:")
            for c in contradictions[:3]:
                reasons.append(f"  * [{c['ref']}] (Tier {c.get('tier', 'N/A')}): {c.get('reason')}")
        if alternative_explanations:
            reasons.append("Eligible evidence documents an alternative cause or explanation for the disruption:")
            for a in alternative_explanations[:3]:
                reasons.append(f"  * [{a['ref']}] (Tier {a.get('tier', 'N/A')}): {a.get('reason')}")
        if retractions:
            for r in retractions[:2]:
                reasons.append(f"[{r['ref']}]: Prior claim was formally retracted by the publisher.")

    else:  # unverifiable
        if post_as_of:
            reasons.append("Evidence mentioning this topic was published after the as-of temporal boundary and cannot be cited.")
        elif unusable:
            reasons.append("Candidate documents are damaged, unreadable, or quarantined under security policies.")
        elif background:
            reasons.append("Corpus contains only general reference and background documents; none confirm or refute event occurrence.")
        else:
            reasons.append(
                f"No eligible Runemark source confirms or contradicts the alleged '{proposition.get('event_type', 'event')}'. "
                "Absence of evidence alone cannot establish falsehood."
            )

    return reasons
