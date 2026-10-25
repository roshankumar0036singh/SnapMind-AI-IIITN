import React from "react";
import {
  Scale,
  Shield,
  Zap,
  Gavel,
  ArrowRight,
  CheckCircle2,
  Lock,
  Brain,
  FileSpreadsheet,
  Layers,
  FileText,
  ExternalLink,
  ChevronRight,
  TrendingDown,
  ShieldAlert,
} from "lucide-react";

export default function ShowcaseLandingView({ onEnterConsole, onOpenBriefing, onOpenDoc }) {
  const agents = [
    {
      name: "Heimdall",
      role: "Gatekeeper & Temporal Sentinel",
      tag: "Verification",
      color: "text-amber-400",
      border: "border-amber-500/20",
      bg: "bg-amber-500/5",
      badgeBg: "bg-amber-500/10 text-amber-300",
      description:
        "Extracts disruption scope, enforces the simulated clock cutoff, and verifies whether the shock is real, a rumour, or unverifiable before waking counsel.",
      constraints: "Does not debate • Re-searches upon Odin send-back • 0 clock leaks",
      stat: "76 Docs Ingested",
    },
    {
      name: "Thor",
      role: "High Exposure Counsel",
      tag: "Prosecution",
      color: "text-rose-400",
      border: "border-rose-500/20",
      bg: "bg-rose-500/5",
      badgeBg: "bg-rose-500/10 text-rose-300",
      description:
        "Builds the strongest evidence-backed case for high commercial exposure, maritime port collapse, and compounding regional supply shocks.",
      constraints: "Every claim cited • Must answer attacks with new evidence or concede",
      stat: "-60.5% Peak Bound",
    },
    {
      name: "Loki",
      role: "Limited Exposure Counsel",
      tag: "Defense",
      color: "text-emerald-400",
      border: "border-emerald-500/20",
      bg: "bg-emerald-500/5",
      badgeBg: "bg-emerald-500/10 text-emerald-300",
      description:
        "Investigates buffer inventories, bilateral surges, and overland rail freight to prove commercial mitigation and resilience.",
      constraints: "Assumptions barred without scale • Modifies search filters via private memory",
      stat: "+32k t/mo Rail Freight",
    },
    {
      name: "Odin",
      role: "Allfather & Supreme Judge",
      tag: "Adjudication",
      color: "text-indigo-400",
      border: "border-indigo-500/20",
      bg: "bg-indigo-500/5",
      badgeBg: "bg-indigo-500/10 text-indigo-300",
      description:
        "Rules impartially on 100% of claims, separates sourced facts from inferences, issues send-backs for missing data, and synthesizes calibrated ranges.",
      constraints: "Never plans or searches • Rulings written only from evidence blackboard",
      stat: "100% Ruled R1 & R2",
    },
  ];

  const proofPillars = [
    {
      title: "Planner-Free Blackboard",
      subtitle: "Deterministic State Machine",
      desc: "No single LLM acts as central orchestrator. Each agent evaluates independent wake conditions over shared case state, preventing hallucinated consensus.",
      badge: "NFR1 Architecture",
    },
    {
      title: "Tool-Layer Temporal Clock Gate",
      subtitle: "Zero Timeline Leaks",
      desc: "Simulated clock cutoff (2027-01-25) enforced in Python tools before LLM prompting. Future reports and post-cutoff trade rows are quarantined deterministically.",
      badge: "Section 6 & 8",
    },
    {
      title: "Deliberate Traps Neutralized",
      subtitle: "8 Out of 8 Traps Caught",
      desc: "0-byte corrupted files, retracted renewal claims (ORV-0043), post-cutoff leaks, and sensational tabloid rumours (ORV-0028) quarantined without crashing.",
      badge: "Section 8 Traps",
    },
    {
      title: "Granular Trade Table Math",
      subtitle: "TABLE-ID#row Verification",
      desc: "Baseline computations calculated via code from tabular rows. Demonstrates maritime contraction (-62.8%) cushioned by bilateral trade surge.",
      badge: "Section 9 Math",
    },
    {
      title: "Private Lasting Memory (NFR9)",
      subtitle: "Observable Behavioral Change",
      desc: "Loki's Tier 4 claim rejected in Run 1 -> Lesson written -> Run 2 search filter auto-restricted to tier_max: 2 -> Verified Tier 1 evidence retrieved.",
      badge: "Acceptance Check 9",
    },
    {
      title: "Open Knowledge Format (OKF)",
      subtitle: "Self-Contained Audit Bundle",
      desc: "Exports reproducible bundle containing case_file.json, events.log, and final_briefing.md with verified [[wiki-links]] to authentic evidence.",
      badge: "Section 7 Deliverables",
    },
  ];

  return (
    <div className="w-full flex flex-col items-center">
      {/* =========================================================================
          HERO SECTION (LINEAR STYLE: AIRY, CONFIDENT, DEEP DARK, SPACIOUS)
          ========================================================================= */}
      <section className="w-full max-w-6xl mx-auto px-6 pt-20 pb-24 sm:pt-28 sm:pb-32 flex flex-col items-center text-center">
        {/* Top Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-xs font-mono text-slate-300 mb-8 hover:bg-white/[0.07] transition cursor-default">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
          <span>Trial of the Nine Realms • Autonomous Multi-Agent Tribunal</span>
        </div>

        {/* Primary Headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-semibold tracking-tight text-white leading-[1.08] max-w-4xl font-sans">
          Supply chain disruption, <br className="hidden sm:inline" />
          <span className="text-slate-400">judged like a court of law.</span>
        </h1>

        {/* Subtitle with Breathing Room */}
        <p className="mt-8 text-base sm:text-lg text-slate-400 max-w-2xl font-sans leading-relaxed">
          An adversarial multi-agent system operating on a deterministic blackboard.
          Four specialized agents investigate, cross-examine, and calibrate commercial
          exposure without a central planner.
        </p>

        {/* CTA Buttons with Generous Spacing */}
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <button
            onClick={onEnterConsole}
            className="flex items-center gap-2.5 px-6 py-3 rounded-lg bg-white text-slate-950 hover:bg-slate-200 font-medium text-sm transition shadow-lg shadow-white/5"
          >
            <span>Enter Live Tribunal Console</span>
            <ArrowRight className="w-4 h-4" />
          </button>

          <button
            onClick={onOpenBriefing}
            className="flex items-center gap-2 px-5 py-3 rounded-lg bg-white/[0.05] hover:bg-white/[0.09] border border-white/[0.1] text-slate-200 font-medium text-sm transition"
          >
            <FileText className="w-4 h-4 text-indigo-400" />
            <span>Read Judicial Briefing (OKF)</span>
          </button>
        </div>

        {/* Spaced-Out Metric Ribbon */}
        <div className="w-full max-w-4xl mt-20 pt-10 border-t border-white/[0.06] grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          <div>
            <div className="text-2xl sm:text-3xl font-semibold font-mono text-white tabular-nums">
              0
            </div>
            <div className="text-xs text-slate-500 font-mono uppercase tracking-wider mt-1">
              Central Planners
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-semibold font-mono text-emerald-400 tabular-nums">
              100%
            </div>
            <div className="text-xs text-slate-500 font-mono uppercase tracking-wider mt-1">
              Grounded Citations
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-semibold font-mono text-indigo-400 tabular-nums">
              8 of 8
            </div>
            <div className="text-xs text-slate-500 font-mono uppercase tracking-wider mt-1">
              Traps Neutralized
            </div>
          </div>
          <div>
            <div className="text-2xl sm:text-3xl font-semibold font-mono text-rose-400 tabular-nums">
              0 Leaks
            </div>
            <div className="text-xs text-slate-500 font-mono uppercase tracking-wider mt-1">
              Simulated Clock Gates
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          INTERACTIVE BENCHMARK SNAPSHOT (CLEAN & SPACIOUS PREVIEW)
          ========================================================================= */}
      <section className="w-full max-w-6xl mx-auto px-6 py-12">
        <div className="rounded-xl border border-white/[0.08] bg-[#0c0e14] p-8 sm:p-10 flex flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/[0.06]">
            <div>
              <div className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                Benchmark Deliberation • Dev Pack E5
              </div>
              <h2 className="text-xl sm:text-2xl font-semibold text-white mt-1">
                Termination of the Multilateral Orvan Sea Corridor
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                Adjudicated & Calibrated
              </span>
              <button
                onClick={onEnterConsole}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-mono flex items-center gap-1 ml-2"
              >
                <span>Inspect in Console</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Calibrated Range Highlight Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="p-6 rounded-lg bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">Midgard Wheat Exposure</span>
                  <span className="text-xs font-mono text-emerald-400">ESTABLISHED</span>
                </div>
                <div className="mt-4 flex items-baseline gap-3">
                  <span className="text-2xl sm:text-3xl font-bold font-mono text-indigo-300 tabular-nums">
                    -44.0% to -51.2%
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    (-$39.5M to -$46.0M/mo)
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-3 leading-relaxed">
                  Thor proved a 60.5% collapse in direct Orvan maritime transits (ORV-0009#P7).
                  Loki proved that overland rail freight via Ravik (+32,000 t/mo) and Vanir bilateral
                  surges (ORV-0027) cushion total commercial exposure.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center gap-2 text-[11px] font-mono text-slate-500">
                <span>Citations:</span>
                <button onClick={() => onOpenDoc("ORV-0009")} className="text-indigo-400 hover:underline">ORV-0009#P7</button>
                <span>•</span>
                <button onClick={() => onOpenDoc("ORV-0027")} className="text-indigo-400 hover:underline">ORV-0027</button>
                <span>•</span>
                <button onClick={() => onOpenDoc("ORV-0050")} className="text-indigo-400 hover:underline">ORV-0050</button>
              </div>
            </div>

            <div className="p-6 rounded-lg bg-white/[0.02] border border-white/[0.06] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-white">Tolan Maize Exposure</span>
                  <span className="text-xs font-mono text-amber-400">CONTESTED</span>
                </div>
                <div className="mt-4 flex items-baseline gap-3">
                  <span className="text-2xl sm:text-3xl font-bold font-mono text-amber-300 tabular-nums">
                    -35.1% to -46.0%
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    (-$5.2M to -$6.8M/mo)
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-3 leading-relaxed">
                  Thor claimed catastrophic feed shortfall due to absence of deepwater grain docks (ORV-0046).
                  Loki argued shallow archipelagic craft absorb 70% of volume (ORV-0022).
                  Odin classified finding as Contested due to winter ice freeze risks.
                </p>
              </div>
              <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center gap-2 text-[11px] font-mono text-slate-500">
                <span>Citations:</span>
                <button onClick={() => onOpenDoc("ORV-0046")} className="text-indigo-400 hover:underline">ORV-0046</button>
                <span>•</span>
                <button onClick={() => onOpenDoc("ORV-0022")} className="text-indigo-400 hover:underline">ORV-0022</button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          THE FOUR AGENTS (SPACIOUS 4-COLUMN ARCHITECTURE GRID)
          ========================================================================= */}
      <section className="w-full max-w-6xl mx-auto px-6 py-16 sm:py-24">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="text-xs font-mono text-indigo-400 uppercase tracking-wider mb-2">
            Section 2 Architecture
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-white tracking-tight">
            Four Adversarial Roles. <br />
            Isolated Tools & Private Memory.
          </h2>
          <p className="text-sm text-slate-400 mt-3 leading-relaxed">
            Every agent operates independently under hard engineering constraints.
            No agent can read another agent's private memory or dictate Odin's verdict.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {agents.map((ag) => (
            <div
              key={ag.name}
              className="p-6 rounded-xl border border-white/[0.08] bg-[#0c0e14] hover:border-white/[0.16] transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className={`text-base font-semibold ${ag.color} font-mono`}>
                    {ag.name}
                  </span>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${ag.badgeBg}`}>
                    {ag.tag}
                  </span>
                </div>
                <div className="text-xs font-medium text-slate-200 mb-2">
                  {ag.role}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  {ag.description}
                </p>
              </div>

              <div className="mt-6 pt-4 border-t border-white/[0.06] flex flex-col gap-2">
                <div className="text-[11px] font-mono text-slate-500">
                  {ag.constraints}
                </div>
                <div className="text-xs font-mono font-medium text-slate-300">
                  {ag.stat}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* =========================================================================
          SIX PROOF PILLARS (VERCEL / LINEAR STYLE FEATURE GRID)
          ========================================================================= */}
      <section className="w-full max-w-6xl mx-auto px-6 py-16 sm:py-24 border-t border-white/[0.06]">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="text-xs font-mono text-indigo-400 uppercase tracking-wider mb-2">
            Engineering Rigor
          </div>
          <h2 className="text-2xl sm:text-4xl font-semibold text-white tracking-tight">
            Built to Pass All 10 Acceptance Checks.
          </h2>
          <p className="text-sm text-slate-400 mt-3 leading-relaxed">
            Engineered against the hard requirements of CONTEXT_UPDATED.md,
            surviving damaged data, deliberate traps, and prompt injections.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {proofPillars.map((p, idx) => (
            <div
              key={idx}
              className="p-6 rounded-xl border border-white/[0.08] bg-[#0c0e14] hover:border-white/[0.14] transition flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-mono text-indigo-400 px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                    {p.badge}
                  </span>
                </div>
                <h3 className="text-base font-semibold text-white font-sans mt-2">
                  {p.title}
                </h3>
                <div className="text-xs font-mono text-slate-400 mt-0.5 mb-2">
                  {p.subtitle}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed font-sans">
                  {p.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* =========================================================================
          BOTTOM CTA SECTION
          ========================================================================= */}
      <section className="w-full max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl sm:text-3xl font-semibold text-white">
          Ready to inspect the live adversarial tribunal?
        </h2>
        <p className="text-sm text-slate-400 mt-2 max-w-lg mx-auto">
          Explore Thor and Loki's cross-examination claims, inspect the 8 neutralized traps, and audit private agent memory events.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          <button
            onClick={onEnterConsole}
            className="flex items-center gap-2 px-6 py-3 rounded-lg bg-white text-slate-950 hover:bg-slate-200 font-medium text-sm transition shadow-lg"
          >
            <span>Launch Tribunal Console</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>
    </div>
  );
}
