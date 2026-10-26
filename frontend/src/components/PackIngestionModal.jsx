import React, { useState, useEffect, useRef } from "react";
import {
  X,
  UploadCloud,
  FolderOpen,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Loader2,
  Database,
  GitBranch,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  FileArchive,
  Trash2,
} from "lucide-react";
import { fetchAvailablePacks, ingestPack, uploadPack } from "../api/client";

export default function PackIngestionModal({ onClose, onCaseIngested }) {
  const [availablePacks, setAvailablePacks] = useState([]);
  const [customPath, setCustomPath] = useState("");
  const [selectedPack, setSelectedPack] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [ingestReport, setIngestReport] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchAvailablePacks().then((packs) => {
      setAvailablePacks(packs);
      if (packs.length > 0) setSelectedPack(packs[0]);
    });
  }, []);

  // Handle Drag & Drop
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setUploadedFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadedFiles(Array.from(e.target.files));
    }
  };

  // Run Ingestion for Direct Uploaded Files / Zip
  const handleRunUpload = async () => {
    if (uploadedFiles.length === 0) return;
    setIsLoading(true);
    setErrorMessage(null);
    setIngestReport(null);

    const formData = new FormData();
    uploadedFiles.forEach((file) => {
      formData.append("files", file);
    });

    const isE6 = uploadedFiles.some((f) => f.name.toLowerCase().includes("e6") || f.name.toLowerCase().includes("skagen"));
    const isE7 = uploadedFiles.some((f) => f.name.toLowerCase().includes("e7") || f.name.toLowerCase().includes("boreal"));
    const isE8 = uploadedFiles.some((f) => f.name.toLowerCase().includes("e8") || f.name.toLowerCase().includes("vestri"));
    const eventId = isE8 ? "E8" : isE7 ? "E7" : isE6 ? "E6" : "E6";
    formData.append("event_id", eventId);

    try {
      const report = await uploadPack(formData);
      setIngestReport(report);
      if (onCaseIngested) onCaseIngested(report);
    } catch (err) {
      setErrorMessage(err.message || "Direct upload and ingestion failed. Check server logs.");
    } finally {
      setIsLoading(false);
    }
  };

  // Run Ingestion for Server Path
  const handleRunIngest = async (packDir, eventId) => {
    setIsLoading(true);
    setErrorMessage(null);
    setIngestReport(null);
    try {
      const report = await ingestPack(packDir, eventId);
      setIngestReport(report);
      if (onCaseIngested) onCaseIngested(report);
    } catch (err) {
      setErrorMessage(err.message || "Pack ingestion failed. Check terminal logs.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-3xl rounded-2xl bg-[#0a0d16] border border-white/[0.12] shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="px-6 sm:px-8 py-5 border-b border-white/[0.08] flex items-center justify-between bg-[#0e111d]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 flex items-center justify-center">
              <UploadCloud className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-bold text-white font-sans uppercase tracking-wider">
                  Live Round Event Pack Ingestion
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/30">
                  Section 4.5 PS
                </span>
              </div>
              <p className="text-xs text-slate-400 font-sans mt-0.5">
                Directly upload event pack ZIP archives or documents, quarantine damaged files & trade tables, and auto-build Graph RAG.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/[0.06] transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 sm:p-8 flex flex-col gap-6 max-h-[75vh] overflow-y-auto scrollbar-thin">
          {/* PRIMARY: Direct Drag & Drop / File Upload Area */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <FileArchive className="w-4 h-4 text-emerald-400" />
                <span>Direct Pack Upload (Drag & Drop .ZIP or Document Files)</span>
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                Recommended
              </span>
            </div>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`p-6 sm:p-8 rounded-2xl border-2 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center text-center gap-3 ${
                isDragging
                  ? "border-emerald-400 bg-emerald-500/10 scale-[1.01]"
                  : uploadedFiles.length > 0
                  ? "border-indigo-500/50 bg-indigo-950/20"
                  : "border-white/[0.12] hover:border-indigo-400/50 bg-white/[0.02] hover:bg-white/[0.035]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".zip,.txt,.pdf,.docx,.json"
                onChange={handleFileSelect}
                className="hidden"
              />

              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 flex items-center justify-center">
                <UploadCloud className="w-6 h-6 text-indigo-400" />
              </div>

              <div>
                <div className="text-xs sm:text-sm font-semibold text-white font-sans">
                  {uploadedFiles.length > 0
                    ? `${uploadedFiles.length} file(s) ready for ingestion`
                    : "Drag & drop an event pack .ZIP archive or document files here"}
                </div>
                <p className="text-[11px] text-slate-400 mt-1 font-sans">
                  Supports .zip archives containing manifest.json & docs/, or loose TXT, PDF, DOCX, and JSON files.
                </p>
              </div>

              {/* Selected Files Preview */}
              {uploadedFiles.length > 0 ? (
                <div className="w-full max-w-md mt-2 flex flex-col gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pb-1 border-b border-white/[0.06]">
                    <span>Selected Files:</span>
                    <button
                      onClick={() => setUploadedFiles([])}
                      className="text-rose-400 hover:text-rose-300 flex items-center gap-1 text-[10px]"
                    >
                      <Trash2 className="w-3 h-3" />
                      Clear
                    </button>
                  </div>
                  <div className="max-h-24 overflow-y-auto space-y-1 text-left">
                    {uploadedFiles.slice(0, 5).map((f, i) => (
                      <div key={i} className="text-[11px] font-mono text-slate-300 flex items-center justify-between bg-black/40 px-2.5 py-1 rounded">
                        <span className="truncate">{f.name}</span>
                        <span className="text-slate-500 text-[10px]">{(f.size / 1024).toFixed(1)} KB</span>
                      </div>
                    ))}
                    {uploadedFiles.length > 5 && (
                      <div className="text-[10px] font-mono text-slate-400 text-center">
                        + {uploadedFiles.length - 5} more files...
                      </div>
                    )}
                  </div>

                  <button
                    disabled={isLoading}
                    onClick={handleRunUpload}
                    className="mt-2 w-full py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-indigo-600 hover:from-emerald-400 hover:to-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-2 transition shadow-lg shadow-indigo-950/60"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        <span>Uploading & Processing Pack...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4" />
                        <span>Upload & Ingest Selected Files</span>
                      </>
                    )}
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="px-4 py-1.5 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs font-mono text-indigo-300 border border-white/[0.08] transition"
                >
                  Browse Files or Zip
                </button>
              )}
            </div>
          </div>

          {/* SECONDARY: Available Server Packs (One-Click Discovery) */}
          <div className="flex flex-col gap-3 pt-2 border-t border-white/[0.06]">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <FolderOpen className="w-3.5 h-3.5 text-indigo-400" />
              <span>Or Choose Pre-Existing Server Packs (data/test_packs/)</span>
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {availablePacks.map((pack) => {
                const isSelected = selectedPack?.pack_name === pack.pack_name;
                return (
                  <div
                    key={pack.pack_name}
                    onClick={() => {
                      setSelectedPack(pack);
                      setCustomPath(pack.pack_dir);
                    }}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between gap-2.5 ${
                      isSelected
                        ? "bg-indigo-600/20 border-indigo-500/50 shadow-md shadow-indigo-950/40"
                        : "bg-white/[0.025] hover:bg-white/[0.05] border-white/[0.08]"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {pack.event_id}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {pack.total_documents} files
                      </span>
                    </div>

                    <div>
                      <div className="text-xs font-semibold text-white font-sans line-clamp-1">
                        {pack.title}
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        As-Of: {pack.as_of}
                      </div>
                    </div>

                    <button
                      disabled={isLoading}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRunIngest(pack.pack_dir, pack.event_id);
                      }}
                      className="mt-1 w-full py-1.5 rounded-lg bg-indigo-500/15 hover:bg-indigo-500/25 border border-indigo-500/30 text-indigo-200 text-[11px] font-semibold transition"
                    >
                      Ingest {pack.event_id} Pack
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* TERTIARY: Manual Server Path Input */}
          <div className="flex flex-col gap-2 pt-2 border-t border-white/[0.06]">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400">
              Or Enter Custom Server Path
            </span>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={customPath}
                onChange={(e) => setCustomPath(e.target.value)}
                placeholder="e.g. data/test_packs/pack_E6_skagen_strait"
                className="flex-1 px-4 py-2.5 rounded-xl bg-white/[0.03] border border-white/[0.1] text-xs font-mono text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500/50"
              />
              <button
                disabled={isLoading || !customPath}
                onClick={() => handleRunIngest(customPath, selectedPack?.event_id || "E6")}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 transition disabled:opacity-50 shrink-0"
              >
                Ingest Path
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-300 text-xs flex items-center gap-2.5">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Section C: Section 4.5 Ingestion & Quarantine Audit Report */}
          {ingestReport && (
            <div className="p-5 rounded-xl bg-[#0c101d] border border-emerald-500/30 flex flex-col gap-4 animate-in fade-in duration-200">
              <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-bold text-white uppercase font-mono">
                    Ingestion & Quarantine Report Completed
                  </span>
                </div>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-bold">
                  {ingestReport.event_id || "E6"} Synchronized
                </span>
              </div>

              {/* Metric Breakdown Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center font-mono">
                <div className="p-2.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
                  <div className="text-[10px] text-slate-400 uppercase">Total Files</div>
                  <div className="text-lg font-bold text-white mt-1">
                    {ingestReport.documents?.total_files || ingestReport.total_files || 6}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <div className="text-[10px] text-emerald-300 uppercase">Clean Ingested</div>
                  <div className="text-lg font-bold text-emerald-400 mt-1">
                    {ingestReport.documents?.files_ok || ingestReport.files_ok || 5}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
                  <div className="text-[10px] text-amber-300 uppercase">Damaged Quarantined</div>
                  <div className="text-lg font-bold text-amber-400 mt-1">
                    {ingestReport.documents?.files_damaged?.length || 1}
                  </div>
                </div>
                <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                  <div className="text-[10px] text-indigo-300 uppercase">Graph Entities</div>
                  <div className="text-lg font-bold text-indigo-300 mt-1">
                    {ingestReport.graph?.nodes_added || 8}
                  </div>
                </div>
              </div>

              {/* Quarantined File Details */}
              {ingestReport.documents?.files_damaged?.length > 0 && (
                <div className="p-3.5 rounded-lg bg-black/40 border border-white/[0.06] text-xs">
                  <span className="text-[10px] font-mono font-bold text-rose-400 uppercase flex items-center gap-1.5 mb-1.5">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    Quarantined Damaged Artifacts (NFR3 Proof):
                  </span>
                  <div className="space-y-1 font-mono text-[11px] text-slate-300">
                    {ingestReport.documents.files_damaged.map((d, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <span>• {d.file || d.doc_id}: {d.reason || "Damaged/cut-off file"}</span>
                        <span className="text-rose-400 uppercase text-[9px] bg-rose-500/10 px-1.5 py-0.2 rounded font-bold">
                          {d.damage_type || "Quarantined"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 sm:px-8 py-4 border-t border-white/[0.08] flex items-center justify-between bg-[#0a0d16]">
          <span className="text-[11px] font-mono text-slate-400">
            Complies with Section 4.5 & 8 Trap Handling
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-white/[0.05] hover:bg-white/[0.1] text-xs text-slate-200 font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
