import pytest
from src.agents.odin.classifier import OdinClassifier
from src.schemas.claims import Claim
from src.schemas.rulings import Ruling, RulingOutcome, RulingBasis


def test_classify_findings():
    classifier = OdinClassifier()
    rulings = [
        Ruling(
            ruling_id="R1",
            claim_id="CLM-01",
            outcome=RulingOutcome.UPHELD,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Valid citation.",
            refs_checked=["DOC-01"],
        ),
        Ruling(
            ruling_id="R2",
            claim_id="CLM-02",
            outcome=RulingOutcome.CONTESTED,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Competing evidence.",
            refs_checked=["DOC-02", "DOC-03"],
        ),
        Ruling(
            ruling_id="R3",
            claim_id="CLM-03",
            outcome=RulingOutcome.CONCEDED,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Conceded following attack.",
            refs_checked=["DOC-04"],
        ),
        Ruling(
            ruling_id="R4",
            claim_id="CLM-04",
            outcome=RulingOutcome.REJECTED,
            basis=RulingBasis.INFERENCE,
            reasoning="Temporal clock violation.",
            refs_checked=["DOC-05"],
        ),
    ]

    summary = classifier.classify_findings(rulings)
    assert summary.established == ["CLM-01"]
    assert summary.contested == ["CLM-02"]
    assert summary.conceded == ["CLM-03", "CLM-04"]


def test_synthesize_ranges_convergent():
    classifier = OdinClassifier()
    
    thor_claim = Claim(
        claim_id="CLM-THOR-01",
        agent="thor",
        text="Wheat trade down by 35% to 45%.",
        country="Nordland",
        sector="Agriculture",
        estimate_low=-45.0,
        estimate_high=-35.0,
        citations=["TRD-01#01"],
    )
    loki_claim = Claim(
        claim_id="CLM-LOKI-01",
        agent="loki",
        text="Rail routes limit wheat drop to 20% to 30%.",
        country="Nordland",
        sector="Agriculture",
        estimate_low=-30.0,
        estimate_high=-20.0,
        citations=["TRD-01#02"],
    )

    rulings = [
        Ruling(
            ruling_id="R1",
            claim_id="CLM-THOR-01",
            outcome=RulingOutcome.UPHELD,
            basis=RulingBasis.CALCULATION,
            reasoning="Valid calculation.",
            refs_checked=["TRD-01#01"],
        ),
        Ruling(
            ruling_id="R2",
            claim_id="CLM-LOKI-01",
            outcome=RulingOutcome.UPHELD,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Rail capacity verified.",
            refs_checked=["TRD-01#02"],
        ),
    ]

    ranges = classifier.synthesize_ranges(
        claims=[thor_claim, loki_claim],
        rulings=rulings,
    )

    assert len(ranges) == 1
    r = ranges[0]
    assert r.country == "Nordland"
    assert r.sector == "Agriculture"
    assert r.odin_low <= r.odin_high
    assert "Established synthesis" in r.basis


def test_synthesize_ranges_contested():
    classifier = OdinClassifier()

    thor_claim = Claim(
        claim_id="CLM-THOR-02",
        agent="thor",
        text="Fertilizer imports collapsed by 60% to 50%.",
        country="Vestri",
        sector="Chemicals",
        estimate_low=-60.0,
        estimate_high=-50.0,
        citations=["DOC-01"],
    )
    loki_claim = Claim(
        claim_id="CLM-LOKI-02",
        agent="loki",
        text="Domestic fertilizer buffer reduces impact to -15% to -10%.",
        country="Vestri",
        sector="Chemicals",
        estimate_low=-15.0,
        estimate_high=-10.0,
        citations=["DOC-02"],
    )

    rulings = [
        Ruling(
            ruling_id="R1",
            claim_id="CLM-THOR-02",
            outcome=RulingOutcome.CONTESTED,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Contested by Loki.",
            refs_checked=["DOC-01"],
        ),
        Ruling(
            ruling_id="R2",
            claim_id="CLM-LOKI-02",
            outcome=RulingOutcome.CONTESTED,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Contested by Thor.",
            refs_checked=["DOC-02"],
        ),
    ]

    ranges = classifier.synthesize_ranges(
        claims=[thor_claim, loki_claim],
        rulings=rulings,
    )

    assert len(ranges) == 1
    r = ranges[0]
    assert r.odin_low == -60.0
    assert r.odin_high == -10.0
    assert "Contested finding" in r.basis


def test_synthesize_ranges_conceded_excluded():
    classifier = OdinClassifier()

    thor_claim = Claim(
        claim_id="CLM-THOR-03",
        agent="thor",
        text="Total maritime shutdown: -90% drop.",
        country="Ostland",
        sector="Maritime",
        estimate_low=-90.0,
        estimate_high=-80.0,
        citations=["DOC-BAD"],
    )
    loki_claim = Claim(
        claim_id="CLM-LOKI-03",
        agent="loki",
        text="Measured rerouting limits drop to -25% to -15%.",
        country="Ostland",
        sector="Maritime",
        estimate_low=-25.0,
        estimate_high=-15.0,
        citations=["DOC-GOOD"],
    )

    rulings = [
        Ruling(
            ruling_id="R1",
            claim_id="CLM-THOR-03",
            outcome=RulingOutcome.CONCEDED,
            basis=RulingBasis.INFERENCE,
            reasoning="Thor conceded claim after port authority correction.",
            refs_checked=["DOC-BAD"],
        ),
        Ruling(
            ruling_id="R2",
            claim_id="CLM-LOKI-03",
            outcome=RulingOutcome.UPHELD,
            basis=RulingBasis.SOURCED_FACT,
            reasoning="Verified and substantiated.",
            refs_checked=["DOC-GOOD"],
        ),
    ]

    ranges = classifier.synthesize_ranges(
        claims=[thor_claim, loki_claim],
        rulings=rulings,
    )

    assert len(ranges) == 1
    r = ranges[0]
    # Thor's -90% must NOT contaminate the synthesized range because it was conceded!
    assert r.odin_low == -25.0
    assert r.odin_high == -15.0
    assert "grounded in Loki's verified evidence" in r.basis
