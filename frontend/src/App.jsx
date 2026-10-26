import React, { useState, useEffect } from "react";
import HeaderCommandBar from "./components/HeaderCommandBar";
import ShowcaseLandingView from "./components/ShowcaseLandingView";
import ClaudeTribunalWorkspace from "./components/ClaudeTribunalWorkspace";
import DocumentDrawer from "./components/DocumentDrawer";
import JudicialBriefingModal from "./components/JudicialBriefingModal";
import PackIngestionModal from "./components/PackIngestionModal";

import { fetchCase, fetchCases, runTrialPipeline } from "./api/client";

export default function App() {
  const [viewMode, setViewMode] = useState("console"); // "console" (Claude workspace) or "showcase"
  const [activeRunNo, setActiveRunNo] = useState(1);
  const [inspectedDocId, setInspectedDocId] = useState(null);
  const [briefingOpen, setBriefingOpen] = useState(false);
  const [ingestModalOpen, setIngestModalOpen] = useState(false);
  const [caseData, setCaseData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const [casesList, setCasesList] = useState([]);

  useEffect(() => {
    fetchCases().then((list) => {
      if (list && list.length) {
        setCasesList(list);
      }
    });
  }, []);

  const handleSelectCase = async (selectedCaseId) => {
    setIsLoading(true);
    try {
      const data = await fetchCase(selectedCaseId);
      if (data) {
        setCaseData(data);
        if (data?.runs?.length) {
          setActiveRunNo(data.runs.length);
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRunInvestigation = async (question, asOf, eventId) => {
    setIsLoading(true);
    try {
      const res = await runTrialPipeline(
        question,
        asOf || caseData?.as_of || "2027-01-25",
        eventId || caseData?.scope?.event_id || "E5"
      );
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

  return (
    <div className="h-screen w-screen overflow-hidden bg-[#06070a] text-slate-100 flex flex-col font-sans selection:bg-white/[0.15] selection:text-white">
      {/* VIEW MODE 1: SHOWCASE LANDING PAGE */}
      {viewMode === "showcase" && (
        <div className="flex-1 overflow-y-auto">
          <HeaderCommandBar
            caseData={caseData}
            casesList={casesList}
            activeRunNo={activeRunNo}
            onRunChange={setActiveRunNo}
            onSelectCase={handleSelectCase}
            onOpenBriefing={() => setBriefingOpen(true)}
            onOpenIngest={() => setIngestModalOpen(true)}
            onExportJson={handleExportJson}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
          <ShowcaseLandingView
            onEnterConsole={() => setViewMode("console")}
            onOpenBriefing={() => setBriefingOpen(true)}
            onOpenDoc={setInspectedDocId}
          />
        </div>
      )}

      {/* VIEW MODE 2: CLAUDE-STYLE TRIBUNAL WORKSPACE (DRAGGABLE DUAL SIDEBARS + DOCKED CHATBAR) */}
      {viewMode === "console" && (
        <div className="flex-1 overflow-hidden flex flex-col">
          <ClaudeTribunalWorkspace
            caseData={caseData}
            casesList={casesList}
            activeRunNo={activeRunNo}
            onRunChange={setActiveRunNo}
            onSelectCase={handleSelectCase}
            onRunInvestigation={handleRunInvestigation}
            onOpenDoc={setInspectedDocId}
            onOpenBriefing={() => setBriefingOpen(true)}
            onOpenIngest={() => setIngestModalOpen(true)}
            onExportJson={handleExportJson}
            onViewModeChange={setViewMode}
            isLoading={isLoading}
          />
        </div>
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

      {/* Live Round Event Pack Ingestion Modal (Section 4.5 Functional Requirement) */}
      {ingestModalOpen && (
        <PackIngestionModal
          onClose={() => setIngestModalOpen(false)}
          onCaseIngested={() => {
            fetchCases().then((list) => {
              if (list && list.length) setCasesList(list);
            });
          }}
        />
      )}
    </div>
  );
}
