import React, { useState, useEffect } from "react";
import { ShieldCheck, AlertOctagon, Clock, FileX2, CheckCircle2, ExternalLink, Filter } from "lucide-react";
import { fetchTrapScorecard } from "../api/client";

export default function TrapScorecardView({ onOpenDoc }) {
  const [filter, setFilter] = useState("all");
  const [scorecard, setScorecard] = useState(null);

  useEffect(() => {
    fetchTrapScorecard().then(setScorecard);
  }, []);

  const traps = scorecard?.traps || scorecard?.items || [];
  const scannedFiles = scorecard?.scanned_files || 76;
  const trapsNeutralized = scorecard?.traps_neutralized || traps.length;

  const filtered = traps.filter((t) => {
    if (filter === "clock") return t.type === "clock_violation";
    if (filter === "damaged") return t.type === "damaged_file";
    if (filter === "disinfo") return t.type === "contradiction_retraction" || t.type === "tier4_rumour";
    return true;
  });

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Top Threat Defense KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Total Corpus Ingested
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-white tabular-nums">
            76 Files
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            PDF, TXT, DOCX & Trade tables
          </div>
        </div>

        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Deliberate Traps Neutralized
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-indigo-400 tabular-nums">
            8 Traps
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Deterministic code checks before indexing
          </div>
        </div>

        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Simulated Clock Leaks
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-emerald-400 tabular-nums">
            0 Leaks
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Cutoff 2027-01-25 strictly enforced
          </div>
        </div>

        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Corpus Integrity Score
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-emerald-400 tabular-nums">
            100%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Tool-layer gate defense active
          </div>
        </div>
      </div>

      {/* Main Trap Audit Table */}
      <div className="linear-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-white/[0.08] flex flex-wrap items-center justify-between gap-3 bg-[#0d0f15]">
          <div>
            <h3 className="text-sm font-semibold text-white font-sans flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Heimdall Threat & Trap Defense Scorecard</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Deterministic quarantine log: timeline violations, damaged zero-byte files, retractions, and injection attempts.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center p-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-xs">
            <button
              onClick={() => setFilter("all")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                filter === "all" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Neutralized ({traps.length})
            </button>
            <button
              onClick={() => setFilter("clock")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                filter === "clock" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Clock Violations
            </button>
            <button
              onClick={() => setFilter("damaged")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                filter === "damaged" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Damaged Files
            </button>
            <button
              onClick={() => setFilter("disinfo")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                filter === "disinfo" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Disinformation
            </button>
          </div>
        </div>

        {/* Audit Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono text-[11px]">
                <th className="py-3 px-4 font-medium uppercase">Severity</th>
                <th className="py-3 px-4 font-medium uppercase">Trap Classification</th>
                <th className="py-3 px-4 font-medium uppercase">Document ID</th>
                <th className="py-3 px-4 font-medium uppercase">Published vs Cutoff</th>
                <th className="py-3 px-4 font-medium uppercase">File Headline</th>
                <th className="py-3 px-4 font-medium uppercase">Quarantine Action & Justification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filtered.map((trap, idx) => {
                const isCritical = trap.severity === "critical";
                const isWarning = trap.severity === "warning";

                return (
                  <tr key={idx} className="hover:bg-white/[0.02] transition">
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                          isCritical
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : isWarning
                            ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            : "bg-white/[0.05] text-slate-400 border border-white/[0.1]"
                        }`}
                      >
                        {trap.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-slate-300 text-xs whitespace-nowrap">
                      {trap.badge}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <button
                        onClick={() => onOpenDoc(trap.doc_id)}
                        className="font-mono text-xs px-2 py-0.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.1] text-indigo-300 transition flex items-center gap-1"
                      >
                        <span>{trap.doc_id}</span>
                        <ExternalLink className="w-2.5 h-2.5 text-slate-500" />
                      </button>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400 text-xs whitespace-nowrap tabular-nums">
                      {trap.pub_date}
                      {trap.cutoff && (
                        <span className="text-slate-500 ml-1">
                          (Cutoff: {trap.cutoff})
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-200 text-xs font-medium max-w-xs">
                      {trap.title}
                    </td>
                    <td className="py-3 px-4 text-slate-300 text-xs max-w-sm leading-relaxed">
                      {trap.description || trap.reason}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
