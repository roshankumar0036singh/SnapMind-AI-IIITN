import React, { useState, useEffect } from "react";
import {
  LayoutDashboard,
  Scale,
  Clock,
  ShieldCheck,
  FileSpreadsheet,
  Brain,
  Download,
  Network,
} from "lucide-react";

import HeaderCommandBar from "./components/HeaderCommandBar";
import ShowcaseLandingView from "./components/ShowcaseLandingView";
import QuestionQueryBox from "./components/QuestionQueryBox";
import CalibratedExposureView from "./components/CalibratedExposureView";
import SupplyChainTopologyView from "./components/SupplyChainTopologyView";
import AdversarialDebateView from "./components/AdversarialDebateView";
import EvidenceFeedView from "./components/EvidenceFeedView";
import TrapScorecardView from "./components/TrapScorecardView";
import TradeLedgerView from "./components/dashboard/TradeLedgerView";
import AgentMemoryView from "./components/AgentMemoryView";
import DocumentDrawer from "./components/DocumentDrawer";
import JudicialBriefingModal from "./components/JudicialBriefingModal";

import { fetchCase, runTrialPipeline } from "./api/client";

export default function App() {
  const [viewMode, setViewMode] = useState("showcase"); // "showcase" or "console"
  const [activeTab, setActiveTab] = useState("overview");
  const [activeRunNo, setActiveRunNo] = useState(1);
  const [inspectedDocId, setInspectedDocId] = useState(null);
  const [briefingOpen, setBriefingOpen] = useState(false);
  const [caseData, setCaseData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchCase().then((data) => {
      setCaseData(data);
      if (data?.runs?.length) {
        setActiveRunNo(data.runs.length);
      }
    });
  }, []);

  const handleRunInvestigation = async (question, asOf) => {
    setIsLoading(true);
    try {
      const res = await runTrialPipeline(question, asOf, caseData?.scope?.event_id || "E5");
      if (res?.case_file) {
        setCaseData(res.case_file);
        if (res.case_file.runs?.length) {
          setActiveRunNo(res.case_file.runs.length);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportJson = () => {
    if (!caseData) return;
    const blob = new Blob([JSON.stringify(caseData, null, 2)], {
      type: "application/json;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `${caseData.case_id || "case_file"}.json`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const activeRun =
    caseData?.runs?.find((r) => r.run_no === activeRunNo) ||
    caseData?.runs?.[activeRunNo - 1] ||
    caseData?.runs?.[caseData?.runs?.length - 1] ||
    caseData?.runs?.[0] ||
    null;

  const navTabs = [
    { id: "overview", label: "Exposure Matrix", icon: LayoutDashboard },
    { id: "graph_rag", label: "Graph Topology", icon: Network },
    { id: "courtroom", label: "Adversarial Debate", icon: Scale, badge: `R${activeRunNo}` },
    { id: "evidence_feed", label: "Evidence Feed", icon: Clock },
    { id: "threat_defense", label: "Trap Scorecard", icon: ShieldCheck },
    { id: "trade_tables", label: "Customs Math", icon: FileSpreadsheet },
    { id: "memory_audit", label: "Memory Audit", icon: Brain },
  ];

  return (
    <div className="min-h-screen bg-[#07080b] text-slate-100 flex flex-col font-sans selection:bg-indigo-500/20 selection:text-white">
      {/* Top Header Command Bar */}
      <HeaderCommandBar
        caseData={caseData}
        activeRunNo={activeRunNo}
        onRunChange={setActiveRunNo}
        onOpenBriefing={() => setBriefingOpen(true)}
        onExportJson={handleExportJson}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
      />

      {/* VIEW MODE 1: SHOWCASE & LANDING PAGE */}
      {viewMode === "showcase" && (
        <ShowcaseLandingView
          onEnterConsole={() => setViewMode("console")}
          onOpenBriefing={() => setBriefingOpen(true)}
          onOpenDoc={setInspectedDocId}
        />
      )}

      {/* VIEW MODE 2: TRIBUNAL ANALYTICAL CONSOLE */}
      {viewMode === "console" && (
        <>
          {/* Question Input Box with Simulated Clock Gate (Acceptance Check 7) */}
          <QuestionQueryBox
            initialQuestion={caseData?.question}
            asOfDate={caseData?.as_of}
            verification={caseData?.verification}
            scope={caseData?.scope}
            onRunInvestigation={handleRunInvestigation}
            onOpenDoc={setInspectedDocId}
            isLoading={isLoading}
          />

          {/* Sub-Navigation Tabs Strip — Single Crisp Horizontal Bar */}
          <div className="border-b border-white/[0.06] bg-[#090b10] px-6 sm:px-8">
            <div className="max-w-7xl mx-auto flex items-center gap-1 overflow-x-auto scrollbar-none py-1.5">
              {navTabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap transition relative ${isActive
                        ? "text-white bg-white/[0.08]"
                        : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.03]"
                      }`}
                  >
                    <Icon
                      className={`w-3.5 h-3.5 ${isActive ? "text-indigo-400" : "text-slate-500"
                        }`}
                    />
                    <span>{tab.label}</span>
                    {tab.badge && (
                      <span
                        className={`text-[9px] font-mono px-1.5 py-0.2 rounded ${isActive
                            ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                            : "bg-white/[0.04] text-slate-500"
                          }`}
                      >
                        {tab.badge}
                      </span>
                    )}
                    {isActive && (
                      <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-indigo-500 rounded-full" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Main Analytical Dashboard Content Area with Generous Spacing */}
          <main className="flex-1 max-w-7xl w-full mx-auto px-6 sm:px-10 py-10">
            {activeTab === "overview" && (
              <CalibratedExposureView
                matrixData={caseData?.exposure_matrix}
                activeRun={activeRun}
                caseData={caseData}
                onOpenDoc={setInspectedDocId}
                onOpenBriefing={() => setBriefingOpen(true)}
              />
            )}

            {activeTab === "graph_rag" && (
              <SupplyChainTopologyView onOpenDoc={setInspectedDocId} />
            )}

            {activeTab === "courtroom" && (
              <AdversarialDebateView
                activeRun={activeRun}
                caseData={caseData}
                onOpenDoc={setInspectedDocId}
              />
            )}

            {activeTab === "evidence_feed" && (
              <EvidenceFeedView onOpenDoc={setInspectedDocId} />
            )}

            {activeTab === "threat_defense" && (
              <TrapScorecardView onOpenDoc={setInspectedDocId} />
            )}

            {activeTab === "trade_tables" && (
              <TradeLedgerView onOpenDoc={setInspectedDocId} />
            )}

            {activeTab === "memory_audit" && (
              <AgentMemoryView
                caseData={caseData}
                onOpenDoc={setInspectedDocId}
              />
            )}
          </main>
        </>
      )}

      {/* Slide-Over Document Drawer (Linear / Vercel style) */}
      <DocumentDrawer
        docId={inspectedDocId}
        onClose={() => setInspectedDocId(null)}
      />

      {/* Judicial Briefing Modal (Open Knowledge Format) */}
      {briefingOpen && (
        <JudicialBriefingModal
          onClose={() => setBriefingOpen(false)}
          onOpenDoc={setInspectedDocId}
          briefingText={caseData?.final_briefing}
        />
      )}
    </div>
  );
}
