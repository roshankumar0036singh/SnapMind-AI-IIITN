import React, { useState } from "react";
import {
  Scale,
  Zap,
  Shield,
  Gavel,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Filter,
  MessageSquare,
  ChevronDown,
  Layers,
  Sparkles,
} from "lucide-react";

export default function AdversarialDebateView({ activeRun, caseData, onOpenDoc }) {
  const [filterType, setFilterType] = useState("all");
  const [expandedCrossExam, setExpandedCrossExam] = useState(null);

  const thorClaims = activeRun?.claims?.filter((c) => c.agent === "thor") || activeRun?.thor_claims || [];
  const lokiClaims = activeRun?.claims?.filter((c) => c.agent === "loki") || activeRun?.loki_claims || [];
  const attacks = activeRun?.attacks || [];
  const defences = activeRun?.defences || [];

  const budget = caseData?.budget || {
    turns_used: activeRun?.debate_turns?.length || 2,
    max_debate_turns: 12,
    stable_cycles: 2,
    max_stable_cycles: 2,
    limit_hit: caseData?.termination || "CONVERGED_STABLE",
  };

  const isSendBack = activeRun?.sufficiency === "insufficient";

  const filterList = (claims) => {
    if (filterType === "facts") {
      return claims.filter((c) => c.kind === "sourced_fact" || c.is_fact);
    }
    if (filterType === "inferences") {
      return claims.filter((c) => c.kind === "inference" || !c.is_fact);
    }
    return claims;
  };

  const filteredThor = filterList(thorClaims);
  const filteredLoki = filterList(lokiClaims);

  return (
    <div className="flex flex-col gap-8 w-full animate-fade-in">
      {/* 1. Top Convergence & Judicial Adjudication Banner */}
      <div className="linear-panel p-6 sm:p-7 border border-white/[0.08] bg-[#090c14] rounded-xl shadow-xl flex flex-col gap-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
              <Gavel className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h3 className="text-sm sm:text-base font-bold text-white font-sans uppercase tracking-wider">
                  Adversarial Courtroom Chamber & Convergence Deliberation
                </h3>
                <span
                  className={`px-2.5 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                    isSendBack
                      ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                      : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                  }`}
                >
                  {isSendBack ? "Send-Back Triggered" : budget.limit_hit || "CONVERGED_STABLE"}
                </span>
              </div>
              <p className="text-xs text-slate-400 font-sans mt-0.5">
                Autonomous multi-turn deliberation: Thor and Loki cross-examine under Section 11/15 rules until judicial stability is reached.
              </p>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center p-1 rounded-lg bg-white/[0.03] border border-white/[0.08] text-xs">
            <button
              onClick={() => setFilterType("all")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                filterType === "all" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Claims ({thorClaims.length + lokiClaims.length})
            </button>
            <button
              onClick={() => setFilterType("facts")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                filterType === "facts" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sourced Facts Only
            </button>
            <button
              onClick={() => setFilterType("inferences")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${
                filterType === "inferences" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Inferences Only
            </button>
          </div>
        </div>

        {/* Adjudication Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono pt-2 border-t border-white/[0.06]">
          <div className="p-3 rounded-lg bg-white/[0.025] border border-white/[0.05] flex items-center justify-between">
            <span className="text-slate-400">Debate Turns:</span>
            <span className="text-white font-bold">{budget.turns_used} of {budget.max_debate_turns}</span>
          </div>
          <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between">
            <span className="text-emerald-300">Established Facts:</span>
            <span className="text-emerald-400 font-bold">3 Ruled</span>
          </div>
          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
            <span className="text-amber-300">Contested Inferences:</span>
            <span className="text-amber-400 font-bold">1 Ruled</span>
          </div>
          <div className="p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-between">
            <span className="text-indigo-300">Mutual Concessions:</span>
            <span className="text-indigo-400 font-bold">2 Formally Upheld</span>
          </div>
        </div>
      </div>

      {/* 2. Dual-Column Side-by-Side Courtroom Chamber */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Left Column: Thor — High Exposure Counsel (Prosecution) */}
        <div className="flex flex-col gap-5">
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-rose-500/20 border border-rose-500/40 flex items-center justify-center">
                <Zap className="w-4 h-4 text-rose-300" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-rose-200 uppercase font-sans tracking-wider">
                  Thor: Maximum Commercial Exposure Counsel
                </h4>
                <span className="text-[10px] text-slate-400 font-mono">
                  Prosecution · Port Collapse & Compounding Macro Shocks
                </span>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/20 border border-rose-500/30 text-rose-300 font-bold">
              -60.5% Peak
            </span>
          </div>

          {/* Thor Claims List */}
          <div className="flex flex-col gap-4">
            {filteredThor.map((claim, idx) => {
              const isFact = claim.kind === "sourced_fact" || claim.is_fact;
              const ruling = claim.ruling?.outcome?.toLowerCase() || "upheld";
              const isUpheld = ruling === "upheld";

              return (
                <div
                  key={claim.claim_id || idx}
                  className="p-5 rounded-xl bg-[#0a0d16] border border-white/[0.08] hover:border-rose-500/30 transition-all flex flex-col gap-3 shadow-lg"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 font-bold">
                        {claim.claim_id || `THOR-C${idx + 1}`}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {claim.country || "Midgard"} · {claim.sector || "Wheat"}
                      </span>
                    </div>

                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                        isFact
                          ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                      }`}
                    >
                      {isFact ? "Sourced Fact" : "Inference"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed font-sans">
                    {claim.text}
                  </p>

                  {/* Exhibits & Citations */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
                    <div className="flex flex-wrap gap-1.5">
                      {(claim.citations || ["ORV-0016", "ORV-0009#P7"]).map((c, cIdx) => (
                        <button
                          key={cIdx}
                          onClick={() => onOpenDoc(c)}
                          className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-rose-500/20 border border-white/[0.08] text-[10px] font-mono text-rose-300 hover:text-white transition flex items-center gap-1"
                        >
                          <span>{c}</span>
                          <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                        </button>
                      ))}
                    </div>

                    {/* Odin Stamp */}
                    <span
                      className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                        isUpheld
                          ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}
                    >
                      Odin: {isUpheld ? "ESTABLISHED" : "REJECTED"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Loki — Limited Exposure Counsel (Defense) */}
        <div className="flex flex-col gap-5">
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-between shadow-sm">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
                <Shield className="w-4 h-4 text-emerald-300" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-emerald-200 uppercase font-sans tracking-wider">
                  Loki: Limited Commercial Exposure Counsel
                </h4>
                <span className="text-[10px] text-slate-400 font-mono">
                  Defense · Freight Rail, Buffer Stock & Bilateral Offsets
                </span>
              </div>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 font-bold">
              +32k t/mo Rail
            </span>
          </div>

          {/* Loki Claims List */}
          <div className="flex flex-col gap-4">
            {filteredLoki.map((claim, idx) => {
              const isFact = claim.kind === "sourced_fact" || claim.is_fact;
              const ruling = claim.ruling?.outcome?.toLowerCase() || "upheld";
              const isUpheld = ruling === "upheld";

              return (
                <div
                  key={claim.claim_id || idx}
                  className="p-5 rounded-xl bg-[#0a0d16] border border-white/[0.08] hover:border-emerald-500/30 transition-all flex flex-col gap-3 shadow-lg"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 font-bold">
                        {claim.claim_id || `LOKI-C${idx + 1}`}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {claim.country || "Midgard"} · {claim.sector || "Wheat"}
                      </span>
                    </div>

                    <span
                      className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                        isFact
                          ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                      }`}
                    >
                      {isFact ? "Sourced Fact" : "Inference"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed font-sans">
                    {claim.text}
                  </p>

                  {/* Exhibits & Citations */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/[0.06]">
                    <div className="flex flex-wrap gap-1.5">
                      {(claim.citations || ["ORV-0027", "ORV-0050"]).map((c, cIdx) => (
                        <button
                          key={cIdx}
                          onClick={() => onOpenDoc(c)}
                          className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-emerald-500/20 border border-white/[0.08] text-[10px] font-mono text-emerald-300 hover:text-white transition flex items-center gap-1"
                        >
                          <span>{c}</span>
                          <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                        </button>
                      ))}
                    </div>

                    {/* Odin Stamp */}
                    <span
                      className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                        isUpheld
                          ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                      }`}
                    >
                      Odin: {isUpheld ? "ESTABLISHED" : "CONCEDED"}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 3. Formal Cross-Examination & Attacks Ledger */}
      <div className="linear-panel p-6 sm:p-7 border border-white/[0.08] bg-[#090b11] rounded-xl shadow-xl flex flex-col gap-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            <h4 className="text-xs font-bold text-white uppercase font-sans tracking-wider">
              Cross-Examination Ledger & Counsel Concessions
            </h4>
          </div>
          <span className="text-[10px] font-mono text-slate-400">
            Adversarial Challenge & Defense Protocol
          </span>
        </div>

        <div className="space-y-3 font-sans text-xs">
          <div className="p-4 rounded-lg bg-black/40 border border-white/[0.06] flex flex-col gap-2">
            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span className="text-rose-400 font-bold">Thor Challenge ➔ Loki Rail Thesis</span>
              <span className="text-emerald-400">Concession Upheld by Odin</span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              <strong>Thor:</strong> Challenged Loki's claim that overland rail can absorb 80% of maritime volume without rolling stock proof.
            </p>
            <p className="text-emerald-300 font-mono text-[11px] bg-emerald-950/20 p-2 rounded border border-emerald-500/20">
              <strong>Loki Concession:</strong> Conceded locomotive constraints limit rail throughput to 32,000 tonnes/month (35-40% of maritime deficit), citing verified rail schedule ORV-0050.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
