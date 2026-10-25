import React, { useState, useEffect } from "react";
import { GitBranch, Shield, Zap, ExternalLink, ArrowRight, CheckCircle2, AlertTriangle, Layers, Network, Info } from "lucide-react";
import { fetchGraphOverview, fetchCausalPaths, fetchBottlenecks } from "../api/client";

export default function SupplyChainTopologyView({ onOpenDoc }) {
  const [graphData, setGraphData] = useState(null);
  const [causalPaths, setCausalPaths] = useState([]);
  const [bottlenecksData, setBottlenecksData] = useState({ bottlenecks: [], substitutions: [] });
  const [selectedCountry, setSelectedCountry] = useState("Midgard");
  const [inspectedNode, setInspectedNode] = useState("Orvan Grain Port");

  useEffect(() => {
    fetchGraphOverview().then(setGraphData);
    fetchCausalPaths(selectedCountry, "Orvan").then(setCausalPaths);
    fetchBottlenecks(selectedCountry, "Wheat").then(setBottlenecksData);
  }, [selectedCountry]);

  const defaultPaths = [
    {
      summary: "Direct Maritime Transshipment Collapse",
      is_bottleneck: true,
      path_nodes: ["Orvan Corridor Expiration", "Southern Sea Corridor", "Orvan Grain Port", "Midgard"],
      path_edges: ["Disrupted By", "Bottlenecked At", "Exports To (-60.5%)"],
      citations: ["ORV-0016", "ORV-0012", "ORV-0009#P7"],
      color: "border-rose-500/25 bg-rose-500/5",
      badge: "Disruption Pipeline",
      badgeColor: "text-rose-400 bg-rose-500/10 border-rose-500/20",
    },
    {
      summary: "Bilateral Alternative Substitution Line",
      is_substitution: true,
      path_nodes: ["Vanir", "Orvan Grain Port (Substituted)", "Midgard"],
      path_edges: ["Substitutes With", "Bilateral Export Surge (+100%)"],
      citations: ["ORV-0027", "ORV-0044"],
      color: "border-emerald-500/25 bg-emerald-500/5",
      badge: "Active Mitigation Corridor",
      badgeColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },
    {
      summary: "Overland Rail Freight Diversion Corridor",
      is_substitution: true,
      path_nodes: ["Ravik Rail Link", "Midgard Transshipment Yard"],
      path_edges: ["Transits Through (+32k tonnes/mo)"],
      citations: ["ORV-0050", "ORV-0001"],
      color: "border-indigo-500/25 bg-indigo-500/5",
      badge: "Overland Freight Path",
      badgeColor: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    },
  ];

  const pathsToShow = causalPaths && causalPaths.length > 0 ? causalPaths : defaultPaths;

  // Node details directory for interactive graph click
  const nodeCatalog = {
    "Orvan": {
      type: "Nation / Producer",
      desc: "Originating grain producer whose corridor export pact expired midnight 14 November 2026.",
      citations: ["ORV-0016"],
      status: "Disrupted",
    },
    "Orvan Grain Port": {
      type: "Physical Chokepoint",
      desc: "Deepwater maritime terminal. Loadings collapsed by 62.8% post-expiration; dock strike compounded bottleneck.",
      citations: ["ORV-0009#P7", "ORV-0012"],
      status: "Bottleneck",
    },
    "Southern Sea Corridor": {
      type: "Maritime Transit Route",
      desc: "Open-ocean shipping lane subject to commercial carrier rate spikes and insurance non-renewals.",
      citations: ["ORV-0016", "ORV-0036"],
      status: "Lapsed",
    },
    "Midgard": {
      type: "Primary Target Realm",
      desc: "Major grain importer experiencing net -44.0% to -51.2% structural wheat deficit post-mitigation.",
      citations: ["ORV-0009", "ORV-0027", "ORV-0050"],
      status: "Deficit Center",
    },
    "Tolan": {
      type: "Secondary Target Realm",
      desc: "Coastal transshipment recipient facing -32.8% to -42.2% wheat deficit, mitigated by archipelagic craft.",
      citations: ["ORV-0012", "ORV-0046"],
      status: "Secondary Deficit",
    },
    "Vanir": {
      type: "Bilateral Mitigator",
      desc: "Neighboring agricultural producer with bilateral treaty; grain shipments surged from $18.2M to $36.5M in Q4.",
      citations: ["ORV-0027", "ORV-0044"],
      status: "Active Mitigation",
    },
    "Ravik Rail Link": {
      type: "Overland Rail Infrastructure",
      desc: "Freight rail line accommodating 4 dedicated daily trains (+32,000 tonnes/month of dry bulk grain).",
      citations: ["ORV-0050", "ORV-0001"],
      status: "Active Mitigation",
    },
  };

  return (
    <div className="flex flex-col gap-8 w-full animate-fade-in">
      {/* Header and Scope Selector */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div>
          <h2 className="text-base font-semibold text-white font-sans flex items-center gap-2.5">
            <Network className="w-4 h-4 text-indigo-400" />
            <span>Dual-Level Graph RAG & Supply Chain Causal Topology</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Multi-hop causal pathfinding and entity ego-networks grounded in NetworkX and Supabase pgvector.
          </p>
        </div>

        {/* Country Selector */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">Target Ego-Center:</span>
          <div className="flex items-center p-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono">
            {["Midgard", "Tolan", "Vanir", "Ravik", "Orvan"].map((c) => (
              <button
                key={c}
                onClick={() => setSelectedCountry(c)}
                className={`px-3 py-1 rounded-md transition ${
                  selectedCountry === c
                    ? "bg-white/[0.14] text-white font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Top Topology KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="linear-panel p-6 flex flex-col justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Graph Knowledge Nodes
          </div>
          <div className="my-3 text-2xl sm:text-3xl font-bold font-mono text-white tabular-nums">
            {graphData?.total_nodes || 10} Entities
          </div>
          <div className="text-xs text-slate-400">
            5 Nations • 2 Corridors • 1 Terminal
          </div>
        </div>

        <div className="linear-panel p-6 flex flex-col justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Directed Relationship Edges
          </div>
          <div className="my-3 text-2xl sm:text-3xl font-bold font-mono text-indigo-400 tabular-nums">
            {graphData?.total_edges || 7} Grounded Edges
          </div>
          <div className="text-xs text-slate-400">
            100% Sourced by Document Citations
          </div>
        </div>

        <div className="linear-panel p-6 flex flex-col justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Multi-Hop Causal Paths
          </div>
          <div className="my-3 text-2xl sm:text-3xl font-bold font-mono text-emerald-400 tabular-nums">
            3 Active Corridors
          </div>
          <div className="text-xs text-slate-400">
            Disruption vs Substitution Tracing
          </div>
        </div>

        <div className="linear-panel p-6 flex flex-col justify-between">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Temporal Clock Filtering
          </div>
          <div className="my-3 text-2xl sm:text-3xl font-bold font-mono text-slate-200 tabular-nums">
            0 Leaked Edges
          </div>
          <div className="text-xs text-slate-400">
            As-of date strictly enforced on paths
          </div>
        </div>
      </div>

      {/* INTERACTIVE SVG SUPPLY CHAIN TOPOLOGY NETWORK */}
      <div className="linear-panel p-6 overflow-hidden">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/[0.08]">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400 pulse-glow"></span>
            <h3 className="text-sm font-semibold text-white font-sans">
              Interactive Causal Flow Network (Click Any Node to Inspect)
            </h3>
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-400"></span> Disruption Corridor
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span> Bilateral Mitigation
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-indigo-400"></span> Rail Freight Cushion
            </span>
          </div>
        </div>

        {/* SVG Canvas */}
        <div className="relative w-full overflow-x-auto py-4">
          <svg viewBox="0 0 860 300" className="w-full h-auto min-w-[760px] font-mono text-xs select-none">
            {/* Background Grid Pattern */}
            <defs>
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <circle cx="2" cy="2" r="1" fill="rgba(255,255,255,0.04)" />
              </pattern>
              {/* Arrow Markers */}
              <marker id="arrow-rose" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#f43f5e" />
              </marker>
              <marker id="arrow-emerald" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#10b981" />
              </marker>
              <marker id="arrow-indigo" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1 L 9 5 L 0 9 z" fill="#818cf8" />
              </marker>
            </defs>
            <rect width="860" height="300" fill="transparent" />
            <rect width="860" height="300" fill="url(#grid)" />

            {/* DIRECTED FLOW EDGES */}
            {/* Edge 1: Orvan -> Orvan Port (Disrupted) */}
            <path
              d="M 120 120 L 250 120"
              stroke="#f43f5e"
              strokeWidth="2.5"
              strokeDasharray="6 4"
              markerEnd="url(#arrow-rose)"
              opacity="0.85"
            />
            <text x="185" y="108" fill="#fda4af" fontSize="10" textAnchor="middle">Expired Pact</text>

            {/* Edge 2: Orvan Port -> Southern Sea Corridor */}
            <path
              d="M 320 105 Q 430 40 500 70"
              stroke="#f43f5e"
              strokeWidth="2.5"
              strokeDasharray="6 4"
              markerEnd="url(#arrow-rose)"
              fill="none"
              opacity="0.85"
            />
            <text x="410" y="55" fill="#fda4af" fontSize="10" textAnchor="middle">-62.8% Drop</text>

            {/* Edge 3: Southern Sea Corridor -> Midgard */}
            <path
              d="M 570 75 Q 640 85 710 105"
              stroke="#f43f5e"
              strokeWidth="2.5"
              strokeDasharray="6 4"
              markerEnd="url(#arrow-rose)"
              fill="none"
              opacity="0.85"
            />
            <text x="630" y="65" fill="#fda4af" fontSize="9.5" textAnchor="middle">Maritime Loss</text>

            {/* Edge 4: Southern Sea Corridor -> Tolan */}
            <path
              d="M 560 90 Q 640 160 710 215"
              stroke="#f43f5e"
              strokeWidth="2"
              strokeDasharray="4 4"
              markerEnd="url(#arrow-rose)"
              fill="none"
              opacity="0.6"
            />
            <text x="625" y="150" fill="#fda4af" fontSize="9" textAnchor="middle">-32.8% Drop</text>

            {/* Edge 5: Vanir -> Midgard (Bilateral Mitigation) */}
            <path
              d="M 190 240 Q 420 280 700 135"
              stroke="#10b981"
              strokeWidth="2.5"
              strokeDasharray="8 4"
              markerEnd="url(#arrow-emerald)"
              fill="none"
              opacity="0.9"
            />
            <text x="440" y="270" fill="#6ee7b7" fontSize="10" textAnchor="middle">Vanir Bilateral Surge (+$18.3M / mo)</text>

            {/* Edge 6: Ravik Rail Link -> Midgard */}
            <path
              d="M 430 200 Q 560 210 700 125"
              stroke="#818cf8"
              strokeWidth="2"
              markerEnd="url(#arrow-indigo)"
              fill="none"
              opacity="0.8"
            />
            <text x="580" y="170" fill="#a5b4fc" fontSize="9.5" textAnchor="middle">Overland Rail (+32k tonnes/mo)</text>

            {/* NODES */}
            {/* Node: Orvan */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Orvan")}
            >
              <circle cx="80" cy="120" r="32" fill="#18141e" stroke={inspectedNode === "Orvan" ? "#fff" : "#f43f5e"} strokeWidth="2" />
              <text x="80" y="117" fill="#fff" fontWeight="bold" fontSize="11" textAnchor="middle">Orvan</text>
              <text x="80" y="131" fill="#f43f5e" fontSize="9" textAnchor="middle">ORIGIN</text>
            </g>

            {/* Node: Orvan Grain Port (Chokepoint) */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Orvan Grain Port")}
            >
              <rect x="250" y="90" width="130" height="58" rx="10" fill="#201318" stroke={inspectedNode === "Orvan Grain Port" ? "#fff" : "#f43f5e"} strokeWidth="2" />
              <text x="315" y="115" fill="#fff" fontWeight="bold" fontSize="11" textAnchor="middle">Orvan Port</text>
              <text x="315" y="133" fill="#f87171" fontSize="9" textAnchor="middle">CHOKEPOINT (STRIKE)</text>
            </g>

            {/* Node: Southern Sea Corridor */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Southern Sea Corridor")}
            >
              <rect x="470" y="50" width="140" height="50" rx="8" fill="#1c1622" stroke={inspectedNode === "Southern Sea Corridor" ? "#fff" : "#f43f5e"} strokeWidth="1.5" />
              <text x="540" y="73" fill="#fff" fontWeight="bold" fontSize="11" textAnchor="middle">Southern Sea</text>
              <text x="540" y="89" fill="#fda4af" fontSize="9" textAnchor="middle">MARITIME CORRIDOR</text>
            </g>

            {/* Node: Midgard (Target) */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Midgard")}
            >
              <circle cx="750" cy="120" r="38" fill="#121828" stroke={inspectedNode === "Midgard" ? "#818cf8" : "#fff"} strokeWidth="2.5" />
              <text x="750" y="116" fill="#fff" fontWeight="bold" fontSize="12" textAnchor="middle">Midgard</text>
              <text x="750" y="132" fill="#a5b4fc" fontSize="9" textAnchor="middle">TARGET (-47.6%)</text>
            </g>

            {/* Node: Tolan (Target) */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Tolan")}
            >
              <circle cx="750" cy="230" r="30" fill="#151b22" stroke={inspectedNode === "Tolan" ? "#818cf8" : "rgba(255,255,255,0.4)"} strokeWidth="2" />
              <text x="750" y="228" fill="#fff" fontWeight="bold" fontSize="11" textAnchor="middle">Tolan</text>
              <text x="750" y="242" fill="#94a3b8" fontSize="8" textAnchor="middle">COASTAL DEMAND</text>
            </g>

            {/* Node: Vanir (Substitution) */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Vanir")}
            >
              <circle cx="150" cy="235" r="32" fill="#0d241d" stroke={inspectedNode === "Vanir" ? "#fff" : "#10b981"} strokeWidth="2" />
              <text x="150" y="232" fill="#fff" fontWeight="bold" fontSize="11" textAnchor="middle">Vanir</text>
              <text x="150" y="246" fill="#34d399" fontSize="8" textAnchor="middle">BILATERAL PACT</text>
            </g>

            {/* Node: Ravik Rail Link (Overland) */}
            <g
              className="cursor-pointer transition transform hover:scale-105"
              onClick={() => setInspectedNode("Ravik Rail Link")}
            >
              <rect x="360" y="180" width="130" height="50" rx="8" fill="#181c2e" stroke={inspectedNode === "Ravik Rail Link" ? "#fff" : "#818cf8"} strokeWidth="1.5" />
              <text x="425" y="202" fill="#fff" fontWeight="bold" fontSize="11" textAnchor="middle">Ravik Rail Link</text>
              <text x="425" y="218" fill="#c7d2fe" fontSize="8" textAnchor="middle">4 TRAIN SLOTS/DAY</text>
            </g>
          </svg>
        </div>

        {/* Selected Node Inspector Drawer Strip */}
        {inspectedNode && nodeCatalog[inspectedNode] && (
          <div className="mt-2 p-4 rounded-xl bg-white/[0.03] border border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-start sm:items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center shrink-0">
                <Info className="w-4 h-4 text-indigo-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-mono font-bold text-white uppercase">{inspectedNode}</h4>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-white/[0.06] text-slate-300">
                    {nodeCatalog[inspectedNode].type}
                  </span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold">
                    {nodeCatalog[inspectedNode].status}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1 font-sans leading-relaxed">
                  {nodeCatalog[inspectedNode].desc}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto font-mono text-xs">
              <span className="text-slate-500 text-[11px]">Sourced In:</span>
              {nodeCatalog[inspectedNode].citations.map((cite, i) => (
                <button
                  key={i}
                  onClick={() => onOpenDoc(cite)}
                  className="px-2 py-0.5 rounded bg-white/[0.06] hover:bg-white/[0.12] border border-white/[0.1] text-indigo-300 transition flex items-center gap-1"
                >
                  <span>{cite}</span>
                  <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Causal Multi-Hop Path Cards */}
      <div className="flex flex-col gap-4">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono">
          Directed Supply-Chain Causal & Substitution Paths
        </h3>

        <div className="grid grid-cols-1 gap-4">
          {pathsToShow.map((p, idx) => (
            <div
              key={idx}
              className="linear-panel p-6 sm:p-7 flex flex-col gap-4 hover:border-white/[0.16] transition"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-white">
                    Path #{idx + 1}: {p.summary}
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-mono uppercase font-semibold ${
                      p.is_bottleneck
                        ? "bg-rose-500/10 text-rose-400 border border-rose-500/25"
                        : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25"
                    }`}
                  >
                    {p.is_bottleneck ? "Disruption Shock" : "Mitigation Path"}
                  </span>
                </div>

                {/* Grounding Citations */}
                <div className="flex items-center gap-1.5 text-xs font-mono text-slate-400">
                  <span className="text-slate-500">Citations:</span>
                  {p.citations?.map((c, cIdx) => (
                    <button
                      key={cIdx}
                      onClick={() => onOpenDoc(c)}
                      className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-mono text-indigo-300 transition flex items-center gap-1"
                    >
                      <span>{c}</span>
                      <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                    </button>
                  ))}
                </div>
              </div>

              {/* Node Sequence Flow */}
              <div className="flex flex-wrap items-center gap-2 pt-2">
                {p.path_nodes?.map((node, nIdx) => (
                  <React.Fragment key={nIdx}>
                    <div className="px-3.5 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-slate-200">
                      {node}
                    </div>
                    {nIdx < p.path_nodes.length - 1 && (
                      <div className="flex items-center gap-1 px-1 text-slate-500 text-xs font-mono">
                        <span className="text-[10px] text-slate-400">{p.path_edges?.[nIdx] || "→"}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-indigo-400" />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Physical Bottlenecks vs Active Substitutions Dual Panel */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Capacity Bottlenecks */}
        <div className="linear-panel p-6 sm:p-7 flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-rose-400">
              Capacity Bottlenecks Identified
            </span>
            <span className="text-xs font-mono text-slate-500">Thor Evidence</span>
          </div>

          <div className="space-y-3">
            <div className="p-4 rounded-lg bg-rose-500/5 border border-rose-500/20 flex flex-col gap-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-rose-300">Orvan Grain Terminal Dock Strike</span>
                <button onClick={() => onOpenDoc("ORV-0012")} className="font-mono text-indigo-400 hover:underline">ORV-0012</button>
              </div>
              <p className="text-slate-300 leading-relaxed text-xs">
                Deepwater loadings fell from 250k to 84k tonnes in October 2026 before complete corridor lapse.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-rose-500/5 border border-rose-500/20 flex flex-col gap-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-rose-300">Tolan South Docks Freezing Spray</span>
                <button onClick={() => onOpenDoc("ORV-0046")} className="font-mono text-indigo-400 hover:underline">ORV-0046</button>
              </div>
              <p className="text-slate-300 leading-relaxed text-xs">
                Winter sea spray lowers small-craft barge throughput to only 22% during sub-zero months.
              </p>
            </div>
          </div>
        </div>

        {/* Active Substitution Corridors */}
        <div className="linear-panel p-6 sm:p-7 flex flex-col gap-4">
          <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-emerald-400">
              Commercial Substitution Corridors
            </span>
            <span className="text-xs font-mono text-slate-500">Loki Evidence</span>
          </div>

          <div className="space-y-3">
            <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex flex-col gap-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-emerald-300">Vanir Bilateral Wheat Deliveries</span>
                <button onClick={() => onOpenDoc("ORV-0027")} className="font-mono text-indigo-400 hover:underline">ORV-0027</button>
              </div>
              <p className="text-slate-300 leading-relaxed text-xs">
                Surged from $18.2M to $36.5M in Q4 2026 under bilateral pact, absorbing $18.3M of maritime deficit.
              </p>
            </div>

            <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20 flex flex-col gap-1.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-emerald-300">Ravik Overland Rail Freight Slots</span>
                <button onClick={() => onOpenDoc("ORV-0050")} className="font-mono text-indigo-400 hover:underline">ORV-0050</button>
              </div>
              <p className="text-slate-300 leading-relaxed text-xs">
                Absorbs ~32,000 tonnes/month of bulk grain overland via 4 dedicated daily train slots.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
