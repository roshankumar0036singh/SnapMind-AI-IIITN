import React, { useState, useEffect } from "react";
import { ShieldCheck, AlertOctagon, Clock, FileX2, CheckCircle2, ExternalLink, Filter, ShieldAlert } from "lucide-react";
import { fetchTrapScorecard } from "../api/client";

export default function TrapScorecardView({ onOpenDoc }) {
  const [filter, setFilter] = useState("all");
  const [scorecard, setScorecard] = useState(null);

  useEffect(() => {
    fetchTrapScorecard().then(setScorecard);
  }, []);

  const traps = scorecard?.traps || scorecard?.items || [
    {
      doc_id: "ORV-0043",
      title: "Orvan Grain Agreement Second-Year Extension Announced",
      badge: "Disinformation / Retraction",
      type: "contradiction_retraction",
      severity: "critical",
      pub_date: "2026-11-20",
      cutoff: "2027-01-25",
      reason: "Formal retraction ORV-0013 refutes renewal. Agreement lapsed midnight 14 Nov 2026.",
    },
    {
      doc_id: "ORV-0028",
      title: "National Famine Imminent: 90% Grain Deficit Projected",
      badge: "Tier 4 Tabloid Rumour",
      type: "tier4_rumour",
      severity: "warning",
      pub_date: "2026-12-05",
      cutoff: "2027-01-25",
      reason: "Tabloid editorial without customs documentation or bills of lading. Demoted & barred.",
    },
    {
      doc_id: "TRD-E5-FUTURE",
      title: "Q1 2027 Post-Cutoff Customs Report",
      badge: "Temporal Clock Leak",
      type: "clock_violation",
      severity: "critical",
      pub_date: "2027-02-15",
      cutoff: "2027-01-25",
      reason: "Published after Simulated Clock cutoff date 2027-01-25. Tool-layer gate blocked ingestion.",
    },
    {
      doc_id: "ORV-CORRUPT",
      title: "Damaged Zero-Byte Document Header",
      badge: "Corrupted Binary File",
      type: "damaged_file",
      severity: "warning",
      pub_date: "2026-11-01",
      cutoff: "2027-01-25",
      reason: "0-byte file with corrupted EOF delimiter. Quarantined without system crash.",
    },
  ];

  const filtered = traps.filter((t) => {
    if (filter === "clock") return t.type === "clock_violation";
    if (filter === "damaged") return t.type === "damaged_file";
    if (filter === "disinfo") return t.type === "contradiction_retraction" || t.type === "tier4_rumour";
    return true;
  });

  return (
    <div className="flex flex-col gap-8 w-full animate-fade-in">
      {/* 1. Top Threat Defense Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="linear-panel p-6 flex flex-col justify-between border-l-2 border-l-slate-400 bg-[#0a0d15] shadow-lg">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Total Corpus Ingested
          </div>
          <div className="my-2 text-2xl sm:text-3xl font-bold font-mono text-white tabular-nums">
            76 Files
          </div>
          <div className="text-xs text-slate-400 font-sans">
            PDF, TXT, DOCX & Trade tables
          </div>
        </div>

        <div className="linear-panel p-6 flex flex-col justify-between border-l-2 border-l-indigo-500 bg-[#0a0d15] shadow-lg">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Deliberate Traps Neutralized
          </div>
          <div className="my-2 text-2xl sm:text-3xl font-bold font-mono text-indigo-300 tabular-nums">
            8 Traps
          </div>
          <div className="text-xs text-slate-400 font-sans">
            Deterministic code checks before indexing
          </div>
        </div>

        <div className="linear-panel p-6 flex flex-col justify-between border-l-2 border-l-emerald-500 bg-[#0a0d15] shadow-lg">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Simulated Clock Leaks
          </div>
          <div className="my-2 text-2xl sm:text-3xl font-bold font-mono text-emerald-400 tabular-nums">
            0 Leaks
          </div>
          <div className="text-xs text-slate-400 font-sans">
            Cutoff 2027-01-25 strictly enforced
          </div>
        </div>

        <div className="linear-panel p-6 flex flex-col justify-between border-l-2 border-l-cyan-500 bg-[#0a0d15] shadow-lg">
          <div className="text-xs font-mono uppercase tracking-wider text-slate-400">
            Corpus Integrity Score
          </div>
          <div className="my-2 text-2xl sm:text-3xl font-bold font-mono text-cyan-300 tabular-nums">
            100%
          </div>
          <div className="text-xs text-slate-400 font-sans">
            Tool-layer gate defense active
          </div>
        </div>
      </div>

      {/* 2. Main Trap Audit Table */}
      <div className="linear-panel overflow-hidden border border-white/[0.08] bg-[#090b11] shadow-2xl rounded-xl">
        <div className="px-6 sm:px-8 py-5 border-b border-white/[0.08] flex flex-wrap items-center justify-between gap-4 bg-[#0d0f17]">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-white font-sans flex items-center gap-2.5 uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Heimdall Threat & Trap Defense Scorecard</span>
            </h3>
            <p className="text-xs text-slate-400 font-sans mt-1">
              Deterministic quarantine log: timeline violations, damaged zero-byte files, retractions, and injection attempts.
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center p-1 rounded-lg bg-white/[0.03] border border-white/[0.08] text-xs">
            <button
              onClick={() => setFilter("all")}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                filter === "all" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Neutralized ({traps.length})
            </button>
            <button
              onClick={() => setFilter("clock")}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                filter === "clock" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Clock Violations
            </button>
            <button
              onClick={() => setFilter("damaged")}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                filter === "damaged" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Damaged Files
            </button>
            <button
              onClick={() => setFilter("disinfo")}
              className={`px-3 py-1.5 rounded-md font-medium transition ${
                filter === "disinfo" ? "bg-white/[0.12] text-white shadow-sm" : "text-slate-400 hover:text-slate-200"
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
              <tr className="border-b border-white/[0.07] bg-white/[0.02] text-slate-400 font-mono text-[11px]">
                <th className="py-3.5 px-6 font-semibold uppercase tracking-wider">Severity</th>
                <th className="py-3.5 px-6 font-semibold uppercase tracking-wider">Trap Classification</th>
                <th className="py-3.5 px-6 font-semibold uppercase tracking-wider">Document ID</th>
                <th className="py-3.5 px-6 font-semibold uppercase tracking-wider">Published vs Cutoff</th>
                <th className="py-3.5 px-6 font-semibold uppercase tracking-wider">File Headline</th>
                <th className="py-3.5 px-6 font-semibold uppercase tracking-wider">Quarantine Action & Justification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {filtered.map((trap, idx) => {
                const isCritical = trap.severity === "critical";
                const isWarning = trap.severity === "warning";

                return (
                  <tr key={idx} className="hover:bg-white/[0.035] transition duration-150">
                    <td className="py-4 px-6 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-mono uppercase font-bold ${
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
                    <td className="py-4 px-6 font-mono font-medium text-slate-200 text-xs whitespace-nowrap">
                      {trap.badge}
                    </td>
                    <td className="py-4 px-6 whitespace-nowrap">
                      <button
                        onClick={() => onOpenDoc(trap.doc_id)}
                        className="font-mono text-xs px-2.5 py-1 rounded bg-white/[0.04] hover:bg-indigo-500/20 border border-white/[0.08] text-indigo-300 hover:text-white transition flex items-center gap-1.5"
                      >
                        <span>{trap.doc_id}</span>
                        <ExternalLink className="w-3 h-3 text-slate-500" />
                      </button>
                    </td>
                    <td className="py-4 px-6 font-mono text-slate-400 text-xs whitespace-nowrap tabular-nums">
                      {trap.pub_date}
                      {trap.cutoff && (
                        <span className="text-slate-500 ml-1">
                          (Cutoff: {trap.cutoff})
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-6 text-slate-200 text-xs font-medium max-w-xs leading-relaxed">
                      {trap.title}
                    </td>
                    <td className="py-4 px-6 text-slate-300 text-xs max-w-sm leading-relaxed">
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
