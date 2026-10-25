import React, { useState } from "react";
import { X, Copy, Check, Download, FileText, Scale } from "lucide-react";

export default function JudicialBriefingModal({ onClose, onOpenDoc, briefingText }) {
  const [copied, setCopied] = useState(false);

  const defaultBriefing = `# TRIAL OF THE NINE REALMS — JUDICIAL EXECUTIVE BRIEFING
**Case ID:** CASE-2027-E5-ORVAN
**Judge:** Odin Allfather, Supreme Court of Asgard
**As-Of Date:** 25 January 2027
**Target Realms:** Midgard, Tolan
**Target Commodities:** Wheat, Maize
**Disruption Event:** Termination of the Multilateral Orvan Corridor Agreement (E5)

---

## 1. Executive Summary
The judicial tribunal finds that the termination of the Orvan Corridor Agreement (ORV-0016) constitutes a verified, permanent structural maritime disruption. Direct Orvan port loadings collapsed by 62% following the expiration on 14 November 2026. However, overall net commercial exposure is materially buffered by overland rail freight via Ravik (ORV-0050, ORV-0001) and bilateral import surges from Vanir (ORV-0027). Extreme claims of catastrophic national starvation (such as tabloid rumors in ORV-0028 or unhedged 90% drops) are firmly rejected.

Net quarterly economic exposure for Midgard is established at -$39.5M to -$46.0M/mo (-44.0% to -51.2%) for Wheat, and -$20.0M to -$24.5M/mo (-48.2% to -59.0%) for Maize. Tolan's exposure is established at -$10.5M to -$13.5M/mo for Wheat, while Tolan Maize remains Contested between -$5.2M and -$6.8M/mo.

---

## 2. Judicial Classification of Findings

### A. Established Findings (Sourced Facts)
- **ORV-0016:** The Orvan Corridor Agreement formally expired at midnight on 14 November 2026 without renewal. Marine insurance subsidies are void.
- **ORV-0009#P7:** Direct Orvan-to-Midgard maritime wheat transits contracted from $90.0M (July 2026) to $34.1M (December 2026).
- **ORV-0027:** Vanir bilateral wheat deliveries to Midgard doubled from $18.2M to $36.5M in Q4 2026, offsetting $18.3M of maritime deficit.
- **ORV-0050:** Ravik Rail Link operations absorbed ~32,000 tonnes/month of overland bulk grain.

### B. Contested Findings (Disputed Inference)
- **Tolan Maize Substitution (ORV-0046 / ORV-0022):** Thor estimates a 55% contraction due to port freezing; Loki contends coastal craft absorb 70%. Odin rules this finding Contested pending verified grain silo audits.

### C. Conceded Findings (Mutual Adversarial Agreement)
- **Loki Concession (ORV-0001):** Loki initially argued rail completely neutralizes sea drop. Following Thor's challenge citing locomotive constraints, Loki conceded that rail offsets at most 35% to 40% of physical volume.
- **Thor Concession (ORV-0027):** Thor conceded that bilateral supply from Vanir prevented immediate terminal grain shortfalls in Midgard.

---

## 3. Exposure Matrix
- **Midgard Wheat:** Thor: -$54.4M (-60.5%) | Loki: -$36.1M (-40.1%) | Odin Calibrated: -$39.5M to -$46.0M (-44.0% to -51.2%)
- **Midgard Maize:** Thor: -$27.8M (-66.2%) | Loki: -$16.5M (-39.8%) | Odin Calibrated: -$20.0M to -$24.5M (-48.2% to -59.0%)
- **Tolan Wheat:** Thor: -$17.6M (-55.0%) | Loki: -$9.0M (-28.0%) | Odin Calibrated: -$10.5M to -$13.5M (-32.8% to -42.2%)
- **Tolan Maize:** Thor: -$8.2M (-55.4%) | Loki: -$4.0M (-27.0%) | Odin Calibrated: -$5.2M to -$6.8M (-35.1% to -46.0%) [Contested]

---

## 4. Next-Quarter Outlook & Assumptions
- **Assumption 1:** Ravik Rail Link maintains 4 daily dedicated freight slots without winter freeze derailments.
- **Assumption 2:** Vanir export tariffs remain stable under the existing bilateral pact.
- **Downside Risk:** If winter sea ice blocks Tolan's shallow coastal fleet, Tolan exposure will widen toward Thor's upper bound (-55%).
`;

  const content = briefingText || defaultBriefing;

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
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
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/70 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="relative w-full max-w-3xl bg-[#0b0d13] border border-white/[0.1] rounded-lg shadow-2xl flex flex-col max-h-[88vh] overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/[0.08] flex items-center justify-between gap-4 bg-[#0d0f15]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-white/[0.06] border border-white/[0.1] flex items-center justify-center">
              <Scale className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-white uppercase">
                  OKF Deliverable
                </span>
                <span className="px-1.5 py-0.2 rounded text-[10px] font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Adjudicated
                </span>
              </div>
              <h3 className="text-xs text-slate-300 font-sans font-medium mt-0.5">
                Odin's Final Judicial Intelligence Briefing (Open Knowledge Format)
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-slate-300 transition"
              title="Copy Markdown"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? "Copied" : "Copy"}</span>
            </button>
            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.08] text-xs text-slate-300 transition"
              title="Download Markdown"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-white/[0.08] text-slate-400 hover:text-slate-200 transition"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Markdown Body */}
        <div className="flex-1 p-6 overflow-y-auto">
          <div className="text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-black/40 p-5 rounded border border-white/[0.06] select-text">
            {content}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-white/[0.06] bg-[#0d0f15] flex items-center justify-between text-xs font-mono text-slate-500">
          <span>Odin Adjudication Grounded in Sourced Rulings Only</span>
          <button
            onClick={onClose}
            className="px-3 py-1 rounded bg-white/[0.06] hover:bg-white/[0.1] text-slate-300 transition font-sans text-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
