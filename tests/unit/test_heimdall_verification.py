"""
tests/unit/test_heimdall_verification.py
========================================
Comprehensive test suite for Heimdall's evidence-based event verification evaluator.
Tests all 15 required verification behaviors without hardcoded dataset phrases.
"""

from datetime import date
import inspect
import pytest

from src.agents.heimdall.verification import (
    extract_event_proposition,
    classify_evidence_relationship,
    evaluate_verification_verdict,
    build_verification_reasons,
)


# ---------------------------------------------------------------------------
# Test 1: A generic unsupported event returns unverifiable
# ---------------------------------------------------------------------------
def test_generic_unsupported_event_returns_unverifiable():
    q = "Did a sudden fire destroy the northern grain terminal before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    # Empty retrieved docs (no document mentions a fire)
    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=[],
    )

    assert result["verdict"] == "unverifiable"
    assert result["proposition_status"] == "insufficient"
    assert result["confidence"] <= 0.3
    assert any("No eligible Runemark source confirms or contradicts" in r for r in result["reasons"])


# ---------------------------------------------------------------------------
# Test 2: A generic claim contradicted by a higher-tier source returns rumour
# ---------------------------------------------------------------------------
def test_generic_claim_contradicted_by_higher_tier_returns_rumour():
    q = "Evaluate the alert claiming that Alpha Harbor was completely destroyed by missile strikes before 2027-01-25."
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "GOV-001",
            "title": "Alpha Harbor Port Authority Official Notice",
            "content": "Alpha Harbor remains open and operating normally. Berth facilities are intact with no damage reported.",
            "pub_date": "2027-01-10",
            "reliability_tier": 1,
        },
        {
            "doc_id": "LOG-002",
            "title": "Maritime Shipping Schedule",
            "content": "Ships continue operating with minor delays due to scheduled maintenance.",
            "pub_date": "2027-01-12",
            "reliability_tier": 2,
        },
        {
            "doc_id": "SOC-003",
            "title": "Social Forum Alert",
            "content": "Unconfirmed rumours on social media claim Alpha Harbor was destroyed by strikes.",
            "pub_date": "2027-01-11",
            "reliability_tier": 4,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert result["verdict"] == "rumour"
    assert result["proposition_status"] == "contradicted"
    assert "GOV-001" in result["contradicting_refs"]
    assert result["confidence"] >= 0.7
    assert any("Higher-reliability records contradict" in r for r in result["reasons"])


# ---------------------------------------------------------------------------
# Test 3: A generic event directly confirmed by an official notice returns real
# ---------------------------------------------------------------------------
def test_generic_event_directly_confirmed_returns_real():
    q = "Did the regional maritime corridor agreement expire without renewal before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "NOT-001",
            "title": "Official Ministry Notice",
            "content": "The regional maritime corridor agreement has expired without renewal as of the scheduled date.",
            "pub_date": "2027-01-15",
            "reliability_tier": 1,
        },
        {
            "doc_id": "TRD-002",
            "title": "Commercial Trade Monitor",
            "content": "Trade operators confirm the corridor agreement ended after non-renewal.",
            "pub_date": "2027-01-16",
            "reliability_tier": 2,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert result["verdict"] == "real"
    assert result["proposition_status"] == "confirmed"
    assert result["confidence"] >= 0.8
    assert "NOT-001" in result["supporting_refs"]
    assert len(result["contradicting_refs"]) == 0


# ---------------------------------------------------------------------------
# Test 4: A weak source alone does not establish a real event
# ---------------------------------------------------------------------------
def test_weak_source_alone_does_not_establish_real():
    q = "Did an unannounced cyberattack shut down custom clearance before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    # Only a Tier-4 social forum post claiming this
    docs = [
        {
            "doc_id": "SOC-999",
            "title": "Forum Post",
            "content": "Rumour on social media: cyberattack shut down customs clearance.",
            "pub_date": "2027-01-18",
            "reliability_tier": 4,
        }
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    # Must NOT be real
    assert result["verdict"] != "real"
    assert result["proposition_status"] != "confirmed"


# ---------------------------------------------------------------------------
# Test 5: A weak source plus strong contradiction returns rumour
# ---------------------------------------------------------------------------
def test_weak_source_plus_strong_contradiction_returns_rumour():
    q = "Did a cyberattack shut down customs clearance before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "SOC-101",
            "title": "Social Forum Alert",
            "content": "Unverified chatter claims cyberattack shut down customs completely.",
            "pub_date": "2027-01-14",
            "reliability_tier": 4,
        },
        {
            "doc_id": "CUS-201",
            "title": "Customs Authority Bulletin",
            "content": "Customs processing continued normally without interruption; refutes allegations of shutdown.",
            "pub_date": "2027-01-15",
            "reliability_tier": 1,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert result["verdict"] == "rumour"
    assert result["proposition_status"] == "contradicted"
    assert "CUS-201" in result["contradicting_refs"]


# ---------------------------------------------------------------------------
# Test 6: A related but different disruption does not confirm the requested proposition
# ---------------------------------------------------------------------------
def test_related_different_disruption_does_not_confirm_requested_proposition():
    q = "Did military strikes destroy the grain silos at Delta Terminal before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    # Documents confirm a severe drop in volume due to a labour strike, but silos are intact
    docs = [
        {
            "doc_id": "REP-301",
            "title": "Port Operations Review",
            "content": "Delta Terminal grain shipments declined 50% due to a labour strike by dockworkers. Silo infrastructure remains intact.",
            "pub_date": "2027-01-20",
            "reliability_tier": 2,
        }
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    # Must NOT verify military destruction as real
    assert result["verdict"] != "real"
    assert result["verdict"] in ("rumour", "unverifiable")


# ---------------------------------------------------------------------------
# Test 7: A correction invalidates the original supporting claim
# ---------------------------------------------------------------------------
def test_correction_invalidates_original_supporting_claim():
    q = "Did the trade agreement expire before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "NEWS-401",
            "title": "Morning Flash",
            "content": "Trade agreement expired today.",
            "pub_date": "2027-01-10",
            "reliability_tier": 3,
        },
        {
            "doc_id": "CORR-402",
            "title": "Correction Notice",
            "content": "Correction: earlier report in NEWS-401 was erroneous; the agreement remains open and valid.",
            "pub_date": "2027-01-11",
            "reliability_tier": 2,
            "is_correction": True,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert result["verdict"] != "real"
    assert "CORR-402" in result["corrections"] or "CORR-402" in result["contradicting_refs"]


# ---------------------------------------------------------------------------
# Test 8: A retraction invalidates the original supporting claim
# ---------------------------------------------------------------------------
def test_retraction_invalidates_original_supporting_claim():
    q = "Did an explosion destroy the eastern terminal before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "WIRE-501",
            "title": "Wire Alert",
            "content": "Explosion destroyed eastern terminal.",
            "pub_date": "2027-01-12",
            "reliability_tier": 3,
            "is_retracted": True,
        },
        {
            "doc_id": "RET-502",
            "title": "Wire Retraction",
            "content": "Wire report WIRE-501 regarding terminal explosion is hereby retracted as unfounded.",
            "pub_date": "2027-01-13",
            "reliability_tier": 2,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert result["verdict"] != "real"
    assert len(result["supporting_refs"]) == 0
    assert result["verdict"] in ("rumour", "unverifiable")


# ---------------------------------------------------------------------------
# Test 9: Post-as-of contradiction is ignored
# ---------------------------------------------------------------------------
def test_post_as_of_contradiction_is_ignored():
    q = "Did the corridor agreement expire before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "OFF-601",
            "title": "Official Expiry Declaration",
            "content": "Corridor agreement expired without renewal on Jan 15.",
            "pub_date": "2027-01-16",
            "reliability_tier": 1,
        },
        {
            "doc_id": "LATE-602",
            "title": "Subsequent Reinstatement",
            "content": "Agreement was unexpectedly reinstated and remains open.",
            "pub_date": "2027-02-15",  # Post-as-of (after 2027-01-25)
            "reliability_tier": 1,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    # Post-as-of document LATE-602 must not overturn pre-as-of confirmation
    assert result["verdict"] == "real"
    assert "OFF-601" in result["supporting_refs"]
    assert "LATE-602" not in result["contradicting_refs"]


# ---------------------------------------------------------------------------
# Test 10: Post-as-of support is ignored
# ---------------------------------------------------------------------------
def test_post_as_of_support_is_ignored():
    q = "Did the pipeline shut down before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "LATE-701",
            "title": "February Incident Report",
            "content": "Pipeline shut down on February 02.",
            "pub_date": "2027-02-03",  # Post-as-of
            "reliability_tier": 1,
        }
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    # Must be unverifiable as of 2027-01-25
    assert result["verdict"] == "unverifiable"
    assert len(result["supporting_refs"]) == 0


# ---------------------------------------------------------------------------
# Test 11: Background documents do not directly establish the event
# ---------------------------------------------------------------------------
def test_background_documents_do_not_establish_event():
    q = "Did the transit canal close before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "BKG-801",
            "title": "Canal Infrastructure & Country Profile",
            "content": "Transit canal historical throughput statistics and tariff schedule baseline.",
            "pub_date": "2026-11-01",
            "event_id": "NONE",
            "reliability_tier": 1,
        }
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert result["verdict"] == "unverifiable"
    assert len(result["supporting_refs"]) == 0


# ---------------------------------------------------------------------------
# Test 12: The output contains evidence roles and decision reasons
# ---------------------------------------------------------------------------
def test_output_contains_evidence_roles_and_decision_reasons():
    q = "Did the maritime corridor agreement expire without renewal before 2027-01-25?"
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "DOC-901",
            "title": "Notice",
            "content": "Agreement expired without renewal.",
            "pub_date": "2027-01-15",
            "reliability_tier": 1,
        }
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    assert "evidence_roles" in result
    assert isinstance(result["evidence_roles"], list)
    assert len(result["evidence_roles"]) == 1
    assert result["evidence_roles"][0]["role"] == "direct_support"
    assert "support_score" in result
    assert "contradiction_score" in result
    assert "decision_basis" in result
    assert len(result["reasons"]) > 0


# ---------------------------------------------------------------------------
# Test 13: Rumour and unverifiable produce different user-facing explanations
# ---------------------------------------------------------------------------
def test_rumour_and_unverifiable_produce_different_explanations():
    as_of = date(2027, 1, 25)

    # 1. Rumour case
    q_rumour = "Did military strikes destroy the grain silos before 2027-01-25?"
    prop_rumour = extract_event_proposition(q_rumour, as_of_date=as_of)
    res_rumour = evaluate_verification_verdict(
        question=q_rumour,
        proposition=prop_rumour,
        as_of_date=as_of,
        retrieved_documents=[
            {
                "doc_id": "PORT-1",
                "title": "Port Notice",
                "content": "Port facility remained open and operating normally.",
                "pub_date": "2027-01-10",
                "reliability_tier": 1,
            }
        ],
    )

    # 2. Unverifiable case
    q_unverifiable = "Did an unrecorded power outage occur at Warehouse 4 before 2027-01-25?"
    prop_unverifiable = extract_event_proposition(q_unverifiable, as_of_date=as_of)
    res_unverifiable = evaluate_verification_verdict(
        question=q_unverifiable,
        proposition=prop_unverifiable,
        as_of_date=as_of,
        retrieved_documents=[],
    )

    assert res_rumour["verdict"] == "rumour"
    assert res_unverifiable["verdict"] == "unverifiable"
    # User-facing reasons must be fundamentally different
    assert any("contradict" in r.lower() or "alternative" in r.lower() for r in res_rumour["reasons"])
    assert any("no eligible runemark source confirms or contradicts" in r.lower() or "insufficient" in r.lower() for r in res_unverifiable["reasons"])


# ---------------------------------------------------------------------------
# Test 14: No event ID, country, document ID, or phrase is hardcoded in evaluator
# ---------------------------------------------------------------------------
def test_no_event_id_country_doc_id_hardcoded_in_evaluator():
    import src.agents.heimdall.verification as v_module
    src_code = inspect.getsource(v_module)

    # Check for hardcoded E5 IDs or document IDs
    forbidden = [
        "ORV-", "TRD-E5", "TRD-E6", "SKAG-", "dev_pack_E5",
        "Orvan Grain Port", "military strikes physically destroyed",
        "Orvan corridor agreement ended", "Midgard", "Tolan"
    ]
    for pattern in forbidden:
        assert pattern not in src_code, f"Forbidden hardcoded pattern found in verification.py: '{pattern}'"


# ---------------------------------------------------------------------------
# Test 15: A decoy claim is rejected while a related broader disruption remains separately representable
# ---------------------------------------------------------------------------
def test_decoy_claim_rejected_while_broader_disruption_remains_representable():
    q = "Evaluate the claim that missile strikes destroyed Port Delta before 2027-01-25."
    as_of = date(2027, 1, 25)
    prop = extract_event_proposition(q, as_of_date=as_of)

    docs = [
        {
            "doc_id": "OFF-DELTA",
            "title": "Port Delta Authority Official Notice",
            "content": "Port Delta remains open and operating. Silos and berths are intact with no structural damage.",
            "pub_date": "2027-01-15",
            "reliability_tier": 1,
        },
        {
            "doc_id": "TRADE-DELTA",
            "title": "Regional Maritime Trade Briefing",
            "content": "Port Delta throughput dropped 65% following the corridor agreement expiry and a dockworker labour strike.",
            "pub_date": "2027-01-18",
            "reliability_tier": 2,
        },
        {
            "doc_id": "SOCIAL-CHAT",
            "title": "Social Forum Rumour",
            "content": "Rumours claim Port Delta was destroyed by missile strikes.",
            "pub_date": "2027-01-16",
            "reliability_tier": 4,
        },
    ]

    result = evaluate_verification_verdict(
        question=q,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=docs,
    )

    # Decoy missile strike claim must be classified as RUMOUR
    assert result["verdict"] == "rumour"
    assert result["proposition_status"] == "contradicted"

    # Broader disruption is recognized in evidence_roles as alternative_explanation / partial_support
    roles = {r["ref"]: r["role"] for r in result["evidence_roles"]}
    assert roles["OFF-DELTA"] == "contradiction"
    assert roles["TRADE-DELTA"] in ("alternative_explanation", "partial_support")
    assert roles["SOCIAL-CHAT"] == "rumour_only"
