import React, { useState } from "react";
import {
  Search,
  Play,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  Loader2,
  Sparkles,
  ExternalLink,
} from "lucide-react";

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

  const handleSelectPreset = (presetQ, presetD) => {
    setQuestion(presetQ);
    setDateVal(presetD);
  };

  const verdict = verification?.verdict?.toLowerCase();
  const isReal = verdict === "real";
  const isRumour = verdict === "rumour";
  const eventId = scope?.event_id || "E5";

  const getNoticeId = (eid) => {
    if (eid === "E6") return "SKA-0001";
    if (eid === "E7") return "BOR-0001";
    if (eid === "E8") return "VES-0003";
    return "ORV-0016";
  };

  const noticeId = getNoticeId(eventId);

  return (
    <div className="border-b border-white/[0.07] bg-[#06070b]/90 px-6 sm:px-10 py-5 sm:py-6 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col gap-3.5">
        {/* Row 1: Unified Minimalist Omnibar Capsule */}
        <form
          onSubmit={handleSubmit}
          className="flex items-center gap-3 p-2 sm:p-2.5 rounded-xl bg-[#0b0e17] hover:bg-[#0e121d] focus-within:bg-[#0f1422] border border-white/[0.09] focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all shadow-xl shadow-black/40"
        >
          {/* Search Icon */}
          <div className="pl-3.5 pr-1 text-slate-400">
            <Search className="w-4 h-4 text-slate-400" />
          </div>

          {/* Inquiry Input */}
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Inquire disruption impact (e.g. As of 25 Jan 2027, how exposed are Midgard and Tolan to Orvan corridor expiration?)..."
            className="flex-1 bg-transparent border-none text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none font-sans py-1"
          />

          {/* Integrated Clock Pill */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.04] border border-white/[0.07] text-xs font-mono text-slate-300 shrink-0">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span className="text-slate-400 text-[11px]">As-Of:</span>
            <input
              type="text"
              value={dateVal}
              onChange={(e) => setDateVal(e.target.value)}
              className="w-24 bg-transparent border-none text-slate-100 focus:outline-none font-mono text-xs font-medium"
            />
          </div>

          {/* Keyboard Shortcut Badge */}
          <div className="hidden md:flex items-center pr-1.5">
            <kbd className="px-2 py-0.5 rounded bg-white/[0.05] border border-white/[0.08] text-[10px] font-mono text-slate-400">
              ⌘K
            </kbd>
          </div>

          {/* Run Pipeline Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 via-indigo-600 to-indigo-700 hover:from-indigo-400 hover:to-indigo-600 text-white disabled:opacity-50 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all shrink-0 shadow-lg shadow-indigo-950/60 hover:shadow-indigo-500/25 active:scale-98"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run Pipeline</span>
              </>
            )}
          </button>
        </form>

        {/* Row 2: Streamlined Scope Capsule & Benchmark Scenario Chips */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-0.5">
          {/* Left: Heimdall Gatekeeper Scope Capsule */}
          <div className="flex items-center gap-2.5 text-slate-400 text-[11px] overflow-x-auto scrollbar-none py-0.5">
            {isRumour ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-mono font-medium shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                <span>Rumour Quarantined</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono font-medium shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-glow"></span>
                <span>Verified ({Math.round((verification?.confidence || 0.98) * 100)}%)</span>
              </span>
            )}
            <span className="text-slate-600">·</span>
            <span className="truncate">
              Realms: <strong className="text-slate-200 font-sans">{(scope?.target_countries || ["Midgard", "Tolan"]).join(", ")}</strong>
            </span>
            <span className="text-slate-600">·</span>
            <span className="truncate">
              Sectors: <strong className="text-slate-200 font-sans">{(scope?.target_sectors || ["Wheat", "Maize"]).join(", ")}</strong>
            </span>
            <span className="text-slate-600">·</span>
            <span className="text-slate-400 shrink-0">Notice:</span>
            <button
              type="button"
              onClick={() => onOpenDoc && onOpenDoc(noticeId)}
              className="text-indigo-400 hover:text-indigo-300 font-mono font-semibold underline decoration-indigo-500/30 shrink-0"
            >
              {noticeId}
            </button>
          </div>

          {/* Right: Quick Benchmark Scenario Chips in Refined Capsule */}
          <div className="flex items-center p-1 rounded-lg bg-white/[0.025] border border-white/[0.06] shadow-xs text-[11px] font-mono shrink-0 gap-1">
            <span className="text-slate-400 px-2 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-indigo-400" />
              <span>Presets:</span>
            </span>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(
                  "As of 25 January 2027, how exposed are Midgard and Tolan to the end of the Orvan corridor agreement? Give a low and high range for wheat and maize imports.",
                  "2027-01-25"
                )
              }
              className="px-2.5 py-1 rounded-md text-slate-300 hover:text-white hover:bg-white/[0.06] transition"
              title="Level 0 Baseline Pack"
            >
              E5 Orvan
            </button>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(
                  "As of 15 February 2027, assess the commercial exposure of Nordland and Tolan to the Skagen Strait container vessel grounding affecting fertiliser and grain trade.",
                  "2027-02-15"
                )
              }
              className="px-2.5 py-1 rounded-md text-slate-300 hover:text-white hover:bg-white/[0.06] transition"
              title="Level 1 Moderate Pack"
            >
              E6 Skagen
            </button>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(
                  "As of 01 March 2027, evaluate the supply shock for iron ore and agriculture between Nordland and Midgard following the Boreal rail transit sabotage.",
                  "2027-03-01"
                )
              }
              className="px-2.5 py-1 rounded-md text-slate-300 hover:text-white hover:bg-white/[0.06] transition"
              title="Level 2 High: Prompt injection & future date filter"
            >
              E7 Boreal
            </button>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(
                  "As of 10 April 2027, evaluate the impact of the Vestri subsea power cable severance on energy and aluminium production across Vestri and Alfheim.",
                  "2027-04-10"
                )
              }
              className="px-2.5 py-1 rounded-md text-slate-300 hover:text-white hover:bg-white/[0.06] transition"
              title="Level 3 Final Round: Complete cable severance"
            >
              E8 Vestri
            </button>
            <button
              type="button"
              onClick={() =>
                handleSelectPreset(
                  "As of 12 April 2027, verify the breaking news of nationwide grain poisoning in Midgard following Orvan sabotage.",
                  "2027-04-12"
                )
              }
              className="px-2.5 py-1 rounded-md bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition font-bold"
              title="Adversarial Trap Decoy: Sensational rumour test"
            >
              E8 Decoy Trap
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
