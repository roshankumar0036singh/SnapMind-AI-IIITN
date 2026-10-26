import React, { useState, useRef, useEffect } from "react";
import {
  Scale,
  Lock,
  Download,
  FileText,
  CheckCircle2,
  Layout,
  Terminal,
  Activity,
  ChevronDown,
  ChevronRight,
  Database,
  ExternalLink,
  UploadCloud,
  Sparkles,
} from "lucide-react";

export default function HeaderCommandBar({
  caseData,
  casesList = [],
  activeRunNo,
  onRunChange,
  onOpenBriefing,
  onOpenIngest,
  onExportJson,
  viewMode,
  onViewModeChange,
  onSelectCase,
}) {
  const [caseMenuOpen, setCaseMenuOpen] = useState(false);
  const dropdownRef = useRef(null);

  const eventId = caseData?.scope?.event_id || caseData?.event_id || "E5";
  const caseId = caseData?.case_id || "CASE_E5_ORVAN_CORRIDOR";

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setCaseMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getEventBadge = (eid) => {
    const id = (eid || "E5").toUpperCase();
    if (id.includes("E6")) return "bg-amber-500/10 text-amber-300 border-amber-500/25";
    if (id.includes("E7")) return "bg-rose-500/10 text-rose-300 border-rose-500/25";
    if (id.includes("E8")) return "bg-purple-500/10 text-purple-300 border-purple-500/25";
    return "bg-indigo-500/10 text-indigo-300 border-indigo-500/25";
  };

  return (
    <header className="bg-[#080a0f] border-b border-white/[0.08] sticky top-0 z-40 px-6 sm:px-10 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 sm:gap-6">
        {/* Left: Brand Mark & Case Selector Dropdown */}
        <div className="flex items-center gap-3.5 shrink-0" ref={dropdownRef}>
          <div
            className="relative group cursor-pointer"
            onClick={() => setCaseMenuOpen(!caseMenuOpen)}
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500/20 via-slate-800 to-cyan-500/20 border border-indigo-500/30 flex items-center justify-center shadow-lg shadow-indigo-950/40 group-hover:border-indigo-400/60 transition duration-150">
              <Scale className="w-4 h-4 text-indigo-300" />
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-[#07090e] pulse-glow" />
          </div>

          {/* Interactive Case Selector */}
          <div className="relative">
            <button
              onClick={() => setCaseMenuOpen(!caseMenuOpen)}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg hover:bg-white/[0.05] border border-transparent hover:border-white/[0.08] transition text-left group"
              title="Switch Case / Dataset"
            >
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold tracking-wider text-slate-100 font-sans uppercase">
                    Ragnarok
                  </span>
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.2 rounded border font-semibold ${getEventBadge(
                      eventId
                    )}`}
                  >
                    {eventId}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 font-mono tracking-tight truncate max-w-[170px] sm:max-w-[240px]">
                  {caseId}
                </span>
              </div>
              <ChevronDown
                className={`w-3.5 h-3.5 text-slate-400 group-hover:text-slate-200 transition-transform duration-200 ${
                  caseMenuOpen ? "rotate-180 text-indigo-400" : ""
                }`}
              />
            </button>

            {/* Dropdown Menu of Available Cases */}
            {caseMenuOpen && (
              <div className="absolute left-0 top-full mt-2 w-80 sm:w-96 rounded-xl bg-[#0c0e17] border border-white/[0.12] shadow-2xl p-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                <div className="px-3.5 py-2.5 border-b border-white/[0.06] flex items-center justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold">
                    Adjudicated Cases & Datasets
                  </span>
                  <span className="text-[10px] font-mono text-indigo-400 font-bold">
                    {casesList.length || 1} available
                  </span>
                </div>
                <div className="max-h-72 overflow-y-auto divide-y divide-white/[0.04] mt-1 scrollbar-thin">
                  {(casesList.length > 0
                    ? casesList
                    : [
                        {
                          case_id: "CASE_E5_ORVAN_CORRIDOR",
                          event_id: "E5",
                          title: "Orvan corridor grain agreement collapse",
                          as_of_date: "2027-01-25",
                        },
                      ]
                  ).map((c) => {
                    const isCurrent = c.case_id === caseId;
                    return (
                      <button
                        key={c.case_id}
                        onClick={() => {
                          if (onSelectCase) onSelectCase(c.case_id);
                          setCaseMenuOpen(false);
                        }}
                        className={`w-full text-left p-2.5 rounded-lg flex items-start gap-2.5 transition ${
                          isCurrent
                            ? "bg-indigo-500/15 border border-indigo-500/30 text-white shadow-xs"
                            : "hover:bg-white/[0.04] text-slate-300 hover:text-white"
                        }`}
                      >
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0 mt-0.5 ${getEventBadge(
                            c.event_id
                          )}`}
                        >
                          {c.event_id || "E5"}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium font-sans truncate">
                            {c.title || c.case_id}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400 flex items-center gap-2 mt-0.5">
                            <span>As-Of: {c.as_of_date || "2027-01-25"}</span>
                            {c.total_runs && <span>· {c.total_runs} Run(s)</span>}
                          </div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Center: View Mode Segmented Pill */}
        <div className="flex items-center p-1 rounded-lg bg-white/[0.03] border border-white/[0.07] shadow-inner shrink-0">
          <button
            onClick={() => onViewModeChange("showcase")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              viewMode === "showcase"
                ? "bg-white/[0.12] text-white shadow-xs border border-white/10"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layout className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Showcase</span>
          </button>
          <button
            onClick={() => onViewModeChange("console")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              viewMode === "console"
                ? "bg-white/[0.12] text-white shadow-xs border border-white/10"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Terminal className="w-3.5 h-3.5 text-cyan-400" />
            <span>Tribunal Console</span>
          </button>
        </div>

        {/* Right Status & Action Cluster */}
        <div className="flex items-center gap-2.5 sm:gap-3.5 shrink-0">
          {/* Simulated Clock Cutoff Badge */}
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/[0.03] border border-white/[0.07] text-[11px] font-mono text-slate-300">
            <Lock className="w-3 h-3 text-amber-400" />
            <span className="text-slate-400">Clock:</span>
            <span className="text-slate-200 font-medium">{caseData?.as_of || "2027-01-25"}</span>
          </div>

          {/* Run Segmented Pill */}
          {viewMode === "console" && (
            <div className="flex items-center p-0.5 rounded-md bg-white/[0.03] border border-white/[0.07] text-xs">
              {(caseData?.runs && caseData.runs.length > 0
                ? caseData.runs
                : [{ run_no: 1, sufficiency: "sufficient" }]
              ).map((run, idx) => {
                const rNum = run.run_no || idx + 1;
                const isInsufficient = run.sufficiency === "insufficient";
                const isSelected = activeRunNo === rNum;
                return (
                  <button
                    key={rNum}
                    onClick={() => onRunChange(rNum)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                      isSelected
                        ? "bg-indigo-600/30 text-indigo-200 border border-indigo-500/40 shadow-xs"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Run {rNum}{" "}
                    <span
                      className={`text-[9px] font-mono ml-0.5 ${
                        isInsufficient ? "text-amber-400" : "text-emerald-400"
                      }`}
                    >
                      {isInsufficient ? "• Send-Back" : "• Upheld"}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Judicial Briefing Trigger */}
          <button
            onClick={onOpenBriefing}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-xs text-indigo-200 font-medium transition shadow-xs"
          >
            <FileText className="w-3.5 h-3.5 text-indigo-300" />
            <span>Briefing</span>
          </button>

          {/* Ingest Pack Trigger (Section 4.5 Live Round Requirement) */}
          <button
            onClick={onOpenIngest}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-xs text-emerald-300 font-medium transition shadow-xs"
            title="Ingest Live Round Event Pack (Section 4.5)"
          >
            <UploadCloud className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">Ingest Pack</span>
          </button>

          {/* Export OKF Deliverables Bundle */}
          <button
            onClick={onExportJson}
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-slate-400 hover:text-slate-200 transition"
            title="Download OKF Deliverables Bundle"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>Export OKF</span>
          </button>
        </div>
      </div>
    </header>
  );
}
