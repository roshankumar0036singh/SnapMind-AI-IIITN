import React, { useState } from "react";
import { Search, Play, CheckCircle2, AlertCircle, Clock, ShieldCheck, Loader2 } from "lucide-react";

export default function QuestionQueryBox({
  initialQuestion,
  asOfDate,
  verification,
  scope,
  onRunInvestigation,
  onOpenDoc,
  isLoading,
}) {
  const [question, setQuestion] = useState(
    initialQuestion ||
      "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports."
  );
  const [dateVal, setDateVal] = useState(asOfDate || "2027-01-25");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onRunInvestigation) {
      onRunInvestigation(question, dateVal);
    }
  };

  const isReal = verification?.verdict === "real";

  return (
    <div className="border-b border-white/[0.06] bg-[#090a0f] px-6 sm:px-8 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col gap-2.5">
        {/* Row 1: Sleek Linear-style Search Input */}
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a disruption query for Heimdall Gatekeeper verification..."
              className="w-full pl-9 pr-12 py-2 bg-white/[0.03] border border-white/[0.08] rounded-md text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/50 focus:bg-white/[0.05] transition font-sans"
            />
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:flex items-center">
              <kbd className="px-1.5 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-[10px] font-mono text-slate-500">
                ⌘K
              </kbd>
            </div>
          </div>

          {/* Temporal Clock Cutoff Pill */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white/[0.03] border border-white/[0.08] rounded-md text-xs font-mono text-slate-300">
              <Clock className="w-3 h-3 text-slate-400" />
              <span className="text-slate-500 text-[11px]">As-Of:</span>
              <input
                type="text"
                value={dateVal}
                onChange={(e) => setDateVal(e.target.value)}
                className="w-20 bg-transparent border-none text-slate-200 focus:outline-none font-mono text-xs"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="px-4 py-1.5 bg-white text-slate-950 hover:bg-slate-200 disabled:opacity-50 rounded-md text-xs font-medium flex items-center gap-1.5 transition shrink-0 shadow-sm"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin text-slate-950" />
                  <span>Evaluating...</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 text-slate-950 fill-slate-950" />
                  <span>Run Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>

        {/* Row 2: Unified Quiet Metadata & Presets Strip */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
          {/* Left: Heimdall Gatekeeper Status */}
          <div className="flex flex-wrap items-center gap-2 text-slate-400 text-[11px]">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-glow"></span>
              <span>Disruption Verified ({(verification?.confidence || 0.98) * 100}%)</span>
            </span>
            <span className="text-slate-600">·</span>
            <span>Realms: <strong className="text-slate-200 font-sans">{(scope?.target_countries || ["Midgard", "Tolan"]).join(", ")}</strong></span>
            <span className="text-slate-600">·</span>
            <span>Commodities: <strong className="text-slate-200 font-sans">{(scope?.target_sectors || ["Wheat", "Maize"]).join(", ")}</strong></span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-400">Notice:</span>
            <button
              onClick={() => onOpenDoc && onOpenDoc("ORV-0016")}
              className="text-indigo-400 hover:text-indigo-300 font-mono font-semibold underline decoration-indigo-500/30"
            >
              ORV-0016
            </button>
          </div>

          {/* Right: Quick Benchmark Presets */}
          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500">
            <span>Presets:</span>
            <button
              type="button"
              onClick={() => setQuestion("As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports.")}
              className="text-slate-400 hover:text-white transition"
            >
              E5 Baseline
            </button>
            <span className="text-slate-700">·</span>
            <button
              type="button"
              onClick={() => setQuestion("Evaluate Midgard wheat exposure under Ravik overland rail diversion vs maritime collapse as of 25 January 2027.")}
              className="text-slate-400 hover:text-white transition"
            >
              Rail Diversion
            </button>
            <span className="text-slate-700">·</span>
            <button
              type="button"
              onClick={() => setQuestion("Assess Tolan coastal transshipment vulnerability for wheat and maize post-corridor expiration.")}
              className="text-slate-400 hover:text-white transition"
            >
              Coastal Shock
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
