"use client";

import { Car, FileImage, ScanLine, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { VehicleModel } from "../types";
import { useChat } from "../hooks/useChat";
import { EmergencyAlertBanner } from "./EmergencyAlertBanner";
import { QuickPromptsBar } from "./QuickPromptsBar";
import { ChatFeed } from "./ChatFeed";
import { ChatInputBar } from "./ChatInputBar";

const VEHICLE_MODELS: VehicleModel[] = [
  "VF8",
  "VF5",
  "VF3",
  "VF6",
  "VF7",
  "VF9",
  "e34",
];

export function CustomerChatContainer() {
  const {
    messages,
    input,
    setInput,
    loading,
    selectedModel,
    setSelectedModel,
    currentCaseId,
    criticalBanner,
    sendMessage,
  } = useChat();
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | null>(null);

  // Pre-load draft from Landing Hero if available
  useState(() => {
    if (typeof window !== "undefined") {
      try {
        const savedPrompt = sessionStorage.getItem("vf_initial_prompt");
        const savedModel = sessionStorage.getItem("vf_initial_model");
        const savedImg = sessionStorage.getItem("vf_initial_image");
        const savedImgName = sessionStorage.getItem("vf_initial_image_name");

        if (savedPrompt) {
          setInput(savedPrompt);
          sessionStorage.removeItem("vf_initial_prompt");
        }
        if (savedModel) {
          const cleanModel = savedModel.replace("VinFast ", "") as VehicleModel;
          if (VEHICLE_MODELS.includes(cleanModel)) {
            setSelectedModel(cleanModel);
          }
          sessionStorage.removeItem("vf_initial_model");
        }
        if (savedImg) {
          setImagePreview(savedImg);
          setImageName(savedImgName || "anh_canh_bao.jpg");
          sessionStorage.removeItem("vf_initial_image");
          sessionStorage.removeItem("vf_initial_image_name");
        }
      } catch {}
    }
  });

  const selectImage = (file: File) => {
    setImageName(file.name);
    const reader = new FileReader();
    reader.onload = () => setImagePreview(String(reader.result));
    reader.readAsDataURL(file);
  };

  const submit = () => {
    const text = input.trim() || (imagePreview ? "Tôi gửi ảnh cảnh báo và chưa rõ vấn đề. Nhờ trợ lý nhận diện dấu hiệu sơ bộ." : "");
    if (!text) return;
    sendMessage(text);
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Critical Alert Banner (SCR-01 / SCR-03) */}
      <EmergencyAlertBanner visible={criticalBanner} />

      {/* Main Chat Box */}
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="bg-white border border-[#E2E8F0] rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden flex flex-col h-[740px]">
          {/* Header */}
          <div className="px-4 py-3 bg-[#0F1115] text-white flex items-center justify-between border-b border-[#1A1F26]">
            <div className="flex items-center space-x-2.5">
              <div className="w-8 h-8 rounded-[10px] bg-[#1E40AF] flex items-center justify-center text-[#10B981]">
                <Car className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="font-bold text-[14px] text-white">Trợ lý Kỹ thuật VinFast AI</div>
                <div className="text-[11px] text-[#64748B] flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] inline-block animate-pulse"></span>
                  <span>Agent sẵn sàng • No-PII Safe Mode</span>
                </div>
              </div>
            </div>

            {/* Model Selector */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-[#64748B] hidden sm:inline uppercase tracking-wider font-semibold">Dòng xe:</span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value as VehicleModel)}
                className="bg-white/10 text-white text-[12px] rounded-[10px] px-2 py-1 border border-white/10 focus:outline-none focus:border-[#0D9488]"
              >
                {VEHICLE_MODELS.map((model) => (
                  <option key={model} value={model} className="bg-[#0F1115] text-white">
                    {model}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick Prompts Bar */}
          <QuickPromptsBar
            onSelectPrompt={(qp) => {
              setSelectedModel(qp.model);
              sendMessage(qp.text);
            }}
          />

          {/* Messages Feed */}
          <ChatFeed
            messages={messages}
            loading={loading}
            onSelectReply={(reply) => sendMessage(reply)}
          />

          {/* Input Bar */}
          <ChatInputBar
            input={input}
            onChangeInput={setInput}
            onSend={submit}
            disabled={loading}
            vehicleModel={selectedModel}
            imagePreview={imagePreview}
            imageName={imageName}
            onSelectImage={selectImage}
            onClearImage={() => { setImagePreview(null); setImageName(null); }}
          />
        </div>

        {/* Sidebar Info - Card 16px, shadow rất nhẹ */}
        <aside className="space-y-4">
          <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[#0D9488]">
              <ScanLine className="h-3.5 w-3.5" /> Tín hiệu Case
            </div>
            <div className="mt-3 space-y-3 text-[13px]">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-[#64748B]">Trạng thái</p>
                <p className="mt-0.5 font-semibold text-[#0F172A]">
                  {currentCaseId ? "Staff Reviewing" : loading ? "AI đang phân tích..." : "Chưa tạo case"}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-medium uppercase tracking-wider text-[#64748B]">Dòng xe</p>
                <p className="mt-0.5 font-semibold text-[#0F172A]">{selectedModel}</p>
              </div>
              {currentCaseId && (
                <div className="rounded-xl bg-[#EFF3FC] border border-[#1E40AF]/20 p-2.5">
                  <p className="text-[11px] text-[#1E40AF] font-medium">Mã hồ sơ tiếp nhận</p>
                  <p className="mt-0.5 font-mono text-[12px] font-bold text-[#0F172A]">{currentCaseId}</p>
                </div>
              )}
            </div>
          </div>

          <div className="rounded-2xl border border-[#E2E8F0] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-[#0D9488]">
              <FileImage className="h-3.5 w-3.5" /> Bằng chứng hình ảnh
            </div>
            {imagePreview ? (
              <>
                <img src={imagePreview} alt="Ảnh cảnh báo" className="mt-3 h-28 w-full rounded-xl object-cover border border-[#E2E8F0]" />
                <p className="mt-2 text-[12px] leading-relaxed text-[#64748B]">
                  <strong className="text-[#0F172A]">Dấu hiệu sơ bộ:</strong> Đã chuyển cho Agent/Staff kiểm tra. Không thay thế chẩn đoán chuyên sâu tại xưởng.
                </p>
              </>
            ) : (
              <p className="mt-2 text-[12px] leading-relaxed text-[#64748B]">
                Tải ảnh chụp táp-lô hoặc trụ sạc để Agent nhận diện tín hiệu sơ bộ trước khi hỏi context.
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-[#E2E8F0] bg-[#F6F7F9] p-4 text-[12px] leading-relaxed text-[#64748B] shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <div className="flex items-center gap-2 font-semibold text-[#0F172A]">
              <ShieldCheck className="h-4 w-4 text-[#10B981]" /> Quy chuẩn an toàn No-PII
            </div>
            <p className="mt-1.5 text-[11px] text-[#64748B]">
              Nếu có nguy cơ kỹ thuật, Agent sẽ chuẩn hóa thành case và chuyển Staff Review phê duyệt. Tuyệt đối không lưu CCCD hay biển số thật.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
