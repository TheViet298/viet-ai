"use client";

import { useState } from "react";
import { ArrowRight, BatteryCharging, BookOpen, CarFront, Check, ChevronDown, ClipboardCheck, FileText, Headphones, Image, Layers3, MessageCircle, ShieldCheck, X } from "lucide-react";
import { useLocale } from "@/features/shared/context/LocaleContext";
import { ServArtwork } from "@/features/shared/components/serv/ServArtwork";
import s from "./ProjectStorySections.module.css";

function useCopy() {
  const { language } = useLocale();
  return (vi: string, en: string) => language === "en" ? en : vi;
}

function ServHead() {
  return <span className={s.servHead} aria-hidden="true"><ServArtwork /></span>;
}

export function ProjectProblemSection() {
  const t = useCopy();
  const actors = [
    { icon: CarFront, role: t("CHỦ XE", "VEHICLE OWNER"), title: t("Cần được hiểu đúng", "Needs to be understood"), lead: t("Đang lo về xe", "Concerned about the vehicle"), sub: t("nhưng chưa biết cần cung cấp những gì", "but unsure which details to share"), items: [t("Dòng xe, mức pin và mã lỗi dễ bị bỏ sót khi báo sự cố.", "Vehicle model, battery level, and error codes are easy to omit."), t("Ảnh cảnh báo chưa đi cùng mô tả đầy đủ.", "Warning photos may lack the context needed to interpret them."), t("Phải kể lại tình trạng khi chuyển người tiếp nhận.", "The story has to be repeated when another person takes over.")] },
    { icon: BookOpen, role: t("THÔNG TIN", "INFORMATION"), title: t("Nằm ở nhiều nơi", "Scattered across sources"), lead: t("Khó đối chiếu", "Hard to verify"), sub: t("khi câu hỏi, tài liệu và hồ sơ rời nhau", "when questions, documents, and cases are disconnected"), items: [t("Cẩm nang, chính sách và lịch sử trao đổi chưa cùng một mạch.", "Manuals, policies, and conversation history are separate."), t("Chưa rõ câu trả lời áp dụng cho dòng xe hoặc tình huống nào.", "It is unclear which model or situation an answer applies to."), t("Thiếu nguồn khiến chủ xe khó tự kiểm tra thông tin.", "Without sources, owners cannot easily check an answer.")] },
    { icon: Headphones, role: t("NHÂN VIÊN DỊCH VỤ", "SERVICE STAFF"), title: t("Cần đủ ngữ cảnh", "Needs the full context"), lead: t("Phải hỏi lại", "Needs to ask again"), sub: t("trước khi có thể tiếp nhận và rà soát", "before intake and review can begin"), items: [t("Dữ kiện quan trọng lẫn trong nhiều lượt hội thoại.", "Important facts are buried in conversation turns."), t("Khó nhìn nhanh điều đã biết và phần còn thiếu.", "Known facts and missing details are difficult to scan."), t("Bàn giao thiếu tóm tắt làm gián đoạn bước tiếp theo.", "A handover without a summary interrupts the next step.")] },
  ];
  return <section id="flow-problem" className={`${s.section} ${s.problem}`} aria-labelledby="problem-title"><div className={s.container}>
    <p className={s.sectionLabel}>{t("01 / BÀI TOÁN", "01 / THE PROBLEM")}</p>
    <div className={s.splitHeading}><h2 id="problem-title">{t("Một yêu cầu dịch vụ.", "One service request.")}<br />{t("Ba mắt xích cần", "Three parts need")} <em>{t("cùng một ngữ cảnh.", "the same context.")}</em></h2><p>{t("Chủ xe cần được hướng dẫn. Nhân viên cần đủ dữ kiện. Tài liệu cần được dùng đúng chỗ. Khi thông tin đứt đoạn, việc tiếp nhận phải bắt đầu lại.", "Owners need guidance. Staff need facts. References need to be used in context. When information breaks apart, intake has to start over.")}</p></div>
    <div className={s.problemChain}>{actors.map((actor, i) => <article className={s.actorCard} key={actor.role}>
      <div className={s.actorTop}><span className={s.iconTile}><actor.icon size={23} aria-hidden="true" /></span><span>{actor.role}</span></div><h3>{actor.title}</h3><div className={s.actorLead}><strong>{actor.lead}</strong><p>{actor.sub}</p></div><ul>{actor.items.map(item => <li key={item}><X size={14} aria-hidden="true" />{item}</li>)}</ul><span className={s.chainArrow} aria-hidden="true"><ArrowRight size={21} /></span>
    </article>)}<aside className={s.chainResult}><span><ClipboardCheck size={29} aria-hidden="true" /></span><h3>{t("Tiếp nhận", "Service intake")}</h3><p>{t("Một hồ sơ cần đủ rõ để người tiếp theo bắt tay vào việc.", "A brief needs to be clear enough for the next person to act.")}</p></aside></div>
    <div className={s.problemRoots}>{[
      [t("Thiếu một hồ sơ xuyên suốt", "No continuous brief"), t("Mỗi nơi giữ một phần thông tin, khó theo dõi toàn bộ yêu cầu.", "Each place holds a fragment of the request.")],
      [t("Thiếu cách làm rõ nhất quán", "Inconsistent clarification"), t("Dễ hỏi lặp nhưng vẫn bỏ sót dữ kiện cần cho nhân viên.", "Repeated questions can still miss the facts staff need.")],
      [t("Thiếu điểm bàn giao rõ ràng", "An unclear handover"), t("Chủ xe cần biết ai đang tiếp nhận và bước tiếp theo là gì.", "Owners need to know who is reviewing the request and what comes next.")],
    ].map(([title, detail]) => <div key={title}><h4>{title}</h4><p>{detail}</p></div>)}</div>
  </div></section>;
}

export function ProjectSolutionSection() {
  const t = useCopy();
  const roles = [
    { icon: CarFront, label: t("DÀNH CHO CHỦ XE", "FOR VEHICLE OWNERS"), title: t("Một nơi bắt đầu yêu cầu", "One place to start"), intro: t("Kể điều đang gặp, gửi thêm ảnh và tiếp tục theo dõi trong Web Support Hub.", "Describe the issue, attach a photo, and keep following the request in the Web Support Hub."), items: [t("Hỏi về pin, sạc, sử dụng xe và dịch vụ", "Ask about batteries, charging, vehicle use, and service"), t("Gửi ảnh táp-lô hoặc màn hình trụ sạc", "Attach a dashboard or charger-screen photo"), t("Bổ sung dữ kiện qua câu hỏi làm rõ", "Add missing facts through clarification"), t("Theo dõi hồ sơ và phản hồi kết quả hỗ trợ", "Track the case and respond to the outcome")], foot: t("Dễ trình bày · Biết bước tiếp theo", "Share clearly · Know the next step") },
    { icon: Headphones, label: t("DÀNH CHO NHÂN VIÊN", "FOR SERVICE STAFF"), title: t("Tiếp nối bằng hồ sơ rõ ràng", "Pick up with a clear brief"), intro: t("Hội thoại được tổng hợp để nhân viên rà soát và quyết định hướng xử lý.", "The conversation becomes a brief for staff to review and decide on the next action."), items: [t("Xem tóm tắt hiện tượng, thông tin xe và ảnh", "Review symptoms, vehicle details, and photos"), t("Nhận biết mức ưu tiên và dữ kiện còn thiếu", "Identify priority and missing facts"), t("Rà soát, chỉnh hồ sơ hoặc yêu cầu bổ sung", "Review, edit, or request more information"), t("Cập nhật trạng thái và kết quả cho chủ xe", "Update the owner on progress and outcome")], foot: t("AI chuẩn bị · Nhân viên quyết định", "AI prepares · Staff decide") },
    { icon: ShieldCheck, label: t("TRI THỨC & AN TOÀN", "KNOWLEDGE & SAFETY"), title: t("Thông tin có thể kiểm tra", "Information you can check"), intro: t("Tra cứu dựa trên tài liệu và đặt giới hạn rõ ràng cho vai trò của AI.", "Retrieve reference material and set explicit limits on AI’s role."), items: [t("Đính kèm nguồn cho câu trả lời tra cứu", "Include references with retrieved answers"), t("Ưu tiên cảnh báo khi có dấu hiệu nguy hiểm", "Prioritize warnings when risk signals appear"), t("Hỏi lại khi ảnh hoặc dữ kiện chưa đủ rõ", "Ask again when photos or facts are unclear"), t("Chuyển nhân viên với nội dung cần rà soát", "Hand over content that needs staff review")], foot: t("Có nguồn · Có giới hạn · Có người rà soát", "Sourced · Bounded · Human-reviewed") },
  ];
  return <section id="flow-solution" className={`${s.section} ${s.solution}`} aria-labelledby="solution-title"><div className={s.container}>
    <div className={s.centerHeading}><p className={s.sectionLabel}>{t("02 / GIẢI PHÁP", "02 / THE SOLUTION")}</p><h2 id="solution-title">VinFast ServiceFlow AI.<br /><em>{t("Một cầu nối cho cả quy trình.", "One connection across the journey.")}</em></h2><p>{t("VFServ kết nối chủ xe, tài liệu và nhân viên dịch vụ — từ lời mô tả đầu tiên đến một hồ sơ có người tiếp nhận.", "VFServ connects owners, reference material, and service staff — from the first description to a brief with a human reviewer.")}</p></div>
    <div className={s.solutionHub}><ServHead /><strong>VFServ</strong><span>Web Support Hub</span><small>{t("Tiếp nhận · Làm rõ · Tra cứu · Bàn giao", "Intake · Clarify · Retrieve · Hand over")}</small></div>
    <div className={s.branchLines} aria-hidden="true"><svg viewBox="0 0 1000 75" preserveAspectRatio="none"><path d="M500 0V25M165 75V50Q165 25 190 25H810Q835 25 835 50V75M500 25V75" /></svg></div>
    <div className={s.solutionCards}>{roles.map(role => <article className={s.roleCard} key={role.label}><div className={s.roleTitle}><span className={s.iconTile}><role.icon size={24} aria-hidden="true" /></span><div><p>{role.label}</p><h3>{role.title}</h3></div></div><p className={s.roleIntro}>{role.intro}</p><ul>{role.items.map(item => <li key={item}><Check size={17} aria-hidden="true" />{item}</li>)}</ul><div className={s.roleFoot}>{role.foot}</div></article>)}</div>
    <div className={s.workflowBlock}><div className={s.workflowIntro}><Layers3 size={28} aria-hidden="true" /><h3>{t("Một luồng Agent.", "One agent workflow.")}<br />{t("Bảy nhóm nghiệp vụ kết nối.", "Seven connected capabilities.")}</h3><p>{t("Các nhánh được sử dụng theo ngữ cảnh của từng yêu cầu.", "Each request follows the branches its context requires.")}</p></div><ol className={s.workflowList}>{[
      t("Tiếp nhận văn bản và hình ảnh", "Text and image intake"), t("Kiểm tra dấu hiệu an toàn", "Safety-signal checks"), t("Phân loại nhu cầu hỗ trợ", "Support-intent triage"), t("Làm rõ dữ kiện còn thiếu", "Missing-fact clarification"), t("Tra cứu tài liệu có nguồn", "Source-linked retrieval"), t("Tổng hợp hồ sơ tiếp nhận", "Structured case preparation"), t("Bàn giao để nhân viên rà soát", "Handover for staff review"),
    ].map((item, i) => <li key={item}><span>{String(i + 1).padStart(2, "0")}</span>{item}</li>)}</ol></div>
    <div className={s.principles}>{[t("Văn bản & hình ảnh", "Text & images"), t("Ngữ cảnh hội thoại", "Conversation context"), t("Tra cứu có nguồn", "Source-linked retrieval"), t("Hồ sơ dịch vụ", "Service briefs"), "Human-in-the-loop"].map(item => <span key={item}>{item}</span>)}</div>
  </div></section>;
}

export function ProjectActionSection() {
  const t = useCopy();
  const [scenario, setScenario] = useState(0);
  const examples = [
    { label: t("Sạc & pin", "Charging"), icon: BatteryCharging, input: t("“VF 8 của tôi không nhận sạc. Pin còn 28%, trụ hiện CC01.”", "“My VF 8 will not charge. Battery is 28%, the charger shows CC01.”"), tags: ["VF 8", "28%", "CC01"], output: t("Hồ sơ sự cố sạc", "Charging-issue brief"), detail: t("Dữ kiện xe và hiện tượng được tổng hợp để nhân viên rà soát.", "Vehicle details and symptoms are summarized for staff review."), action: t("Chuẩn bị bàn giao", "Prepare handover") },
    { label: t("Ảnh cảnh báo", "Warning photo"), icon: Image, input: t("“Táp-lô hiện biểu tượng lạ. Tôi gửi ảnh để bạn xem thêm.”", "“There is an unfamiliar warning on the dashboard. Here is a photo.”"), tags: [t("Ảnh táp-lô", "Dashboard photo"), t("Cần ngữ cảnh", "Context needed")], output: t("Dấu hiệu cần làm rõ", "Evidence to clarify"), detail: t("Ảnh bổ sung dấu hiệu; dữ kiện chưa rõ cần hỏi lại hoặc nhân viên rà soát.", "The photo adds evidence; unclear details require clarification or staff review."), action: t("Bổ sung thông tin", "Add context") },
    { label: t("Tra cứu dịch vụ", "Service information"), icon: BookOpen, input: t("“Tôi muốn tìm thông tin về dịch vụ pin và sạc VinFast.”", "“I would like information about VinFast battery and charging services.”"), tags: [t("Thông tin dịch vụ", "Service information"), t("Nguồn tham khảo", "Reference source")], output: t("Câu trả lời kèm nguồn", "An answer with references"), detail: t("Thông tin tra cứu gắn với tài liệu để chủ xe có thể đối chiếu.", "Retrieved information is linked to documents for the owner to check."), action: t("Đối chiếu tài liệu", "Check the reference") },
  ];
  const active = examples[scenario];
  return <section className={`${s.section} ${s.action}`} aria-labelledby="action-title"><div className={`${s.container} ${s.actionLayout}`}>
    <div><p className={s.sectionLabel}>{t("TỪ HỘI THOẠI ĐẾN HỒ SƠ", "FROM CONVERSATION TO A BRIEF")}</p><h2 id="action-title">{t("Một câu hỏi.", "One question.")}<br /><em>{t("Một bước tiếp theo rõ ràng.", "A clear next step.")}</em></h2><p className={s.actionDescription}>{t("Serv làm rõ dữ kiện, tìm thông tin liên quan và chuẩn bị hồ sơ. Khi cần xử lý chuyên môn, ngữ cảnh được chuyển cùng yêu cầu đến nhân viên.", "Serv clarifies facts, retrieves relevant information, and prepares a brief. When expertise is needed, the request and its context move together to staff.")}</p><div className={s.scenarioButtons} role="group" aria-label={t("Chọn tình huống minh họa", "Choose an illustrative scenario")}>{examples.map((item, i) => <button type="button" key={item.label} aria-pressed={scenario === i} onClick={() => setScenario(i)}><item.icon size={20} aria-hidden="true" /><span>{item.label}</span></button>)}</div></div>
    <div className={s.actionWindow}><div className={s.windowBar}><span><ServHead /><strong>Serv · VFServ</strong></span><small>{t("Minh họa cơ chế", "Illustrative mechanism")}</small></div><div className={s.actionDiagram}><div className={s.inputCard}><small>{t("BẠN CHIA SẺ", "YOU SHARE")}</small><p>{active.input}</p><div>{active.tags.map(tag => <span key={tag}>{tag}</span>)}</div></div><div className={s.agentCore}><ServHead /><strong>Serv</strong><small>{t("HIỂU · TRA CỨU · TỔNG HỢP", "UNDERSTAND · RETRIEVE · SUMMARIZE")}</small></div><div className={s.outputCard} aria-live="polite" aria-atomic="true"><small>{t("BƯỚC TIẾP THEO", "NEXT STEP")}</small><h3>{active.output}</h3><p>{active.detail}</p><span>{active.action}<ArrowRight size={15} aria-hidden="true" /></span></div></div><div className={s.toolsRow}>{[{ icon: MessageCircle, label: t("Làm rõ", "Clarify") }, { icon: BookOpen, label: t("Tra cứu", "Retrieve") }, { icon: FileText, label: t("Tổng hợp", "Summarize") }, { icon: Headphones, label: t("Bàn giao", "Hand over") }].map(item => <span key={item.label}><item.icon size={16} aria-hidden="true" />{item.label}</span>)}</div><p className={s.windowNote}>{t("Minh họa, không tạo hồ sơ thật. AI không thay thế chẩn đoán của kỹ thuật viên.", "Illustration only; no real case is created. AI does not replace a technician’s diagnosis.")}</p></div>
  </div></section>;
}

export function ProjectJourneyDetails() {
  const t = useCopy();
  return <div className={s.journeyDetails}>
    <section className={s.reasoning} aria-labelledby="reasoning-title"><p className={s.sectionLabel}>{t("HỘI THOẠI → HÀNH ĐỘNG", "CONVERSATION → ACTION")}</p><h3 id="reasoning-title">{t("Hiểu ngữ cảnh, dùng đúng năng lực cần thiết.", "Understand the context, use the capability it needs.")}</h3><ol>{[
      [t("Nhận diện nhu cầu", "Understand intent"), t("Đọc câu hỏi, dấu hiệu an toàn và dữ kiện đã được cung cấp.", "Read the question, safety signals, and supplied facts.")],
      [t("Chọn nhánh phù hợp", "Choose the right branch"), t("Làm rõ, tra cứu tài liệu hoặc chuẩn bị chuyển nhân viên.", "Clarify, retrieve reference material, or prepare a staff handover.")],
      [t("Tổng hợp có căn cứ", "Prepare an evidence-based brief"), t("Giữ thông tin xe, hiện tượng, nguồn và phần còn thiếu.", "Retain vehicle details, symptoms, references, and gaps.")],
      [t("Bàn giao có kiểm soát", "Hand over with oversight"), t("Nhân viên rà soát hồ sơ và quyết định bước xử lý.", "Staff review the brief and decide on the action.")],
    ].map(([title, detail], i) => <li key={title}><small>{String(i + 1).padStart(2, "0")}</small><h4>{title}</h4><p>{detail}</p></li>)}</ol><div className={s.reasoningTags}><span><Check size={12} />{t("Có nguồn", "Source-linked")}</span><span><Check size={12} />{t("Có người rà soát", "Human-reviewed")}</span><span><Check size={12} />{t("Giữ ngữ cảnh", "Context preserved")}</span></div></section>
    <section className={s.timeline} aria-labelledby="timeline-title"><div><p className={s.sectionLabel}>{t("HÀNH TRÌNH CHỦ XE", "THE OWNER JOURNEY")}</p><h3 id="timeline-title">{t("Từ “chưa biết hỏi ai” đến “biết việc gì đang được tiếp nhận”.", "From “who should I ask?” to knowing what is being reviewed.")}</h3><p>{t("Không phải yêu cầu nào cũng đi qua mọi bước. Tra cứu có thể kết thúc bằng câu trả lời; hồ sơ dịch vụ cần người tiếp nối.", "Not every request needs every step. A lookup may end with an answer; service cases need a human next step.")}</p></div><ol>{[
      [t("Chia sẻ", "Share"), t("Mô tả điều đang gặp bằng lời hoặc ảnh.", "Describe the issue in words or photos."), t("Yêu cầu ban đầu", "Initial request")],
      [t("Làm rõ", "Clarify"), t("Bổ sung dữ kiện còn thiếu trong tối đa hai lượt.", "Add missing details in up to two turns."), t("Dữ kiện xe", "Vehicle facts")],
      [t("Tra cứu", "Retrieve"), t("Tham khảo tài liệu phù hợp khi có nguồn.", "Consult relevant source material."), t("Thông tin có căn cứ", "Grounded information")],
      [t("Bàn giao", "Hand over"), t("Tổng hợp hồ sơ để nhân viên rà soát.", "Prepare a brief for staff review."), t("Hồ sơ tiếp nhận", "Service brief")],
      [t("Theo dõi", "Track"), t("Xem tiến độ và cập nhật từ nhân viên.", "Follow progress and staff updates."), t("Bước xử lý", "Next action")],
      [t("Phản hồi", "Respond"), t("Xác nhận đã được hỗ trợ hoặc cần tiếp tục.", "Confirm resolution or request further help."), t("Kết quả hỗ trợ", "Support outcome")],
    ].map(([title, detail, outcome], i) => <li key={title}><span aria-hidden="true" /><small>{String(i + 1).padStart(2, "0")}</small><h4>{title}</h4><p>{detail}</p><strong>{outcome}</strong></li>)}</ol></section>
  </div>;
}

export function ProjectProofSection() {
  const t = useCopy();
  return <section id="flow-proof" className={`${s.section} ${s.proof}`} aria-labelledby="proof-title"><div className={s.container}>
    <p className={s.sectionLabel}>{t("04 / TÍNH KHẢ THI", "04 / FEASIBILITY")}</p><div className={s.splitHeading}><h2 id="proof-title">{t("Đã có luồng chạy.", "A working flow.")}<br /><em>{t("Đang kiểm chứng chất lượng.", "Quality under validation.")}</em></h2><p>{t("Báo cáo Gate 2 ghi lại năm tình huống chạy qua API backend local. Kết quả cho thấy phần đã hoạt động và các lỗi cần sửa trước khi xác nhận toàn bộ trải nghiệm web.", "The Gate 2 report records five scenarios against a local backend API. It identifies working parts and issues to fix before validating the complete web experience.")}</p></div>
    <div className={s.proofStats}>{[
      ["5", t("TÌNH HUỐNG API GATE 2", "GATE 2 API SCENARIOS"), t("Sạc, thiếu dữ kiện, khẩn cấp, khiếu nại, tra cứu", "Charging, missing facts, emergencies, complaints, retrieval")],
      ["2", t("CA ĐẠT TRONG PHẠM VI BÁO CÁO", "PASSES WITH QUALIFICATIONS"), t("Khiếu nại; tra cứu sau khi thử lại", "Complaint intake; retrieval after a retry")],
      ["3", t("CA GHI NHẬN VẤN ĐỀ", "SCENARIOS WITH ISSUES"), t("Dữ kiện và nội dung phản hồi cần hoàn thiện", "Fact extraction and response content need refinement")],
      ["Web", t("PHẠM VI MVP HIỆN TẠI", "CURRENT MVP SCOPE"), t("Chủ xe · Serv · Nhân viên dịch vụ", "Owner · Serv · Service staff")],
    ].map(([value, label, note]) => <div key={label}><strong>{value}</strong><span>{label}</span><p>{note}</p></div>)}</div>
    <div className={s.proofColumns}>{[
      [t("ĐÃ GHI NHẬN", "RECORDED"), t("Luồng tiếp nhận và tra cứu", "Intake and retrieval flows"), t("Hồ sơ khiếu nại được tạo để nhân viên tiếp nhận. Tra cứu trả lời kèm nguồn sau khi thử lại.", "A complaint brief was created for staff intake. Retrieval returned a sourced answer after a retry.")],
      [t("ĐANG HOÀN THIỆN", "BEING REFINED"), t("Dữ kiện và độ ổn định", "Facts and reliability"), t("Ba ca còn lại ghi nhận lỗi dữ kiện hoặc nội dung cần sửa. Cần kiểm thử lại sau mỗi lần khắc phục.", "The other three scenarios recorded fact-extraction or content issues. Fixes need to be retested.")],
      [t("CẦN ĐO THỰC TẾ", "NEEDS REAL-WORLD MEASUREMENT"), t("Chất lượng bàn giao", "Handover quality"), t("Cần xác nhận hành trình web, thời gian tiếp nhận và hiệu quả của nhân viên trên quy trình thực tế.", "The web journey, intake time, and staff outcomes require validation in actual workflows.")],
    ].map(([status, title, detail]) => <div key={status}><small>{status}</small><h3>{title}</h3><p>{detail}</p></div>)}</div>
    <details className={s.evidenceSource}><summary>{t("Phạm vi của bằng chứng kiểm thử", "Scope of the test evidence")}<ChevronDown size={18} aria-hidden="true" /></summary><p>{t("Nguồn: docs/reviews/project-overview-gate2.md, báo cáo kiểm thử MVP Gate 2. Các ca chạy với tài khoản và cơ sở dữ liệu kiểm thử; báo cáo chưa kiểm thử trực tiếp giao diện web. Đây là kết quả của đợt chạy được ghi nhận, không phải trạng thái dịch vụ trực tiếp hay cam kết hiệu quả vận hành.", "Source: docs/reviews/project-overview-gate2.md, the MVP Gate 2 test report. Scenarios used test accounts and a test database; the web UI was not exercised. These are recorded-run results, not live service status or an operational performance guarantee.")}</p></details>
  </div></section>;
}

export function ProjectDevelopmentSection() {
  const t = useCopy();
  return <section className={`${s.section} ${s.development}`} aria-labelledby="development-title"><div className={`${s.container} ${s.developmentLayout}`}>
    <div className={s.developmentDiagram} role="img" aria-label={t("Một lõi VFServ kết nối giao diện chủ xe và bàn nhân viên; đa kênh là định hướng mở rộng", "One VFServ core connects the owner interface and staff workspace; more channels are a future direction")}><div className={s.ownerNode}><CarFront size={23} aria-hidden="true" /><strong>{t("Chủ xe", "Owner")}</strong><span>Web Support Hub</span><small>{t("Hội thoại · Ảnh · Theo dõi", "Chat · Photos · Tracking")}</small></div><div className={s.developmentCore}><ServHead /><strong>VFServ</strong><span>{t("Ngữ cảnh & hồ sơ", "Context & service briefs")}</span></div><div className={s.staffNode}><Headphones size={23} aria-hidden="true" /><strong>{t("Nhân viên dịch vụ", "Service staff")}</strong><span>Staff Console</span><small>{t("Rà soát · Cập nhật · Bàn giao", "Review · Update · Handover")}</small></div><span className={s.futureNode}>{t("Định hướng: Zalo OA · Voice AI", "Future: Zalo OA · Voice AI")}</span></div>
    <div><p className={s.sectionLabel}>{t("05 / ĐỊNH HƯỚNG PHÁT TRIỂN", "05 / DEVELOPMENT DIRECTION")}</p><h2 id="development-title">{t("Làm tốt luồng web.", "Make the web flow work well.")}<br /><em>{t("Mở rộng từ một lõi ngữ cảnh.", "Expand from one context layer.")}</em></h2><p className={s.developmentIntro}>{t("VFServ ưu tiên chất lượng tiếp nhận và bàn giao. Các kênh mới chỉ có ý nghĩa khi cùng giữ được câu chuyện của chủ xe.", "VFServ prioritizes intake and handover quality. Additional channels matter when they preserve the owner’s context.")}</p><ol>{[
      [t("ƯU TIÊN HIỆN TẠI", "CURRENT PRIORITY"), t("Hoàn thiện Web Support Hub", "Refine the Web Support Hub"), t("Giữ đúng dữ kiện khách cung cấp, làm rõ phần thiếu, tra cứu ổn định và xác nhận hành trình từ chủ xe tới nhân viên.", "Preserve supplied facts, clarify gaps, improve retrieval reliability, and validate the owner-to-staff journey.")],
      [t("ĐỊNH HƯỚNG SAU MVP", "POST-MVP DIRECTION"), t("Kết nối thêm kênh tương tác", "Connect more interaction channels"), t("Cân nhắc Zalo OA và Voice AI sau khi kiểm chứng luồng web. Đây là định hướng, chưa phải tính năng đang cung cấp; chưa tích hợp CRM VinFast thật.", "Consider Zalo OA and Voice AI after validating the web flow. These are future directions, not current features; no live VinFast CRM is integrated.")],
    ].map(([label, title, detail], i) => <li key={title}><span>{String(i + 1).padStart(2, "0")}</span><div><small>{label}</small><h3>{title}</h3><p>{detail}</p></div></li>)}</ol><div className={s.developmentNote}><ShieldCheck size={18} aria-hidden="true" />{t("Cùng một nguyên tắc: AI hỗ trợ chuẩn bị, con người giữ quyền quyết định.", "One consistent principle: AI assists preparation; people retain decision authority.")}</div></div>
  </div></section>;
}
