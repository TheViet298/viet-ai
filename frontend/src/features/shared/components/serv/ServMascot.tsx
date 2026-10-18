"use client";

import { useEffect, useRef, useState, type RefObject } from "react";
import { useLocale } from "@/features/shared/context/LocaleContext";
import { ServArtwork } from "./ServArtwork";
import styles from "./ServMascot.module.css";

export type ServStatus = "idle" | "thinking" | "result" | "care" | "uploading";
type Pose = "idle" | "hello" | "happy" | "wink" | "surprise" | "listen" | "think" | "search" | "read" | "present" | "care" | "sleep" | "run" | "tap";
interface ServMascotProps {
  inputRef: RefObject<HTMLTextAreaElement | HTMLInputElement>;
  status?: ServStatus;
  responseKey?: string;
  compact?: boolean;
}

const copy: Record<Pose, [string, string]> = {
  idle: ["Chào bạn, mình là Serv!", "Hi, I'm Serv!"],
  hello: ["Serv sẵn sàng đồng hành cùng bạn.", "Serv is here to help."],
  happy: ["Bạn cứ hỏi, mình cùng tìm hiểu nhé.", "Ask away. Let's find out together."],
  wink: ["Có Serv ở đây rồi nhé.", "Serv is right here with you."],
  surprise: ["Ồ, bạn gọi Serv à?", "Oh, were you calling Serv?"],
  listen: ["Serv đang nghe…", "Serv is listening…"],
  think: ["Serv đang xem câu hỏi của bạn…", "Serv is working on your question…"],
  search: ["Serv đang chờ phản hồi…", "Serv is waiting for a response…"],
  read: ["Serv đang xem thông tin ảnh…", "Serv is checking the image…"],
  present: ["Có phản hồi rồi, bạn xem bên dưới nhé.", "A response is ready below."],
  care: ["Bạn xem lưu ý trong cuộc trò chuyện nhé.", "Please check the notice in the conversation."],
  sleep: ["Serv vẫn ở đây. Chạm để gọi mình nhé.", "Serv is here. Tap to say hello."],
  run: ["Serv đến ngay đây!", "Serv is on the way!"],
  tap: ["Mình nghe bạn gọi rồi!", "You have my attention!"],
};

export function ServMascot({ inputRef, status = "idle", responseKey, compact = false }: ServMascotProps) {
  const { language } = useLocale();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const tapRef = useRef<() => void>(() => {});
  const [pose, setPose] = useState<Pose>("idle");

  useEffect(() => {
    const root = rootRef.current, button = buttonRef.current, input = inputRef.current;
    if (!root || !button || !input) return;
    const controller = new AbortController();
    const signal = controller.signal;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    let timer: ReturnType<typeof setTimeout>, frame = 0, active = true, taps = 0, idleTurn = 0;
    let lastActivity = Date.now();
    const busy = status === "thinking" || status === "uploading";
    const locked = busy || status === "care";
    const base: Pose = status === "thinking" ? "think" : status === "uploading" ? "read" : status === "care" ? "care" : "idle";
    const gaze = (x: number, y: number) => { root.style.setProperty("--gx", `${x}px`); root.style.setProperty("--gy", `${y}px`); };
    const show = (next: Pose) => { clearTimeout(timer); setPose(next); if (next !== "listen") gaze(0, 0); };
    const lookAt = (x: number, y: number) => {
      const box = button.getBoundingClientRect(), dx = x - box.left - box.width / 2, dy = y - box.top - box.height * .55;
      gaze(Math.max(-7, Math.min(7, dx / Math.max(140, Math.abs(dy)) * 10)), Math.max(-4, Math.min(7, dy / 90)));
    };
    const mirror = document.createElement("div");
    mirror.className = styles.caretMirror;
    mirror.setAttribute("aria-hidden", "true");
    document.body.append(mirror);
    const followCaret = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        if (document.activeElement !== input || locked || !active) return;
        const rect = input.getBoundingClientRect(), style = getComputedStyle(input);
        // Matching real typography preserves wrapping, mid-word editing and Vietnamese input.
        for (const prop of ["fontFamily", "fontSize", "fontWeight", "fontStyle", "letterSpacing", "lineHeight", "textAlign", "textIndent", "tabSize", "paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "borderTopWidth", "borderRightWidth", "borderBottomWidth", "borderLeftWidth", "wordBreak", "overflowWrap", "direction"] as const) mirror.style[prop] = style[prop];
        Object.assign(mirror.style, { left: `${rect.left}px`, top: `${rect.top}px`, width: `${rect.width}px`, whiteSpace: input.tagName === "TEXTAREA" ? "pre-wrap" : "pre" });
        const caretIndex = input.selectionDirection === "backward" ? input.selectionStart ?? 0 : input.selectionEnd ?? input.value.length;
        mirror.textContent = input.value.slice(0, caretIndex);
        const marker = document.createElement("span"); marker.textContent = "\u200b"; mirror.append(marker);
        mirror.append(document.createTextNode(input.value.slice(caretIndex) || " "));
        const caret = marker.getBoundingClientRect();
        const x = Math.max(rect.left, Math.min(rect.right, caret.left - input.scrollLeft));
        const y = Math.max(rect.top, Math.min(rect.bottom, caret.top - input.scrollTop + (parseFloat(style.lineHeight) || 20) / 2));
        lookAt(x, y); root.dataset.gazeSource = "caret";
      });
    };
    const restore = () => { show(locked ? base : document.activeElement === input ? "listen" : "idle"); followCaret(); };
    const react = (next: Pose) => { if (locked) return; show(next); timer = setTimeout(restore, 1800); };
    const editing = () => { lastActivity = Date.now(); if (!locked) { show("listen"); followCaret(); } };
    const activity = () => { lastActivity = Date.now(); };
    const pointer = (e: PointerEvent) => {
      activity(); if (e.pointerType === "touch" || !active || locked || document.activeElement === input) return;
      lookAt(e.clientX, e.clientY); root.dataset.gazeSource = "pointer";
    };
    for (const event of ["focus", "input", "compositionend"] as const) input.addEventListener(event, editing, { signal });
    for (const event of ["keyup", "click", "select", "scroll"] as const) input.addEventListener(event, followCaret, { signal });
    input.addEventListener("blur", () => { if (!locked) timer = setTimeout(restore, 160); }, { signal });
    document.addEventListener("selectionchange", followCaret, { signal });
    document.addEventListener("pointermove", pointer, { signal, passive: true });
    window.addEventListener("resize", followCaret, { signal });
    window.addEventListener("scroll", followCaret, { signal, passive: true });
    button.addEventListener("pointerenter", () => { activity(); if (document.activeElement !== input) react("hello"); }, { signal });
    tapRef.current = () => { activity(); react((["hello", "wink", "surprise", "tap", "happy", "run"] as Pose[])[taps++ % 6]); };
    const pause = () => { root.dataset.paused = String(!active || document.hidden); };
    document.addEventListener("visibilitychange", pause, { signal });
    const observer = new IntersectionObserver(entries => { active = entries[0].isIntersecting; pause(); if (active) followCaret(); });
    observer.observe(root);
    const idle = setInterval(() => {
      if (reduced.matches || !active || document.hidden || locked || document.activeElement === input) return;
      if (Date.now() - lastActivity > 30000) show("sleep");
      else if (Date.now() - lastActivity > 5500) react((["happy", "wink", "hello"] as Pose[])[idleTurn++ % 3]);
    }, 7000);
    if (status === "result") { show("present"); timer = setTimeout(restore, 3200); }
    else restore();
    // Only a real pending request may show a waiting prop; no simulated completion.
    const waiting = status === "thinking" ? setTimeout(() => show("search"), 2200) : undefined;
    return () => { controller.abort(); clearTimeout(timer); clearTimeout(waiting); clearInterval(idle); cancelAnimationFrame(frame); observer.disconnect(); mirror.remove(); tapRef.current = () => {}; };
  }, [inputRef, status, responseKey]);

  const message = copy[pose][language === "en" ? 1 : 0];
  return (
    <div ref={rootRef} className={`${styles.root} ${compact ? styles.compact : styles.hero}`} data-serv data-state={pose}>
      {!compact && <span className={styles.sparks} aria-hidden="true"><svg viewBox="0 0 220 220"><path d="m24 27 3 7 7 3-7 3-3 7-3-7-7-3 7-3Z"/><path d="m194 66 4 9 9 4-9 4-4 9-4-9-9-4 9-4Z"/><path d="m166 181 2 5 5 2-5 2-2 5-2-5-5-2 5-2Z"/></svg></span>}
      {!compact && <p className={styles.speech} data-serv-speech>{message}</p>}
      <button ref={buttonRef} type="button" className={styles.character} onClick={() => tapRef.current()} aria-label={language === "en" ? "Say hello to Serv" : "Chào Serv"} title={compact ? undefined : message}>
        <ServArtwork />
      </button>
      {compact && <span className={styles.srOnly}>Serv</span>}
    </div>
  );
}
