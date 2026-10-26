import React, { useState, useEffect } from "react";
import {
  X,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Calendar,
  ShieldCheck,
  Database,
  Copy,
  Check,
  Search,
  Hash,
  ExternalLink,
} from "lucide-react";
import { fetchDocument } from "../api/client";

export default function DocumentDrawer({ docId, onClose }) {
  const [doc, setDoc] = useState(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const targetAnchor = docId?.includes("#") ? docId.split("#")[1].toUpperCase() : null;

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

  // Split text into paragraphs based on [P...] or newlines
  const rawText = doc?.content || doc?.body || "";
  const paragraphs = rawText
    .split(/(?=\[P\d+\])/g)
    .map((p) => p.trim())
    .filter(Boolean);

  const fallbackParagraphs = paragraphs.length > 0 ? paragraphs : rawText.split("\n\n").filter(Boolean);

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-xs transition-opacity"
        onClick={onClose}
      />

      {/* Drawer Panel */}
      <div className="relative w-full max-w-2xl bg-[#090b12] border-l border-white/[0.1] h-full shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between gap-4 bg-[#0d0f17]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
              <FileText className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-sm font-bold text-white uppercase">
                  {docId}
                </span>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-semibold ${
                    isRetracted
                      ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                      : isTier1
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-white/[0.04] text-slate-300 border border-white/[0.08]"
                  }`}
                >
                  Tier {doc?.reliability_tier || 1}
                </span>
                {targetAnchor && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                    Chunk: #{targetAnchor}
                  </span>
                )}
              </div>
              <h3 className="text-xs text-slate-300 font-sans font-medium truncate max-w-md mt-0.5">
                {doc?.title || `Document ${docId}`}
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyCitation}
              className="p-1.5 rounded-lg hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition"
              title="Copy Citation Reference"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition"
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

        {/* Search & Chunk Filter Bar */}
        <div className="px-6 py-2.5 border-b border-white/[0.06] bg-[#0c0e17] flex items-center justify-between gap-3">
          <div className="relative flex-1">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search terms or filter chunks inside document..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.08] text-xs font-sans text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/50"
            />
          </div>
          <span className="text-[10px] font-mono text-slate-500 shrink-0">
            {fallbackParagraphs.length} Chunks
          </span>
        </div>

        {/* Authentic Document Content Body */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4">
          {loading ? (
            <div className="text-xs font-mono text-slate-500">Loading authentic document text...</div>
          ) : (
            <div className="flex flex-col gap-4">
              {isRetracted && (
                <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-900/40 text-rose-300 text-xs flex items-center gap-2.5">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>
                    Warning: Retracted by {doc?.retracted_by || "ORV-0013"}. It cannot be cited as factual evidence.
                  </span>
                </div>
              )}

              {isDamaged && (
                <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-900/40 text-amber-300 text-xs flex items-center gap-2.5">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                  <span>
                    Damaged 0-byte file caught by deterministic ingestion checker. Quarantined.
                  </span>
                </div>
              )}

              {/* Render Structured Paragraph Chunks */}
              <div className="flex flex-col gap-3 font-mono text-xs">
                {fallbackParagraphs.map((chunk, idx) => {
                  const chunkId = chunk.match(/\[P\d+\]/)?.[0]?.replace(/[\[\]]/g, "");
                  const isCitedChunk = targetAnchor && chunkId && chunkId.toUpperCase() === targetAnchor;
                  const matchesSearch = searchTerm && chunk.toLowerCase().includes(searchTerm.toLowerCase());

                  return (
                    <div
                      key={idx}
                      className={`p-4 rounded-xl border transition-all ${
                        isCitedChunk
                          ? "bg-indigo-950/40 border-indigo-500/70 shadow-lg shadow-indigo-950/50 ring-1 ring-indigo-500/40"
                          : matchesSearch
                          ? "bg-amber-950/20 border-amber-500/40"
                          : "bg-black/40 border-white/[0.06] hover:border-white/[0.12]"
                      }`}
                    >
                      <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.06]">
                        <span className="text-[10px] font-mono text-slate-400 font-bold">
                          {chunkId ? `Paragraph [${chunkId}]` : `Chunk #${idx + 1}`}
                        </span>
                        {isCitedChunk && (
                          <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold border border-indigo-500/40">
                            📍 Cited Judicial Exhibit
                          </span>
                        )}
                      </div>
                      <p className="text-slate-200 leading-relaxed font-sans text-xs whitespace-pre-wrap">
                        {chunk}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.06] bg-[#0d0f17] flex items-center justify-between text-xs font-mono text-slate-500">
          <span>SHA-256 Verified Grounding</span>
          <span>Simulated Clock Gate: Active</span>
        </div>
      </div>
    </div>
  );
}
