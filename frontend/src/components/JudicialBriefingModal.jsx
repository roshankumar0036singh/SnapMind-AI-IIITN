import React, { useState } from "react";
import { X, Copy, Check, Download, FileText, Scale, Lock } from "lucide-react";

export default function JudicialBriefingModal({ onClose, onOpenDoc, briefingText }) {
  const [copied, setCopied] = useState(false);

  const hasBriefing = Boolean(briefingText && briefingText.trim());
  const content = hasBriefing ? briefingText.trim() : null;

  const handleCopy = () => {
    if (!content) return;
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!content) return;
    const blob = new Blob([content], { type: "text/markdown;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "final_briefing_OKF.md");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 animate-fade-in">
      <div className="relative w-full max-w-3xl bg-[#0b0d13] border border-white/[0.1] rounded-xl shadow-2xl flex flex-col max-h-[88vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between gap-4 bg-[#0d0f15]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white/[0.06] border border-white/[0.1] flex items-center justify-center">
              <Scale className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-white uppercase tracking-wide">
                  OKF Deliverable
                </span>
                {hasBriefing ? (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                    Adjudicated
                  </span>
                ) : (
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-mono uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20 font-bold">
                    Awaiting Adjudication
                  </span>
                )}
              </div>
              <h3 className="text-xs text-slate-300 font-sans font-medium mt-0.5">
                Odin's Final Judicial Intelligence Briefing (Open Knowledge Format)
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={!hasBriefing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition ${
                hasBriefing
                  ? "bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.08] text-slate-300 cursor-pointer"
                  : "bg-white/[0.02] border-white/[0.04] text-slate-600 cursor-not-allowed opacity-40"
              }`}
              title={hasBriefing ? "Copy Markdown" : "Briefing not ready"}
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
            <button
              onClick={handleDownload}
              disabled={!hasBriefing}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs transition ${
                hasBriefing
                  ? "bg-white/[0.04] hover:bg-white/[0.08] border-white/[0.08] text-slate-300 cursor-pointer"
                  : "bg-white/[0.02] border-white/[0.04] text-slate-600 cursor-not-allowed opacity-40"
              }`}
              title={hasBriefing ? "Download Markdown" : "Briefing not ready"}
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 p-6 overflow-y-auto">
          {hasBriefing ? (
            <div className="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-black/40 p-5 rounded-lg border border-white/[0.06] select-text">
              {content}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center text-center py-20 px-6 space-y-4 min-h-[320px]">
              <div className="w-12 h-12 rounded-xl bg-white/[0.03] border border-white/[0.08] flex items-center justify-center text-slate-500">
                <Lock className="w-5 h-5 text-slate-500" />
              </div>
              <div className="space-y-1.5 max-w-sm">
                <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wide">
                  Briefing Awaiting Adjudication
                </h4>
                <p className="text-xs text-slate-500 font-sans leading-relaxed">
                  This document remains sealed. The official judicial executive briefing (Open Knowledge Format) will be compiled and displayed here once Supreme Judge Odin completes the final calibrated rulings.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.06] bg-[#0d0f15] flex items-center justify-between text-xs font-mono text-slate-500">
          <span>{hasBriefing ? "Odin Adjudication Grounded in Sourced Rulings Only" : "Deliberation Pre-Trial Standby"}</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 transition font-sans text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
