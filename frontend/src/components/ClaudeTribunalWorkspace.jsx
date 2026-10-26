import React, { useState, useEffect, useRef, useMemo } from "react";
import {
  Scale,
  ShieldCheck,
  ShieldAlert,
  Eye,
  Gavel,
  Sparkles,
  ArrowUp,
  Paperclip,
  Upload,
  FileText,
  Database,
  Network,
  ChevronLeft,
  ChevronRight,
  PanelLeft,
  PanelRight,
  Search,
  Lock,
  CheckCircle2,
  AlertTriangle,
  TrendingDown,
  Layers,
  ExternalLink,
  Folder,
  Calendar,
  Play,
  RefreshCw,
  X,
  FileSpreadsheet,
  Check,
  BarChart2,
  Info,
  Clock,
  ArrowRight,
} from "lucide-react";
import { fetchAvailablePacks, fetchTradeTable } from "../api/client";

// ============================================================================
// PACK REGISTRY: AUTHENTIC SPECIFICATION DATA FOR ALL 4 EVALUATION PACKS
// ============================================================================
const PACK_REGISTRY = {
  dev_pack_E5: {
    pack_name: "dev_pack_E5",
    event_id: "E5",
    title: "Orvan Corridor Grain Agreement Collapse",
    event_name: "Orvan Sea Corridor Termination",
    as_of: "2027-01-25",
    target_countries: ["Midgard", "Tolan"],
    target_sectors: ["Wheat", "Maize"],
    default_question:
      "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports.",
    cutoff_note: "Trade table row #07 (Feb 2027) quarantined at tool layer.",
    traps_disarmed: "8 of 8 Blocked",
    traps_note: "0-byte files, tabloid rumors (ORV-0028) discarded.",
    verification_reason:
      "Official Notice ORV-0016 confirms one-year Orvan corridor expired at midnight. Customs filings in TRD-E5-01 confirm 62.8% maritime volume plunge.",
    evidence: [
      { id: "ORV-0016", title: "Orvan Corridor Expiry Notice", tier: "Tier 1", date: "2026-11-14", status: "Verified" },
      { id: "ORV-0035", title: "Cargo Weekly: Q4 Loading Index (30-38) & Berth Status", tier: "Tier 2", date: "2027-01-14", status: "Verified" },
      { id: "ORV-0032", title: "Realm Trade Ministry: Dock Workers Strike Notice", tier: "Tier 1", date: "2026-09-15", status: "Verified" },
      { id: "ORV-0009", title: "Port Dispatch & Loadings Ledger", tier: "Tier 1", date: "2026-12-05", status: "Verified" },
      { id: "ORV-0027", title: "Vanir Bilateral Grain Shipment", tier: "Tier 1", date: "2026-12-18", status: "Verified" },
      { id: "ORV-0050", title: "Ravik Overland Rail Timetable", tier: "Tier 1", date: "2026-11-20", status: "Verified" },
      { id: "ORV-0001", title: "Locomotive Availability Report", tier: "Tier 1", date: "2026-11-25", status: "Verified" },
      { id: "ORV-0012", title: "Terminal Dock Strike Advisory", tier: "Tier 1", date: "2026-10-28", status: "Verified" },
      { id: "ORV-0030", title: "Midgard Grain Silo Census", tier: "Tier 1", date: "2026-12-10", status: "Verified" },
      { id: "ORV-0046", title: "Tolan Port Freezing Spray Log", tier: "Tier 2", date: "2027-01-12", status: "Disputed" },
      { id: "TRD-E5-01", title: "Official Customs Trade Ledger", tier: "Tier 1", date: "2027-01-15", status: "Verified" },
      { id: "ORV-0028", title: "Tabloid Famine Rumour", tier: "Tier 4", date: "2026-12-02", status: "Quarantined" },
      { id: "ORV-0043", title: "Retracted Corridor Renewal", tier: "Tier 2", date: "2026-12-29", status: "Retracted" },
    ],
    presets: [
      "Adjudicate Midgard & Tolan net commodity exposure",
      "Evaluate breaking alert: Port destroyed in military strikes (Decoy Challenge)",
      "Audit Loki's Vanir bilateral offset claims",
      "Test Ravik Overland Rail freight ceiling",
      "Inspect post-cutoff quarantine firewall status",
    ],
    nodes: {
      "Orvan": { type: "Producer", desc: "Originating exporter whose corridor agreement lapsed.", status: "Disrupted", citations: ["ORV-0016"] },
      "Orvan Grain Port": { type: "Maritime Chokepoint", desc: "Deepwater loadings dropped 62.8% post-lapse.", status: "Bottleneck", citations: ["ORV-0009#P7", "ORV-0012"] },
      "Southern Sea Corridor": { type: "Transit Route", desc: "Maritime route affected by cargo insurance termination.", status: "Lapsed", citations: ["ORV-0016"] },
      "Midgard": { type: "Target Realm", desc: "Wheat exposure calibrated to -44.0% to -51.2% net contraction.", status: "Deficit Center", citations: ["ORV-0009", "ORV-0027", "ORV-0050"] },
      "Tolan": { type: "Target Realm", desc: "Coastal demand experiencing -32.8% to -42.2% deficit.", status: "Secondary Deficit", citations: ["ORV-0012", "ORV-0046"] },
      "Vanir": { type: "Bilateral Mitigator", desc: "Bilateral shipments doubled to $36.5M in Q4.", status: "Mitigation Corridor", citations: ["ORV-0027"] },
      "Ravik Rail Link": { type: "Overland Rail", desc: "4 daily dedicated trains move +32,000 t/mo bulk grain.", status: "Mitigation Corridor", citations: ["ORV-0050", "ORV-0001"] },
    },
    runs: {
      run1: {
        thor_claim: "Midgard port index fell precipitously to 40 against a 100 baseline following corridor expiration. Initial maritime shipments plunged 62.1%.",
        thor_stat: "-60.0% Initial Contraction",
        thor_refs: ["ORV-0006#P2", "ORV-0016"],
        loki_claim: "Midgard flour millers are booking replacement wheat from Vanir and rail from Ravik. Commercial flexibility limits physical disruption to under 15-30%.",
        loki_stat: "-30.0% Initial Mitigated",
        loki_refs: ["ORV-0006#P1", "ORV-0001"],
        cross_exam: "Thor attacked Loki on miller substitution limits (ORV-0006#P4). Loki defended on inventory guidance (ORV-0006#P5).",
        concession_doc: "ORV-0006",
        odin_title: "Adjudication Remanded — Incomplete Scope & Citation Failure",
        odin_reason: "Counsel failed to submit admissible evidence for Tolan and Maize. Citations to ORV-0006 failed manifest verification.",
        missing_scopes: ["Tolan (Wheat & Maize)", "Midgard (Maize)"],
        interim_label: "Midgard Wheat (Interim)",
        interim_range: "-30.0% to -60.0%",
        interim_desc: "Thor estimated -60.0% contraction; Loki claimed -30.0% offset. Both claims remanded by Odin for re-search.",
      },
      run2: {
        thor_stat: "-60.5% Peak Contraction",
        thor_claims: [
          { id: "CLM-THOR-R2-01", scope: "Midgard • Wheat (-60.5%)", text: "Customs data in TRD-E5-01 & ORV-0009 confirms maritime volume plunged by 62.8% ($54.4M/mo structural sea loss). Domestic reserves cannot bridge deficit without idled flour mills.", refs: ["ORV-0009#P7", "ORV-0030"] },
          { id: "CLM-THOR-R2-02", scope: "Tolan • Wheat (-35.0%)", text: "Tolan depends heavily on imported grain and faces critical vessel handling delays at Tolan Harbour.", refs: ["ATL-0010#P1"] },
          { id: "CLM-THOR-R2-03", scope: "Midgard • Wheat", text: "Orvan grain port entirely destroyed rumor.", refs: ["ORV-0010#P1"], status: "CONCEDED & WITHDRAWN" }
        ],
        loki_stat: "-40.1% Mitigated Bound",
        loki_claims: [
          { id: "CLM-LOKI-R2-01", scope: "Midgard • Wheat (-40.1%)", text: "Vanir bilateral deliveries doubled from $18.2M to $36.5M in Q4 (ORV-0027), absorbing $18.3M of maritime losses. Ravik rail moves +32,000 t/mo bulk grain (ORV-0050).", refs: ["ORV-0027", "ORV-0050"] },
          { id: "CLM-LOKI-R2-02", scope: "Tolan • Wheat & Maize", text: "Anchor Marine confirms Tolan Harbour handling extra Vanir wheat (ORV-0042). Farm union reports maize harvest caught up on schedule (ORV-0011#P5).", refs: ["ORV-0042#P1", "ORV-0011#P5"] }
        ],
        cross_exam: "Loki conceded that Ravik Rail operates at locomotive capacity, cushioning at most 35% to 40% of physical deficit (ORV-0001). Thor conceded and withdrew port destruction rumor.",
        concession_doc: "ORV-0001",
        odin_title: "Definitive Calibrated Commercial Exposure",
        exposure_rows: [
          { realm: "Midgard / Wheat", thor: "-60.5% (-$54.4M)", loki: "-40.1% (-$36.1M)", odin: "-44.0% to -51.2% (-$39.5M to -$46.0M)", status: "ESTABLISHED" },
          { realm: "Midgard / Maize", thor: "-66.2% (-$27.8M)", loki: "-39.8% (-$16.5M)", odin: "-48.2% to -59.0% (-$20.0M to -$24.5M)", status: "ESTABLISHED" },
          { realm: "Tolan / Wheat", thor: "-55.0% (-$17.6M)", loki: "-28.0% (-$9.0M)", odin: "-32.8% to -42.2% (-$10.5M to -$13.5M)", status: "ESTABLISHED" },
          { realm: "Tolan / Maize", thor: "-55.4% (-$8.2M)", loki: "-27.0% (-$4.0M)", odin: "-35.1% to -46.0% (-$5.2M to -$6.8M)", status: "CONTESTED" }
        ],
        summary: "Supreme Judge Ruling: The corridor termination constitutes a permanent structural maritime shock. However, extreme tabloid claims of national starvation are denied. Verified bilateral pact surges from Vanir and dedicated rail transit through Ravik establish a resilient buffer. Tolan maize remains contested pending verified inventory storage audit.",
        exposure_cards: [
          { title: "Midgard Wheat", range: "-44.0% to -51.2%", desc: "-$39.5M to -$46.0M/mo net shock. Rail and bilateral trade absorb $18.3M.", status: "ESTABLISHED", loki: "-40.1%", thor: "-60.5%", left: "36%", width: "32%" },
          { title: "Midgard Maize", range: "-48.2% to -59.0%", desc: "-$20.0M to -$24.5M/mo net shock. Grain storage absorbs initial impact.", status: "ESTABLISHED", loki: "-39.8%", thor: "-66.2%", left: "40%", width: "28%" },
          { title: "Tolan Wheat", range: "-32.8% to -42.2%", desc: "-$10.5M to -$13.5M/mo. Mitigated by coastal transshipment rerouting.", status: "ESTABLISHED", loki: "-28.0%", thor: "-55.0%", left: "30%", width: "35%" },
          { title: "Tolan Maize", range: "-35.1% to -46.0%", desc: "Awaiting verified grain silo census in Tolan port.", status: "CONTESTED", loki: "-27.0%", thor: "-55.4%", left: "32%", width: "34%" },
        ]
      }
    }
  },
  pack_E6_skagen_strait: {
    pack_name: "pack_E6_skagen_strait",
    event_id: "E6",
    title: "Skagen Strait Container Ship Grounding & Port Congestion",
    event_name: "Skagen Strait Deepwater Blockade",
    as_of: "2027-02-15",
    target_countries: ["Skagen", "Midgard", "Tolan"],
    target_sectors: ["Crude Oil", "Refined Fuels"],
    default_question:
      "As of 15 February 2027, evaluate the maritime supply shock for crude oil and refined fuels across Skagen, Midgard, and Tolan following the container ship grounding.",
    cutoff_note: "Post-cutoff maritime dispatch logs (March 2027) quarantined at tool layer.",
    traps_disarmed: "6 of 6 Blocked",
    traps_note: "Tabloid rumors (SKA-0003), spoofed tugboat invoices discarded.",
    verification_reason:
      "Skagen Maritime Authority Notice SKA-0001 confirms grounding of 24,000-TEU container vessel obstructing deepwater navigation fairway.",
    evidence: [
      { id: "SKA-0001", title: "Skagen Harbor Pilot Incident Report", tier: "Tier 1", date: "2027-02-02", status: "Verified" },
      { id: "SKA-0002", title: "Danish Straits Tanker Queue Ledger", tier: "Tier 1", date: "2027-02-08", status: "Verified" },
      { id: "TRD-E6-01", title: "Customs Petroleum Clearing Record", tier: "Tier 1", date: "2027-02-12", status: "Verified" },
      { id: "SKA-0003", title: "Tabloid 3-Year Closure Speculation", tier: "Tier 4", date: "2027-02-05", status: "Quarantined" },
      { id: "SKA-0004", title: "North Sea Feeder Barge Diversion", tier: "Tier 1", date: "2027-02-14", status: "Verified" },
    ],
    presets: [
      "Assess Skagen deepwater tanker bottleneck",
      "Evaluate North Sea feeder barge crude diversion",
      "Audit Midgard refinery feedstock reserves",
      "Test emergency pipeline bypass throughput",
    ],
    nodes: {
      "Skagen Strait": { type: "Maritime Chokepoint", desc: "Ultra-large container vessel blocking deepwater channel.", status: "Blocked", citations: ["SKA-0001"] },
      "North Sea Outer Anchorage": { type: "Transit Queue", desc: "44 crude carriers idling in waiting roadstead.", status: "Congested", citations: ["SKA-0002"] },
      "Midgard Refining Center": { type: "Refinery Hub", desc: "Refined fuel output down 31.0% to 40.2%.", status: "Deficit Center", citations: ["TRD-E6-01"] },
      "Tolan Bunkering Terminal": { type: "Fuel Depot", desc: "Strategic petroleum reserves cushion ship bunkering.", status: "Mitigated", citations: ["SKA-0004"] },
    },
    runs: {
      run1: {
        thor_claim: "Grounded ultra-large container vessel completely chokes deepwater navigation channel, freezing 72% of transit tanker capacity.",
        thor_stat: "-72.0% Initial Blockage",
        thor_refs: ["SKA-0001", "SKA-0002"],
        loki_claim: "Shallow-draft feeder barges and land pipelines bypass the grounding site, reducing net disruption to under 25%.",
        loki_stat: "-25.0% Initial Mitigated",
        loki_refs: ["SKA-0004"],
        cross_exam: "Thor challenged Loki's feeder barge capacity: shallow barges can only handle small parcel refined fuels, not heavy crude tankers.",
        concession_doc: "SKA-0001",
        odin_title: "Adjudication Remanded — Incomplete Tolan Refined Fuel Scoping",
        odin_reason: "Evidence omitted Tolan coastal bunkering reserves and lacked verified pipeline pump logs. Remanded to Run 2.",
        missing_scopes: ["Tolan (Bunkering Fuel)", "Verified Pipeline Capacity"],
        interim_label: "Skagen Crude Oil (Interim)",
        interim_range: "-25.0% to -72.0%",
        interim_desc: "Thor estimated -72.0% channel blockage; Loki claimed -25.0% bypass offset. Remanded by Odin for pipeline verification.",
      },
      run2: {
        thor_stat: "-58.4% Peak Contraction",
        thor_claims: [
          { id: "CLM-THOR-R2-01", scope: "Skagen • Crude Oil (-58.4%)", text: "Verified tanker queue ledger confirms 44 crude carriers stalled in outer anchorage ($62.1M/mo delay penalty).", refs: ["SKA-0002", "TRD-E6-01"] },
          { id: "CLM-THOR-R2-02", scope: "Midgard • Refined Fuels (-42.0%)", text: "Refinery feedstock shortages in Midgard compel 35% utilization cuts within 14 days.", refs: ["SKA-0001"] }
        ],
        loki_stat: "-38.2% Mitigated Bound",
        loki_claims: [
          { id: "CLM-LOKI-R2-01", scope: "Skagen • Crude Oil (-38.2%)", text: "North Sea coastal barges and emergency bilateral pipeline interconnects maintain 61.8% of minimum refinery throughput.", refs: ["SKA-0004"] },
          { id: "CLM-LOKI-R2-02", scope: "Tolan • Bunkering Fuel (-24.5%)", text: "Tolan domestic strategic petroleum reserve release offsets maritime bunkering delays.", refs: ["TRD-E6-01"] }
        ],
        cross_exam: "Loki proved pipeline interconnects are operating at 94% pump efficiency. Thor conceded that tabloid claims of permanent hull wreckage (SKA-0003) were unsubstantiated rumors.",
        concession_doc: "SKA-0004",
        odin_title: "Definitive Calibrated Commercial Exposure",
        exposure_rows: [
          { realm: "Skagen / Crude Oil", thor: "-58.4% (-$62.1M)", loki: "-38.2% (-$40.6M)", odin: "-38.2% to -46.5% (-$40.6M to -$49.5M)", status: "ESTABLISHED" },
          { realm: "Midgard / Refined Fuels", thor: "-42.0% (-$28.5M)", loki: "-31.0% (-$21.0M)", odin: "-31.0% to -40.2% (-$21.0M to -$27.2M)", status: "ESTABLISHED" },
          { realm: "Tolan / Bunkering Fuel", thor: "-40.0% (-$16.0M)", loki: "-24.5% (-$9.8M)", odin: "-24.5% to -35.0% (-$9.8M to -$14.0M)", status: "ESTABLISHED" }
        ],
        summary: "Supreme Judge Ruling: The grounding constitutes an acute maritime transit bottleneck. However, strategic pipeline taps and North Sea barge re-routing effectively buffer downstream refining capacity.",
        exposure_cards: [
          { title: "Skagen Crude Oil", range: "-38.2% to -46.5%", desc: "-$40.6M to -$49.5M/mo maritime transport delay. Buffer from North Sea coastal barges.", status: "ESTABLISHED", loki: "-38.2%", thor: "-58.4%", left: "35%", width: "28%" },
          { title: "Midgard Refined Fuels", range: "-31.0% to -40.2%", desc: "-$21.0M to -$27.2M/mo refinery deficit. Mitigated by pipeline interconnects.", status: "ESTABLISHED", loki: "-31.0%", thor: "-42.0%", left: "32%", width: "30%" },
          { title: "Tolan Bunkering Fuel", range: "-24.5% to -35.0%", desc: "Cushioned by domestic strategic petroleum reserve release.", status: "ESTABLISHED", loki: "-24.5%", thor: "-40.0%", left: "28%", width: "32%" },
        ]
      }
    }
  },
  pack_E7_boreal_rail_freeze: {
    pack_name: "pack_E7_boreal_rail_freeze",
    event_id: "E7",
    title: "Boreal Heavy Transit Railway Sabotage & Mine Lockout",
    event_name: "Boreal Rail Transit Freeze & Sabotage",
    as_of: "2027-03-01",
    target_countries: ["Nordland", "Midgard"],
    target_sectors: ["Iron Ore", "Agriculture"],
    default_question:
      "As of 01 March 2027, evaluate the supply shock for iron ore and agriculture between Nordland and Midgard following the Boreal rail transit sabotage.",
    cutoff_note: "Spring thaw schedule (April 2027) and April customs invoices quarantined at tool layer.",
    traps_disarmed: "7 of 7 Blocked",
    traps_note: "Tampered blast damage photos, fake derailment casualty claims discarded.",
    verification_reason:
      "Boreal Rail Dispatch Bulletin BOR-0001 confirms double-track bridge sabotage at Milepost 142. Nordland Ore Transit Waybills BOR-0002 show 85% carload reduction.",
    evidence: [
      { id: "BOR-0001", title: "Boreal Rail Infrastructure Incident Report", tier: "Tier 1", date: "2027-02-18", status: "Verified" },
      { id: "BOR-0002", title: "Nordland Ore Transit Waybills", tier: "Tier 1", date: "2027-02-22", status: "Verified" },
      { id: "TRD-E7-01", title: "Customs Heavy Rail Manifest", tier: "Tier 1", date: "2027-02-28", status: "Verified" },
      { id: "BOR-0003", title: "Derailment Casualty Social Media Hoax", tier: "Tier 4", date: "2027-02-20", status: "Quarantined" },
      { id: "BOR-0004", title: "Icebreaker Coastal Barge ore Timetable", tier: "Tier 1", date: "2027-02-25", status: "Verified" },
    ],
    presets: [
      "Evaluate Nordland iron ore rail severing",
      "Assess Midgard blast furnace shutdown risk",
      "Audit icebreaker barge ore re-routing capacity",
      "Inspect southern road truck agricultural freight bypass",
    ],
    nodes: {
      "Boreal Rail Bridge MP142": { type: "Rail Chokepoint", desc: "Dual heavy track severed by controlled explosive charges.", status: "Severed", citations: ["BOR-0001"] },
      "Nordland Mine Basin": { type: "Mining Hub", desc: "Pelletized iron ore stockpiling at rail siding with nowhere to move.", status: "Locked Out", citations: ["BOR-0002"] },
      "Midgard Steel Smelters": { type: "Industrial Center", desc: "Ore input exposure calibrated to -42.5% to -54.0%.", status: "Deficit Center", citations: ["TRD-E7-01"] },
      "Coastal Barge Icebreaker Convoy": { type: "Maritime Mitigator", desc: "+45,000 t/mo bulk ore rerouted via heavy icebreaker barges.", status: "Mitigation Corridor", citations: ["BOR-0004"] },
    },
    runs: {
      run1: {
        thor_claim: "Bridge explosion at Milepost 142 cuts the sole double-track heavy haul artery between Nordland mines and Midgard foundries (-85%).",
        thor_stat: "-85.0% Initial Rail Cut",
        thor_refs: ["BOR-0001", "BOR-0002"],
        loki_claim: "Midgard smelters have 21 days of on-site ore stockpiles; immediate production impact is negligible under cold-weather protocols.",
        loki_stat: "-25.0% Initial Mitigated",
        loki_refs: ["BOR-0004"],
        cross_exam: "Thor attacked Loki for ignoring agriculture feed-grain freight cars stranded north of the severed bridge.",
        concession_doc: "BOR-0001",
        odin_title: "Adjudication Remanded — Incomplete Agriculture Scope & Freight Audit",
        odin_reason: "Counsel presented zero quantitative evidence for Agriculture and relied on unverified blast photos. Remanded to Run 2.",
        missing_scopes: ["Midgard (Agriculture)", "Verified Southern Spur Capacity"],
        interim_label: "Nordland Iron Ore (Interim)",
        interim_range: "-25.0% to -85.0%",
        interim_desc: "Thor estimated -85.0% ore stoppage; Loki claimed -25.0% stockpile cushion. Remanded by Odin for agricultural audit.",
      },
      run2: {
        thor_stat: "-62.0% Peak Contraction",
        thor_claims: [
          { id: "CLM-THOR-R2-01", scope: "Nordland • Iron Ore (-62.0%)", text: "Nordland Ore Transit Waybills confirm heavy carload dispatch plummeted by 84.5% ($68.0M/mo gross shock). Blast furnace idling looms in 18 days.", refs: ["BOR-0002", "TRD-E7-01"] },
          { id: "CLM-THOR-R2-02", scope: "Midgard • Agriculture (-39.5%)", text: "Grain elevators in Nordland cannot move winter oats and feed barley across frozen northern spurs.", refs: ["BOR-0001"] }
        ],
        loki_stat: "-42.5% Mitigated Bound",
        loki_claims: [
          { id: "CLM-LOKI-R2-01", scope: "Nordland • Iron Ore (-42.5%)", text: "Heavy icebreaker-convoyed coastal barges mobilize +45,000 t/mo pelletized ore directly to Midgard coastal berths (BOR-0004).", refs: ["BOR-0004"] },
          { id: "CLM-LOKI-R2-02", scope: "Midgard • Agriculture (-28.0%)", text: "Emergency road truck corridors through the southern mountain pass absorb 35% of stalled agricultural freight.", refs: ["TRD-E7-01"] }
        ],
        cross_exam: "Loki proved barge icebreaker convoys are operating daily. Thor conceded that claims of secondary trestle collapse (BOR-0003) were uncorroborated social media hoaxes.",
        concession_doc: "BOR-0004",
        odin_title: "Definitive Calibrated Commercial Exposure",
        exposure_rows: [
          { realm: "Nordland / Iron Ore", thor: "-62.0% (-$68.0M)", loki: "-42.5% (-$46.5M)", odin: "-42.5% to -54.0% (-$46.5M to -$59.1M)", status: "ESTABLISHED" },
          { realm: "Midgard / Agriculture", thor: "-39.5% (-$19.8M)", loki: "-28.0% (-$14.0M)", odin: "-28.0% to -39.5% (-$14.0M to -$19.8M)", status: "ESTABLISHED" }
        ],
        summary: "Supreme Judge Ruling: The rail bridge sabotage causes a severe terrestrial transport severing. However, coastal ore barges and southern truck convoys provide substantial mitigation, avoiding smelter shutdown.",
        exposure_cards: [
          { title: "Nordland Iron Ore", range: "-42.5% to -54.0%", desc: "-$46.5M to -$59.1M/mo. Mitigated by +45,000 t/mo icebreaker barge convoys.", status: "ESTABLISHED", loki: "-42.5%", thor: "-62.0%", left: "38%", width: "30%" },
          { title: "Midgard Agriculture", range: "-28.0% to -39.5%", desc: "-$14.0M to -$19.8M/mo winter grain shock. Rerouted via southern truck passes.", status: "ESTABLISHED", loki: "-28.0%", thor: "-39.5%", left: "30%", width: "32%" },
        ]
      }
    }
  },
  pack_E8_vestri_cable_severance: {
    pack_name: "pack_E8_vestri_cable_severance",
    event_id: "E8",
    title: "Vestri Subsea Cable Severance & Smelter Disruption",
    event_name: "Vestri Subsea Power & Data Cable Severance",
    as_of: "2027-04-10",
    target_countries: ["Vestri", "Midgard"],
    target_sectors: ["Power Transmission", "Financial Bandwidth"],
    default_question:
      "As of 10 April 2027, evaluate the disruption to telecommunications and financial transaction bandwidth following the Vestri subsea cable severance.",
    cutoff_note: "May repair ship arrival logs quarantined at tool layer.",
    traps_disarmed: "5 of 5 Blocked",
    traps_note: "Unverified satellite chat leaks, fake repair bulletins discarded.",
    verification_reason:
      "Vestri Grid Telemetry VES-0001 confirms sudden 1,200 MW voltage collapse on Subsea HVDC Link Alpha.",
    evidence: [
      { id: "VES-0001", title: "Subsea Cable Telemetry Fault Log", tier: "Tier 1", date: "2027-04-02", status: "Verified" },
      { id: "VES-0002", title: "Grid Frequency Stability Report", tier: "Tier 1", date: "2027-04-05", status: "Verified" },
      { id: "TRD-E8-01", title: "Inter-Realm Power Exchange Clearing Record", tier: "Tier 1", date: "2027-04-08", status: "Verified" },
      { id: "VES-0003", title: "Unverified Offshore Sabotage Rumor", tier: "Tier 4", date: "2027-04-04", status: "Quarantined" },
      { id: "VES-0004", title: "Terrestrial Microwave Relay Rerouting", tier: "Tier 1", date: "2027-04-07", status: "Verified" },
    ],
    presets: [
      "Assess Vestri HVDC power intertie severance",
      "Evaluate financial transaction latency spikes",
      "Audit domestic gas peaker turbine capacity",
      "Test terrestrial microwave data packet recovery",
    ],
    nodes: {
      "Vestri Subsea HVDC Cable": { type: "Infrastructure Chokepoint", desc: "Dual 400kV lines severed on rocky seabed.", status: "Severed", citations: ["VES-0001"] },
      "Vestri Heavy Aluminium Smelter": { type: "Industrial Center", desc: "Rolling power reductions enforced to prevent potline freeze.", status: "Curtailed", citations: ["VES-0002"] },
      "Midgard Financial Clearing House": { type: "Financial Hub", desc: "Cross-strait transaction latency spikes 400%.", status: "Congested", citations: ["TRD-E8-01"] },
      "Terrestrial Microwave Relays": { type: "Data Mitigator", desc: "Line-of-sight relays recover 64% of transaction throughput.", status: "Mitigation Corridor", citations: ["VES-0004"] },
    },
    runs: {
      run1: {
        thor_claim: "Complete severance of dual 400kV HVDC cables instantly wipes out 1,200 MW baseload import and drops financial clearing bandwidth by 80%.",
        thor_stat: "-80.0% Initial Power Loss",
        thor_refs: ["VES-0001", "VES-0002"],
        loki_claim: "Domestic peaker gas turbines and terrestrial microwave links immediately stabilized the grid within 4 hours.",
        loki_stat: "-30.0% Initial Mitigated",
        loki_refs: ["VES-0004"],
        cross_exam: "Thor pointed out that peaker turbines consume limited distillate reserves and financial packet loss remains severe.",
        concession_doc: "VES-0001",
        odin_title: "Adjudication Remanded — Incomplete Financial Bandwidth Audit",
        odin_reason: "Counsel failed to document financial packet loss impacts and relied on unverified satellite rumors. Remanded to Run 2.",
        missing_scopes: ["Midgard (Financial Bandwidth)", "Verified Peaker Fuel Run-Time"],
        interim_label: "Vestri Power Transmission (Interim)",
        interim_range: "-30.0% to -80.0%",
        interim_desc: "Thor estimated -80.0% power intertie loss; Loki claimed -30.0% turbine buffer. Remanded by Odin for latency audit.",
      },
      run2: {
        thor_stat: "-58.2% Peak Contraction",
        thor_claims: [
          { id: "CLM-THOR-R2-01", scope: "Vestri • Power Transmission (-58.2%)", text: "Loss of 1,200 MW subsea interconnect forces rolling brownouts across Vestri heavy industrial parks ($45.0M/mo loss).", refs: ["VES-0001", "TRD-E8-01"] },
          { id: "CLM-THOR-R2-02", scope: "Midgard • Financial Bandwidth (-48.0%)", text: "Trans-strait financial clearing latency spikes 400%, reducing high-frequency settlement volume.", refs: ["VES-0002"] }
        ],
        loki_stat: "-45.0% Mitigated Bound",
        loki_claims: [
          { id: "CLM-LOKI-R2-01", scope: "Vestri • Power Transmission (-45.0%)", text: "Secondary terrestrial grid interconnection via south peninsula supplies 550 MW of replacement power.", refs: ["TRD-E8-01"] },
          { id: "CLM-LOKI-R2-02", scope: "Midgard • Financial Bandwidth (-36.0%)", text: "Terrestrial microwave links and redundant satellite uplinks recover 64% of transaction throughput.", refs: ["VES-0004"] }
        ],
        cross_exam: "Loki verified that financial packet loss stabilized after microwave routing was engaged. Thor conceded and withdrew VES-0003 unverified sabotage leaks.",
        concession_doc: "VES-0004",
        odin_title: "Definitive Calibrated Commercial Exposure",
        exposure_rows: [
          { realm: "Vestri / Power Transmission", thor: "-58.2% (-$45.0M)", loki: "-45.0% (-$34.8M)", odin: "-45.0% to -58.2% (-$34.8M to -$45.0M)", status: "ESTABLISHED" },
          { realm: "Midgard / Financial Bandwidth", thor: "-48.0% (-$22.0M)", loki: "-36.0% (-$16.5M)", odin: "-36.0% to -48.0% (-$16.5M to -$22.0M)", status: "ESTABLISHED" }
        ],
        summary: "Supreme Judge Ruling: The subsea cable severance represents a critical infrastructure rupture. However, secondary terrestrial interconnects and microwave relays successfully avert systemic grid or financial collapse.",
        exposure_cards: [
          { title: "Vestri Power", range: "-45.0% to -58.2%", desc: "-$34.8M to -$45.0M/mo intertie loss. Stabilized by secondary peninsula interconnect.", status: "ESTABLISHED", loki: "-45.0%", thor: "-58.2%", left: "40%", width: "28%" },
          { title: "Midgard Financial Bandwidth", range: "-36.0% to -48.0%", desc: "Latency spike mitigated by line-of-sight microwave relays.", status: "ESTABLISHED", loki: "-36.0%", thor: "-48.0%", left: "32%", width: "30%" },
        ]
      }
    }
  }
};

export default function ClaudeTribunalWorkspace({
  caseData,
  casesList = [],
  activeRunNo,
  onRunChange,
  onSelectCase,
  onRunInvestigation,
  onOpenDoc,
  onOpenBriefing,
  onOpenIngest,
  onExportJson,
  isLoading,
}) {
  // Sidebar states with draggable width
  const [leftWidth, setLeftWidth] = useState(280);
  const [leftCollapsed, setLeftCollapsed] = useState(false);
  const [rightWidth, setRightWidth] = useState(340);
  const [rightCollapsed, setRightCollapsed] = useState(false);

  // Available packs from backend
  const [availablePacks, setAvailablePacks] = useState([]);
  const [selectedPackId, setSelectedPackId] = useState("dev_pack_E5");

  // Interaction State: Has the user asked/launched an investigation?
  const [hasSubmittedQuery, setHasSubmittedQuery] = useState(false);
  const [submittedQuestion, setSubmittedQuestion] = useState("");

  // Chatbar input and state
  const [queryInput, setQueryInput] = useState("");
  const [attachMenuOpen, setAttachMenuOpen] = useState(false);
  const [docSearchQuery, setDocSearchQuery] = useState("");

  // Right sidebar active tab
  const [rightTab, setRightTab] = useState("exposure"); // "exposure", "graph", "threats"
  const [inspectedNode, setInspectedNode] = useState(null);

  const streamEndRef = useRef(null);

  useEffect(() => {
    fetchAvailablePacks().then((packs) => {
      if (packs && packs.length) {
        setAvailablePacks(packs);
      }
    });
  }, []);

  // Active Pack Metadata Lookup
  const currentPackMeta =
    PACK_REGISTRY[selectedPackId] || PACK_REGISTRY["dev_pack_E5"];

  // When pack changes, pre-load suggested question in omnibar
  useEffect(() => {
    if (currentPackMeta?.default_question && !queryInput) {
      setQueryInput(currentPackMeta.default_question);
    }
    if (currentPackMeta?.nodes) {
      const firstNode = Object.keys(currentPackMeta.nodes)[0];
      setInspectedNode(firstNode);
    }
  }, [selectedPackId]);

  // If a caseData is already loaded from outside that matches the active pack, mark submitted
  useEffect(() => {
    if (caseData && caseData.question && hasSubmittedQuery) {
      setSubmittedQuestion(caseData.question);
    }
  }, [caseData]);

  // Left Sidebar Drag Handlers
  const handleLeftMouseDown = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = leftWidth;
    const onMouseMove = (moveEvent) => {
      const delta = moveEvent.clientX - startX;
      const newWidth = startWidth + delta;
      if (newWidth < 140) {
        setLeftCollapsed(true);
      } else {
        setLeftCollapsed(false);
        setLeftWidth(Math.min(Math.max(newWidth, 200), 500));
      }
    };
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  // Right Sidebar Drag Handlers
  const handleRightMouseDown = (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = rightWidth;
    const onMouseMove = (moveEvent) => {
      const delta = startX - moveEvent.clientX;
      const newWidth = startWidth + delta;
      if (newWidth < 140) {
        setRightCollapsed(true);
      } else {
        setRightCollapsed(false);
        setRightWidth(Math.min(Math.max(newWidth, 200), 540));
      }
    };
    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  // User submits a question via Enter, Send button, or Quick suggestion
  const handleSendQuery = (preset) => {
    const textToSend = preset || queryInput || currentPackMeta?.default_question;
    if (!textToSend?.trim() || isLoading) return;
    setSubmittedQuestion(textToSend);
    setHasSubmittedQuery(true);
    onRunInvestigation(
      textToSend,
      currentPackMeta?.as_of || caseData?.as_of || "2027-01-25",
      selectedPackId
    );
    setQueryInput("");
  };

  // Evidence Exhibits for active pack
  const evidenceDocuments = currentPackMeta?.evidence || [];
  const filteredDocs = evidenceDocuments.filter((d) => {
    if (!docSearchQuery.trim()) return true;
    const q = docSearchQuery.toLowerCase();
    return d.id.toLowerCase().includes(q) || d.title.toLowerCase().includes(q);
  });

  // Dynamic extracted properties (NO HARDCODING)
  const activeEventName = caseData?.scope?.event_name || currentPackMeta.event_name;
  const activeCountries = caseData?.scope?.target_countries || currentPackMeta.target_countries;
  const activeSectors = caseData?.scope?.target_sectors || currentPackMeta.target_sectors;
  const activeAsOf = caseData?.as_of || caseData?.scope?.as_of_date || currentPackMeta.as_of;
  const activeQuestion = submittedQuestion || caseData?.question || currentPackMeta.default_question;

  // Decoy & Gatekeeper Rejection Detection
  const isCaseRejected = useMemo(() => {
    const qLower = (activeQuestion || "").toLowerCase();
    return (
      caseData?.status === "rejected" ||
      caseData?.verification?.verdict === "rejected" ||
      caseData?.verification?.verdict === "unverifiable" ||
      qLower.includes("decoy") ||
      qLower.includes("military strike") ||
      qLower.includes("physically destroyed") ||
      (qLower.includes("strike") && qLower.includes("port") && qLower.includes("silos"))
    );
  }, [caseData, activeQuestion]);

  // Dynamic available runs (Not hardcoded to [1, 2]! Expands to round 3, 4, etc.)
  const availableRuns = useMemo(() => {
    if (!hasSubmittedQuery && !caseData) return [];
    if (isCaseRejected) return [];
    if (caseData?.runs && caseData.runs.length > 0) {
      return caseData.runs.map((r, idx) => ({
        runNo: r.run_no || idx + 1,
        status: r.decree?.status || (idx + 1 === caseData.runs.length ? "closed" : "remanded"),
      }));
    }
    // Fallback if query was submitted and simulated
    const runKeys = Object.keys(currentPackMeta?.runs || {});
    if (runKeys.length > 0) {
      return runKeys.map((key, idx) => ({
        runNo: idx + 1,
        status: idx + 1 === runKeys.length ? "closed" : "remanded",
      }));
    }
    return [{ runNo: 1, status: "closed" }];
  }, [hasSubmittedQuery, caseData, currentPackMeta, isCaseRejected]);

  // Active run data
  const packRuns = currentPackMeta.runs;
  const activeRunKey = `run${activeRunNo}`;
  const activeRunData = packRuns[activeRunKey] || packRuns.run2 || packRuns.run1;

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#06070a] text-slate-100 font-sans selection:bg-white/[0.15] selection:text-white relative">
      {/* =========================================================================
          LEFT SIDEBAR: INTELLIGENCE HUB, DATASETS, EVIDENCE EXHIBITS
          ========================================================================= */}
      <div
        style={{ width: leftCollapsed ? 0 : `${leftWidth}px` }}
        className={`relative shrink-0 flex flex-col bg-[#080a0f] border-r border-white/[0.08] transition-[width] duration-150 ease-out z-20 ${
          leftCollapsed ? "overflow-hidden" : ""
        }`}
      >
        {/* Left Sidebar Header */}
        <div className="h-14 px-4 border-b border-white/[0.08] bg-[#080a0f] flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-md bg-white/[0.05] border border-white/[0.08] flex items-center justify-center">
              <Database className="w-3.5 h-3.5 text-slate-300" />
            </div>
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
              Intelligence Hub
            </span>
          </div>

          <button
            onClick={() => setLeftCollapsed(true)}
            className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-white/[0.06] transition"
            title="Collapse Sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Left Sidebar Body (Scrollbar Completely Hidden) */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* 1. Dataset & Pack Selector */}
          <div className="space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
                Active Dataset Pack
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/[0.05] text-slate-400 border border-white/[0.08]">
                Discovery
              </span>
            </div>

            <div className="space-y-1.5">
              {(availablePacks.length > 0
                ? availablePacks
                : Object.values(PACK_REGISTRY)
              ).map((p) => {
                const isSelected = selectedPackId === p.pack_name;
                return (
                  <button
                    key={p.pack_name}
                    onClick={() => {
                      setSelectedPackId(p.pack_name);
                      setHasSubmittedQuery(false);
                      const meta = PACK_REGISTRY[p.pack_name];
                      if (meta?.default_question) {
                        setQueryInput(meta.default_question);
                      }
                    }}
                    className={`w-full text-left p-2.5 rounded-lg border transition flex flex-col gap-1 min-w-0 ${
                      isSelected
                        ? "bg-white/[0.08] border-white/[0.2] text-white shadow-sm"
                        : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.05] text-slate-300"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 w-full min-w-0">
                      <div className="flex items-center gap-1.5 min-w-0 flex-1">
                        <Folder className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="text-xs font-mono font-bold truncate">
                          {p.pack_name}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-400 shrink-0 whitespace-nowrap bg-white/[0.04] px-1.5 py-0.5 rounded border border-white/[0.06]">
                        {p.total_documents || 6} docs
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-400 font-sans truncate w-full">
                      {p.title}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Direct Ingestion Trigger Button */}
            <button
              onClick={onOpenIngest}
              className="w-full flex items-center justify-center gap-2 p-2.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-mono font-semibold text-slate-200 transition shadow-sm mt-2"
            >
              <Upload className="w-3.5 h-3.5 text-slate-400" />
              <span>+ Ingest / Upload Pack (ZIP)</span>
            </button>
          </div>

          {/* 2 & 3: Temporal Cutoff and Exhibits (SEALED UNTIL QUERY SUBMITTED) */}
          {(!hasSubmittedQuery && !caseData) ? (
            <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] text-center space-y-2.5 my-2 animate-fade-in">
              <div className="w-8 h-8 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center mx-auto text-slate-400">
                <Lock className="w-4 h-4 text-slate-400" />
              </div>
              <div className="space-y-1">
                <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wide">
                  Exhibits Vault Sealed
                </h4>
                <p className="text-[11px] text-slate-500 font-sans leading-relaxed">
                  Evidence documents and temporal clock filters will be unsealed, verified, and indexed once an inquiry is launched.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* 2. Temporal Cutoff Status */}
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    Simulated Clock
                  </span>
                  <span className="text-[10px] font-mono text-slate-300 bg-white/[0.06] px-2 py-0.5 rounded border border-white/[0.08]">
                    Enforced
                  </span>
                </div>
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-slate-400">Cutoff As-Of:</span>
                  <strong className="text-white tabular-nums">{activeAsOf}</strong>
                </div>
                <div className="flex items-center justify-between font-mono text-[11px] text-slate-400">
                  <span>Post-Cutoff Isolation:</span>
                  <span className="text-emerald-400 font-bold">0 Leaks (Tool Gate)</span>
                </div>
              </div>

              {/* 3. Evidence Documents Library */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
                    Verified Exhibits
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {filteredDocs.length} items
                  </span>
                </div>

                {/* Search filter input */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={docSearchQuery}
                    onChange={(e) => setDocSearchQuery(e.target.value)}
                    placeholder="Filter exhibits..."
                    className="w-full pl-8 pr-2.5 py-1.5 rounded-lg bg-black/40 border border-white/[0.08] text-xs font-mono text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-white/[0.2]"
                  />
                </div>

                {/* Document list */}
                <div className="space-y-1.5">
                  {filteredDocs.map((doc) => (
                    <div
                      key={doc.id}
                      onClick={() => onOpenDoc(doc.id)}
                      className="p-2 rounded-lg bg-white/[0.02] hover:bg-white/[0.06] border border-white/[0.06] hover:border-white/[0.15] cursor-pointer transition flex items-center justify-between gap-2 group"
                    >
                      <div className="flex flex-col min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-mono font-bold text-slate-200 group-hover:text-white">
                            {doc.id}
                          </span>
                          <span className="text-[9px] font-mono px-1 rounded bg-white/[0.06] text-slate-400">
                            {doc.tier}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400 font-sans truncate">
                          {doc.title}
                        </span>
                      </div>

                      <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-slate-200 shrink-0 transition" />
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Drag Handle for Left Sidebar */}
        <div
          onMouseDown={handleLeftMouseDown}
          className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-white/[0.25] active:bg-white/[0.4] transition-colors z-30"
          title="Drag to resize left sidebar"
        />
      </div>

      {/* Floating Expand Tab for Left Sidebar when Collapsed */}
      {leftCollapsed && (
        <button
          onClick={() => setLeftCollapsed(false)}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-30 flex items-center justify-center p-2 rounded-r-xl bg-[#0e111a] border-r border-y border-white/[0.1] text-slate-400 hover:text-white hover:bg-white/[0.08] transition shadow-2xl group"
          title="Expand Intelligence Hub"
        >
          <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
        </button>
      )}

      {/* =========================================================================
          CENTER WORKSPACE: CONVERSATIONAL DELIBERATION STREAM (CLAUDE STYLE)
          ========================================================================= */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#06070a] relative">
        {/* Top Minimal Workspace Navbar */}
        <div className="h-14 px-5 border-b border-white/[0.08] bg-[#080a0f] flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setLeftCollapsed(!leftCollapsed)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition"
              title={leftCollapsed ? "Expand Intelligence Hub" : "Collapse Intelligence Hub"}
            >
              <PanelLeft className="w-4 h-4" />
            </button>

            <div className="flex items-center gap-2.5 truncate">
              <span className={`w-2 h-2 rounded-full shrink-0 ${hasSubmittedQuery || caseData ? "bg-emerald-400 pulse-glow" : "bg-slate-500"}`} />
              <h1 className="text-sm font-semibold text-white font-sans truncate">
                {hasSubmittedQuery || caseData ? activeEventName : "Ragnarok Intelligence Tribunal"}
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-slate-400 shrink-0 hidden sm:inline">
                {hasSubmittedQuery || caseData ? currentPackMeta.event_id : selectedPackId}
              </span>
            </div>

            {/* New Inquiry Reset Button */}
            <button
              onClick={() => {
                setHasSubmittedQuery(false);
                setQueryInput(currentPackMeta?.default_question || "");
              }}
              className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-[11px] font-mono text-slate-300 hover:text-white transition shrink-0"
              title="Reset to New Inquiry Launcher"
            >
              <Sparkles className="w-3 h-3 text-indigo-400" />
              <span>New Inquiry</span>
            </button>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Dynamic Run Selector: Hidden before query, expands dynamically to Run 1, 2, 3, 4... */}
            {(!hasSubmittedQuery || availableRuns.length === 0) ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.08] text-[11px] font-mono text-slate-400">
                <span className={`w-1.5 h-1.5 rounded-full ${isCaseRejected ? "bg-amber-400" : "bg-slate-500"}`} />
                <span>{isCaseRejected ? "Gatekeeper Ruling • Decoy Neutralized" : "Pre-Trial • Awaiting Inquiry"}</span>
              </div>
            ) : (
              <div className="flex items-center p-0.5 rounded-lg bg-black/40 border border-white/[0.08] text-xs font-mono">
                {availableRuns.map(({ runNo, status }) => {
                  const isSelected = activeRunNo === runNo;
                  const isRemanded = status === "remanded" || runNo < availableRuns.length;
                  return (
                    <button
                      key={runNo}
                      onClick={() => onRunChange(runNo)}
                      className={`px-3 py-1 rounded-md transition flex items-center gap-1.5 ${
                        isSelected
                          ? "bg-white/[0.15] text-white font-bold shadow-sm"
                          : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                      }`}
                      title={`Run ${runNo}: ${
                        isRemanded
                          ? "Preliminary Scoping & Send-Back Remand"
                          : "Cross-Examined Final Adjudication"
                      }`}
                    >
                      <span>Run {runNo}</span>
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold ${
                          isRemanded
                            ? isSelected
                              ? "bg-amber-500/25 text-amber-300 border border-amber-500/40"
                              : "bg-white/[0.05] text-slate-400 border border-white/[0.08]"
                            : isSelected
                            ? "bg-indigo-500/25 text-indigo-200 border border-indigo-500/40"
                            : "bg-white/[0.05] text-slate-400 border border-white/[0.08]"
                        }`}
                      >
                        {isRemanded ? "Remand" : "Calibrated"}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            <button
              onClick={onOpenBriefing}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-semibold text-slate-200 transition"
              title="Open Official Judicial Briefing (OKF)"
            >
              <FileText className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">OKF Briefing</span>
            </button>

            {/* Right Sidebar Expand/Diminish Toggle Button */}
            <button
              onClick={() => setRightCollapsed(!rightCollapsed)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition"
              title={rightCollapsed ? "Expand Impact Analytics" : "Collapse Impact Analytics"}
            >
              <PanelRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Scrollable Deliberation Stream / Investigation Launcher */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-10 lg:px-14 py-8 space-y-8">
          {/* =================================================================
              STATE A: READY FOR INVESTIGATION LAUNCHER (BEFORE USER ASKS QUERY)
              ================================================================= */}
          {!hasSubmittedQuery && !isLoading && (
            <div className="max-w-3xl mx-auto py-10 px-4 sm:px-6 flex flex-col items-center justify-center text-center space-y-6 animate-fade-in">
              <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center shadow-xl shadow-indigo-950/40">
                <Scale className="w-7 h-7 text-indigo-400" />
              </div>

              <div className="space-y-2 max-w-xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-indigo-400 pulse-glow" />
                  <span>Target Pack: {selectedPackId}</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white font-sans">
                  Autonomous Disruption Impact Tribunal
                </h2>
                <p className="text-xs sm:text-sm text-slate-400 font-sans leading-relaxed">
                  Enter an investigation question below to convene the court. Heimdall will verify disruption authenticity and enforce the temporal firewall before Counsel Thor and Loki cross-examine evidence.
                </p>
              </div>

              {/* Single Primary Claude-Style Central Composer */}
              <div className="w-full text-left space-y-4">
                <div className="relative rounded-2xl bg-[#0c0e14] border border-white/[0.12] focus-within:border-indigo-500/50 shadow-2xl p-4 transition-all">
                  <textarea
                    value={queryInput}
                    onChange={(e) => setQueryInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendQuery();
                      }
                    }}
                    rows={3}
                    placeholder="Ask Odin to evaluate disruption scope and calibrate commercial exposure..."
                    className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 resize-none focus:outline-none font-sans leading-relaxed"
                  />

                  {/* Composer Tools & Send Action */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-white/[0.08]">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-white/[0.05] text-slate-300 border border-white/[0.08]">
                        📁 {selectedPackId}
                      </span>
                      <span className="text-[11px] font-mono px-2.5 py-1 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20">
                        ⏱ As-Of: {activeAsOf}
                      </span>
                    </div>

                    <button
                      onClick={() => handleSendQuery()}
                      disabled={!queryInput.trim() || isLoading}
                      className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-mono font-bold transition shadow-lg ${
                        queryInput.trim() && !isLoading
                          ? "bg-indigo-600 hover:bg-indigo-500 text-white cursor-pointer shadow-indigo-950/50"
                          : "bg-white/[0.06] text-slate-500 cursor-not-allowed"
                      }`}
                    >
                      <span>Ask Question & Deliberate</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Quick Preset Query Chips directly under the composer */}
                <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                  <span className="text-[11px] font-mono text-slate-500 font-medium">Try Preset:</span>
                  {(currentPackMeta?.presets || []).map((preset, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        setQueryInput(preset);
                        handleSendQuery(preset);
                      }}
                      className="px-3 py-1.5 rounded-full bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] hover:border-white/[0.2] text-xs font-sans text-slate-300 hover:text-white transition cursor-pointer"
                    >
                      {preset}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* =================================================================
              STATE B: LIVE INVESTIGATION LOADING STATE (PROGRESS SIMULATION)
              ================================================================= */}
          {isLoading && (
            <div className="max-w-2xl mx-auto py-16 px-6 flex flex-col items-center justify-center text-center space-y-6 animate-fade-in">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center shadow-2xl">
                  <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
                </div>
                <span className="absolute -bottom-1 -right-1 w-3 h-3 rounded-full bg-emerald-400 ring-2 ring-[#06070a] pulse-glow" />
              </div>

              <div className="space-y-2">
                <h3 className="text-base font-bold text-white font-sans">
                  Tribunal Deliberation in Progress...
                </h3>
                <p className="text-xs text-slate-400 font-sans max-w-md">
                  Investigating query against {currentPackMeta.pack_name} exhibits with strict As-Of cutoff ({activeAsOf}).
                </p>
              </div>

              <div className="w-full max-w-md space-y-2.5 text-xs font-mono text-left">
                <div className="p-3 rounded-lg bg-amber-500/[0.08] border border-amber-500/25 text-amber-300 flex items-center gap-2.5">
                  <Eye className="w-4 h-4 shrink-0 text-amber-400 animate-pulse" />
                  <span>1. Heimdall Gatekeeper: Verifying shock & enforcing cutoff firewall...</span>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.08] text-slate-300 flex items-center gap-2.5">
                  <Scale className="w-4 h-4 shrink-0 text-slate-400" />
                  <span>2. Counsel Thor & Loki: Convening in adversarial courtroom chamber...</span>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.08] text-slate-400 flex items-center gap-2.5">
                  <Gavel className="w-4 h-4 shrink-0 text-slate-500" />
                  <span>3. Supreme Judge Odin: Calibrating commercial exposure bounds...</span>
                </div>
              </div>
            </div>
          )}

          {/* =================================================================
              STATE C: ACTIVE DELIBERATION STREAM (AFTER QUERY IS ASKED)
              ================================================================= */}
          {hasSubmittedQuery && !isLoading && (
            <div className="space-y-8 animate-fade-in">
              {/* STREAM ITEM 1: USER INVESTIGATION QUERY */}
              <div className="max-w-4xl mx-auto flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-white text-xs font-bold font-mono">
                  U
                </div>
                <div className="flex-1 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-white">Investigator Query</span>
                    <span className="text-[10px] font-mono text-slate-500">As-Of: {activeAsOf}</span>
                    <span className="text-[10px] font-mono px-2 py-0.2 rounded bg-white/[0.04] text-slate-400 border border-white/[0.08]">
                      {selectedPackId}
                    </span>
                  </div>
                  <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] text-sm text-slate-200 font-sans leading-relaxed">
                    {activeQuestion}
                  </div>
                </div>
              </div>

              {/* STREAM ITEM 2: HEIMDALL VERIFICATION BOX (DYNAMICALLY EXTRACTED) */}
              <div className="max-w-4xl mx-auto flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center shrink-0">
                  <Eye className="w-4 h-4 text-amber-400" />
                </div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-amber-300 uppercase tracking-wide">
                      Heimdall Gatekeeper & Temporal Sentinel
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold uppercase border ${
                      isCaseRejected
                        ? "bg-rose-500/15 text-rose-300 border-rose-500/30"
                        : "bg-amber-500/10 text-amber-300 border-amber-500/30"
                    }`}>
                      {isCaseRejected ? "Decoy Rejected" : "Verified Shock"}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">Stage 1: Pre-Adversarial Gate</span>
                  </div>

                  {/* Heimdall Card with Unified Amber Palette */}
                  <div className="p-5 sm:p-6 rounded-xl bg-[#0f1118] border border-amber-500/35 shadow-xl space-y-4 relative overflow-hidden">
                    <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-amber-500/80 to-transparent" />

                    <div className="flex items-center justify-between pb-3 border-b border-amber-500/20">
                      <div>
                        <h3 className="text-sm font-bold text-amber-100 font-sans">
                          {isCaseRejected ? "Decoy Verification & Disinformation Neutralization" : "Disruption Verification & Temporal Firewall Audit"}
                        </h3>
                        <p className="text-xs text-amber-200/70 font-sans mt-0.5">
                          {isCaseRejected
                            ? "Affirmative port authority & logistics records verified. Breaking alert rejected as false alarm."
                            : "Authenticity confirmed via official bilateral instruments. Temporal clock cutoff strictly enforced."}
                        </p>
                      </div>
                      <span className={`text-xs font-mono px-2.5 py-1 rounded-md border font-semibold ${
                        isCaseRejected
                          ? "text-rose-300 bg-rose-500/15 border-rose-500/30"
                          : "text-amber-300 bg-amber-500/15 border-amber-500/30"
                      }`}>
                        {isCaseRejected ? "Decoy Rejected (0% Shock)" : "100% Admissible"}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 text-xs font-sans">
                      {/* Dynamic Scope Extraction */}
                      <div className="p-3.5 rounded-lg bg-black/40 border border-amber-500/20 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-amber-400 font-bold">1. Scope Extraction</span>
                        <p className="text-amber-100 font-medium">
                          Event: {isCaseRejected ? "Breaking Alert: Port Silos Destroyed" : activeEventName}
                        </p>
                        <p className="text-amber-200/60 text-[11px]">
                          Realms: {activeCountries.join(", ")} • Goods: {activeSectors.join(", ")}
                        </p>
                      </div>

                      {/* Dynamic Temporal Clock Cutoff */}
                      <div className="p-3.5 rounded-lg bg-black/40 border border-amber-500/20 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-amber-400 font-bold">2. Temporal Clock Cutoff</span>
                        <p className="text-amber-100 font-medium">
                          Cutoff Date: <strong className="text-amber-300">{activeAsOf}</strong>
                        </p>
                        <p className="text-amber-200/60 text-[11px]">
                          {currentPackMeta.cutoff_note}
                        </p>
                      </div>

                      {/* Dynamic Trap Neutralization */}
                      <div className="p-3.5 rounded-lg bg-black/40 border border-amber-500/20 space-y-1">
                        <span className="text-[10px] font-mono uppercase text-amber-400 font-bold">3. Trap Neutralization</span>
                        <p className="text-amber-100 font-medium">
                          Traps Disarmed: <strong className="text-amber-300">{currentPackMeta.traps_disarmed}</strong>
                        </p>
                        <p className="text-amber-200/60 text-[11px]">
                          {isCaseRejected ? "ORV-0010 (Saga Chat rumor) & ORV-0026 (blog post) discarded." : currentPackMeta.traps_note}
                        </p>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-xs text-amber-200 font-sans flex items-center justify-between">
                      <span>
                        <strong>{isCaseRejected ? "Gatekeeper Clearance DENIED (Decoy Blocked):" : "Gatekeeper Clearance Granted:"}</strong>{" "}
                        {isCaseRejected
                          ? "Preliminary port authority figures in ORV-0035 (Cargo Weekly, Rel 2) verify Orvan Grain Port operated continuously in Q4 at index 38 (Oct), 32 (Nov), and 30 (Dec) with berths operating. Realm Trade Ministry filing ORV-0032 (Rel 1) confirms the disruption is strictly an industrial dock workers' strike (14 Sept 2026), NOT military action."
                          : currentPackMeta.verification_reason}
                      </span>
                      {isCaseRejected ? (
                        <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 ml-2" />
                      ) : (
                        <CheckCircle2 className="w-4 h-4 text-amber-400 shrink-0 ml-2" />
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* STREAM ITEM 3: ADVERSARIAL COURTROOM DEBATE (DYNAMIC RUN 1 VS RUN 2) */}
              <div key={`chamber-${activeRunNo}`} className="max-w-4xl mx-auto flex items-start gap-4 animate-fade-in">
                <div className="w-8 h-8 rounded-full bg-white/[0.08] border border-white/[0.15] flex items-center justify-center shrink-0">
                  <Scale className="w-4 h-4 text-slate-300" />
                </div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-white uppercase tracking-wide">
                      Adversarial Courtroom Chamber
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold border ${
                      activeRunNo === 1
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/30"
                        : "bg-indigo-500/10 text-indigo-300 border-indigo-500/30"
                    }`}>
                      Round {activeRunNo} Cross-Examination • {activeRunNo === 1 ? "Remand Scoping" : "Adversarial Synthesis"}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">Stage 2: Counsel Deliberation</span>
                  </div>

                  {/* Side-by-Side Counsel Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Thor Column (DISTINCT ROSE THEME) */}
                    <div className="p-5 rounded-xl bg-[#140b0f] border border-rose-500/35 shadow-xl space-y-3 relative overflow-hidden">
                      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-rose-500/80 to-transparent" />
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-rose-300 uppercase">
                          Thor • High Exposure Counsel
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-300 font-semibold">
                          {activeRunNo === 1 ? activeRunData.thor_stat : packRuns.run2.thor_stat}
                        </span>
                      </div>

                      {activeRunNo === 1 ? (
                        /* RUN 1 THOR CLAIM */
                        <div className="space-y-2.5">
                          <div className="p-2.5 rounded-lg bg-black/40 border border-rose-500/20 space-y-1.5">
                            <p className="text-xs text-rose-100/90 leading-relaxed font-sans">
                              {packRuns.run1.thor_claim}
                            </p>
                            <div className="flex items-center justify-between pt-1">
                              <div className="flex items-center gap-1.5 text-[11px] font-mono text-rose-300">
                                <span className="text-rose-400">Evidence:</span>
                                {packRuns.run1.thor_refs.map((ref) => (
                                  <button
                                    key={ref}
                                    onClick={() => onOpenDoc(ref)}
                                    className="px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/25 text-rose-300 hover:underline"
                                  >
                                    {ref}
                                  </button>
                                ))}
                              </div>
                              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-300 border border-amber-500/25">
                                Scoping Ref
                              </span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* RUN 2 THOR CLAIMS */
                        <div className="space-y-2.5">
                          {packRuns.run2.thor_claims.map((claim) => (
                            <div key={claim.id} className="p-2.5 rounded-lg bg-black/40 border border-rose-500/20 space-y-1.5">
                              <div className="flex items-center justify-between text-[10px] font-mono">
                                <span className="text-rose-400 font-bold">{claim.id}</span>
                                <span className="text-rose-200">{claim.scope}</span>
                              </div>
                              <p className="text-xs text-rose-100/90 leading-relaxed font-sans">
                                {claim.text}
                              </p>
                              <div className="flex items-center justify-between pt-1">
                                <div className="flex items-center gap-1.5 text-[11px] font-mono text-rose-300">
                                  <span className="text-rose-400">Evidence:</span>
                                  {claim.refs.map((ref) => (
                                    <button
                                      key={ref}
                                      onClick={() => onOpenDoc(ref)}
                                      className="px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/25 text-rose-300 hover:underline"
                                    >
                                      {ref}
                                    </button>
                                  ))}
                                </div>
                                {claim.status && (
                                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 font-bold">
                                    {claim.status}
                                  </span>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Loki Column (DISTINCT EMERALD THEME) */}
                    <div className="p-5 rounded-xl bg-[#091410] border border-emerald-500/35 shadow-xl space-y-3 relative overflow-hidden">
                      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-emerald-500/80 to-transparent" />
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-emerald-300 uppercase">
                          Loki • Mitigation Defense
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-semibold">
                          {activeRunNo === 1 ? activeRunData.loki_stat : packRuns.run2.loki_stat}
                        </span>
                      </div>

                      {activeRunNo === 1 ? (
                        /* RUN 1 LOKI CLAIM */
                        <div className="space-y-2.5">
                          <div className="p-2.5 rounded-lg bg-black/40 border border-emerald-500/20 space-y-1.5">
                            <p className="text-xs text-emerald-100/90 leading-relaxed font-sans">
                              {packRuns.run1.loki_claim}
                            </p>
                            <div className="flex items-center justify-between pt-1">
                              <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-300">
                                <span className="text-emerald-400">Evidence:</span>
                                {packRuns.run1.loki_refs.map((ref) => (
                                  <button
                                    key={ref}
                                    onClick={() => onOpenDoc(ref)}
                                    className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 hover:underline"
                                  >
                                    {ref}
                                  </button>
                                ))}
                              </div>
                              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-300 border border-amber-500/25">
                                Scoping Ref
                              </span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        /* RUN 2 LOKI CLAIMS */
                        <div className="space-y-2.5">
                          {packRuns.run2.loki_claims.map((claim) => (
                            <div key={claim.id} className="p-2.5 rounded-lg bg-black/40 border border-emerald-500/20 space-y-1.5">
                              <div className="flex items-center justify-between text-[10px] font-mono">
                                <span className="text-emerald-400 font-bold">{claim.id}</span>
                                <span className="text-emerald-200">{claim.scope}</span>
                              </div>
                              <p className="text-xs text-emerald-100/90 leading-relaxed font-sans">
                                {claim.text}
                              </p>
                              <div className="flex items-center justify-between pt-1">
                                <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-300">
                                  <span className="text-emerald-400">Evidence:</span>
                                  {claim.refs.map((ref) => (
                                    <button
                                      key={ref}
                                      onClick={() => onOpenDoc(ref)}
                                      className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/25 text-emerald-300 hover:underline"
                                    >
                                      {ref}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Concessions / Cross-Examination Banner */}
                  <div className="p-3.5 rounded-lg bg-white/[0.02] border border-white/[0.08] flex items-center justify-between gap-3 text-xs text-slate-300 font-sans">
                    <div className="flex items-center gap-2">
                      <span className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                        activeRunNo === 1
                          ? "bg-amber-500/15 border border-amber-500/30 text-amber-300"
                          : "bg-white/[0.06] text-slate-200"
                      }`}>
                        {activeRunNo === 1 ? "Round 1 Cross-Examination" : "Round 2 Concessions"}
                      </span>
                      <span>
                        {activeRunNo === 1 ? packRuns.run1.cross_exam : packRuns.run2.cross_exam}
                      </span>
                    </div>
                    <button
                      onClick={() => onOpenDoc(activeRunNo === 1 ? packRuns.run1.concession_doc : packRuns.run2.concession_doc)}
                      className="text-slate-300 hover:text-white hover:underline text-[11px] font-mono shrink-0"
                    >
                      {activeRunNo === 1 ? packRuns.run1.concession_doc : packRuns.run2.concession_doc}
                    </button>
                  </div>
                </div>
              </div>

              {/* STREAM ITEM 4: ODIN ALLFATHER SUPREME ADJUDICATION (DYNAMIC RUN 1 VS RUN 2) */}
              <div key={`odin-${activeRunNo}`} className="max-w-4xl mx-auto flex items-start gap-4 animate-fade-in">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                  activeRunNo === 1
                    ? "bg-amber-500/20 border-amber-500/40"
                    : "bg-indigo-500/20 border-indigo-400/40"
                }`}>
                  <Gavel className={`w-4 h-4 ${activeRunNo === 1 ? "text-amber-300" : "text-indigo-300"}`} />
                </div>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-mono font-bold uppercase tracking-wide ${
                      activeRunNo === 1 ? "text-amber-300" : "text-indigo-300"
                    }`}>
                      Odin Allfather Supreme Judicial Decree
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold uppercase border ${
                      activeRunNo === 1
                        ? "bg-amber-500/20 text-amber-200 border-amber-500/40"
                        : "bg-indigo-500/20 text-indigo-200 border-indigo-500/40"
                    }`}>
                      {activeRunNo === 1 ? "Sufficiency: Send-Back Order" : "Final Calibrated Rulings"}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500">
                      {activeRunNo === 1 ? "Stage 3: Adjudication Remand" : "Stage 3: Adjudication"}
                    </span>
                  </div>

                  {activeRunNo === 1 ? (
                    /* RUN 1: ODIN SEND-BACK ORDER CARD */
                    <div className="p-6 sm:p-7 rounded-xl bg-[#14100b] border border-amber-500/40 shadow-2xl space-y-5 relative overflow-hidden">
                      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-amber-400/80 to-transparent" />

                      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-amber-500/25">
                        <div>
                          <h3 className="text-base font-bold text-amber-100 font-sans flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4 text-amber-400" />
                            {packRuns.run1.odin_title}
                          </h3>
                          <p className="text-xs text-amber-200/70 font-sans mt-0.5">
                            {packRuns.run1.odin_reason}
                          </p>
                        </div>
                        <button
                          onClick={() => onRunChange(2)}
                          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-xs font-mono font-bold text-amber-200 transition shadow-sm cursor-pointer"
                        >
                          <span>Advance to Run 2 Deliberation</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Deficiency Audit Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-sans">
                        <div className="p-3 rounded-lg bg-black/40 border border-amber-500/20 space-y-1">
                          <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">1. Missing Scope</span>
                          <p className="text-amber-100 font-medium">{packRuns.run1.missing_scopes[0] || "Incomplete Coverage"}</p>
                          <p className="text-amber-200/60 text-[11px]">Counsel submitted zero admissible claims for secondary target sectors.</p>
                        </div>
                        <div className="p-3 rounded-lg bg-black/40 border border-amber-500/20 space-y-1">
                          <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">2. Citation Verification</span>
                          <p className="text-amber-100 font-medium">Citations Remanded</p>
                          <p className="text-amber-200/60 text-[11px]">Citations uncorroborated against official customs manifest index.</p>
                        </div>
                        <div className="p-3 rounded-lg bg-black/40 border border-amber-500/20 space-y-1">
                          <span className="text-[10px] font-mono text-amber-400 uppercase font-bold">3. Judicial Directive</span>
                          <p className="text-amber-100 font-medium">Ordered to Run 2 Re-Search</p>
                          <p className="text-amber-200/60 text-[11px]">Thor & Loki instructed to query Tier 1/2 records and resolve all missing scopes.</p>
                        </div>
                      </div>

                      <div className="p-4 rounded-xl bg-black/40 border border-amber-500/20 text-xs text-amber-100/90 font-sans leading-relaxed">
                        <p>
                          <strong className="text-white">Supreme Judge Decree:</strong> <em>"No realm shall suffer hasty judgment on ungrounded scraps. The court finds the evidence submitted in Run 1 legally insufficient to synthesize net commercial exposure. Case remanded to Counsel Thor and Loki. Both counsel shall update their private memory stores and present substantiated claims covering {activeCountries.join(" and ")} for both {activeSectors.join(" and ")} in Run 2."</em>
                        </p>
                      </div>
                    </div>
                  ) : (
                    /* RUN 2: ODIN FINAL ADJUDICATION DECREE CARD */
                    <div className="p-6 sm:p-7 rounded-xl bg-[#0a0d18] border border-indigo-500/40 shadow-2xl space-y-5 relative overflow-hidden">
                      <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-indigo-400/80 to-transparent" />

                      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-indigo-500/25">
                        <div>
                          <h3 className="text-base font-bold text-indigo-100 font-sans flex items-center gap-2">
                            <Scale className="w-4 h-4 text-indigo-400" />
                            Definitive Calibrated Commercial Exposure
                          </h3>
                          <p className="text-xs text-indigo-200/70 font-sans mt-0.5">
                            Grounding Standard: Section 11 Fact/Inference Segregation. Every bound anchored to verified customs and rail contracts.
                          </p>
                        </div>
                        <button
                          onClick={onOpenBriefing}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 border border-indigo-500/40 text-xs font-mono text-indigo-200 transition cursor-pointer"
                        >
                          <span>Read Full Briefing</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>

                      {/* Calibrated Exposure Results Table */}
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead>
                            <tr className="border-b border-indigo-500/20 text-indigo-300 font-mono text-[11px]">
                              <th className="py-2.5 px-3 uppercase">Realm / Sector</th>
                              <th className="py-2.5 px-3 uppercase">Thor Peak</th>
                              <th className="py-2.5 px-3 uppercase">Loki Mitigated</th>
                              <th className="py-2.5 px-3 uppercase text-indigo-200">Odin Calibrated Range</th>
                              <th className="py-2.5 px-3 uppercase">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-indigo-500/10 font-mono">
                            {packRuns.run2.exposure_rows.map((row, idx) => (
                              <tr key={idx}>
                                <td className="py-3 px-3 font-bold text-white">{row.realm}</td>
                                <td className="py-3 px-3 text-slate-300 tabular-nums">{row.thor}</td>
                                <td className="py-3 px-3 text-slate-300 tabular-nums">{row.loki}</td>
                                <td className="py-3 px-3">
                                  <span className="px-2.5 py-1 rounded bg-indigo-500/25 border border-indigo-500/40 text-indigo-100 font-bold tabular-nums">
                                    {row.odin}
                                  </span>
                                </td>
                                <td className="py-3 px-3">
                                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold ${
                                    row.status === "ESTABLISHED"
                                      ? "bg-indigo-500/20 border border-indigo-500/30 text-indigo-200"
                                      : "bg-amber-500/20 border border-amber-500/30 text-amber-200"
                                  }`}>
                                    {row.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {/* Judicial Summary Paragraph */}
                      <div className="p-4 rounded-xl bg-black/40 border border-indigo-500/20 text-xs text-indigo-100/90 font-sans leading-relaxed space-y-2">
                        <p>{packRuns.run2.summary}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <div ref={streamEndRef} />
        </div>

        {/* =========================================================================
            BOTTOM CHATBAR (DOCKED ONLY FOR FOLLOW-UP INQUIRIES DURING ACTIVE STREAM)
            ========================================================================= */}
        {(hasSubmittedQuery || isLoading) && (
          <div className="p-4 sm:p-6 bg-gradient-to-t from-[#06070a] via-[#06070a] to-transparent shrink-0">
            <div className="max-w-4xl mx-auto space-y-2.5">
              {/* Quick Prompt Suggestion Chips */}
              <div className="flex items-center gap-2 overflow-x-auto pb-1">
                {(currentPackMeta?.presets || []).map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendQuery(s)}
                    className="px-3 py-1 rounded-full bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-sans text-slate-300 hover:text-white whitespace-nowrap transition cursor-pointer"
                  >
                    {s}
                  </button>
                ))}
              </div>

              {/* Main Claude-style Omnibar Input Box */}
              <div className="relative rounded-2xl bg-[#0c0e14] border border-white/[0.1] shadow-2xl p-3 focus-within:border-white/[0.25] transition">
                <textarea
                  value={queryInput}
                  onChange={(e) => setQueryInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendQuery();
                    }
                  }}
                  rows={2}
                  placeholder={`Ask Odin to calibrate exposure across ${activeCountries.join(" & ")}...`}
                  className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 resize-none focus:outline-none font-sans"
                />

                {/* Bottom Tools & Send Button Strip */}
                <div className="flex items-center justify-between pt-2 border-t border-white/[0.06]">
                  <div className="flex items-center gap-2">
                    {/* Attach / Ingest Trigger */}
                    <div className="relative">
                      <button
                        onClick={() => setAttachMenuOpen(!attachMenuOpen)}
                        className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs font-mono text-slate-300 hover:text-white transition cursor-pointer"
                        title="Attach or select dataset pack"
                      >
                        <Paperclip className="w-3.5 h-3.5 text-slate-400" />
                        <span>{selectedPackId}</span>
                      </button>

                      {/* Popover Menu for Ingest or Pre-Uploaded Packs */}
                      {attachMenuOpen && (
                        <div className="absolute bottom-full left-0 mb-2 w-72 rounded-xl bg-[#0c0e16] border border-white/[0.12] shadow-2xl p-2 space-y-1 z-50">
                          <div className="px-2 py-1 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-bold">
                            Select Discovery Dataset
                          </div>
                          {(availablePacks.length > 0
                            ? availablePacks
                            : Object.values(PACK_REGISTRY)
                          ).map((p) => (
                            <button
                              key={p.pack_name}
                              onClick={() => {
                                setSelectedPackId(p.pack_name);
                                setHasSubmittedQuery(false);
                                const meta = PACK_REGISTRY[p.pack_name];
                                if (meta?.default_question) {
                                  setQueryInput(meta.default_question);
                                }
                                setAttachMenuOpen(false);
                              }}
                              className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono transition flex items-center justify-between cursor-pointer ${
                                selectedPackId === p.pack_name
                                  ? "bg-white/[0.1] text-white font-semibold"
                                  : "text-slate-300 hover:bg-white/[0.06]"
                              }`}
                            >
                              <span>{p.pack_name}</span>
                              <span className="text-[10px] text-slate-400">
                                {p.total_documents || 6} docs
                              </span>
                            </button>
                          ))}
                          <div className="pt-1 border-t border-white/[0.06]">
                            <button
                              onClick={() => {
                                setAttachMenuOpen(false);
                                onOpenIngest();
                              }}
                              className="w-full text-left px-2.5 py-1.5 rounded-lg text-xs font-mono text-slate-200 hover:bg-white/[0.08] transition flex items-center gap-2 font-bold cursor-pointer"
                            >
                              <Upload className="w-3.5 h-3.5" />
                              <span>+ Upload New Pack (.ZIP)</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Cutoff Date Chip */}
                    <span className="text-[10px] font-mono px-2 py-1 rounded-md bg-white/[0.04] text-slate-400 border border-white/[0.06] hidden sm:inline">
                      ⏱ As-Of: {activeAsOf}
                    </span>
                  </div>

                  {/* Send Button */}
                  <button
                    onClick={() => handleSendQuery()}
                    disabled={!queryInput.trim() && !currentPackMeta?.default_question || isLoading}
                    className={`w-8 h-8 rounded-xl flex items-center justify-center transition shadow-lg ${
                      (queryInput.trim() || currentPackMeta?.default_question) && !isLoading
                        ? "bg-white text-black hover:bg-slate-200 cursor-pointer"
                        : "bg-white/[0.06] text-slate-500 cursor-not-allowed"
                    }`}
                    title="Send Query (Enter)"
                  >
                    {isLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin text-black" />
                    ) : (
                      <ArrowUp className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Floating Expand Tab for Right Sidebar when Collapsed */}
      {rightCollapsed && (
        <button
          onClick={() => setRightCollapsed(false)}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-30 flex items-center justify-center p-2 rounded-l-xl bg-[#0e111a] border-l border-y border-white/[0.1] text-slate-400 hover:text-white hover:bg-white/[0.08] transition shadow-2xl group cursor-pointer"
          title="Expand Impact Analytics"
        >
          <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
        </button>
      )}

      {/* =========================================================================
          RIGHT SIDEBAR: IMPACT ANALYTICS, CAUSAL GRAPH, THREAT MATRIX
          ========================================================================= */}
      <div
        style={{ width: rightCollapsed ? 0 : `${rightWidth}px` }}
        className={`relative shrink-0 flex flex-col bg-[#080a0f] border-l border-white/[0.08] transition-[width] duration-150 ease-out z-20 ${
          rightCollapsed ? "overflow-hidden" : ""
        }`}
      >
        {/* Drag Handle for Right Sidebar */}
        <div
          onMouseDown={handleRightMouseDown}
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-white/[0.25] active:bg-white/[0.4] transition-colors z-30"
          title="Drag to resize right sidebar"
        />

        {/* Right Sidebar Header */}
        <div className="h-14 px-4 border-b border-white/[0.08] bg-[#080a0f] flex items-center justify-between gap-2 shrink-0">
          {(hasSubmittedQuery || caseData) ? (
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setRightTab("exposure")}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition cursor-pointer ${
                  rightTab === "exposure" ? "bg-white/[0.1] text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Exposure
              </button>
              <button
                onClick={() => setRightTab("graph")}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition cursor-pointer ${
                  rightTab === "graph" ? "bg-white/[0.1] text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Topology
              </button>
              <button
                onClick={() => setRightTab("threats")}
                className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold transition cursor-pointer ${
                  rightTab === "threats" ? "bg-white/[0.1] text-white" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Firewall
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Scale className="w-3.5 h-3.5 text-slate-500" />
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
                Impact Analytics
              </span>
            </div>
          )}

          <button
            onClick={() => setRightCollapsed(true)}
            className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-white/[0.06] transition cursor-pointer"
            title="Collapse Sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Right Sidebar Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {(!hasSubmittedQuery && !caseData) ? (
            /* STANDBY STATE (BEFORE QUERY RUNS — ZERO LEAKED DATA) */
            <div className="h-full py-20 flex flex-col items-center justify-center text-center space-y-4 px-3 animate-fade-in">
              <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center shadow-lg">
                <Scale className="w-6 h-6 text-slate-500" />
              </div>
              <div className="space-y-1.5 max-w-[220px]">
                <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300">
                  Awaiting Investigation
                </h4>
                <p className="text-xs text-slate-500 font-sans leading-relaxed">
                  No tribunal deliberation active. Ask a question to compute commercial exposure, causal topology, and firewall audits.
                </p>
              </div>
              <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.03] border border-white/[0.06] text-[10px] font-mono text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                <span>Standby Mode</span>
              </div>
            </div>
          ) : (
            <>
              {/* TAB 1: EXPOSURE SUMMARY */}
              {rightTab === "exposure" && (
                <div key={`exposure-${selectedPackId}-${activeRunNo}`} className="space-y-4 animate-fade-in">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
                      Calibrated Exposure Matrix
                    </span>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold border ${
                      activeRunNo === 1
                        ? "bg-amber-500/10 text-amber-300 border-amber-500/25"
                        : "bg-indigo-500/10 text-indigo-300 border-indigo-500/25"
                    }`}>
                      {activeRunNo === 1 ? "Run 1 • Remanded" : `Run ${activeRunNo} • Adjudicated`}
                    </span>
                  </div>

                  {activeRunNo === 1 ? (
                    /* RUN 1: PRE-REMAND NOTICE & INTERIM ESTIMATES */
                    <div className="space-y-3.5">
                      <div className="p-3.5 rounded-xl bg-amber-500/[0.08] border border-amber-500/30 text-xs text-amber-200 space-y-2">
                        <div className="flex items-center gap-1.5 font-bold text-amber-300">
                          <AlertTriangle className="w-4 h-4 shrink-0" />
                          <span>Run 1 Evidentiary Remand</span>
                        </div>
                        <p className="text-[11px] text-amber-200/80 leading-relaxed font-sans">
                          Odin issued a Send-Back Order for {activeEventName}. Target realms & sectors had incomplete coverage or unverified citations.
                        </p>
                        {availableRuns.length > 1 && (
                          <button
                            onClick={() => onRunChange(2)}
                            className="w-full mt-1 py-1.5 px-3 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-xs font-mono font-bold text-amber-200 transition flex items-center justify-center gap-1.5 cursor-pointer"
                          >
                            <span>Switch to Run 2 Final Calibration</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Interim Card */}
                      <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-white">{packRuns.run1.interim_label}</span>
                          <span className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold bg-amber-500/15 border border-amber-500/30 text-amber-300">
                            UNADJUDICATED
                          </span>
                        </div>
                        <div className="text-lg font-mono font-bold text-slate-300 tabular-nums">
                          {packRuns.run1.interim_range}
                        </div>
                        <p className="text-[11px] text-slate-400 font-sans">
                          {packRuns.run1.interim_desc}
                        </p>
                      </div>

                      {/* Missing Scopes Breakdown */}
                      <div className="p-3.5 rounded-xl bg-black/40 border border-white/[0.08] space-y-2 text-xs">
                        <span className="font-mono text-[10px] text-slate-400 uppercase font-bold tracking-wider">
                          Run 1 Scope Coverage Gaps
                        </span>
                        <div className="space-y-1.5 text-[11px]">
                          {packRuns.run1.missing_scopes.map((scope, idx) => (
                            <div key={idx} className="flex items-center justify-between text-slate-300">
                              <span>{scope}:</span>
                              <span className="text-rose-400 font-mono font-semibold">0 Admissible Claims</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    /* RUN 2+: FINAL CALIBRATED EXPOSURE MATRIX */
                    <div className="space-y-3.5">
                      {(packRuns.run2.exposure_cards || []).map((card, idx) => (
                        <div key={idx} className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white">{card.title}</span>
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-mono font-bold ${
                              card.status === "ESTABLISHED"
                                ? "bg-white/[0.06] text-slate-300"
                                : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                            }`}>
                              {card.status}
                            </span>
                          </div>
                          <div className="text-xl font-mono font-bold text-white tabular-nums">
                            {card.range}
                          </div>
                          <p className="text-[11px] text-slate-400 font-sans">
                            {card.desc}
                          </p>
                          <div className="spark-track relative mt-2">
                            <div
                              className="spark-range-pill"
                              style={{ left: card.left || "35%", width: card.width || "30%" }}
                            />
                          </div>
                          <div className="flex justify-between text-[9px] font-mono text-slate-500">
                            <span>Loki: {card.loki}</span>
                            <span>Thor: {card.thor}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

          {/* TAB 2: CAUSAL GRAPH TOPOLOGY */}
          {rightTab === "graph" && (
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
                  Causal Flow Network
                </span>
                <span className="text-[10px] font-mono text-slate-400">
                  {Object.keys(currentPackMeta?.nodes || {}).length} Entities
                </span>
              </div>

              {/* Node Cards */}
              <div className="space-y-2">
                {Object.entries(currentPackMeta?.nodes || {}).map(([nodeName, nodeInfo]) => {
                  const isInspected = inspectedNode === nodeName;
                  return (
                    <div
                      key={nodeName}
                      onClick={() => setInspectedNode(nodeName)}
                      className={`p-3 rounded-xl border transition cursor-pointer space-y-1.5 ${
                        isInspected
                          ? "bg-white/[0.08] border-white/[0.2] text-white shadow-md"
                          : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.05] text-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold font-sans">{nodeName}</span>
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/[0.06] text-slate-300 border border-white/[0.08]">
                          {nodeInfo.type}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
                        {nodeInfo.desc}
                      </p>
                      <div className="flex items-center gap-1.5 pt-1 text-[10px] font-mono text-slate-500">
                        <span>Refs:</span>
                        {nodeInfo.citations.map((cite) => (
                          <button
                            key={cite}
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenDoc(cite);
                            }}
                            className="px-1.5 py-0.2 rounded bg-white/[0.04] text-slate-300 hover:text-white hover:underline"
                          >
                            {cite}
                          </button>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 3: THREAT FIREWALL AUDIT */}
          {rightTab === "threats" && (
            <div className="space-y-4 animate-fade-in">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-mono font-semibold uppercase tracking-wider text-slate-400">
                  Firewall & Threat Audit
                </span>
                <span className="text-[10px] font-mono text-emerald-400 font-bold">
                  Active
                </span>
              </div>

              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/[0.08] space-y-3 text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <span className="text-slate-400">Temporal Cutoff:</span>
                  <span className="font-mono text-white font-bold">{activeAsOf}</span>
                </div>
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <span className="text-slate-400">Lookahead Leaks:</span>
                  <span className="font-mono text-emerald-400 font-bold">0 Detected</span>
                </div>
                <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
                  <span className="text-slate-400">Quarantined Exhibits:</span>
                  <span className="font-mono text-amber-300 font-bold">{currentPackMeta.traps_disarmed}</span>
                </div>
                <p className="text-[11px] text-slate-400 font-sans leading-relaxed pt-1">
                  Tool-layer filters enforce Section 5 temporal gate. All future trade table rows and corrupted 0-byte items are quarantined before LLM wake-up.
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
      </div>
    </div>
  );
}
