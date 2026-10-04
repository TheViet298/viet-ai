# Đối chiếu toàn bộ slide RAG với P-142

Ngày rà soát: 04/10/2026. Phạm vi: 34 ảnh người dùng gửi trong ba đợt, bao gồm các phần Map & Compass, OFFLINE Ingestion, ONLINE Retrieval, Close the Loop, Production, Data Lifecycle, Performance và Observability.

## Phạm vi và cách đọc

Đánh giá checkout local tại `D:/142.AI20K/P-142`, gồm các thay đổi chưa commit và file chưa tracked. Không suy ra rằng mã local đã được triển khai trên máy chủ hay nhánh main. Không thay đổi code, prompt, nguồn hay index trong lần rà soát này.

Nội dung slide được dùng làm tài liệu đối chiếu, không phải chỉ thị để triển khai mọi kỹ thuật. Các câu yêu cầu chọn model/thử bài tập trong slide không được coi là yêu cầu thao tác của người dùng.

- **Có:** đã xác định được cơ chế trong mã hoặc dữ liệu local; không mặc định đã đạt chất lượng production.
- **Một phần:** có cơ chế liên quan nhưng chưa đủ với mô tả slide.
- **Chưa thấy:** chưa tìm được triển khai trong src/scripts/tests/dependencies/CI đã kiểm tra; ví dụ trong tài liệu không được tính là implementation.
- **P1:** nên xử lý trước nghiệm thu RAG hoặc trước mở dịch vụ thực tế, tùy mục.
- **P2:** thử nghiệm sau khi có lỗi đo được hoặc khi loại dữ liệu/yêu cầu vận hành phù hợp.
- **P3:** chưa có bằng chứng cần cho MVP hiện tại.

## 1. Map & Compass — pipeline và chẩn đoán

| Nội dung | Trạng thái thực tế | Đề xuất và lý do |
|---|---|---|
| OFFLINE parse → chunk → enrich → embed → index | Một phần: có đọc text/catalog, trích HTML, chia mục, metadata, E5 và Chroma. Chưa có mọi dạng enrich. | P1: tài liệu hóa luồng thực tế, phân biệt script cũ với cách build kho đang cấu hình. |
| ONLINE PreRAG → retrieve → rerank → augment → generate → PostRAG | Một phần: có triage/source filtering, retrieval, xếp hạng heuristic, kiểm tra metadata/context, generation tùy chọn và fallback. | P1: đặt tên đúng cơ chế; không coi từng ô trên slide là một module đã có. |
| Error Tree | Có lý do loại ứng viên và audit eval, chưa có cây lỗi xuyên suốt. | P1: tách parse/chunk/embed/retrieve/rank/context/generation/provider/storage. |
| Ca chạy mẫu xuyên suốt | Có demo và datasets/eval, không phải đúng TailieuBot trên slide. | P1: dùng một ca VinFast có nguồn, điều kiện và phiên bản để truy vết từng tầng. |

Bằng chứng: [RAG service](D:/142.AI20K/P-142/src/services/rag_service.py), [RAG node](D:/142.AI20K/P-142/src/agents/nodes/rag_node.py), [graph](D:/142.AI20K/P-142/src/agents/graph.py), [audit](D:/142.AI20K/P-142/scripts/audit_agent_eval.py). Đường dẫn bằng chứng chính xác được liệt kê ở phần cuối.

## 2. OFFLINE — parse, chunking và enrichment

| Kỹ thuật | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| Fixed-size | Có ở script cũ: khoảng 500 ký tự, overlap 80 ký tự, ưu tiên ranh giới câu/dòng. | P1: khai báo đơn vị rõ ràng; không tương đương 512 token/64 token trong slide. |
| Structure-aware | Một phần: Markdown heading, mục đánh số, giữ heading và các bước; HTML trích bảng thành dòng. | P1: kiểm tra điều kiện/ngoại lệ, bảng nhiều cấp, cấu trúc lồng và giới hạn encoder. Không phải parser layout tổng quát. |
| Chọn chunking theo data | Có xử lý riêng text/catalog/HTML; chưa có policy/router chung theo loại tài liệu. | P1: ghi rõ quy tắc cho từng nguồn, tránh một bộ tham số cho mọi tài liệu. |
| Sentence Window | Chưa thấy tìm bằng câu rồi mở rộng câu lân cận. | P2: thử khi bằng chứng thiếu ngữ cảnh gần câu được tìm. |
| Hierarchical parent–child | Chưa thấy liên kết parent/child trong schema kho hoặc retriever. | P2: tìm child nhỏ rồi lấy parent có ngân sách; chỉ thử nếu mất ngữ cảnh thực sự là lỗi chính. Giữ heading/nguyên mục không đồng nghĩa parent–child. |
| Semantic chunking | Chưa thấy chia theo similarity/đổi chủ đề. | P3: chỉ thử trên corpus hỗn hợp có lỗi chia cấu trúc; không áp cosine 0,85 mặc định. |
| Late chunking | Chưa có: E5 encode từng passage riêng, sau đó mean pool cả passage. | P3: cần encoder/ngữ cảnh và pooling theo span thích hợp; đổi kích thước chunk không tạo late chunking. |
| RAPTOR | Chưa có cluster và cây tóm tắt đệ quy. | P3: chỉ thử cho câu hỏi tổng hợp xuyên nhiều đoạn/tài liệu. Parent–child và RAPTOR không phải một cơ chế. |
| Layout-aware PDF/OCR | Chưa thấy trong ingestion RAG đã kiểm tra. | P2 khi nhận PDF scan/bảng/layout phức tạp. OCR nhận diện xe, nếu bổ sung ở luồng khác, không tự tạo ingestion PDF. |
| Multimodal ingestion | Chưa thấy index ảnh trang/diagram. | P3 với kho text hiện tại; P2 khi câu trả lời phụ thuộc hình. |
| Contextual prepend | Có heading ở một số passage, chưa có LLM tạo context riêng cho mỗi chunk. | P2: thử context xác định từ title/section/model trước; dùng LLM cho đoạn mơ hồ nếu có lợi ích đo được. |
| Summarization cho retrieval | Chưa có vector summary liên kết chunk gốc. | P3: chỉ dùng summary để tìm, giữ nguyên văn để trả lời và trích dẫn. |
| Hypothetical Q&A offline | Chưa có index câu hỏi giả định. | P2 cho FAQ lệch từ vựng; cần liên kết question-vector → original chunk và kiểm tra câu hỏi sinh ra. |
| Metadata enrichment | Có source_id/title/url/source_type/verified_at/applicable_models; kho hiện tại có status_code. | P1: thêm trường hiệu lực/phiên bản khi có chính sách chồng lấn. Chưa thấy LLM extract topic/entity; lưu metadata không đồng nghĩa embed metadata. |

Luồng kho hiện tại là E5 candidate → rewrite source sections, giữ vector/chunk SRC-007/008/009 từ candidate trước và rebuild SRC-001…006. Vì vậy kho không dùng một chiến lược chunking đồng nhất. Bộ trích HTML có trong code nhưng lần refresh được ghi nhận bị HTTP 403; không được suy ra rằng toàn bộ kho đang chứa HTML mới được tải thành công.

## 3. ONLINE — retrieval và reranking

| Kỹ thuật | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| Dense retrieval | Có E5 ONNX local, vector 384 chiều, squared L2 trên vector chuẩn hóa. | P1: giữ metric/threshold/version nhất quán và đánh giá recall. |
| Hybrid lexical + dense | Có điểm giao từ khóa có trọng số tần suất kết hợp điểm vector. | Có baseline riêng của dự án; không gọi nó là BM25 + RRF. |
| BM25 + RRF | Chưa thấy. | P2: benchmark đối chứng cho mã lỗi, model, phiên bản và thuật ngữ hiếm. Không thay baseline khi chưa có kết quả tốt hơn. |
| Tách từ tiếng Việt | Regex và chuẩn hóa Unicode/model; chưa thấy word segmenter. | P2: đo tác động cùng lexical retrieval; không mặc định thư viện tách từ luôn tăng chất lượng. |
| Two-stage top-20 → top-3 | Có shortlist tối đa 20 rồi xếp hạng/lọc tối đa 3. | Một phần so với slide: không có cross-encoder và không phải lấy đúng 20/3 trong mọi lượt. |
| Cross-encoder reranker | Chưa có model đọc query+passage. | P2: thử nếu đoạn đúng nằm trong candidate pool nhưng bị xếp thấp; không sửa được candidate bị bỏ trước đó. |
| ColBERT token-level | Chưa có multi-vector/MaxSim. | P3: chỉ thử khi exact/token detail vẫn thất bại sau baseline đơn giản. |
| SPLADE learned sparse | Chưa có. | P3: cần corpus/model đa ngôn ngữ phù hợp và lợi ích đo được. |
| Weighted/learned fusion | Có cộng điểm cố định 0,35 lexical + 0,65 semantic; chưa train theo relevance labels. | P2 sau dữ liệu nhãn đáng tin; không gọi trọng số thủ công là learned fusion/tensor fusion. |
| Dynamic weighting | Chưa có đổi trọng số theo query class. | P3 trước khi có baseline và nhãn; tỷ lệ 80/20 trên slide chỉ là ví dụ. |
| ColPali/ColQwen | Chưa có index patch ảnh. | P3 hiện tại; P2 khi parse làm mất bằng chứng hình/bảng. |
| Reranker landscape | Chưa có model nào trong danh sách slide được triển khai. | Chọn bằng benchmark tiếng Việt, chiều dài passage, phần cứng và giấy phép; không lấy bảng xếp hạng/latency slide làm kết luận. |

Hai giới hạn cần chú ý: (1) nhánh đang phù hợp với kho L2+embedding_function lấy toàn bộ corpus và tính khoảng cách bằng NumPy rồi xếp hạng, không chỉ ANN top-k; (2) lexical score không tự vượt qua điều kiện distance tối đa. Vì vậy vẫn có thể loại đoạn exact đúng có distance lớn. Source prefilter dùng từ khóa cũng có thể thu hẹp sai một query nhiều chủ đề; đây là khả năng cần đo, chưa phải lỗi đã chứng minh bằng ca production.

## 4. Control Flow, Augmentation, Generate và PostRAG

| Nội dung | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| HyDE | Chưa có. | P3: thêm online LLM call cạnh tranh với budget một attempt/lượt. Thử Q&A/context offline trước cho vocab gap. |
| Multi-query / decomposition | Chưa có nhiều retrieval query rồi hợp kết quả. | P2: cho câu hỏi nhiều ý hoặc so sánh; đo đủ bằng chứng từng ý. Query expansion và decomposition là hai cách khác nhau dù slide gộp. |
| Corrective RAG | Có gate kết quả và fallback chuyên viên; chưa evaluator/rewrite/retrieve lại/web. | P1: tách nguyên nhân thất bại; P2 cho correction có giới hạn. Không tự dùng web chưa duyệt như nguồn chính thức. |
| NLI verification | Chưa có model entailment. | P2 nếu có ca phủ định/mâu thuẫn; relevance query–chunk không đồng nhất với entailment giữa premise và claim. |
| Compression | Giữ đoạn nguyên vẹn; bỏ đoạn vượt ngân sách, có thể bỏ cả lớp context. | P1: đơn vị và chính sách budget; P2 cho nén giữ số/điều kiện/ngoại lệ. Đây chưa phải LLMLingua/compression ngữ nghĩa. |
| Citation injection | Context có source ID, câu trả lời có link, state có chunk_id. | Một phần: P1 thêm claim → chunk/source mapping và kiểm tra bằng chứng; link cuối câu trả lời chưa chứng minh từng ý. |
| Conflict resolution v2/v3 | Chưa có bộ chọn chính sách theo ngày hiệu lực/quan hệ thay thế. | P1 khi có nguồn chồng lấn; verified_at không phải effective_at. Không áp newest-wins nếu phạm vi/model khác nhau. |
| Grounded generation | Có structured answer/source_ids/supported và prompt yêu cầu bám nguồn; có trả nguyên trích đoạn nếu LLM không khả dụng. | Một phần: supported là model tự khai báo; ID đúng không chứng minh claim đúng. P1 đo số liệu/điều kiện/nguồn theo từng claim. |
| PostRAG/fallback | Có kiểm tra metadata, distance, một số nội dung unsafe, PII và chuyển chuyên viên khi không đủ nguồn. | Có cơ chế nhưng chưa chứng minh đầy đủ factual correctness hoặc chống mọi hallucination. |
| LangGraph/control routing | Có StateGraph intake/safety/triage/clarify/rag/case_brief. | Có; StateGraph không đồng nghĩa GraphRAG hay đầy đủ multi-agent/agentic retrieval. |
| HITL | Có ticket, bắt buộc review theo nhóm sự cố/giao dịch, API staff actions và frontend console. | Có cơ bản; FAQ đủ nguồn có thể trả trực tiếp, không phải tất cả output đều được duyệt trước. |

`resolve_policy_conflict()` hiện là regex kiểm tra thao tác nguy hiểm/jailbreak, không phải phát hiện mâu thuẫn giữa hai tài liệu. Fact recency của hội thoại không phải quản lý hiệu lực chính sách trong KB.

## 5. Close the Loop — đánh giá và giới hạn embedding

| Nội dung | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| Context Recall | Chưa có metric RAGAS hoặc đo đủ facts ở retrieved context độc lập. | P1; đo retrieval trước khi generation và sau context budget. |
| Context Precision | Chưa có metric xếp hạng relevance độc lập. | P1; cần nhãn query–chunk và rank-aware measurement. |
| Faithfulness | Kiểm tra source IDs/từ khóa/facts ở câu trả lời; chưa có kiểm chứng claim tổng quát. | P1; chỉ số grounded hiện tại không tương đương RAGAS Faithfulness. |
| Answer Relevancy | Chưa có metric riêng. | P1 cùng đáp án mẫu/đánh giá người; không chỉ đo câu trả lời chứa từ khóa. |
| Error Tree theo metric | Có audit intent/routing/review/grounding. | P1 mở rộng loại lỗi và tra lại ca; metric không xác định nguyên nhân duy nhất. |
| Negation/entity/numeric/temporal | Có một số lọc model/variant/year và test số; chưa phủ toàn bộ. | P1 thêm cặp đối chứng và điều kiện/ngoại lệ. Similarity là độ gần, không phải bộ kiểm chứng logic. |
| Model/data replacement | Có candidate model/KB version. | Không tự động đổi/fine-tune chỉ vì một metric thấp; chẩn đoán raw source → candidate → context → output. |

Các ngưỡng slide không phải ngưỡng nghiệm thu đã phê duyệt. Bộ 90 ca còn draft; log trước đây không được dùng làm bằng chứng nghiệm thu production. Không kết luận đạt RAGAS vì metric khác đạt ngưỡng.

## 6. Production — latency, cost, security, reliability

| Nội dung | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| End-to-end latency SLA | Có node latency và p50/p95 eval, deadline model/turn. | P1 trước production: HTTP latency, p95/p99, tải đồng thời, cold/warm và fallback. Deadline asyncio chưa là SLA toàn request. |
| Streaming/TTFT | Chưa có streaming chat; trả structured JSON hoàn chỉnh. | P2 theo UX. TTFT không phải thời gian hoàn tất output. |
| Token/cost economics | Có attempt/context limits và token usage khi provider trả; cost field chưa thấy tính tiền/tổng ngân sách. | P1 trước gọi API ở quy mô lớn: cost/turn, budget/circuit/quota rõ ràng. |
| Circuit breaker | Có in-memory circuit theo provider configuration, cooldown và probe; xử lý rate/auth lỗi. | Có cơ bản; chưa distributed breaker hay hoàn chỉnh cho mọi lỗi/provider. |
| Gateway/rate limit | Có guest quota theo phiên; chưa gateway throttling theo thời gian/tenant/API key. | P1 trước public production; guest có thể tạo phiên mới, quota này không thay anti-abuse rate limit. |
| Production identity/SSO/JWT | Có static demo tokens, cùng customer-demo/staff-demo principal theo vai. | P1 trước nhiều người dùng thật: identity độc lập, expiry/revocation và role/ownership. |
| Session/ownership | Có server session, role/owner checks và kiểm tra version chống ghi đè. | Có ở demo; chưa chứng minh cách ly nhiều danh tính thật vì adapter auth đang demo. |
| Search-time tenant ACL | Chưa có tenant/access metadata trong KB. | P1 trước private/multi-tenant corpus; model/source filters không phải ACL. Kho public hiện tại không cần giả định có tenant bí mật. |
| Guardrails/PII | Có regex masking intake/output/trace, hard safety và prompt boundaries. | Có một phần; P1 adversarial tests, retention và coverage. Không tuyên bố ngăn tuyệt đối injection/toxicity/leakage. |
| Vector DB HA/distribution | Chroma local, backend Docker Compose; store SQLite. | P2 khi SLA/tải/dung lượng yêu cầu. Không có căn cứ đổi DB ngay vì kho 2.163 đoạn. |
| DB decision framework | Chưa có migration Qdrant/Milvus/Pinecone/pgvector. | Giữ tiêu chí chọn theo vận hành và benchmark, không coi một DB luôn tốt nhất. Dịch vụ managed vẫn có chi phí vận hành/sử dụng. |

## 7. Enterprise ingestion — vòng đời dữ liệu và index

| Nội dung | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| CDC/connectors Confluence/SharePoint/SQL | Chưa có. | P3 cho MVP public; P2 khi nguồn thường xuyên thay đổi và có quyền truy cập. |
| Incremental upsert | Có upsert theo batch, chưa event-driven/hash-diff processing đầy đủ. | P1/P2: phát hiện tài liệu thay đổi, ID/version ổn định và idempotency trước CDC nặng. |
| Delete/source withdrawal | Chưa thấy dọn toàn bộ chunk cũ khi nguồn bị xóa/thu hồi hoặc tài liệu ngắn lại. | P1: đối soát doc → chunks, xóa/disable index và invalidation cache. Upsert không tự xóa chunk dư. |
| Freshness | Registry/verified_at và refresh script; lần refresh ghi nhận 403. | P1: phân biệt fetch success, verification, effective date và stale-source handling. Không tự phê duyệt nguồn mới. |
| Candidate/rollback | Có build kho riêng, giữ kho cũ, đổi env rồi restart backend. | Có nền tảng; chưa zero-downtime. |
| Blue–green/atomic switch/alias | Chưa có alias/router atomic cutover. | P2 khi cần cập nhật không gián đoạn; phối hợp encoder, metric, threshold, cache và source registry theo index version. |
| MRL nhỏ → đầy đủ | Chưa có; vector hiện tại 384 chiều. | P3: chỉ dùng model hỗ trợ/trained phù hợp và benchmark. Không tự cắt E5 384 thành 128 rồi gọi MRL. |

## 8. Online performance và observability/CI-CD

| Nội dung | Trạng thái | Có cần bổ sung, vì sao |
|---|---|---|
| Semantic answer cache | Chưa có; cache corpus/model khác cache query → answer. | P2 khi có hit-rate đo được; bắt đầu cache chính xác cho FAQ public nếu đủ lợi ích. |
| Cache threshold/TTL | Chưa có answer-cache policy. | P2: key theo query/model/variant/year/intent/KB/prompt/ACL, TTL và invalidation. Cosine cao không đủ để tái dùng câu trả lời. |
| Reranker ONNX/TensorRT/INT8 | Chưa có reranker; E5 embedding đã ONNX quantized CPU. | P2 sau khi chọn reranker; kiểm chứng rank/recall, throughput và p95 trước/sau quantization. |
| Sync trace/replay | Có node/LLM trace, sanitization và replay; lưu SQLite đồng bộ. | Có audit cơ bản; P1/P2 đo overhead và retention. |
| Async telemetry queue | Chưa có queue/worker. | P2 hoặc P1 nếu load test cho thấy nút thắt; bounded buffer và policy khi queue đầy. Không nhất thiết dùng Kafka. |
| Drift monitoring/alerts | Có distance từng lượt, chưa trend/segment dashboard hoặc alert. | P2 khi có traffic; so cùng model/index/nhóm query, không dùng distance một mình để chứng minh drift. |
| Golden dataset | Có 90 acceptance, 24 label-review, 15 RAG v1; không chứng minh độc lập/non-overlap. | P1: duyệt nguồn, đáp án, chunk/facts, ngoại lệ, phiên bản và tách dev/holdout. 200+ không là số bắt buộc. |
| CI regression | CI hiện chạy Ruff + pytest. | Có software checks; chưa RAG eval gate gắn artifact KB/model/dataset. |
| Quality gate chặn phát hành | Eval trả metrics/báo cáo, acceptance_approved=false; CI chưa gọi nó làm gate. | P1: job kiểm tra ngưỡng, missing-data/error handling, exit status và nối vào release; cần cấu hình bảo vệ branch/deploy ngoài code. |
| Shadow/A-B | Chưa có. | P2 khi đã có traffic và gate; shadow cần cách ly side effects, giới hạn chi phí/tài nguyên trước chia output thực. |

## Kết quả kiểm tra mới trong lần rà soát

Đọc SQLite bằng URI `mode=ro`; đo bằng tokenizer E5 local có thêm prefix `passage: ` và tắt truncation để xác định chiều dài thật. `.env` trỏ `./data/chroma-quality-v4`; schema kho xác nhận E5 registered embedding, L2 và 384 chiều. Không kết luận backend đang chạy sử dụng đúng env này.

| Chỉ số | Kết quả |
|---|---:|
| Số document trong kho | 2.163 |
| Input passage vượt 256 E5 token | 4 |
| Passage dài nhất | 741 token |
| Document vượt 1.200 byte UTF-8 | 3 |
| Metadata parent/child, tenant ACL, effective date | Không có trong keys kho được đọc |
| Test liên quan được chạy mới | 29 passed, 10,03 giây |

| Chunk | E5 input token | UTF-8 byte | Tác động cần kiểm tra |
|---|---:|---:|---|
| SRC-008-0503 | 307 | 643 | Input vượt truncation encoder. |
| SRC-008-0508 | 309 | 632 | Input vượt truncation encoder. |
| SRC-001-sections-47 | 255 | 1.318 | Không vượt encoder nhưng vượt ngân sách bằng chứng ban đầu. |
| SRC-001-sections-48 | 310 | 1.588 | Vượt cả encoder và budget context. |
| SRC-001-sections-50 | 741 | 3.285 | Vượt cả encoder và budget context. |

Ba đoạn vượt 1.200 byte sẽ không được chấp nhận bởi filter khi đến bước budget. Các đoạn nhỏ hơn vẫn có thể bị loại khi tổng budget đã giảm sau nhận đoạn trước. Đây là đo độ dài và phân tích code, không phải đo tỷ lệ câu hỏi production bị ảnh hưởng. Không chứng minh vector cũ đã được sinh bằng đúng từng dòng code hiện tại; schema/manifest và giới hạn hiện tại cho thấy đây là các đoạn cần đối soát đầu tiên.

Lệnh kiểm tra đã chạy:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_agents/test_hybrid_retrieval.py tests/test_agents/test_rag_quality.py tests/test_agents/test_retrieval_prefilter_cache.py tests/test_agents/test_source_sections.py tests/test_agents/test_source_capture.py tests/test_agents/test_multilingual_embeddings.py tests/test_agents/test_rag_node.py tests/test_agents/test_llm_budget.py tests/test_eval/test_quality_measurement.py -q -p no:cacheprovider --basetemp=.test-runs/slides-audit-20261004
```

Các tests này kiểm tra cơ chế với fixtures/mocks và môi trường tách biệt, không thay bộ đánh giá thực trên toàn KB, production load test hay nghiệm thu RAGAS. Không gọi LLM thật trong lượt kiểm tra này.

## Điều chỉnh các kết luận trước và cách hiểu slide

1. **Ngân sách 1.200 là byte:** tên hàm/comment dùng token nhưng implementation đếm byte. Đếm byte có thể là lựa chọn bảo thủ có chủ đích; vấn đề cần sửa là đơn vị không nhất quán và bằng chứng bị loại quá sớm, không mặc định cứ đếm byte là sai.
2. **Hybrid có, BM25+RRF chưa có:** weighted lexical overlap + distance không phải BM25/RRF. RRF cộng reciprocal rank, không phải weighted sum raw scores 0,5/0,5; weighted RRF cũng có thể tồn tại.
3. **Structure-aware chỉ một phần:** giữ heading, dòng và quy trình không bảo đảm mọi bảng/ngoại lệ nguyên vẹn, cũng không tạo parent–child tự động.
4. **Rerank có heuristic, chưa model cross-encoder:** top-20 → top-3 mới là khung, không có chất lượng/latency như slide.
5. **NLI khác relevance:** question không phải claim; premise/hypothesis hoặc claim được tạo cần đúng để kiểm chứng entailment.
6. **Giới hạn embedding là rủi ro, không định luật tuyệt đối:** model có thể mã hóa số/thời gian/phủ định ở mức nào đó, nhưng similarity không bảo đảm phân biệt logic. Metadata và kiểm chứng bù phần còn thiếu.
7. **Các metric thấp không xác định một thủ phạm:** recall thấp có thể do nguồn/parse/chunk/budget/filter, không chỉ retriever; faithfulness thấp không chỉ do prompt. Tăng lọc có thể giảm recall. Faithfulness cao không chứng minh nguồn đúng hay còn hiệu lực.
8. **Quality thresholds không là chuẩn universal:** slide dùng recall 0,75 rồi 0,80; faithfulness 0,85 rồi 0,80. Cần ngưỡng dự án và ca safety/ACL không được che bởi trung bình cao. Không thấy nguồn chứng minh tỷ lệ “90% prototype” như một thống kê chung.
9. **TTFT không phải total latency:** budget 50+100+50+250 ms là minh họa đến token đầu, chưa tính sinh toàn output, hàng đợi hoặc lỗi. Hiện API trả sau structured output hoàn chỉnh.
10. **Cache ví dụ chưa đúng:** bảo hành và đổi trả không mặc định đồng nghĩa; semantic match cần giữ model/variant/year/phủ định/intent/ACL. TTL không tự vô hiệu hóa ngay tài liệu bị thu hồi.
11. **Quantization/MRL không có mức lợi ích bảo đảm:** slide benchmark thiếu model/phần cứng/sequence length/batch/dataset cụ thể để áp vào dự án. 1.536 → 128 chiều giảm phần vector nhỏ, nhưng giữ vector đầy đủ để rerank vẫn tốn bộ nhớ/storage; không tự suy ra tổng storage giảm >90%.
12. **CDC không bảo đảm cập nhật tức thì hoặc hết hallucination:** cần retry/order/idempotency/delete propagation và kiểm tra nguồn; index cũ không phải nguyên nhân duy nhất của câu trả lời sai.
13. **Alias/ACL/guardrails không bảo đảm an toàn tuyệt đối:** cần identity/filter integrity, version đồng bộ, rollout/rollback và adversarial tests; cache hit cũng phải thực thi quyền.
14. **Async telemetry/shadow vẫn tiêu thụ tài nguyên:** chuyển việc khỏi request không đồng nghĩa overhead bằng không hay hoàn toàn không ảnh hưởng production.
15. **Không cần bật mọi kỹ thuật:** Chroma hiện tại chưa có bằng chứng phải thay; các kỹ thuật advanced chỉ được ưu tiên khi lỗi/scale/dữ liệu yêu cầu.

## Ưu tiên sau khi đối chiếu tất cả slide

1. Thống nhất byte/token và đối soát 5 chunk có ít nhất một giới hạn; kiểm tra điều kiện bị mất trước generation.
2. Tách lỗi retrieval/provider/storage/timeout với thiếu nguồn, bổ sung Error Tree và dữ liệu diagnostic không lộ PII.
3. Duyệt tập độc lập, đo retrieval trước/sau budget và generation riêng; gắn version KB/model/prompt/dataset vào kết quả và CI gate.
4. Quản lý source lifecycle: hiệu lực, phiên bản, thay thế, thu hồi/xóa và freshness, không phê duyệt dựa vào fetch đơn thuần.
5. Benchmark baseline hiện tại với BM25+dense+RRF; nếu candidate đúng bị xếp thấp thì thử cross-encoder; nếu thiếu ngữ cảnh thì thử prepend/parent–child/Q&A theo ca lỗi.
6. Trước public production: identity thật, rate limiting, ownership, load test end-to-end, budget/cost và trace overhead. Tenant ACL bắt buộc trước private multi-tenant KB.
7. Chỉ sau đo tải/traffic mới thêm answer cache, async worker, atomic index rollout và shadow. MRL/ColBERT/SPLADE/ColPali/RAPTOR/GraphRAG/CDC lớn là lựa chọn có điều kiện.

## Bằng chứng trong dự án

- `D:/142.AI20K/P-142/scripts/process_chunks.py:15` — fixed-size ký tự và overlap.
- `D:/142.AI20K/P-142/scripts/refresh_agent_sources.py:18` — HTML blocks/table; `:122` — source sections; `:143` — candidate rewrite.
- `D:/142.AI20K/P-142/src/services/multilingual_embeddings.py:29` — truncation 256; `:34` — ONNX CPU.
- `D:/142.AI20K/P-142/src/services/rag_service.py:90` — weighted ranking; `:174` — retrieval; `:219` — broad exception; `:229` — context budget.
- `D:/142.AI20K/P-142/src/agents/context_manager.py:60` — byte counting; `:85` — unsafe/jailbreak regex.
- `D:/142.AI20K/P-142/src/agents/nodes/rag_node.py:23` — retrieval/generation/fallback.
- `D:/142.AI20K/P-142/src/services/agent_llm.py:56` — LLM call budget/circuit.
- `D:/142.AI20K/P-142/src/api/auth.py:20` — demo identity adapter.
- `D:/142.AI20K/P-142/src/api/customer.py` — staff actions/ownership.
- `D:/142.AI20K/P-142/src/services/tracer.py:24` và `src/services/session_store.py:222` — synchronous trace persistence.
- `D:/142.AI20K/P-142/scripts/run_agent_eval.py:43` — current grounded metric; `:214` — acceptance not approved.
- `D:/142.AI20K/P-142/.github/workflows/ci.yml:28` — pytest CI, chưa RAG quality gate.
- `D:/142.AI20K/P-142/docs/agent-quality-v2.md` — candidate build, rollback, freshness và giới hạn nghiệm thu.

## Nguồn kỹ thuật đối chiếu

- [Anthropic Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval): giảm retrieval failure 49%/67% trong thử nghiệm của họ, không phải mức cải thiện P-142.
- [Jina late chunking](https://github.com/jina-ai/late-chunking): encode ngữ cảnh trước pooling theo chunk spans.
- [RAPTOR paper](https://arxiv.org/abs/2401.18059): cây tóm tắt nhiều mức, khác parent–child sections.
- [Elastic RRF](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion): fusion theo thứ hạng.
- [Corrective RAG paper](https://arxiv.org/abs/2401.15884): retrieval evaluator và correction, không đồng nhất fallback chuyên viên.
- [RAGAS metrics](https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/): các metric retrieval/generation và factual correctness riêng.
- [Matryoshka Embeddings](https://www.sbert.net/examples/sentence_transformer/training/matryoshka/README.html): cấu trúc embedding phù hợp với truncation dimensions cần training thích hợp.
- [ONNX quantization](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html): kiểm tra accuracy/performance khi lượng tử hóa.
- [Qdrant embedding migration](https://qdrant.tech/documentation/tutorials-operations/embedding-model-migration/): candidate collection và atomic alias operations.
