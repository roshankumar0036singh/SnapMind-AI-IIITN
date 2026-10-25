import pytest
from datetime import date
from unittest.mock import MagicMock

from src.agents.odin.adjudicator import OdinAdjudicator
from src.schemas.claims import Claim, Attack, Defence, ClaimKind
from src.schemas.rulings import RulingOutcome, RulingBasis
from src.schemas.citations import CitationVerifyResponse


@pytest.fixture
def mock_validator():
    validator = MagicMock()
    return validator


def test_adjudicate_valid_claim_upheld(mock_validator):
    mock_validator.verify_citation.return_value = CitationVerifyResponse(
        citation_ref="DOC-E5-001#P1",
        is_valid=True,
        reason="verified_ok",
        doc_id="DOC-E5-001",
        pub_date=date(2026, 3, 1),
    )

    adjudicator = OdinAdjudicator(citation_validator=mock_validator)
    claim = Claim(
        claim_id="CLM-THOR-01",
        agent="thor",
        text="Port of Skagen closed operations on March 1st.",
        country="Nordland",
        sector="Maritime",
        citations=["DOC-E5-001#P1"],
    )

    rulings = adjudicator.adjudicate_claims(
        claims=[claim],
        as_of=date(2026, 3, 15),
    )

    assert len(rulings) == 1
    ruling = rulings[0]
    assert ruling.claim_id == "CLM-THOR-01"
    assert ruling.outcome == RulingOutcome.UPHELD
    assert ruling.basis == RulingBasis.SOURCED_FACT
    assert "DOC-E5-001#P1" in ruling.refs_checked


def test_adjudicate_temporal_clock_violation(mock_validator):
    mock_validator.verify_citation.return_value = CitationVerifyResponse(
        citation_ref="DOC-E5-099",
        is_valid=False,
        reason="post_as_of_violation",
        doc_id="DOC-E5-099",
        pub_date=date(2026, 3, 20),
    )

    adjudicator = OdinAdjudicator(citation_validator=mock_validator)
    claim = Claim(
        claim_id="CLM-LOKI-01",
        agent="loki",
        text="Recovery underway by late March.",
        country="Nordland",
        sector="Maritime",
        citations=["DOC-E5-099"],
    )

    rulings = adjudicator.adjudicate_claims(
        claims=[claim],
        as_of=date(2026, 3, 15),
    )

    assert len(rulings) == 1
    ruling = rulings[0]
    assert ruling.outcome == RulingOutcome.REJECTED
    assert "citation verification failure" in ruling.reasoning


def test_adjudicate_formal_concession(mock_validator):
    mock_validator.verify_citation.return_value = CitationVerifyResponse(
        citation_ref="DOC-E5-005",
        is_valid=True,
        reason="verified_ok",
        doc_id="DOC-E5-005",
        pub_date=date(2026, 3, 5),
    )

    adjudicator = OdinAdjudicator(citation_validator=mock_validator)
    claim = Claim(
        claim_id="CLM-THOR-02",
        agent="thor",
        text="All 4 berths damaged permanently.",
        country="Nordland",
        sector="Maritime",
        citations=["DOC-E5-005"],
    )
    attack = Attack(
        attack_id="ATK-LOKI-01",
        from_agent="loki",
        target_claim_id="CLM-THOR-02",
        grounds="retracted",
        evidence_refs=["DOC-E5-006"],
        text="Port authority corrected statement: only 1 berth damaged.",
    )
    defence = Defence(
        defence_id="DEF-THOR-01",
        attack_id="ATK-LOKI-01",
        response_type="concede",
        new_refs=[],
        text="Conceded: port authority correction confirms only berth 2 damaged.",
    )

    rulings = adjudicator.adjudicate_claims(
        claims=[claim],
        attacks=[attack],
        defences=[defence],
        as_of=date(2026, 3, 15),
    )

    assert len(rulings) == 1
    ruling = rulings[0]
    assert ruling.outcome == RulingOutcome.CONCEDED
    assert "conceded by thor" in ruling.reasoning.lower()


def test_adjudicate_calculation_and_inference_basis(mock_validator):
    mock_validator.verify_citation.return_value = CitationVerifyResponse(
        citation_ref="TRD-E5-01#04",
        is_valid=True,
        reason="verified_ok",
        is_table_row=True,
        table_id="TRD-E5-01",
        row_no=4,
    )

    adjudicator = OdinAdjudicator(citation_validator=mock_validator)
    
    calc_claim = Claim(
        claim_id="CLM-THOR-03",
        agent="thor",
        text="Export volume dropped 42% relative to 12-month baseline.",
        country="Nordland",
        sector="Agriculture",
        kind=ClaimKind.CALCULATION,
        citations=["TRD-E5-01#04"],
    )

    inf_claim = Claim(
        claim_id="CLM-LOKI-02",
        agent="loki",
        text="We forecast rail capacity will likely substitute 15% of wheat cargo.",
        country="Nordland",
        sector="Logistics",
        kind=ClaimKind.INFERENCE,
        citations=["TRD-E5-01#04"],
    )

    rulings = adjudicator.adjudicate_claims(
        claims=[calc_claim, inf_claim],
        as_of=date(2026, 3, 15),
    )

    assert rulings[0].basis == RulingBasis.CALCULATION
    assert rulings[0].outcome == RulingOutcome.UPHELD
    assert rulings[1].basis == RulingBasis.INFERENCE
    assert rulings[1].outcome == RulingOutcome.UPHELD
