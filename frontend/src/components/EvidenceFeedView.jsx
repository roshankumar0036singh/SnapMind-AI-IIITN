import React, { useState, useEffect } from "react";
import { Clock, Filter, ExternalLink, Calendar, Shield, Search } from "lucide-react";
import { fetchEvidenceFeed } from "../api/client";

export default function EvidenceFeedView({ onOpenDoc }) {
  const [selectedTier, setSelectedTier] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [feedItems, setFeedItems] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    fetchEvidenceFeed()
      .then((items) => {
        setFeedItems(items || []);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const filtered = feedItems.filter((item) => {
    if (selectedTier !== "all" && item.tier !== selectedTier) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchText = (item.text || item.summary || "").toLowerCase();
      const matchDoc = (item.doc_id || "").toLowerCase();
      const matchSrc = (item.source || "").toLowerCase();
      return matchText.includes(q) || matchDoc.includes(q) || matchSrc.includes(q);
    }
    return true;
  });

  return (
    <div className="flex flex-col gap-5 w-full animate-fade-in">
      {/* Controls & Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-white/[0.06]">
        <div>
          <h2 className="text-sm font-semibold text-white font-sans flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-400" />
            <span>Chronological Evidence Feed (Replayed to Simulated Clock Cutoff)</span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Strict temporal ordering of verified Runemark documents. Post-cutoff items are blocked.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Search Input */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search feed..."
              className="pl-8 pr-3 py-1 bg-white/[0.04] border border-white/[0.08] rounded text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-white/[0.2]"
            />
          </div>

          {/* Tier Filter */}
          <div className="flex items-center p-0.5 rounded-md bg-white/[0.04] border border-white/[0.08] text-xs">
            <button
              onClick={() => setSelectedTier("all")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                selectedTier === "all" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Tiers
            </button>
            <button
              onClick={() => setSelectedTier("Tier 1")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                selectedTier === "Tier 1" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Tier 1 (Official)
            </button>
            <button
              onClick={() => setSelectedTier("Tier 2")}
              className={`px-2.5 py-1 rounded text-xs font-medium transition ${
                selectedTier === "Tier 2" ? "bg-white/[0.12] text-white" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Tier 2 (Trade Press)
            </button>
          </div>
        </div>
      </div>

      {/* Feed List (Linear Issue Feed Style) */}
      <div className="linear-panel divide-y divide-white/[0.04]">
        {filtered.map((item, idx) => {
          const isTier1 = item.tier === "Tier 1";
          const isRetracted = (item.text || "").includes("[RETRACTED]");

          return (
            <div
              key={item.id || idx}
              onClick={() => onOpenDoc(item.doc_id)}
              className="p-3.5 sm:px-5 hover:bg-white/[0.02] cursor-pointer transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
            >
              <div className="flex items-start sm:items-center gap-3">
                <span className="font-mono text-xs text-slate-400 tabular-nums shrink-0 mt-0.5 sm:mt-0">
                  {item.date}
                </span>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenDoc(item.doc_id);
                  }}
                  className="font-mono text-xs px-1.5 py-0.5 rounded bg-white/[0.04] group-hover:bg-white/[0.08] border border-white/[0.08] text-indigo-300 transition shrink-0"
                >
                  {item.doc_id}
                </button>

                <div className="flex flex-col sm:flex-row sm:items-center gap-1.5 sm:gap-2">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-mono uppercase font-semibold shrink-0 ${
                      isRetracted
                        ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                        : isTier1
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-white/[0.04] text-slate-300 border border-white/[0.08]"
                    }`}
                  >
                    {item.tier}
                  </span>

                  <span className="text-xs text-slate-200 leading-normal font-sans">
                    {item.text || item.summary}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-400 shrink-0 self-end sm:self-auto font-mono text-[11px]">
                <span>{item.source}</span>
                <ExternalLink className="w-3 h-3 text-slate-500 opacity-0 group-hover:opacity-100 transition" />
              </div>
            </div>
          );
        })}

        {filtered.length === 0 && (
          <div className="p-8 text-center text-xs text-slate-400">
            No events match the selected filter.
          </div>
        )}
      </div>
    </div>
  );
}
