# Etsy 客服草稿助手：Chrome 插件 × RAG 知识库 设计与开发计划

> 版本：2026-10-10 · 项目：CedarSeaGoods / EtsyKnowledge
> 前提：RAG 查询流程已在 `~/PycharmProjects/knowledge_base` 跑通（eval_v2 32/33，意图分流 33/33），之后迁到 EtsyKnowledge。

---

## 0. 一句话结论

- **Etsy API 拿不到买家消息，也发不了消息。** Etsy 开放 API v3 没有任何站内信（Conversations）接口，读、写都没有。
- 所以**消息只能从卖家自己登录的 Etsy 网页上读**（Chrome 插件的页面脚本），**发送只能由人在网页上点 Send**。
- Etsy API 在这个方案里的作用是**补数据**：按订单号查发货状态/物流单号（售后草稿用），按 listing 拉商品信息（知识库同步用）。

```
买家消息 ──(只能从网页读)──▶ 插件 ──▶ 后端 RAG ──▶ 草稿 ──▶ 插件填进回复框 ──▶ 人点 Send
                                        ▲
                         Etsy API（订单、商品数据）
```

---

## 1. 拿到买家消息的三种途径

| 途径 | 怎么做 | 优点 | 缺点 | 定位 |
|---|---|---|---|---|
| **A. 插件读 Etsy 消息页 DOM** | 卖家打开某个对话时，页面脚本读出对话里的消息、商品卡片、订单卡片 | 信息最全（多轮历史、listing、订单号都在页面上）；不用额外授权 | Etsy 改版页面结构就要改选择器 | **主方案** |
| **B. 右键菜单 / 粘贴** | 选中买家消息 → 右键"生成草稿"，或在侧边栏粘贴 | 不依赖页面结构，永远能用 | 要手动选；拿不到 listing/订单上下文（可以手动选商品） | **兜底 + MVP 第一版** |
| **C. 读 Etsy 新消息通知邮件** | 用 Gmail API 读 Etsy 发给卖家的"新消息"通知邮件 | 可以后台批量预生成草稿 | 邮件里是否有完整消息、商品和订单信息**需要实测**；回复仍要回 Etsy 网页发 | 以后可选，不做第一版 |

**不要做**：模拟登录或爬虫抓 Etsy 消息、插件自动点 Send。Etsy 条款限制对网站的自动化访问；只读页面、填草稿、由人点击发送的风险要低得多（这是对条款的理解，不是法律意见，正式使用前请自己读一遍 [Etsy API Terms](https://www.etsy.com/legal/api-archived/)）。

---

## 2. 整体架构

```
┌──────────────── Chrome（卖家已登录 etsy.com）────────────────┐
│                                                              │
│  content script（只注入 Etsy 消息页）                         │
│   ├─ 读：当前对话的消息列表、买家名、商品卡片(listing_id)、     │
│   │      订单卡片(receipt_id)、对话 ID                         │
│   └─ 写：把选中的草稿填进回复输入框（不点发送）                 │
│                                                              │
│  side panel（侧边栏 UI）                                      │
│   ├─ 显示：意图、草稿、依据的资料片段、"需要人工"提示          │
│   └─ 按钮：生成草稿 / 重新生成 / 填入回复框 / 复制             │
│                                                              │
│  service worker（后台）                                       │
│   ├─ 调后端 /draft（带 token）                                 │
│   ├─ 右键菜单"用选中文字生成草稿"                              │
│   └─ 上报"草稿 → 实际发出"记录                                 │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS + Bearer token
┌───────────────────────────▼──────────────────────────────────┐
│ 后端（现有 query_service，FastAPI，8001）                     │
│  POST /draft      ← 新增：一次性 JSON 返回草稿                 │
│  POST /feedback   ← 新增：记录草稿与实际发出的版本             │
│  POST /query + GET /stream/{task_id}（保留，给 chat.html 用） │
│                                                              │
│  LangGraph 查询流程（已有）：                                  │
│   node_intent_route → presale/shop_general → 商品确认 → 检索 → │
│                       rerank → 回答                           │
│                     → order_status/cancel/delay/issue → 售后   │
│                       （新：先用 Etsy API 查订单再生成）        │
│                     → feedback → 好评模板                      │
│                                                              │
│  Etsy API 客户端（新增）：receipts、listings；OAuth token 存储 │
│  Milvus / Mongo / MinIO（已有）                               │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. 和现有 RAG 的对接点（大部分已经铺好了）

| 插件拿到的信息 | 传给后端的方式 | 对应现有流程 | 现状 |
|---|---|---|---|
| 当前对话所在商品的 listing 标题 + id | 问题前缀 `[Message sent from the Etsy listing: {title} (#{listing_id})]` | node_intent_route 判断"从商品页发来≠已下单"；node_item_name_confirm 去掉 `(#id)` 后直接确认商品 | ✅ eval_v2 就是按这个格式测的 |
| Etsy 对话 ID | `session_id = "etsy_" + conversation_id` | Mongo 历史对话 → 多轮追问（"How long is it?"）沿用上一轮的商品 | ✅ 已支持，多轮题 M1/M2 已验证 |
| 买家最新一条消息 | `query` | 原样进入流程 | ✅ |
| 对话里更早的消息（插件第一次打开该对话时） | `thread` 字段，后端写入 Mongo 历史后再跑 | 历史对话 | ⚠️ 需新增：把页面上的历史"补录"进 Mongo，否则第一次只看得到最新一条 |
| 订单号 receipt_id | `receipt_id` 字段 | 售后意图（order_status / cancel_change / delay / issue） | ⚠️ 需新增：用 Etsy API 查订单，把状态写进 prompt，替代"请发订单号"模板 |
| 买家名 | `buyer_name` | 草稿称呼（"Hi Nicole,"） | ⚠️ 需新增：prompt 里加一个占位 |

### 3.1 售后意图的升级（价值最大的一块）

真实客服记录里，#3 #4 #5 #6 都是售后（发货更新、改 ship-by 日期、取消退款、安抚）。现在的转人工模板只会说"请发订单号"。有了 receipt_id 以后：

```
order_status + receipt_id
  → Etsy API getShopReceipt(receipt_id)
  → 拿到：是否已发货、发货时间、承运商、物流单号、预计送达
  → 生成草稿："Hi Nicole, your cufflinks shipped on Sep 25 via USPS, tracking 9400… 🤍"
没有 receipt_id → 仍走现有模板（请发订单号）
cancel_change / issue → 仍然只出草稿 + 标记"需要人工"（退款、补发必须人来决定）
```

---

## 4. 后端：新增接口

### 4.1 `POST /draft`

请求：
```json
{
  "conversation_id": "1234567890",
  "buyer_name": "Nicole",
  "message": "Hi! When will my cufflinks ship?",
  "thread": [
    {"role": "buyer",  "text": "...", "ts": "2026-10-08T10:00:00Z"},
    {"role": "seller", "text": "...", "ts": "2026-10-08T11:00:00Z"}
  ],
  "listing": {"listing_id": "4565343414", "title": "Birth Flower Cufflinks – Gold, Groom"},
  "receipt_id": "3456789012"
}
```

响应：
```json
{
  "draft": "Hi Nicole! ...",
  "intent": "order_status",
  "needs_human": false,
  "item_names": ["Birth Flower Cufflinks – Gold, Groom"],
  "sources": [{"title": "## How long will it take to ship my order?", "snippet": "...", "score": 0.80}],
  "order": {"is_shipped": true, "shipped_at": "2026-09-25", "tracking_code": "9400..."},
  "latency_ms": 8200
}
```

实现要点（基于 `atguigu/web/api/query_service.py` 现有写法）：
```python
class DraftRequest(BaseModel):
    conversation_id: str
    message: str
    buyer_name: str | None = None
    thread: list[dict] = []
    listing: dict | None = None
    receipt_id: str | None = None

@app.post("/draft")
def draft(req: DraftRequest, authorization: str = Header(None)):
    check_token(authorization)                       # 简单 Bearer token
    session_id = f"etsy_{req.conversation_id}"
    backfill_history(session_id, req.thread)         # 第一次打开对话时把页面历史补进 Mongo（按 ts 去重）
    query = req.message
    if req.listing:
        query = f"[Message sent from the Etsy listing: {req.listing['title']} (#{req.listing['listing_id']})]\n{query}"
    init_state = {"original_query": query, "session_id": session_id,
                  "task_id": str(uuid.uuid4()), "receipt_id": req.receipt_id,
                  "buyer_name": req.buyer_name, "is_stream": False}
    result = {}
    for chunk in KBQueryWorkflow.create_and_run(init_state, stream=True):   # 同步跑完，收集各节点输出
        for node_name, node_result in chunk.items():
            if isinstance(node_result, dict):
                result.update(node_result)
    return {"draft": result.get("answer", ""), "intent": result.get("intent"),
            "needs_human": result.get("intent") in ("cancel_change", "issue"),
            "item_names": result.get("item_names", []),
            "sources": summarize(result.get("reranked_docs", []))}
```

> `/draft` 是同步接口（一题 ~9 秒），插件侧显示"生成中…"即可。以后想要逐字显示，再改成和 `/query` 一样的 task_id + SSE。

### 4.2 `POST /feedback`

插件在人点击 Send 前（监听发送按钮的 click）上报：
```json
{"conversation_id": "...", "draft": "AI 原稿", "sent": "实际发出的文字", "intent": "presale", "ts": "..."}
```
存 Mongo `etsy_kb.draft_feedback`。用途：
1. **独立测试集**：真实买家消息 + 实际发出的回复 = 参考答案，不再拿 eval_v2 调 prompt（避免"拿考题当教材"）。
2. **Sherry 口吻 few-shot**：挑改动小、买家反馈好的回复。
3. **效果指标**：草稿被采纳率、平均编辑距离、按意图统计。

### 4.3 安全
- 后端只认 `Authorization: Bearer <token>`；token 放在插件的 options 页里，存 `chrome.storage.local`。
- CORS：现在是 `allow_origins=["*"]`，上线后改成只允许 `chrome-extension://<插件ID>`。
- 买家姓名、订单信息属于个人数据：日志里不打全量，`draft_feedback` 只给自己人看。

---

## 5. Etsy API 部分（只读）

| 用途 | 接口（v3） | 权限 scope |
|---|---|---|
| 售后草稿查订单状态、物流 | `getShopReceipt`（`/v3/application/shops/{shop_id}/receipts/{receipt_id}`），返回里有发货/shipments 信息 | `transactions_r` |
| 订单里买的是哪个商品 | `getShopReceiptTransactionsByReceipt` | `transactions_r` |
| 知识库同步（商品改了就重导） | `getListingsByShop`、`getListing`（看 `updated_timestamp`） | `listings_r` |
| 新订单提醒（可选） | Etsy webhooks（如 order.paid） | — |

接入步骤：
1. 在 Etsy 开发者后台注册应用，拿 keystring（个人自用 app，审批需要等）。
2. OAuth 2.0 授权码 + PKCE 流程，店主授权一次，拿 access_token / refresh_token，存后端（加密或至少不进 git）。
3. 后端封装 `etsy_client.py`：自动刷新 token、限速、错误重试。
4. 新增 LangGraph 节点 `node_order_lookup`：售后意图且有 receipt_id 时调用，结果写进 state，ANSWER_PROMPT 增加【订单信息】一段。

> 接口名、字段名和请求头格式以 [Etsy 官方开发文档](https://developers.etsy.com/documentation/) 为准，写代码前逐个核对。

---

## 6. Chrome 插件（Manifest V3）

### 6.1 目录结构
```
etsy-reply-assistant/
├── manifest.json
├── src/
│   ├── background.js        # service worker：调后端、右键菜单、消息中转
│   ├── content.js           # 注入 Etsy 消息页：读对话、填回复框、监听 Send
│   ├── selectors.js         # 所有 DOM 选择器集中在这里（Etsy 改版只改这个文件）
│   ├── sidepanel.html/.js   # 侧边栏 UI
│   └── options.html/.js     # 配置后端地址和 token
└── icons/
```

### 6.2 manifest.json（草稿）
```json
{
  "manifest_version": 3,
  "name": "CedarSeaGoods Reply Assistant",
  "version": "0.1.0",
  "permissions": ["sidePanel", "storage", "contextMenus", "activeTab"],
  "host_permissions": ["https://www.etsy.com/*", "http://127.0.0.1:8001/*"],
  "background": {"service_worker": "src/background.js", "type": "module"},
  "side_panel": {"default_path": "src/sidepanel.html"},
  "options_page": "src/options.html",
  "content_scripts": [{
    "matches": ["https://www.etsy.com/messages/*", "https://www.etsy.com/your/conversations/*"],
    "js": ["src/selectors.js", "src/content.js"],
    "run_at": "document_idle"
  }]
}
```
> `matches` 里的消息页 URL **需要在你们登录后的 Etsy 上确认**，上面两个是待验证的猜测。后端搬到云上后，`host_permissions` 换成正式域名。

### 6.3 content.js 核心逻辑（伪代码）
```js
// 1. 读当前对话
function readConversation() {
  const S = window.ETSY_SELECTORS;                       // 来自 selectors.js
  const msgs = [...document.querySelectorAll(S.messageItem)].map(el => ({
    role: el.matches(S.fromSeller) ? "seller" : "buyer",
    text: el.querySelector(S.messageText)?.innerText.trim() ?? "",
    ts:   el.querySelector(S.messageTime)?.getAttribute("datetime") ?? ""
  }));
  const listingLink = document.querySelector(S.listingCardLink)?.href ?? "";
  const receiptLink = document.querySelector(S.receiptCardLink)?.href ?? "";
  return {
    conversation_id: location.pathname.split("/").pop(),
    buyer_name: document.querySelector(S.buyerName)?.innerText.trim(),
    message: [...msgs].reverse().find(m => m.role === "buyer")?.text ?? "",
    thread: msgs,
    listing: listingLink ? { listing_id: listingLink.match(/listing\/(\d+)/)?.[1],
                             title: document.querySelector(S.listingCardTitle)?.innerText.trim() } : null,
    receipt_id: receiptLink.match(/(\d{6,})/)?.[1] ?? null
  };
}

// 2. 填草稿（不点发送）
function fillReply(text) {
  const box = document.querySelector(window.ETSY_SELECTORS.replyBox);
  box.focus();
  box.value = text;                                      // 若是 contenteditable，用 innerText
  box.dispatchEvent(new Event("input", { bubbles: true })); // 让 Etsy 的前端框架感知到变化
}

// 3. 记录实际发出的内容
document.addEventListener("click", e => {
  if (e.target.closest(window.ETSY_SELECTORS.sendButton)) {
    chrome.runtime.sendMessage({ type: "SENT", sent: document.querySelector(window.ETSY_SELECTORS.replyBox).value });
  }
}, true);

chrome.runtime.onMessage.addListener((msg, _, reply) => {
  if (msg.type === "READ") reply(readConversation());
  if (msg.type === "FILL") fillReply(msg.text);
});
```

### 6.4 background.js 核心逻辑
```js
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: "draft", title: "用选中文字生成回复草稿", contexts: ["selection"] });
});
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  await chrome.sidePanel.open({ tabId: tab.id });
  const draft = await callDraft({ conversation_id: "manual_" + Date.now(), message: info.selectionText });
  chrome.runtime.sendMessage({ type: "DRAFT_READY", draft });
});
async function callDraft(payload) {
  const { apiBase, token } = await chrome.storage.local.get(["apiBase", "token"]);
  const r = await fetch(`${apiBase}/draft`, { method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
    body: JSON.stringify(payload) });
  return r.json();
}
```

### 6.5 侧边栏 UI
```
┌─────────────────────────────┐
│ Nicole · 售后·订单状态        │
│ 商品：Birth Flower Cufflinks │
│ 订单：已发货 9/25 USPS 9400… │
├─────────────────────────────┤
│ [草稿文本框，可直接编辑]      │
│                             │
├─────────────────────────────┤
│ ⚠ 需要人工确认（退款/补发）    │  ← needs_human 时显示
│ 依据：▸ How long will it…   │  ← 可展开看切片
├─────────────────────────────┤
│ [生成草稿] [重新生成] [填入] [复制] │
└─────────────────────────────┘
```

---

## 7. 部署

| 阶段 | 后端位置 | 适用 |
|---|---|---|
| 开发/自用 | 你的 Mac，`http://127.0.0.1:8001`，Docker 跑 Milvus/Mongo/MinIO | 只有你的 Mac 上的 Chrome 能用；Mac 要开着、服务要启动 |
| 合伙人也要用 | 一台云服务器（2C4G 起，Milvus standalone 吃内存，建议 4–8G）+ HTTPS + token | 两个人各自的 Chrome 都能连 |

注意：大模型 / rerank 走 DashScope，网络已断过三次（10-09 11:51、12:43，10-10 09:44）；`/draft` 要有超时（30 秒）和一次重试，失败时插件显示"生成失败，可重试"，不要卡住。

---

## 8. 开发里程碑

| # | 内容 | 产出 | 估计 | 依赖 |
|---|---|---|---|---|
| M1 | 后端 `/draft`（JSON）+ token 校验 | curl 能拿到草稿 | 0.5 天 | 现有 query_service |
| M2 | 插件 MVP：侧边栏粘贴消息 / 右键选中 → 草稿 → 复制 | **可以开始日常用** | 0.5–1 天 | M1 |
| M3 | 看真实 Etsy 消息页结构，写 `selectors.js`；content script 读对话、填回复框 | 一键读对话 + 填草稿 | 1–2 天 | 需要在登录后的消息页查看 DOM（可用 Claude in Chrome 协助） |
| M4 | `/feedback` + 插件监听 Send | 草稿→实发数据开始积累 | 0.5 天 | M3 |
| M5 | Etsy API：注册应用、OAuth、`node_order_lookup`；售后草稿带真实发货信息 | 售后草稿可直接用 | 1–2 天 + 审批等待 | Etsy 开发者账号 |
| M6 | 商品同步：定期拉 listings，`updated_timestamp` 变了 → 重新生成 MD/PDF → 顺序导入 | 知识库不过期 | 1–2 天 | M5 的 OAuth |
| M7 | 后端上云 + HTTPS | 合伙人也能用 | 1 天 | — |

**先做 M1 + M2**：两步做完就能在真实回复里用起来，并且开始暴露真实问题。M3 之后的每一步都可以单独上线。

---

## 9. 测试

- **后端**：`run_eval.py` 加一个 `--endpoint draft` 模式，用 eval_v2 的 33 题走 `/draft`，结果应与 `/query` 一致（回归测试）。
- **插件**：在 Etsy 消息页手动测 10 个真实对话（售前、售后、好评、多轮各几条），检查读对话 / listing / 订单号是否正确、填框后 Etsy 能否正常发送。
- **真实效果**：M4 上线两周后，看 `draft_feedback`：采纳率（几乎没改就发）、平均修改量、哪些意图改得最多 → 决定下一步优化哪里。

---

## 10. 待确认问题

1. Etsy 卖家消息页的真实 URL 和 DOM 结构（商品卡片、订单卡片是否在对话页里可见、回复框是 textarea 还是 contenteditable）。
2. Etsy 新消息通知邮件里有没有完整的消息正文和商品/订单信息（决定途径 C 值不值得做）。
3. 平时谁回消息、用哪台电脑 → 决定 M7 要不要提前。
4. Etsy 开发者应用的审批时间、个人自用 app 的限额。
5. 售后里哪些情况允许草稿直接给出结论（比如已发货给单号），哪些必须"需要人工"（退款、补发、改价）——需要店主定规则。
