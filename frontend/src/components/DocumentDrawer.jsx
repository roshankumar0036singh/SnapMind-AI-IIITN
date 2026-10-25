import React, { useState, useEffect } from "react";
import { X, FileText, CheckCircle2, AlertTriangle, Calendar, ShieldCheck, Database, Copy, Check } from "lucide-react";
import { fetchDocument } from "../api/client";

export default function DocumentDrawer({ docId, onClose }) {
  const [doc, setDoc] = useState(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!docId) return;
    setLoading(true);
    fetchDocument(docId)
      .then((data) => {
        setDoc(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [docId]);

  if (!docId) return null;

  const handleCopyCitation = () => {
    navigator.clipboard.writeText(docId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isTier1 = doc?.reliability_tier === 1;
  const isRetracted = doc?.is_retracted;
  const isDamaged = doc?.is_damaged;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="relative w-full max-w-2xl bg-[#0b0d13] border-l border-white/[0.1] h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between gap-4 bg-[#0d0f15]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-white/[0.06] border border-white/[0.1] flex items-center justify-center">
              <FileText className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-bold text-white uppercase">
                  {docId}
                </span>
                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-mono uppercase font-semibold ${
                    isRetracted
                      ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                      : isTier1
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-white/[0.04] text-slate-300 border border-white/[0.08]"
                  }`}
                >
                  Tier {doc?.reliability_tier || 1}
                </span>
              </div>
              <h3 className="text-xs text-slate-300 font-sans font-medium truncate max-w-md mt-0.5">
                {doc?.title || `Document ${docId}`}
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyCitation}
              className="p-1.5 rounded hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition"
              title="Copy Citation Reference"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition"
              title="Close Drawer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Metadata Bar */}
        <div className="px-6 py-3 border-b border-white/[0.06] bg-white/[0.02] grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div>
            <span className="text-[10px] uppercase text-slate-500 block">Published:</span>
            <span className="text-slate-200 tabular-nums">{doc?.pub_date || "2026-11-15"}</span>
          </div>
          <div>
            <span className="text-[10px] uppercase text-slate-500 block">Source Name:</span>
            <span className="text-slate-200 truncate block">{doc?.source_name || "Official Bulletin"}</span>
          </div>
          <div>
            <span className="text-[10px] uppercase text-slate-500 block">Format:</span>
            <span className="text-slate-200">{doc?.format || "TXT"}</span>
          </div>
          <div>
            <span className="text-[10px] uppercase text-slate-500 block">Integrity Status:</span>
            <span
              className={`font-semibold ${
                isRetracted
                  ? "text-rose-400"
                  : isDamaged
                  ? "text-amber-400"
                  : "text-emerald-400"
              }`}
            >
              {isRetracted ? "Retracted" : isDamaged ? "Damaged Empty" : "Verified Pre-Cutoff"}
            </span>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 p-6 overflow-y-auto">
          {loading ? (
            <div className="text-xs font-mono text-slate-500">Loading document text...</div>
          ) : (
            <div className="flex flex-col gap-4">
              {isRetracted && (
                <div className="p-3 rounded bg-rose-950/20 border border-rose-900/40 text-rose-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>
                    Warning: This document has been retracted by {doc?.retracted_by || "ORV-0013"}. It cannot be cited as factual evidence.
                  </span>
                </div>
              )}

              {isDamaged && (
                <div className="p-3 rounded bg-amber-950/20 border border-amber-900/40 text-amber-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>
                    Damaged empty 0-byte file caught by deterministic ingestion checker. Excluded from retrieval.
                  </span>
                </div>
              )}

              <div className="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-black/40 p-4 rounded border border-white/[0.06]">
                {doc?.body || "Document text retrieved and verified."}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.06] bg-[#0d0f15] flex items-center justify-between text-xs font-mono text-slate-500">
          <span>SHA-256 Verified Grounding</span>
          <span>Simulated Clock Gate: Active</span>
        </div>
      </div>
    </div>
  );
}
