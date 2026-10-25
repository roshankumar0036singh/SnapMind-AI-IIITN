import React, { useState } from "react";
import { Scale, Zap, Shield, Gavel, CheckCircle2, AlertTriangle, ArrowRight, ExternalLink, Filter } from "lucide-react";

export default function AdversarialDebateView({ activeRun, caseData, onOpenDoc }) {
  const [filterType, setFilterType] = useState("all");
  const thorClaims = activeRun?.claims?.filter((c) => c.agent === "thor") || activeRun?.thor_claims || [];
  const lokiClaims = activeRun?.claims?.filter((c) => c.agent === "loki") || activeRun?.loki_claims || [];
  const attacks = activeRun?.attacks || [];
  const defences = activeRun?.defences || [];

  const budget = caseData?.budget || {
    turns_used: activeRun?.debate_turns?.length || 2,
    max_debate_turns: 12,
    stable_cycles: 2,
    max_stable_cycles: 2,
    tool_calls_used: caseData?.limits?.tool_calls_used || 8,
    max_tool_calls: 40,
    tokens_used: caseData?.limits?.tokens_used || 24500,
    max_tokens: 120000,
    wall_seconds_used: 14.2,
    limit_hit: caseData?.termination || "CONVERGED_STABLE",
  };

  const isSendBack = activeRun?.sufficiency === "insufficient";
  const establishedList = activeRun?.classification?.established || [];
  const contestedList = activeRun?.classification?.contested || [];
  const concededList = activeRun?.classification?.conceded || [];

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
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Sub-Header Bar: Controls & Filters */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-white/[0.06]">
        <div>
          <h2 className="text-base font-semibold text-white font-sans flex items-center gap-2.5">
            <Scale className="w-4 h-4 text-indigo-400" />
            <span>Adversarial Courtroom Chamber (Open-Ended Convergence Deliberation)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Autonomous multi-turn convergence debate: Counsel cross-examine until judicial stability is reached or safety budget fires.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-white/[0.04] border border-white/[0.08] text-xs">
          <button
            onClick={() => setFilterType("all")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${filterType === "all" ? "bg-white/[0.14] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
          >
            All Claims ({thorClaims.length + lokiClaims.length})
          </button>
          <button
            onClick={() => setFilterType("facts")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${filterType === "facts" ? "bg-white/[0.14] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
          >
            Sourced Facts Only
          </button>
          <button
            onClick={() => setFilterType("inferences")}
            className={`px-3 py-1.5 rounded-md text-xs font-medium transition ${filterType === "inferences" ? "bg-white/[0.14] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
          >
            Inferences Only
          </button>
        </div>
      </div>

      {/* NEW ELEMENT: Debate Convergence & Judicial State Visualizer */}
      <div className="linear-panel p-5 border-white/[0.08] bg-[#0c0e15] flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
              <Gavel className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-200">
                  Judicial State & Convergence Loop
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${isSendBack
                      ? "bg-amber-500/15 text-amber-300 border border-amber-500/30"
                      : "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                    }`}
                >
                  {isSendBack ? "Send-Back Triggered" : budget.limit_hit || "CONVERGED_STABLE"}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans mt-0.5">
                {isSendBack
                  ? "Odin found evidence insufficient for judicial closure. Case remanded to Heimdall for supplemental retrieval."
                  : "Debate achieved stable equilibrium across adversarial counsel with verified citations and cross-examination answers."}
              </p>
            </div>
          </div>

          {/* Classification Stats Chips */}
          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
              Established: <strong>{establishedList.length}</strong>
            </span>
            <span className="px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-amber-300">
              Contested: <strong>{contestedList.length}</strong>
            </span>
            <span className="px-2.5 py-1 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300">
              Conceded: <strong>{concededList.length}</strong>
            </span>
          </div>
        </div>

        {/* Safety Budget & Resource Telemetry Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-white/[0.06] font-mono text-xs">
          <div className="p-2.5 rounded bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500 block uppercase">Debate Turns</span>
            <span className="text-slate-200 font-semibold">
              {budget.turns_used} / {budget.max_debate_turns || 12}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">({budget.stable_cycles || 2} stable)</span>
          </div>
          <div className="p-2.5 rounded bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500 block uppercase">Tool Call Budget</span>
            <span className="text-slate-200 font-semibold">
              {budget.tool_calls_used || 0} / {budget.max_tool_calls || 40}
            </span>
            <span className="text-[10px] text-slate-500 ml-1">calls</span>
          </div>
          <div className="p-2.5 rounded bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500 block uppercase">Token Burn</span>
            <span className="text-slate-200 font-semibold">
              {(budget.tokens_used || 0).toLocaleString()} / {(budget.max_tokens || 120000).toLocaleString()}
            </span>
          </div>
          <div className="p-2.5 rounded bg-white/[0.02] border border-white/[0.04]">
            <span className="text-[10px] text-slate-500 block uppercase">Convergence Status</span>
            <span className="text-emerald-400 font-semibold">
              {budget.stable_cycles >= 2 ? "Equilibrium reached" : "Deliberating..."}
            </span>
          </div>
        </div>

        {/* Send-Back Missing Evidence Request Alert */}
        {isSendBack && activeRun?.missing?.length > 0 && (
          <div className="p-3 rounded bg-amber-950/20 border border-amber-900/40 text-xs">
            <span className="text-amber-400 font-mono font-bold block mb-1">
              Odin Evidence Deficit Remand Notice:
            </span>
            <ul className="list-disc list-inside text-amber-200/80 space-y-0.5">
              {activeRun.missing.map((m, i) => (
                <li key={i}>{m}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Dual Column Debate Grid (Thor on Left, Loki on Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* THOR'S COLUMN (HIGH EXPOSURE) */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between px-4 py-3 rounded-t-lg bg-rose-950/20 border border-rose-900/40 border-b-0">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-rose-300 font-mono">
                Thor • High Exposure Counsel
              </span>
            </div>
            <span className="text-xs font-mono text-rose-400">
              {filteredThor.length} claims
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {filteredThor.map((claim, idx) => {
              const claimId = claim.claim_id || claim.id;
              const ruling =
                claim.ruling ||
                activeRun?.rulings?.find((r) => r.claim_id === claimId);
              const isUpheld = ruling?.outcome === "upheld";
              const isRejected = ruling?.outcome === "rejected";
              const isContested =
                ruling?.outcome === "contested" ||
                contestedList.includes(claimId);
              const isEstablished =
                isUpheld || establishedList.includes(claimId);
              const isConceded =
                isRejected || concededList.includes(claimId);
              const isFact = claim.kind === "sourced_fact" || claim.is_fact;

              return (
                <div
                  key={claimId || idx}
                  className="linear-panel p-6 flex flex-col gap-3.5 hover:border-white/[0.16] transition"
                >
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-slate-200 font-semibold text-sm">
                        {claimId}
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="text-slate-300 font-medium">{claim.country} / {claim.sector}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Classification Badge */}
                      {isEstablished && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          Established
                        </span>
                      )}
                      {isContested && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-500/15 text-amber-400 border border-amber-500/30">
                          Contested
                        </span>
                      )}
                      {isConceded && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          Conceded / Refuted
                        </span>
                      )}

                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase ${isFact
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                          }`}
                      >
                        {isFact ? "Sourced Fact" : "Inference"}
                      </span>
                      {claim.estimate_high !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-mono text-xs font-bold">
                          {claim.estimate_high}%
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-slate-200 leading-relaxed font-sans">
                    {claim.text}
                  </p>

                  {/* Citations */}
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs text-slate-400 font-mono">Citations:</span>
                    {(claim.citations || [claim.citation]).filter(Boolean).map((cite, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => onOpenDoc(cite)}
                        className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-mono text-indigo-300 transition flex items-center gap-1.5"
                      >
                        <span>{cite}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500" />
                      </button>
                    ))}
                  </div>

                  {/* Odin's Definitive Judicial Ruling */}
                  {ruling && (
                    <div className="mt-2 pt-3 border-t border-white/[0.06] flex items-start gap-3 bg-white/[0.015] -mx-6 -mb-6 p-4 rounded-b-lg">
                      <Gavel className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                      <div className="flex-1 text-xs">
                        <div className="flex items-center gap-2.5 mb-1">
                          <span
                            className={`font-mono text-xs font-bold uppercase px-2 py-0.5 rounded ${isUpheld
                                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                                : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                              }`}
                          >
                            Odin: {ruling.outcome}
                          </span>
                          <span className="text-slate-400 font-mono text-xs">
                            ({ruling.basis})
                          </span>
                        </div>
                        <p className="text-slate-300 leading-relaxed">
                          {ruling.reasoning}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* LOKI'S COLUMN (LIMITED EXPOSURE / MITIGATION) */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between px-4 py-3 rounded-t-lg bg-emerald-950/20 border border-emerald-900/40 border-b-0">
            <div className="flex items-center gap-2.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-300 font-mono">
                Loki • Limited Exposure Counsel
              </span>
            </div>
            <span className="text-xs font-mono text-emerald-400">
              {filteredLoki.length} claims
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {filteredLoki.map((claim, idx) => {
              const claimId = claim.claim_id || claim.id;
              const ruling =
                claim.ruling ||
                activeRun?.rulings?.find((r) => r.claim_id === claimId);
              const isUpheld = ruling?.outcome === "upheld";
              const isRejected = ruling?.outcome === "rejected";
              const isContested =
                ruling?.outcome === "contested" ||
                contestedList.includes(claimId);
              const isEstablished =
                isUpheld || establishedList.includes(claimId);
              const isConceded =
                isRejected || concededList.includes(claimId);
              const isFact = claim.kind === "sourced_fact" || claim.is_fact;

              return (
                <div
                  key={claimId || idx}
                  className="linear-panel p-6 flex flex-col gap-3.5 hover:border-white/[0.16] transition"
                >
                  <div className="flex items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono text-slate-200 font-semibold text-sm">
                        {claimId}
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="text-slate-300 font-medium">{claim.country} / {claim.sector}</span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Classification Badge */}
                      {isEstablished && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          Established
                        </span>
                      )}
                      {isContested && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-amber-500/15 text-amber-400 border border-amber-500/30">
                          Contested
                        </span>
                      )}
                      {isConceded && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-rose-500/15 text-rose-400 border border-rose-500/30">
                          Conceded / Refuted
                        </span>
                      )}

                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-mono uppercase ${isFact
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-sky-500/10 text-sky-400 border border-sky-500/20"
                          }`}
                      >
                        {isFact ? "Sourced Fact" : "Inference"}
                      </span>
                      {claim.estimate_high !== undefined && (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono text-xs font-bold">
                          {claim.estimate_high}%
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="text-sm text-slate-200 leading-relaxed font-sans">
                    {claim.text}
                  </p>

                  {/* Citations */}
                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <span className="text-xs text-slate-400 font-mono">Citations:</span>
                    {(claim.citations || [claim.citation]).filter(Boolean).map((cite, cIdx) => (
                      <button
                        key={cIdx}
                        onClick={() => onOpenDoc(cite)}
                        className="px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-xs font-mono text-indigo-300 transition flex items-center gap-1.5"
                      >
                        <span>{cite}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500" />
                      </button>
                    ))}
                  </div>

                  {/* Odin's Definitive Judicial Ruling */}
                  {ruling && (
                    <div className="mt-2 pt-3 border-t border-white/[0.06] flex items-start gap-3 bg-white/[0.015] -mx-6 -mb-6 p-4 rounded-b-lg">
                      <Gavel className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                      <div className="flex-1 text-xs">
                        <div className="flex items-center gap-2.5 mb-1">
                          <span
                            className={`font-mono text-xs font-bold uppercase px-2 py-0.5 rounded ${isUpheld
                                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                                : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                              }`}
                          >
                            Odin: {ruling.outcome}
                          </span>
                          <span className="text-slate-400 font-mono text-xs">
                            ({ruling.basis})
                          </span>
                        </div>
                        <p className="text-slate-300 leading-relaxed">
                          {ruling.reasoning}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Cross-Examination & Concessions Section with Generous Padding */}
      <div className="linear-panel p-6 sm:p-8">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 font-mono mb-4">
          Cross-Examination Attacks & Adversarial Concessions (Round 2)
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Attacks */}
          <div className="flex flex-col gap-3">
            <div className="text-xs font-mono text-slate-400 uppercase font-semibold">
              Attacks Filed:
            </div>
            {attacks.map((atk, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.06] flex flex-col gap-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-rose-400 font-semibold">
                    {atk.attack_id} → {atk.target_claim_id}
                  </span>
                  <span className="px-2 py-0.5 rounded bg-white/[0.04] text-slate-400 font-mono text-[11px] uppercase">
                    Grounds: {atk.grounds}
                  </span>
                </div>
                <p className="text-slate-300 leading-relaxed text-xs">
                  {atk.text}
                </p>
                {atk.evidence_refs?.length > 0 && (
                  <div className="flex items-center gap-2 mt-1 text-xs font-mono text-slate-400">
                    <span>Evidence:</span>
                    {atk.evidence_refs.map((ref, rIdx) => (
                      <button
                        key={rIdx}
                        onClick={() => onOpenDoc(ref)}
                        className="text-indigo-400 hover:underline"
                      >
                        {ref}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Defences & Concessions */}
          <div className="flex flex-col gap-3">
            <div className="text-xs font-mono text-slate-400 uppercase font-semibold">
              Defences & Concessions:
            </div>
            {defences.map((def, idx) => {
              const isConcession = def.response_type === "concede";
              return (
                <div key={idx} className="p-4 rounded-lg bg-white/[0.02] border border-white/[0.06] flex flex-col gap-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-200 font-semibold">
                      {def.defence_id} (re: {def.attack_id})
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-mono uppercase font-bold ${isConcession
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        }`}
                    >
                      {isConcession ? "Concession" : "New Evidence"}
                    </span>
                  </div>
                  <p className="text-slate-300 leading-relaxed text-xs">
                    {def.text}
                  </p>
                  {def.new_refs?.length > 0 && (
                    <div className="flex items-center gap-2 mt-1 text-xs font-mono text-slate-400">
                      <span>New Ref:</span>
                      {def.new_refs.map((ref, rIdx) => (
                        <button
                          key={rIdx}
                          onClick={() => onOpenDoc(ref)}
                          className="text-indigo-400 hover:underline"
                        >
                          {ref}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
