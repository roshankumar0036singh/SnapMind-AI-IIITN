import React, { useState, useEffect } from "react";
import { FileSpreadsheet, Lock, CheckCircle2, AlertOctagon, TrendingDown, ExternalLink } from "lucide-react";
import { fetchTradeTable } from "../../api/client";

export default function TradeLedgerView({ onOpenDoc }) {
  const [tableData, setTableData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    setIsLoading(true);
    fetchTradeTable("TRD-E5-01")
      .then(setTableData)
      .finally(() => setIsLoading(false));
  }, []);

  const tableMeta = {
    table_id: tableData?.table_id || "TRD-E5-01",
    country_pair: tableData?.country_pair || "Orvan -> Midgard",
    sector: tableData?.sector || "Wheat (Bulk Maritime Freight)",
    unit: tableData?.unit || "USD Millions",
    period: tableData?.period || "2026-07 to 2026-12",
    as_of: "2027-01-25",
  };

  const rows = tableData?.rows || [];
  const summary = tableData?.calculation_summary || {
    pre_expiry_baseline: 93.05,
    post_expiry_trough: 34.63,
    net_drop_percent: -62.8,
    net_drop_value: -58.42,
  };

  return (
    <div className="flex flex-col gap-6 w-full animate-fade-in">
      {/* Top Math Summary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Pre-Expiry Baseline (Jul-Aug)
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-white tabular-nums">
            ${summary.pre_expiry_baseline?.toFixed(2)}M / mo
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Mean baseline volume: 259,000 tonnes
          </div>
        </div>

        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Post-Expiry Trough (Oct-Dec)
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-rose-400 tabular-nums">
            ${summary.post_expiry_trough?.toFixed(2)}M / mo
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Customs filings ORV-0009 row 4-6
          </div>
        </div>

        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Verified Maritime Contraction
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-rose-400 tabular-nums">
            {summary.net_drop_percent?.toFixed(1)}% ({summary.net_drop_value ? `$${summary.net_drop_value.toFixed(2)}M` : ""})
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Thor's raw maritime upper bound
          </div>
        </div>

        <div className="linear-panel p-4 flex flex-col justify-between">
          <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400">
            Row Cutoff Gate
          </div>
          <div className="mt-2 text-xl sm:text-2xl font-bold font-mono text-emerald-400 tabular-nums">
            Row #07 Quarantined
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            Feb 2027 row strictly excluded
          </div>
        </div>
      </div>

      {/* Main Trade Table */}
      <div className="linear-panel overflow-hidden">
        <div className="px-5 py-3.5 border-b border-white/[0.08] flex flex-wrap items-center justify-between gap-3 bg-[#0d0f15]">
          <div>
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-white font-sans">
                Trade Ledger: {tableMeta.table_id} ({tableMeta.country_pair} • {tableMeta.sector})
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Granular trade row verification. Every row identified by TABLE-ID#row.
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs text-slate-400">
            <span>Unit: <strong className="text-slate-200">{tableMeta.unit}</strong></span>
            <span>•</span>
            <span>Period: <strong className="text-slate-200">{tableMeta.period}</strong></span>
          </div>
        </div>

        {/* Rows Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-white/[0.06] bg-white/[0.02] text-slate-400 font-mono text-[11px]">
                <th className="py-3 px-4 font-medium uppercase">Citation ID</th>
                <th className="py-3 px-4 font-medium uppercase">Reporting Month</th>
                <th className="py-3 px-4 font-medium uppercase">Value ($M)</th>
                <th className="py-3 px-4 font-medium uppercase">Volume (Tonnes)</th>
                <th className="py-3 px-4 font-medium uppercase">Status</th>
                <th className="py-3 px-4 font-medium uppercase">Analytical Phase</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04]">
              {rows.map((r, idx) => {
                const isBlocked = r.status === "excluded_post_cutoff";
                return (
                  <tr
                    key={idx}
                    className={`transition ${isBlocked ? "bg-rose-950/10 text-slate-500 line-through opacity-70" : "hover:bg-white/[0.02] text-slate-200"}`}
                  >
                    <td className="py-3 px-4 font-mono font-medium whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.08] text-indigo-300">
                        {r.citation || `${tableMeta.table_id}#${String(r.row_no).padStart(2, "0")}`}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono whitespace-nowrap tabular-nums">
                      {r.month}
                    </td>
                    <td className="py-3 px-4 font-mono font-semibold tabular-nums whitespace-nowrap">
                      ${r.value.toFixed(1)}M
                    </td>
                    <td className="py-3 px-4 font-mono tabular-nums whitespace-nowrap">
                      {r.volume.toLocaleString()} t
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold ${
                          isBlocked
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        }`}
                      >
                        {isBlocked ? "Blocked: Post-Cutoff" : "Valid (Pre-Cutoff)"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-xs font-sans">
                      {r.phase}
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
