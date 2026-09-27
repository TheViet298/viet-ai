"use client";

import { Car } from "lucide-react";
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
    criticalBanner,
    sendMessage,
  } = useChat();

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Critical Alert Banner (SCR-01 / SCR-03) */}
      <EmergencyAlertBanner visible={criticalBanner} />

      {/* Main Chat Box */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden flex flex-col h-[750px]">
        {/* Header */}
        <div className="px-5 py-3.5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center text-white">
              <Car className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-sm">Trợ lý Dịch vụ VinFast AI</div>
              <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-ping"></span>
                <span>Sẵn sàng tiếp nhận • No-PII Safe Mode</span>
              </div>
            </div>
          </div>

          {/* Model Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 hidden sm:inline">Dòng xe:</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value as VehicleModel)}
              className="bg-slate-800 text-white text-xs rounded-lg px-2.5 py-1.5 border border-slate-700 focus:outline-none focus:border-blue-500"
            >
              {VEHICLE_MODELS.map((model) => (
                <option key={model} value={model}>
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
          onSend={() => sendMessage()}
          disabled={loading}
          vehicleModel={selectedModel}
        />
      </div>
    </div>
  );
}
