# 掌柜智库 × CedarSeaGoods 实施计划

Oct 8, 2026 · @Zhi Dong

## 目标与原则

用 CedarSeaGoods 的真实商品，把掌柜智库课程的导入流程和查询流程完整跑一遍。目标是学习，不是尽快上线。

- **1 对 1 跟课程**：每个节点都保留，代码尽量不改。课程原本的输入是"产品手册 PDF"，这里就给每个 listing 做一份产品手册 PDF
- **只做三处最小改动**（见下文），其余全部照课程走
- **先做 10 个商品试点，再扩到全店 128 个**：试点阶段专门挑容易混淆的商品，用来检验"产品确认"节点
- **每个节点都留下中间结果**：这些记录就是回答课程 8 道面试题的素材

## 课程节点对照表

两条流程的每个节点都保留；只有「答案生成」这一个节点要改提示词。

**导入流程（import\_process）**

| 课程天数 | 节点 | 课程里的输入 | 对应到店铺 | 这一步要观察什么 |
| --- | --- | --- | --- | --- |
| day02 | 入口节点 | 上传 PDF/MD | 上传商品手册 PDF | 是否按后缀正确路由 |
| day02 | PDF 转 MD（MinerU） | 设备手册 | 商品手册（干净版）+ listing 页面打印的 PDF（脏数据） | 多级标题能否保留 |
| day03–04 | MD 图片处理 | 手册插图 | 尺寸图、字体选项、颜色卡、实拍图 | 图片里的文字能否被检索到 |
| day05 | 文档切片 | 按标题切 + 长切 | 按手册里固定的 `##` 小节切 | chunk 大小和 overlap 怎么设 |
| day07 | 主体识别 | LLM 从前 5 个 chunk 中识别 item\_name | 同上，手册首行写规范商品名 | 近似商品会不会被识别成同一个名字 |
| day06–08 | 向量化 + 写入 Milvus | BGE-M3 稠密/稀疏向量 | 不变 | 不变 |

**查询流程（query\_process）**

| 课程天数 | 节点 | 对应到店铺 | 这一步要观察什么 |
| --- | --- | --- | --- |
| day09 | 产品确认（阈值 0.85 / 0.6） | 买家问 "the gold cufflinks"，店里有两款 | 是否走到"候选"分支并反问买家 |
| day10 | 向量检索 | 不变 | 不变 |
| day10 | HyDE | 买家口语化的问题 | 开启和关闭 HyDE 的效果对比 |
| day10 | 联网搜索（MCP） | 快递节日截单日、Etsy Purchase Protection、各国关税 | 网上信息和店铺规则冲突时怎么处理 |
| day10 | RRF 融合 | 不变 | 去掉 RRF 后排序会怎样变化 |
| day11 | Rerank + 断崖检测 | 不变 | 断崖在哪里截断、为什么 |
| day14 | 答案生成 + Mongo 历史 + 图片 | 用英文、按店铺客服的语气回答，答案后附商品图 | 多轮对话里的商品能否跟住上下文 |
| day12–14 | FastAPI + SSE + 前端 | import.html 上传文件，chat.html 做对话 | 不变 |

## 三处最小改动

只有这三处偏离课程，而且都不碰检索代码。

1. **店铺通用政策写进每份手册的附录**：在手册最后加一节 `## Shop Policies & FAQ`。课程的检索带了 `item_name in item_names` 过滤，如果把店铺 FAQ 单独存成一个文档，它永远不会被检索到。这样做的代价是同一份 FAQ 重复存储了 128 遍。
2. **答案生成的提示词补一句要求**：用英文回复买家，语气温和；当网上搜到的信息和店铺规则冲突时，以店铺规则为准；不承诺退款、补发、具体的到货日期。其余提示词保留中文。
3. **运行环境换成 Mac**：BGE-M3 的 `bge_device` 设为 `cpu` 或 `mps`，`bge_fp16` 设为 `False`。Milvus、Mongo、MinIO 可以照课程装在虚拟机里，也可以直接用 Mac 上的 Docker，但 docker-compose 配置保持不变。

价格不写进手册。店里长期在做 40%–50% 的折扣，写进去很快就过时了；买家问价格时，引导对方以 listing 页面上的价格为准。

## 分阶段执行计划

共 7 个阶段。Phase 0 和 Phase 1 互不依赖，可以同时开始；从 Phase 2 起按顺序推进。

| 阶段 | 做什么 | 产出 | 验收标准 | 谁做 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 0 环境就绪 | 用 Docker 启动 Milvus/Mongo/MinIO；BGE-M3 在 CPU 上跑通；配置百炼 key 和 MinerU token | 可用的 .env、跑起来的中间件 | 用课程自带的示例 PDF，导入和查询两条流程都能跑通 | 你 | Not started |
| 1 收集试点商品数据 | 抓取 10 个商品 listing 公开页面的内容；从后台抄下 shipping profile 和 return policy；补充内部知识 | 每个商品一份 MD 草稿，缺的信息用 TODO 占位 | 所有 TODO 都已填完 | Claude 抓取，你们补充 | Not started |
| 2 生成 PDF 手册 | 按模板生成 10 份干净版 PDF；另外从浏览器打印 3 份 listing 页面 PDF | 13 份 PDF | MinerU 转出的 MD 保留了多级标题 | Claude | Not started |
| 3 导入 | 通过 import.html 逐份上传，并保存每个节点的中间结果 | MD、图片摘要、chunks.json、item\_name 表 | Milvus 里存了 10 个互不相同的 item\_name | 你 | Not started |
| 4 修改查询侧 + 跑基线 | 完成三处最小改动；编写评测集；跑第一次基线 | eval.csv 及基线结果 | 30 道题都有标注好的对错 | Claude 出题，你来跑 | Not started |
| 5 对照实验 | 逐个开关 HyDE、RRF、Rerank、联网搜索；对比干净版和脏数据 PDF | 实验记录 | 课程 8 道面试题都能用自己的数据回答 | 你 | Not started |
| 6 扩展到 128 个商品 | 用脚本批量调用上传接口；重跑评测集做回归 | 全店知识库 | 评测结果不低于试点阶段 | Claude 写脚本，你来跑 | Not started |

## 10 个试点商品

挑了 3 组容易混淆的商品（共 7 个），再加 3 个各有考察点的商品。规范商品名是草拟的，可以直接改。

| # | Listing | 规范商品名（草拟） | 为什么选它 |
| --- | --- | --- | --- |
| 1 | [4565343414](https://www.etsy.com/listing/4565343414) | Birth Flower Cufflinks – Gold, Groom | 混淆组 A：同样是金色 birth flower 袖扣 |
| 2 | [4574931348](https://www.etsy.com/listing/4574931348) | Birth Flower Cufflinks – Gold, for Dad | 混淆组 A |
| 3 | [4543886236](https://www.etsy.com/listing/4543886236) | Muslin Car Seat Canopy – Classic | 混淆组 B：三款 canopy，这款有买家评价 |
| 4 | [4547942371](https://www.etsy.com/listing/4547942371) | Muslin Car Seat Canopy – Baby Girl | 混淆组 B |
| 5 | [4567079693](https://www.etsy.com/listing/4567079693) | Muslin Car Seat Canopy – Ruffle Bow | 混淆组 B |
| 6 | [4580818745](https://www.etsy.com/listing/4580818745) | A6 Journal Set – Travel | 混淆组 C：同一个商品上了两个 listing，写了两版文案 |
| 7 | [4580819257](https://www.etsy.com/listing/4580819257) | A6 Journal Set – Graduation | 混淆组 C |
| 8 | [4568658292](https://www.etsy.com/listing/4568658292) | Baby's First Christmas Blanket | 节日时效问题，考察联网搜索 |
| 9 | [4581501374](https://www.etsy.com/listing/4581501374) | Pet Memorial Keychain – Raw Brass | 带情感色彩的话题，考察回复语气 |
| 10 | [4584685484](https://www.etsy.com/listing/4584685484) | Gemstone Name Bracelet | 涉及尺寸和材质，考察图片摘要 |

## PDF 手册模板

每份手册使用相同的标题层级。为了让主体识别节点读前 5 个 chunk 就能认出商品，第一页要写上规范商品名和 listing ID。

```markdown
# Birth Flower Cufflinks – Gold, Groom (Listing 4565343414)
## Product Overview
## Personalization Options
### Font Options        ← 放字体选项图
### Character Limits
## Materials & Dimensions   ← 放尺寸图
## Processing & Shipping
### Production Time
### US Shipping
### International Shipping & Customs
## Returns & Exchanges
## Care Instructions
## Shop Policies & FAQ      ← 店铺通用内容，每份手册都一样
```

各部分内容的来源：

- **公开页面**：标题、描述、variations、个性化说明、商品图片、页面上显示的处理时间
- **后台**：shipping profile（各目的地运费、加急选项）、return policy
- **内部知识**：哪个生产伙伴制作（香港纸品 / 洛杉矶刺绣）、实际工期、尺寸、材质、洗涤说明、是否提供 proof、节日截单日

生成方式：先写 MD，再转成带图片的 PDF，然后交给 MinerU 解析。这个"MD → PDF → MD"的来回本身没有业务意义，只是为了练 MinerU 这个节点；所以还要做 3 份从浏览器直接打印的 listing 页面 PDF，用来对比解析质量。

## 评测集与对照实验

评测集共 30 道题，每类题对应一个要重点观察的节点。题目优先从历史买家消息里挑，不够的再自己编。

| 题型 | 题数 | 示例 | 期望行为 | 重点观察的节点 |
| --- | --- | --- | --- | --- |
| 模糊商品 | 6 | Do the gold cufflinks come in silver? | 走到"候选"分支，反问买家问的是哪一款 | 产品确认 |
| 答案只在图片里 | 4 | What fonts can I choose for the blanket? | 答出图片里列的字体名 | 图片处理 |
| 商品规则与 FAQ 冲突 | 4 | Can I return the embroidered blanket if I change my mind? | 给出与 listing 规则一致的答案，并说明例外情况 | 切片 + Rerank |
| 时效问题 | 5 | Will it arrive before Christmas if I order Dec 15? | 店铺工期加上快递截单日，但不承诺具体日期 | 联网搜索 |
| 口语化 / 拼写错误 | 5 | hey can u put my dogs name on the keychain?? | 正确找到对应的个性化说明 | HyDE |
| 多轮对话 | 3 | 先问 canopy，再问 "how long does it take?" | 第二轮仍然认得是哪个商品 | 产品确认 + Mongo 历史 |
| 知识库之外 | 3 | Do you sell wedding dresses? | 诚实地说没有这类商品，不编造 | 产品确认（无效分支） |

每道题都记录：产品确认的分数、两路检索各自的前 5 条结果、RRF 后的排序、断崖在第几条截断、最终答案的对错。

对照实验（每次只改一个变量，用同一套 30 题重跑）：

1. 关闭 HyDE
2. 去掉 RRF，只保留向量检索这一路
3. 关闭 Rerank，固定取 top 5（对应面试题 8）
4. 关闭联网搜索
5. 把 3 个商品的手册换成脏数据 PDF
6. 对比不同的 chunk 大小（对应面试题 5）

## 风险与已知限制

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| Etsy API 不开放消息的收发接口 | 做不到自动回复买家 | 在 chat.html 里生成回复，人工复制发送 |
| 公开页面上的运费是按浏览者地址算的 | 抓下来的运费不准 | 运费一律以后台的 shipping profile 为准 |
| 百炼的 web search MCP 偏向中文网页 | 英文的快递截单信息可能搜不到 | 先按课程原样跑；搜不到时把这个问题记入实验记录 |
| BGE-M3 在 Mac 上用 CPU 跑 | 导入比课程慢 | 10 个商品这个量可以接受；扩到 128 个时可以改用 mps |
| 同一份 FAQ 重复存了 128 遍 | 检索到的 FAQ 片段可能来自别的商品文档 | 有 item\_name 过滤，影响不大；在实验里观察有没有发生 |
| 价格和折扣经常变 | 答案里的价格可能过时 | 价格不写进手册 |

## 待决定事项

- [ ] 先做哪一步：Phase 0（环境）还是 Phase 1（抓取数据）。两者互不依赖，可以同时进行
- [ ] 10 个试点商品和规范商品名是否确认
- [ ] 中间件装在哪里：照课程装在 CentOS 虚拟机里，还是直接用 Mac 上的 Docker
- [ ] 哪些内部知识由谁来补充（生产伙伴、工期、个性化限制）
- [ ] 能否导出历史买家消息，用来做评测集
