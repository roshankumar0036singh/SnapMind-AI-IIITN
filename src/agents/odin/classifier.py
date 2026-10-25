"""
src/agents/odin/classifier.py
=============================
Tri-Partite Findings Classification & Calibrated Range Synthesis (FR4.2 & FR8).

Responsibilities:
  - Sorts adjudicated claims into Established, Contested, and Conceded.
  - Synthesizes calibrated [Low, High] exposure bounds per country and economic sector.
  - Narrows the exposure range where Thor and Loki evidence converges.
  - Widens the exposure range where evidence remains contested or uncertain.
  - Explains the exact synthesis rationale (basis) for each country-sector range.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any

from src.schemas.claims import Claim
from src.schemas.rulings import (
    Ruling,
    RulingOutcome,
    ClassificationSummary,
    CountrySectorRange,
)
from src.schemas.case_file import EventScope


class OdinClassifier:
    """
    Judicial classifier and range calibration engine implementing FR4.2 and FR8.
    """

    def classify_findings(self, rulings: List[Ruling]) -> ClassificationSummary:
        """
        Sort claim IDs into established, contested, and conceded categories.
        """
        established: List[str] = []
        contested: List[str] = []
        conceded: List[str] = []

        for r in rulings:
            if r.outcome == RulingOutcome.UPHELD:
                established.append(r.claim_id)
            elif r.outcome == RulingOutcome.CONTESTED:
                contested.append(r.claim_id)
            elif r.outcome in (RulingOutcome.CONCEDED, RulingOutcome.REJECTED):
                conceded.append(r.claim_id)

        return ClassificationSummary(
            established=established,
            contested=contested,
            conceded=conceded,
        )

    def synthesize_ranges(
        self,
        claims: List[Claim],
        rulings: List[Ruling],
        scope: Optional[EventScope] = None,
    ) -> List[CountrySectorRange]:
        """
        Synthesize calibrated [Low, High] exposure bounds per country and sector.
        """
        rulings_by_claim: Dict[str, Ruling] = {r.claim_id: r for r in rulings}

        # Group claims by (country, sector)
        claims_by_group: Dict[Tuple[str, str], List[Claim]] = {}
        for c in claims:
            key = (c.country, c.sector)
            claims_by_group.setdefault(key, []).append(c)

        ranges: List[CountrySectorRange] = []

        for (country, sector), group_claims in claims_by_group.items():
            thor_claims = [c for c in group_claims if c.agent.lower() == "thor"]
            loki_claims = [c for c in group_claims if c.agent.lower() == "loki"]

            thor_estimates = self._extract_bounds(thor_claims, rulings_by_claim)
            loki_estimates = self._extract_bounds(loki_claims, rulings_by_claim)

            # Determine whether contested or established
            group_ruling_outcomes = [
                rulings_by_claim[c.claim_id].outcome
                for c in group_claims
                if c.claim_id in rulings_by_claim
            ]
            is_contested = RulingOutcome.CONTESTED in group_ruling_outcomes

            # Synthesize [odin_low, odin_high]
            odin_low, odin_high, basis = self._calibrate_bounds(
                country=country,
                sector=sector,
                thor_bounds=thor_estimates,
                loki_bounds=loki_estimates,
                is_contested=is_contested,
            )

            ranges.append(
                CountrySectorRange(
                    country=country,
                    sector=sector,
                    unit="percent_change",
                    thor_low=thor_estimates.get("low"),
                    thor_high=thor_estimates.get("high"),
                    loki_low=loki_estimates.get("low"),
                    loki_high=loki_estimates.get("high"),
                    odin_low=odin_low,
                    odin_high=odin_high,
                    basis=basis,
                )
            )

        return ranges

    def _extract_bounds(
        self,
        agent_claims: List[Claim],
        rulings_by_claim: Dict[str, Ruling],
    ) -> Dict[str, Optional[float]]:
        """
        Extract low and high estimates from valid (upheld or contested) claims.
        Excludes conceded or rejected claims.
        """
        lows: List[float] = []
        highs: List[float] = []

        for c in agent_claims:
            ruling = rulings_by_claim.get(c.claim_id)
            # Conceded or rejected claims must not contaminate synthesized range
            if ruling and ruling.outcome in (RulingOutcome.CONCEDED, RulingOutcome.REJECTED):
                continue

            if c.estimate_low is not None:
                lows.append(c.estimate_low)
            if c.estimate_high is not None:
                highs.append(c.estimate_high)

        return {
            "low": min(lows) if lows else (min(highs) if highs else None),
            "high": max(highs) if highs else (max(lows) if lows else None),
        }

    def _calibrate_bounds(
        self,
        country: str,
        sector: str,
        thor_bounds: Dict[str, Optional[float]],
        loki_bounds: Dict[str, Optional[float]],
        is_contested: bool,
    ) -> Tuple[float, float, str]:
        t_low, t_high = thor_bounds.get("low"), thor_bounds.get("high")
        l_low, l_high = loki_bounds.get("low"), loki_bounds.get("high")

        # Scenario 1: Both Thor and Loki provided valid bounds
        if t_low is not None and l_low is not None:
            all_vals = [v for v in (t_low, t_high, l_low, l_high) if v is not None]
            min_val = min(all_vals)
            max_val = max(all_vals)

            if is_contested:
                # Contested: preserve wide bounds to reflect evidential uncertainty
                basis = (
                    f"Contested finding for {country} ({sector}): conflicting evidence and methodology "
                    f"between Thor [{t_low}%, {t_high}%] and Loki [{l_low}%, {l_high}%]. Preserving wide calibrated bounds."
                )
                return min_val, max_val, basis
            else:
                # Established: evidence converges, narrow calibrated interval
                # e.g., Thor argues -40 to -30%, Loki argues -25 to -15%.
                # Calibrated range balances high disruption against substitution evidence
                c_low = round((min_val + sorted(all_vals)[1]) / 2, 2) if len(all_vals) >= 2 else min_val
                c_high = round((max_val + sorted(all_vals)[-2]) / 2, 2) if len(all_vals) >= 2 else max_val
                if c_low > c_high:
                    c_low, c_high = c_high, c_low

                basis = (
                    f"Established synthesis for {country} ({sector}): converging verified trade and document data. "
                    f"Calibrated Thor bounds [{t_low}%, {t_high}%] with Loki offsets [{l_low}%, {l_high}%]."
                )
                return c_low, c_high, basis

        # Scenario 2: Only Thor provided valid bounds (Loki conceded or lacked data)
        elif t_low is not None:
            t_hi = t_high if t_high is not None else t_low
            low = min(t_low, t_hi)
            high = max(t_low, t_hi)
            basis = (
                f"Judicial synthesis for {country} ({sector}) grounded in Thor's verified evidence "
                f"[{low}%, {high}%] (Loki claims unadjudicated or conceded)."
            )
            return low, high, basis

        # Scenario 3: Only Loki provided valid bounds (Thor conceded or lacked data)
        elif l_low is not None:
            l_hi = l_high if l_high is not None else l_low
            low = min(l_low, l_hi)
            high = max(l_low, l_hi)
            basis = (
                f"Judicial synthesis for {country} ({sector}) grounded in Loki's verified evidence "
                f"[{low}%, {high}%] (Thor claims unadjudicated or conceded)."
            )
            return low, high, basis

        # Scenario 4: Qualitative claims only (no numerical bounds submitted)
        else:
            basis = (
                f"Qualitative evidence established for {country} ({sector}); "
                f"no quantitative percentage bounds provided in submitted claims."
            )
            return 0.0, 0.0, basis
