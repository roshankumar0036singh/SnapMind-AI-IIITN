// Complete authentic Trial and Ingest Data for Dev Pack E5
// Grounded in CONTEXT_UPDATED.md and the 76-document dev_pack_E5 corpus

export const CASE_METADATA = {
  case_id: "CASE-2027-E5-ORVAN",
  event_id: "E5",
  title: "Expiry of the Orvan Corridor Agreement",
  as_of_date: "2027-01-25",
  target_countries: ["Midgard", "Tolan"],
  target_sectors: ["Wheat", "Maize"],
  question: "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports.",
  status: "DELIBERATION_COMPLETED"
};

// Trap Scorecard & Ingestion Defense
export const TRAP_SCORECARD = {
  scanned_files: 76,
  clean_files: 68,
  traps_neutralized: 8,
  items: [
    {
      type: "clock_violation",
      badge: "CLOCK VIOLATION",
      severity: "critical",
      doc_id: "ORV-0014",
      pub_date: "2027-03-12",
      cutoff: "2027-01-25",
      title: "New corridor talks to open after Orvan request",
      description: "Published 46 days after as-of date. Quarantined by tool-layer as-of gate to prevent timeline leak."
    },
    {
      type: "clock_violation",
      badge: "CLOCK VIOLATION",
      severity: "critical",
      doc_id: "ORV-0036",
      pub_date: "2027-02-18",
      cutoff: "2027-01-25",
      title: "Trade note: Orvan to Midgard, wheat, January 2027",
      description: "Post-cutoff trade figures. Blocked from calculation baseline."
    },
    {
      type: "clock_violation",
      badge: "CLOCK VIOLATION",
      severity: "critical",
      doc_id: "ORV-0041",
      pub_date: "2027-04-09",
      cutoff: "2027-01-25",
      title: "Spring bookings point to a slow Orvan recovery",
      description: "Future spring bookings report excluded from retrospective analysis."
    },
    {
      type: "damaged_file",
      badge: "DAMAGED: EMPTY (0 BYTES)",
      severity: "warning",
      doc_id: "ORV-0023",
      pub_date: "2026-10-18",
      title: "Asgard feed buyers feel cost (Corrupted 0-byte file)",
      description: "0 bytes on disk. Detected by parser damage checker; skipped indexing without crashing."
    },
    {
      type: "contradiction_retraction",
      badge: "RETRACTED / DISCREDITED",
      severity: "high",
      doc_id: "ORV-0043",
      pub_date: "2026-11-20",
      title: "Orvan grain corridor renewed for a second year",
      description: "False renewal claim retracted by ORV-0013 and confirmed expired by Tier 1 official notice ORV-0016."
    },
    {
      type: "tier4_rumour",
      badge: "TIER 4 SENSATIONAL",
      severity: "medium",
      doc_id: "ORV-0010",
      pub_date: "2026-10-04",
      title: "Orvan port gone (Social Post)",
      description: "Unverified panic claim. Down-weighted by reliability tier rules (Tier 4 cannot support fact claims)."
    },
    {
      type: "tier4_rumour",
      badge: "TIER 4 SENSATIONAL",
      severity: "medium",
      doc_id: "ORV-0026",
      pub_date: "2026-10-30",
      title: "Sources: every grain ship sunk (Blog Post)",
      description: "Fabricated maritime sinkings. Disproved by commercial port logs ORV-0012."
    },
    {
      type: "tier4_rumour",
      badge: "TIER 4 SENSATIONAL",
      severity: "medium",
      doc_id: "ORV-0028",
      pub_date: "2026-11-05",
      title: "FAMINE FEAR AS ORVAN GRAIN VANISHES (Tabloid)",
      description: "Tabloid hyperbole ignored in favor of hard customs filings."
    }
  ]
};

// Live Feed Replay
export const LIVE_NEWS_FEED = [
  { id: 1, date: "2026-07-15", doc_id: "ATL-0014", tier: "Tier 1", source: "Runemark Atlas", text: "Corridor baseline: Orvan sea corridor handles 68% of regional grain transits via Southern Channel." },
  { id: 2, date: "2026-09-08", doc_id: "ORV-0008", tier: "Tier 2", source: "Shipping Dispatch", text: "Orvan Grain Port reports dockworkers strike entering first week; loadings slow." },
  { id: 3, date: "2026-10-12", doc_id: "ORV-0012", tier: "Tier 1", source: "Gov Port Bulletin", text: "Orvan Grain Port loadings fall from 250,000 tonnes in July to 84,000 tonnes in October." },
  { id: 4, date: "2026-11-15", doc_id: "ORV-0016", tier: "Tier 1", source: "Realm Trade Ministry", text: "OFFICIAL: One-year Orvan Corridor Agreement expires with no renewal agreement in place." },
  { id: 5, date: "2026-11-20", doc_id: "ORV-0043", tier: "Tier 2", source: "Regional News", text: "[RETRACTED] Corridor renewed for second year (Debunked by ORV-0013)." },
  { id: 6, date: "2026-12-05", doc_id: "ORV-0033", tier: "Tier 1", source: "Ravik Ministry of Rail", text: "Ravik Rail Link expands freight slots to absorb diverted grain overland." },
  { id: 7, date: "2026-12-28", doc_id: "ORV-0009", tier: "Tier 1", source: "Trade Note", text: "December Orvan-Midgard wheat transits close at USD 34.1M (down 59.8% YoY)." },
  { id: 8, date: "2027-01-14", doc_id: "ORV-0027", tier: "Tier 1", source: "Trade Note", text: "Alternative supply line: Vanir wheat deliveries to Midgard jump 42% in Q4." }
];

// Trial Debate Claims & Rulings for Run 1 and Run 2
export const TRIAL_ROUNDS_DATA = {
  run1: {
    run_no: 1,
    sufficiency: "SEND_BACK_INSUFFICIENT",
    send_back_reason: "Thor and Loki focused exclusively on maritime port decline. Evidence regarding rail substitution capacity and secondary grain (Maize) exposure remains thin. Heimdall must retrieve specific overland customs data and Tolan maize figures.",
    thor_claims: [
      {
        id: "TC-101",
        country: "Midgard",
        sector: "Wheat",
        kind: "SOURCED_FACT",
        citation: "ORV-0009#P7",
        text: "Direct monthly Orvan-to-Midgard sea wheat transit collapsed from $90.0M (July 2026) to $34.1M (Dec 2026), representing a severe 62.1% loss of trade value.",
        estimate: "High: -62.1% (Loss of $55.9M/mo)",
        attacked_by: "LC-101",
        ruling: "UPHELD",
        ruling_basis: "Strict calculation from verified Trade Note table rows P2 vs P7."
      },
      {
        id: "TC-102",
        country: "Tolan",
        sector: "Wheat",
        kind: "INFERENCE",
        citation: "ORV-0045",
        text: "Tolan faces an extreme 80% to 90% deficit in wheat supply as Corvan Grain channel checks indicate maritime shipments are essentially frozen.",
        estimate: "High: -85.0% Exposure",
        attacked_by: "LC-102",
        ruling: "CONTESTED",
        ruling_basis: "ORV-0045 is an analyst note without customs verification. Overlooks small-vessel coastal rerouting reported in ORV-0037."
      }
    ],
    loki_claims: [
      {
        id: "LC-101",
        country: "Midgard",
        sector: "Wheat",
        kind: "INFERENCE",
        citation: "ORV-0001",
        text: "The disruption is largely cushioned by rail transit through Ravik; Vantro Trading confirms markets have adapted and net disruption is limited to under 15%.",
        estimate: "Low: -15.0% Exposure",
        attacked_by: "TC-101",
        ruling: "CONCEDED",
        ruling_basis: "Thor presented ORV-0001 text explicitly stating 'rail is a partial substitute, not a replacement'. Loki concedes rail absorbs at most 35% of volume."
      },
      {
        id: "LC-102",
        country: "Tolan",
        sector: "Wheat",
        kind: "SOURCED_FACT",
        citation: "ORV-0037",
        text: "Tolan's domestic small boat coastal fleet expanded coastal transshipments, compensating for deep-water berth freezes.",
        estimate: "Low: -22.0% Exposure",
        attacked_by: null,
        ruling: "UPHELD",
        ruling_basis: "Verified by port harbor master bulletin ORV-0037 and commercial report ORV-0042."
      }
    ]
  },
  run2: {
    run_no: 2,
    sufficiency: "SUFFICIENT_PROCEED_TO_VERDICT",
    new_evidence_retrieved: ["ORV-0027", "ORV-0029", "ORV-0030", "ORV-0044", "ORV-0046", "ORV-0050"],
    memory_impact: "Loki memory applied: In Run 1 Tier 4 tabloid was rejected; Loki adjusted query filter to 'tier_max: 2' and retrieved hard trade notes ORV-0027 & ORV-0044.",
    thor_claims: [
      {
        id: "TC-201",
        country: "Midgard",
        sector: "Wheat",
        kind: "SOURCED_FACT",
        citation: "ORV-0009#P4-P7",
        text: "Sustained Q4 maritime wheat deliveries averaged only $35.5M/mo vs 2025 baseline of $89.9M/mo. Structural sea loss stands at -$54.4M per month (-60.5%).",
        estimate: "High: -$54.4M / month (-60.5%)",
        ruling: "UPHELD",
        ruling_basis: "Confirmed by verified customs table. Fact established."
      },
      {
        id: "TC-202",
        country: "Midgard",
        sector: "Maize",
        kind: "SOURCED_FACT",
        citation: "ORV-0030#P3-P6",
        text: "Orvan to Midgard Maize imports fell from $42.0M in Aug 2026 to $14.2M in Nov 2026. Feed grain supply faces a severe 66.2% cut.",
        estimate: "High: -66.2% ($27.8M drop)",
        ruling: "UPHELD",
        ruling_basis: "Derived from newly ingested trade note ORV-0030."
      },
      {
        id: "TC-203",
        country: "Tolan",
        sector: "Wheat & Maize",
        kind: "INFERENCE",
        citation: "ORV-0046",
        text: "Tolan suffers a minimum 55% loss across both grains despite coastal craft, because high winter tariffs limit deep-sea re-docking.",
        estimate: "High: -55.0% Exposure",
        ruling: "CONTESTED",
        ruling_basis: "Conflates wheat and maize; Vanir substitution in ORV-0044 significantly reduces wheat exposure."
      }
    ],
    loki_claims: [
      {
        id: "LC-201",
        country: "Midgard",
        sector: "Wheat",
        kind: "SOURCED_FACT",
        citation: "ORV-0027",
        text: "Vanir to Midgard bilateral wheat route surged from $18.2M to $36.5M in Q4 (+100.5%), offsetting $18.3M of the Orvan loss.",
        estimate: "Low: Net loss -$36.1M/mo (-40.1%)",
        ruling: "UPHELD",
        ruling_basis: "Established. Trade note ORV-0027 proves bilateral diversion."
      },
      {
        id: "LC-202",
        country: "Midgard",
        sector: "Rail Mitigation",
        kind: "SOURCED_FACT",
        citation: "ORV-0050",
        text: "Ravik Rail Link added 4 daily freight trains carrying 32,000 tonnes/mo of grain directly into Midgard, reducing physical volume shortfall to -38%.",
        estimate: "Mitigation: 32k tonnes / mo",
        ruling: "UPHELD",
        ruling_basis: "Sourced fact from railway operational filings."
      },
      {
        id: "LC-203",
        country: "Tolan",
        sector: "Wheat",
        kind: "SOURCED_FACT",
        citation: "ORV-0044",
        text: "Vanir to Tolan wheat shipments rose by $12.4M in Nov-Dec, compensating for 48% of the Orvan route shortfall.",
        estimate: "Low: -28.0% Net Exposure",
        ruling: "UPHELD",
        ruling_basis: "Proven via ORV-0044 trade table."
      }
    ]
  }
};

// Odin's Final Calibrated Exposure Matrix
export const EXPOSURE_MATRIX = [
  {
    country: "Midgard",
    sector: "Wheat",
    unit: "USD M / Month",
    baseline: "$89.9M",
    thor_range: "-$54.4M (-60.5%)",
    loki_range: "-$36.1M (-40.1%)",
    odin_ruling: "-$39.5M to -$46.0M (-44.0% to -51.2%)",
    status: "ESTABLISHED",
    confidence: "94%",
    key_drivers: "Orvan sea route collapsed (-$54M), softened by Vanir substitution (+$18M) and Ravik rail relief."
  },
  {
    country: "Midgard",
    sector: "Maize",
    unit: "USD M / Month",
    baseline: "$41.5M",
    thor_range: "-$27.8M (-66.2%)",
    loki_range: "-$16.5M (-39.8%)",
    odin_ruling: "-$20.0M to -$24.5M (-48.2% to -59.0%)",
    status: "ESTABLISHED",
    confidence: "88%",
    key_drivers: "Limited alternative maize suppliers in northern realms; feed mills face higher net contraction."
  },
  {
    country: "Tolan",
    sector: "Wheat",
    unit: "USD M / Month",
    baseline: "$32.0M",
    thor_range: "-$17.6M (-55.0%)",
    loki_range: "-$9.0M (-28.0%)",
    odin_ruling: "-$10.5M to -$13.5M (-32.8% to -42.2%)",
    status: "ESTABLISHED",
    confidence: "91%",
    key_drivers: "Tolan coastal fleet agility and direct Vanir bilateral imports cushion 48% of gross loss."
  },
  {
    country: "Tolan",
    sector: "Maize",
    unit: "USD M / Month",
    baseline: "$14.8M",
    thor_range: "-$8.2M (-55.4%)",
    loki_range: "-$4.0M (-27.0%)",
    odin_ruling: "-$5.2M to -$6.8M (-35.1% to -46.0%)",
    status: "CONTESTED",
    confidence: "76%",
    key_drivers: "Contested inventory drawdowns; livestock feed substitutions remain under active scrutiny."
  }
];

// Document Pool Archive for Click-Through Modal
export const DOCUMENT_CATALOG = {
  "ORV-0009": {
    doc_id: "ORV-0009",
    event_id: "E5",
    title: "Trade note: Orvan to Midgard, wheat, July to December 2026",
    source_name: "Realm Trade Ministry",
    source_type: "trade_note",
    reliability: "Tier 1 (Official)",
    pub_date: "2027-01-19",
    country: "Midgard",
    sector: "Wheat",
    body: `Route: Orvan to Midgard, wheat.\n\nIn July 2026, the value was USD 90.0M and the volume was 250,000 tonnes.\nIn August 2026, the value was USD 96.1M and the volume was 267,000 tonnes.\nIn September 2026, the value was USD 38.2M and the volume was 93,000 tonnes.\nIn October 2026, the value was USD 34.5M and the volume was 84,000 tonnes.\nIn November 2026, the value was USD 35.3M and the volume was 86,000 tonnes.\nIn December 2026, the value was USD 34.1M and the volume was 83,000 tonnes.\n\nBaseline comparison (2025): July was $94.7M (263k t), Dec was $85.0M (236k t).\nConclusion: December marked the weakest month of the half-year as maritime transits halted.`,
    trade_table: [
      { month: "2026-07", value_usd: "90.0M", volume_tonnes: "250,000", status: "ok" },
      { month: "2026-08", value_usd: "96.1M", volume_tonnes: "267,000", status: "ok" },
      { month: "2026-09", value_usd: "38.2M", volume_tonnes: "93,000", status: "ok" },
      { month: "2026-10", value_usd: "34.5M", volume_tonnes: "84,000", status: "ok" },
      { month: "2026-11", value_usd: "35.3M", volume_tonnes: "86,000", status: "ok" },
      { month: "2026-12", value_usd: "34.1M", volume_tonnes: "83,000", status: "ok" }
    ]
  },
  "ORV-0016": {
    doc_id: "ORV-0016",
    event_id: "E5",
    title: "Corridor Agreement expires with no renewal",
    source_name: "Realm Trade Ministry",
    source_type: "gov_notice",
    reliability: "Tier 1 (Official)",
    pub_date: "2026-11-15",
    country: "Orvan / Midgard / Tolan",
    sector: "Logistics",
    body: `Notice is hereby given that the multilateral grain corridor pact expired at midnight on 14 November 2026 without mutual renewal terms being ratified. Vessel insurance subsidies provided under the convention have formally terminated. Maritime carriers transiting the Southern Channel do so at discretionary commercial risk.`
  },
  "ORV-0001": {
    doc_id: "ORV-0001",
    event_id: "E5",
    title: "Vantro Trading: rail is a partial substitute, not a replacement",
    source_name: "Vantro Trading Logistics",
    source_type: "company_statement",
    reliability: "Tier 2 (Commercial)",
    pub_date: "2026-12-08",
    country: "Ravik / Midgard",
    sector: "Logistics",
    body: `Vantro Logistics confirms that overland rail link operations through Ravik have absorbed up to 35,000 tonnes of diverted grain per month. However, physical railway gauge changes and locomotive availability dictate that rail can serve as an emergency partial cushion, not a full volume substitute for 250,000 tonne maritime bulk vessels.`
  },
  "ATL-0012": {
    doc_id: "ATL-0012",
    event_id: "NONE",
    title: "Runemark Outlet Credibility Guide",
    source_name: "All-Realm Archives",
    source_type: "atlas",
    reliability: "Tier 1 (Archival)",
    pub_date: "2024-01-15",
    country: "Global",
    sector: "Reference",
    body: `Credibility Tier Hierarchy:\n- Tier 1: Official gazettes, customs tables, ministry decrees.\n- Tier 2: Wire services, corporate logistics statements, audited port bulletins.\n- Tier 3: Regional newspapers, unconfirmed brokerage circulars.\n- Tier 4: Tabloids, social messages, anonymous forum postings. Tier 4 documents cannot support independent factual findings.`
  }
};
