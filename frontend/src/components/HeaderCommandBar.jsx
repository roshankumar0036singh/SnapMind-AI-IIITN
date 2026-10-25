import React from "react";
import { Scale, Lock, Download, FileText, CheckCircle2, Layout, LayoutDashboard, Terminal } from "lucide-react";

export default function HeaderCommandBar({
  caseData,
  activeRunNo,
  onRunChange,
  onOpenBriefing,
  onExportJson,
  viewMode,
  onViewModeChange,
}) {
  return (
    <header className="border-b border-white/[0.08] bg-[#090a0f]/95 backdrop-blur-md sticky top-0 z-40 px-6 sm:px-10 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Brand & Context */}
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-lg bg-white/[0.06] border border-white/[0.12] flex items-center justify-center">
            <Scale className="w-4 h-4 text-slate-200" />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold tracking-tight text-white font-sans uppercase">
              Ragnarok Intelligence
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-white/[0.06] border border-white/[0.1] text-slate-300">
              {caseData?.scope?.event_id || "E5"}
            </span>
            <span className="hidden lg:inline text-xs text-slate-500 font-mono">
              / {caseData?.case_id || "CASE-2027-E5-ORVAN"}
            </span>
          </div>
        </div>

        {/* View Mode Switcher: Showcase vs Console */}
        <div className="flex items-center p-1 rounded-lg bg-white/[0.04] border border-white/[0.08]">
          <button
            onClick={() => onViewModeChange("showcase")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition ${
              viewMode === "showcase"
                ? "bg-white/[0.14] text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Layout className="w-3.5 h-3.5" />
            <span>Showcase & Overview</span>
          </button>
          <button
            onClick={() => onViewModeChange("console")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition ${
              viewMode === "console"
                ? "bg-white/[0.14] text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Tribunal Console</span>
          </button>
        </div>

        {/* Right Status Controls */}
        <div className="flex items-center gap-3">
          {/* Simulated Clock Cutoff Gate */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/[0.03] border border-white/[0.08] text-xs font-mono text-slate-300">
            <Lock className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Clock Cutoff:</span>
            <span className="text-slate-200 font-medium">
              {caseData?.as_of || "2027-01-25"}
            </span>
          </div>

          {/* Dynamic Run Segmented Control */}
          {viewMode === "console" && (
            <div className="flex items-center p-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-xs">
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
                    className={`px-3 py-1 rounded text-xs font-medium transition ${
                      isSelected
                        ? "bg-white/[0.14] text-white shadow-sm"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Run {rNum}{" "}
                    <span
                      className={`text-[10px] font-mono ml-1 ${
                        isInsufficient ? "text-amber-400" : "text-emerald-400"
                      }`}
                    >
                      {isInsufficient ? "Send-Back" : "Verdict"}
                    </span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Action: Judicial Briefing */}
          <button
            onClick={onOpenBriefing}
            className="flex items-center gap-2 px-3.5 py-1.5 rounded-md bg-white/[0.06] hover:bg-white/[0.1] border border-white/[0.1] text-xs text-slate-200 font-medium transition"
          >
            <FileText className="w-3.5 h-3.5 text-slate-300" />
            <span>Briefing</span>
          </button>

          {/* Action: Export OKF Bundle */}
          <button
            onClick={onExportJson}
            className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-slate-400 hover:text-slate-200 transition"
            title="Download OKF deliverables bundle"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export OKF</span>
          </button>
        </div>
      </div>
    </header>
  );
}
