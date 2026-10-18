"use client";

import { useRef, useState, type KeyboardEvent } from "react";
import Link from "next/link";
import NextImage from "next/image";
import {
  ArrowDown, ArrowRight, ArrowUpRight, BookOpen,
  Check, CheckCheck, ChevronDown, ChevronLeft, ChevronRight, CircleHelp,
  ClipboardCheck, FileText, Image, Menu, MessageCircle,
  ShieldCheck,
} from "lucide-react";
import { useLocale } from "@/features/shared/context/LocaleContext";
import { ServArtwork } from "@/features/shared/components/serv/ServArtwork";
import { ProductMark } from "@/features/shared/components/ProductMark";
import { LanguageSwitch } from "@/features/shared/components/LanguageSwitch";
import { ThemeToggle } from "@/features/shared/components/ThemeToggle";
import { ProjectProblemSection, ProjectSolutionSection, ProjectActionSection, ProjectJourneyDetails, ProjectProofSection, ProjectDevelopmentSection } from "./ProjectStorySections";
import s from "./ServiceFlowPage.module.css";

function ServMark() {
  return <span className={s.servMark} aria-hidden="true"><ServArtwork /></span>;
}

export function ServiceFlowPage() {
  const { language } = useLocale();
  const text = (vi: string, en: string) => language === "en" ? en : vi;
  const [step, setStep] = useState(0);
  const [isCharging, setIsCharging] = useState(false);
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);

  const steps = [
    { title: text("Tiếp nhận", "Receive"), icon: MessageCircle,
      description: text("Bắt đầu từ câu chuyện của bạn.", "Start with your own words."),
      explanation: text("Mô tả điều bạn đang gặp bằng ngôn ngữ tự nhiên. Có ảnh cảnh báo? Bạn có thể gửi kèm trong cuộc trò chuyện.", "Describe what happened in your own words. You can also attach a warning photo in the conversation."),
      user: text("Xe của tôi cắm sạc nhưng trụ báo đèn đỏ, không vào điện.", "My car is plugged in, but the charger shows a red light and charging will not start."),
      reply: text("Mình sẽ ghi nhận tình trạng sạc. Bạn đang sử dụng dòng xe nào và pin hiện còn bao nhiêu phần trăm?", "Let’s capture the charging issue. Which model do you drive, and what is the current battery level?"),
      status: text("Đang thu thập thông tin", "Gathering information") },
    { title: text("Làm rõ", "Clarify"), icon: CircleHelp,
      description: text("Hỏi đúng điều còn thiếu.", "Ask for the missing context."),
      explanation: text("Dữ kiện về dòng xe, mức pin và mã lỗi giúp yêu cầu có ngữ cảnh. Trợ lý làm rõ tối đa hai lượt trước khi bàn giao.", "Vehicle model, battery level, and error codes give the request context. The assistant clarifies for up to two turns before handover."),
      user: text("Tôi đi VF 8, pin còn 28%. Màn hình trụ hiện mã CC01.", "I drive a VF 8. The battery is at 28%, and the charger displays CC01."),
      reply: text("Mình đã ghi nhận VF 8, pin 28% và mã CC01. Bạn cho biết vị trí trạm sạc để nhân viên có thêm thông tin tiếp nhận nhé.", "I have noted VF 8, 28% battery, and CC01. Please share the charging station location so the service team has the context."),
      status: text("Đã bổ sung dữ kiện xe", "Vehicle context added") },
    { title: text("Tra cứu", "Look up"), icon: BookOpen,
      description: text("Thông tin đi cùng nguồn tham khảo.", "Information with a traceable source."),
      explanation: text("Trợ lý tra cứu tài liệu liên quan và đính kèm nguồn để bạn kiểm tra. Dấu hiệu từ ảnh hỗ trợ làm rõ, không thay thế chẩn đoán kỹ thuật.", "The assistant retrieves relevant documents and links the sources. Image signals help clarify context and do not replace a technical diagnosis."),
      user: text("Tôi muốn tìm hiểu thông tin về sạc và pin trước khi được hỗ trợ.", "I would like to read about charging and battery services while waiting for support."),
      reply: text("Bạn có thể tham khảo tài liệu dịch vụ pin và sạc của VinFast. Mình sẽ giữ mã lỗi và thông tin xe trong hồ sơ để nhân viên rà soát.", "You can review VinFast’s battery and charging service information. The error code and vehicle details remain in the case for staff review."),
      status: text("Có nguồn tham khảo", "Reference available") },
    { title: text("Bàn giao", "Hand over"), icon: ClipboardCheck,
      description: text("Một hồ sơ rõ ràng. Một người tiếp nối.", "A clear case. A human next step."),
      explanation: text("Nội dung được tổng hợp thành hồ sơ để nhân viên rà soát, yêu cầu bổ sung hoặc điều phối. Bạn theo dõi tiến độ tại Trung tâm hỗ trợ.", "The conversation becomes a case for staff to review, request more details, or route. You can track progress in the support center."),
      user: text("Nhờ chuyển thông tin để nhân viên dịch vụ hỗ trợ tôi.", "Please pass these details to the service team."),
      reply: text("Đây là bản tóm tắt thông tin đã ghi nhận. Nhân viên sẽ rà soát và quyết định bước xử lý tiếp theo; trợ lý không tự điều phối cứu hộ.", "Here is the summary of the information collected. Staff review and decide the next action; the assistant does not dispatch roadside assistance."),
      status: text("Chờ nhân viên rà soát", "Awaiting staff review") },
  ];
  const active = steps[step];
  const pageLinks = [
    { href: "#flow-problem", label: text("Bài toán", "Problem") },
    { href: "#flow-solution", label: text("Giải pháp", "Solution") },
    { href: "#flow-demo", label: text("Hành trình", "Journey") },
    { href: "#flow-proof", label: text("Kiểm chứng", "Validation") },
    { href: "#flow-project", label: text("Về dự án", "The project") },
  ];

  function navigateTabs(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let next = index;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = (index + 1) % steps.length;
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = (index + steps.length - 1) % steps.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = steps.length - 1;
    else return;
    event.preventDefault();
    setStep(next);
    tabsRef.current[next]?.focus();
  }

  return (
    <div className={s.page} data-project-overview>
      <a href="#project-overview-content" className={s.skipLink}>{text("Đến nội dung chính", "Skip to content")}</a>
      <header className={s.projectHeader}>
        <div className={s.container}>
          <a href="#project-overview-content" className={s.headerBrand} aria-label={text("VFServ — Giới thiệu dự án", "VFServ — Project introduction")}><span className={s.headerBrandIcon}><ProductMark /></span><span className={s.headerBrandCopy}><strong>VFServ</strong><small>VINFAST EV HUB</small></span></a>
          <nav className={s.projectNav} aria-label={text("Nội dung giới thiệu dự án", "Project introduction sections")}>{pageLinks.map(link => <a href={link.href} key={link.href}>{link.label}</a>)}</nav>
          <div className={s.headerActions}>
            <div className={s.headerPreferences}><LanguageSwitch /><ThemeToggle /></div>
            <Link href="/" className={s.headerCta}>{text("Khám phá sản phẩm", "Explore the product")}<ArrowUpRight size={16} aria-hidden="true" /></Link>
            <details className={s.mobileMenu}><summary aria-label={text("Mở menu giới thiệu", "Open introduction menu")}><Menu size={22} aria-hidden="true" /></summary><nav aria-label={text("Menu giới thiệu trên điện thoại", "Mobile introduction menu")}>{pageLinks.map(link => <a href={link.href} key={link.href} onClick={event => event.currentTarget.closest("details")?.removeAttribute("open")}>{link.label}</a>)}</nav></details>
          </div>
        </div>
      </header>
      <section className={s.hero} id="project-overview-content" aria-labelledby="flow-title">
        <div className={s.container}>
          <div className={s.heroGrid}>
            <div className={s.heroCopy}>
              <h1 id="flow-title">{text("Hiểu đúng vấn đề.", "Understand the issue.")}<br /><span>{text("An tâm mỗi", "Confidence for")}<br className={s.desktopBreak} /> {text("hành trình.", "every journey.")}</span></h1>
              <p className={s.heroDescription}>{text("Gặp Serv, trợ lý AI của VFServ. Từ câu hỏi về xe, ảnh cảnh báo đến hồ sơ dịch vụ, Serv giúp bạn cung cấp đúng thông tin để nhân viên tiếp nối mà không mất ngữ cảnh.", "Meet Serv, VFServ’s AI assistant. From vehicle questions and warning photos to a service brief, Serv helps you share the right information so staff can pick up with the context intact.")}</p>
              <div className={s.heroActions}><Link href="/" className={s.primaryCta}>{text("Khám phá sản phẩm", "Explore the product")}<ArrowUpRight size={20} aria-hidden="true" /></Link><a href="#flow-demo">{text("Xem hành trình minh họa", "See the illustrative journey")}<ArrowDown size={16} aria-hidden="true" /></a></div>
              <div className={s.heroPrinciples}><span><Check size={14} aria-hidden="true" />{text("Hiểu ngữ cảnh", "Context-aware")}</span><span><Check size={14} aria-hidden="true" />{text("Tra cứu có nguồn", "Source-linked")}</span><span><Check size={14} aria-hidden="true" />{text("Con người phê duyệt", "Human approval")}</span></div>
            </div>
            <div className={s.heroArtwork}>
              <button type="button" className={s.heroToggle} aria-label={text("Đổi trạng thái cắm sạc của hình minh họa", "Toggle the illustration’s charging connection")} aria-pressed={isCharging} onClick={() => setIsCharging(value => !value)}>
                <NextImage className={s.idleImage} src="/images/project/serviceflow-hero-vf6-charger-clean.png" alt={text("Minh họa xe VinFast VF 6 chưa cắm sạc bên trụ sạc VinFast", "Illustration of a VinFast VF 6 unplugged beside a VinFast charging station")} aria-hidden={isCharging} width={1254} height={1254} priority sizes="(max-width: 800px) 95vw, 55vw" />
                <NextImage className={s.chargingImage} src="/images/project/serviceflow-hero-vf6-charging-clean.png" alt={text("Minh họa xe VinFast VF 6 đang cắm sạc từ trụ sạc VinFast", "Illustration of a VinFast VF 6 plugged into a VinFast charging station")} aria-hidden={!isCharging} width={1254} height={1254} priority sizes="(max-width: 800px) 95vw, 55vw" />
              </button>
            </div>
          </div>
        </div>
      </section>

      <div className={s.capabilityStrip}><div className={s.container}>
        {[{ icon: MessageCircle, label: text("Tiếp nhận bằng hội thoại", "Conversational intake") }, { icon: Image, label: text("Hỗ trợ gửi hình ảnh", "Photo attachments") }, { icon: BookOpen, label: text("Tra cứu có nguồn", "Source-linked answers") }, { icon: ClipboardCheck, label: text("Bàn giao có ngữ cảnh", "Context-rich handover") }].map(item => <span key={item.label}><item.icon size={19} aria-hidden="true" />{item.label}</span>)}
      </div></div>

      <ProjectProblemSection />
      <ProjectSolutionSection />
      <ProjectActionSection />

      <section id="flow-demo" className={`${s.section} ${s.demo}`} aria-labelledby="demo-title">
        <div className={s.container}>
          <div className={s.centerHeading}><p className={s.journeyLabel}>{text("03 / HỘI THOẠI & HÀNH TRÌNH", "03 / CONVERSATION & JOURNEY")}</p><h2 id="demo-title">{text("Từ “xe tôi bị sao?”", "From “what’s wrong?”")}<br /><span>{text("đến một bước tiếp theo rõ ràng.", "to a clear next step.")}</span></h2><p>{text("Cùng đi qua một tình huống sạc không vào điện. Chọn từng bước để thấy thông tin được tiếp nối như thế nào.", "Walk through a charging issue. Select a step to see how each piece of information stays connected.")}</p></div>
          <div className={s.workspace}>
            <div className={s.workspaceBar}><div><ServMark /><strong>Serv</strong><span>{text("Trợ lý AI của VFServ", "VFServ’s AI assistant")}</span></div><span className={s.demoLabel}>{text("Tình huống minh họa", "Illustrative scenario")}</span></div>
            <div className={s.workspaceBody}>
              <div className={s.demoSidebar}>
                <p>{text("Hành trình hỗ trợ", "Support journey")}</p>
                <div role="tablist" aria-label={text("Quy trình hỗ trợ minh họa", "Illustrative support journey")} aria-orientation="vertical" className={s.demoTabs}>
                  {steps.map((item, index) => <button key={item.title} type="button" role="tab" id={`flow-tab-${index}`} aria-controls="flow-panel" aria-selected={step === index} tabIndex={step === index ? 0 : -1} ref={el => { tabsRef.current[index] = el; }} onClick={() => setStep(index)} onKeyDown={event => navigateTabs(event, index)}><span>{String(index + 1).padStart(2, "0")}</span><item.icon size={17} aria-hidden="true" />{item.title}{step > index && <Check className={s.stepCheck} size={14} aria-hidden="true" />}</button>)}
                </div>
                <div className={s.sidebarNote}><ShieldCheck size={20} aria-hidden="true" /><p>{text("Thông tin được giữ xuyên suốt cuộc trò chuyện.", "Context stays with the conversation.")}</p></div>
              </div>
              <div role="tabpanel" id="flow-panel" aria-labelledby={`flow-tab-${step}`} tabIndex={0} className={s.demoPanel}>
                <div className={s.conversation}>
                  <div className={s.conversationTitle}><span><MessageCircle size={17} aria-hidden="true" />{text("Cuộc trò chuyện", "Conversation")}</span><span>{step + 1} / 4</span></div>
                  <div className={s.userMessage}><p>{active.user}</p><span>{text("Chủ xe", "Vehicle owner")}<CheckCheck size={14} aria-hidden="true" /></span></div>
                  <div className={s.assistantMessage}><div className={s.assistantAvatar}><ServMark /></div><div><strong>Serv</strong><p>{active.reply}</p>{step === 2 && <a className={s.sourceLink} href="https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien" target="_blank" rel="noopener noreferrer"><BookOpen size={14} aria-hidden="true" />{text("Dịch vụ pin VinFast", "VinFast battery services")}<ArrowUpRight size={13} aria-hidden="true" /></a>}</div></div>
                  <div className={s.conversationStatus}><Check size={14} aria-hidden="true" />{active.status}</div>
                </div>
                <aside className={s.caseBrief} aria-label={text("Hồ sơ minh họa", "Illustrative case brief")}>
                  <h3><FileText size={17} aria-hidden="true" />{text("Hồ sơ tiếp nhận", "Intake brief")}</h3><span className={s.briefTag}>{text("Sạc & Pin", "Charging & battery")}</span>
                  <dl><div><dt>{text("Tình trạng", "Issue")}</dt><dd>{text("Sạc không vào điện", "Charging will not start")}</dd></div><div><dt>{text("Dòng xe", "Vehicle")}</dt><dd>{step > 0 ? "VF 8" : text("Chờ bổ sung", "Not yet provided")}</dd></div><div><dt>{text("Mức pin / Mã lỗi", "Battery / Error")}</dt><dd>{step > 0 ? "28% / CC01" : text("Chờ bổ sung", "Not yet provided")}</dd></div></dl>
                  <div className={s.briefStatus}><ClipboardCheck size={16} aria-hidden="true" />{active.status}</div>
                  <p className={s.caseDisclaimer}>{text("Dữ liệu minh họa, không phải hồ sơ thực tế.", "Illustrative data, not a real service case.")}</p>
                </aside>
              </div>
            </div>
            <div className={s.workspaceBottom}><div><strong>{active.description}</strong><p>{active.explanation}</p></div><div className={s.demoControls}><button type="button" disabled={step === 0} onClick={() => setStep(step - 1)} aria-label={text("Bước trước", "Previous step")}><ChevronLeft size={20} /></button><button type="button" disabled={step === 3} onClick={() => setStep(step + 1)} aria-label={text("Bước tiếp theo", "Next step")}><ChevronRight size={20} /></button></div></div>
          </div>
          <p className={s.demoFootnote}>{text("Đây là minh họa cách dự án hoạt động.", "This is an illustration of how the project works.")} <Link href="/">{text("Khám phá sản phẩm thực tế", "Explore the actual product")}<ArrowUpRight size={13} aria-hidden="true" /></Link></p>
          <ProjectJourneyDetails />

      </div>
      </section>



      <ProjectProofSection />
      <ProjectDevelopmentSection />

      <section id="flow-project" className={`${s.section} ${s.project}`} aria-labelledby="project-title"><div className={`${s.container} ${s.projectGrid}`}>
        <div><h2 id="project-title">{text("VFServ.", "VFServ.")}<br /><span>{text("Dự án của team chúng tôi.", "A project by our team.")}</span></h2><p className={s.sectionDescription}>{text("Team VFO2O-18 phát triển VinFast ServiceFlow AI với mục tiêu giúp việc tiếp nhận và bàn giao yêu cầu dịch vụ rõ ràng, có ngữ cảnh và có người kiểm soát.", "Team VFO2O-18 is developing VinFast ServiceFlow AI to make service intake and handover clear, contextual, and human-supervised.")}</p><strong className={s.teamName}>Team VFO2O-18</strong></div>
        <div className={s.projectStack}><h3>{text("Ba lớp, một luồng thông tin.", "Three layers, one information flow.")}</h3><ol><li><span>01</span><div><strong>Web Support Hub</strong><p>{text("Giao diện cho chủ xe và bàn làm việc cho nhân viên.", "An owner interface and a service staff workspace.")}</p><small>Next.js · React · TypeScript</small></div></li><li><span>02</span><div><strong>{text("Lớp tiếp nhận & lưu trữ", "Intake & storage layer")}</strong><p>{text("Kết nối hội thoại, tài khoản và hồ sơ dịch vụ.", "Connects conversations, accounts, and service cases.")}</p><small>FastAPI · API · Session</small></div></li><li><span>03</span><div><strong>{text("Luồng xử lý AI có kiểm soát", "Human-supervised AI workflow")}</strong><p>{text("Phân loại, làm rõ, tra cứu và tổng hợp hồ sơ.", "Triage, clarification, retrieval, and case preparation.")}</p><small>LangGraph · RAG · Human-in-the-loop</small></div></li></ol></div>
      </div></section>



      <section id="flow-faq" className={`${s.section} ${s.faq}`} aria-labelledby="faq-title"><div className={`${s.container} ${s.faqGrid}`}><div><h2 id="faq-title">{text("Hiểu thêm", "More about")}<br /><span>{text("về dự án.", "the project.")}</span></h2><p className={s.sectionDescription}>{text("Mục tiêu, phạm vi và cách trải nghiệm VFServ.", "The goals, scope, and how to explore VFServ.")}</p></div><div className={s.faqItems}>{[
        { q: text("Dự án VFServ giải quyết bài toán gì?", "What problem does VFServ address?"), a: text("Dự án tập trung vào việc tiếp nhận thông tin từ chủ xe, làm rõ dữ kiện còn thiếu và chuẩn hóa hồ sơ để nhân viên dịch vụ tiếp nối. Mục tiêu là giảm việc hỏi lại và tránh mất ngữ cảnh khi bàn giao.", "The project focuses on collecting owner information, clarifying missing facts, and preparing a structured case for service staff. It aims to reduce repeated questions and preserve context during handover.") },
        { q: text("AI có tự quyết định xử lý sự cố không?", "Does AI decide how to resolve an issue?"), a: text("AI hỗ trợ phân loại, tra cứu và tổng hợp. Nhân viên rà soát hồ sơ và quyết định bước xử lý; chẩn đoán kỹ thuật và điều phối cứu hộ nằm ngoài quyền tự quyết của trợ lý.", "AI supports triage, retrieval, and summarization. Staff review cases and decide the next action; technical diagnosis and roadside dispatch are outside the assistant’s authority.") },
        { q: text("Phạm vi hiện tại của dự án gồm những gì?", "What is the current project scope?"), a: text("Web Support Hub gồm giao diện khách hàng, hội thoại văn bản và hình ảnh, tra cứu tài liệu, theo dõi yêu cầu và bàn rà soát cho nhân viên. Các kênh như Zalo OA và Voice AI thuộc định hướng mở rộng.", "The Web Support Hub includes owner interfaces, text and image conversations, reference retrieval, case tracking, and a staff review workspace. Channels such as Zalo OA and Voice AI are future directions.") },
        { q: text("Làm thế nào để trải nghiệm sản phẩm?", "How can I explore the product?"), a: text("Bấm “Khám phá sản phẩm” để chuyển sang giao diện chính của VFServ. Trang bạn đang xem chỉ giới thiệu dự án và minh họa cách hệ thống hoạt động.", "Select “Explore the product” to open the main VFServ application. This page introduces the project and illustrates how the system works.") },
      ].map(item => <details key={item.q}><summary>{item.q}<ChevronDown size={20} aria-hidden="true" /></summary><p>{item.a}</p></details>)}</div></div></section>

      <section className={s.cta} aria-labelledby="cta-title"><div className={s.container}><div className={s.ctaMark}><ProductMark /></div><h2 id="cta-title">{text("Từ ý tưởng của team.", "From our team’s idea.")}<br />{text("Đến trải nghiệm của bạn.", "To your experience.")}</h2><p>{text("Khám phá giao diện và các luồng hỗ trợ mà team đang xây dựng với VFServ.", "Explore the interface and support journeys our team is building with VFServ.")}</p><div className={s.ctaActions}><Link href="/">{text("Khám phá sản phẩm", "Explore the product")}<ArrowUpRight size={20} aria-hidden="true" /></Link><a href="#flow-project">{text("Tìm hiểu về dự án", "About the project")}<ArrowRight size={18} aria-hidden="true" /></a></div></div></section>
      <footer className={s.projectFooter}><div className={s.container}><div><a href="#project-overview-content" className={s.projectBrand}><span><ProductMark /></span><strong>VFServ</strong></a><p>VinFast ServiceFlow AI · Team VFO2O-18</p></div><div className={s.footerPreferences}><LanguageSwitch /><ThemeToggle /></div><Link href="/">{text("Khám phá sản phẩm", "Explore the product")}<ArrowUpRight size={15} aria-hidden="true" /></Link></div></footer>
    </div>
  );
}
