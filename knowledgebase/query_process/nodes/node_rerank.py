from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger
from knowledgebase.tool.rerank_tool import text_rerank

class NodeRerank(NodeBase):
    """
    节点功能：使用 Cross-Encoder 模型对 RRF 后的结果进行精确打分重排。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_rerank"

    def process(self, state: QueryGraphState):
        rewritten_query = state.get("rewritten_query")
        rrf_chunks = state.get("rrf_chunks") or []
        web_search_docs = state.get("web_search_docs") or []

        # 之前的score不再关注了,因为重排序模型会重新精确打分
        merged_chunks = rrf_chunks + web_search_docs
        if not merged_chunks:
            logger.info("No chunks to rerank")
            return {"reranked_docs": []}
        # 把所有的chunk字典整理一致
        merged_chunks = [
            {
                "title": chunk.get("item_name") or chunk.get("title"),
                "content": chunk.get("content"),
                "url": chunk.get("url", ""),
                "source": chunk.get("source", ""),
            }
            for chunk in merged_chunks
        ]

        rerank_res = text_rerank(
            query=rewritten_query, 
            texts=[item.get("content") for item in merged_chunks], 
            limit=len(merged_chunks))
        print(json_format(rerank_res))

        # rerank的结果确实按照分数排序的，但是此时分数并没给到每个chunk，所以我们的先把分数对应下标给到每个chunk
        # 最后再把chunk的列表按照分数从高到低排序
        for item in rerank_res:
            merged_chunks[item["index"]]["score"] = item["score"]
        rerank_chunks = sorted(merged_chunks, key=lambda x: x["score"], reverse=True)

        # 要么就是chunk高的chunk不全

        # 动态 TopK：硬上限：最多取N条(<=10)
        RERANK_MAX_TOPK: int = 10
        # 最小 TopK：至少保留前N条(>=1, 且<=RERANK_MAX_TIOK)
        RERANK_MIN_TOPK: int = 3
        # 断崖阈值（相对）
        RERANK_GAP_RATIO: float = 0.25
        # 断崖阈值（绝对）
        RERANK_GAP_ABS: float = 0.20

        # 上面设定的最大和最小是我们心中所想，但是真实情况害的看最终数据有没有达到这个心中所想的可能
        use_max_topk = min(RERANK_MAX_TOPK, len(rerank_chunks))
        use_min_topk = min(RERANK_MIN_TOPK, use_max_topk)

        # 3, 10
        break_idx = use_max_topk
        for i in range(use_min_topk - 1, use_max_topk - 1): # 下标最后建议是为了防止列表越界
            current_score = rerank_chunks[i].get("score")
            next_score = rerank_chunks[i + 1].get("score")
        
            abs_gap = abs(current_score - next_score) # 求出来绝对差值
            ratio_gap = abs_gap / (current_score + 1e-6) # 求出相对差值

            if abs_gap > RERANK_GAP_ABS or ratio_gap > RERANK_GAP_RATIO:
                break_idx = i + 1
                break

        # 取前 break_idx条
        return {
            "reranked_docs": rerank_chunks[:break_idx]
        }


if __name__ == "__main__":
    node = NodeRerank()
    init_state = {
        "rewritten_query": "How to use Birth Flower Cufflinks?",
        "rrf_chunks": [
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Product Highlights\n\n• One pair — 2 cufflinks included\n\n• Choose from our 12-monthBirth Flower Collection\n\n• Each cufflink can feature its own birth flower\n\n• Create a matching pair or combine two meaningful months\n\n• Openwork floral design with a polished gold-plated finish\n\n• Approx. 15 mm / 0.59in face diameter",
                "part": 1,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340289,
                "title": "## Product Highlights",
                "score": 0.03225806451612903,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Product Overview\n\nPersonalized birth flower cufflinks designed to turn meaningful birth months into a distinctive gold-plated keepsake for the groom, husband, dad, or someone special.\n\nEach cufflink features an openwork floral design representing a meaningful birth month",
                "part": 1,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340287,
                "title": "## Product Overview",
                "score": 0.031746031746031744,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Please Note\n\n• This listing includes one pair of cufflinks.\n\n• Birth flower traditions can vary; this listing follows the fixed Birth Flower Collection shown above.\n\n• Matching and mixed-monthpairs are available at the same price.\n\n• The floral designs are fixed as shown in the listing photos.\n\n• Slight variations in appearance may occur due to lighting, viewing angle, and screen settings.",
                "part": 1,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340294,
                "title": "## Please Note",
                "score": 0.031009615384615385,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Birth Flowers\n\nChoose Birth Flower 1 (first cufflink) and Birth Flower 2 (second cufflink). Same month twice = matching pair; two months = mixed pair.\n\n<table><tr><td>Month</td><td>Flower</td></tr><tr><td>JAN</td><td>Carnation</td></tr><tr><td>FEB</td><td>Violet</td></tr><tr><td>MAR</td><td>Daffodil</td></tr><tr><td>APR</td><td>Daisy</td></tr><tr><td>MAY</td><td>Hawthorn</td></tr><tr><td>JUN</td><td>Rose</td></tr><tr><td>JUL</td><td>Lotus</td></tr><tr><td>AUG</td><td>Poppy</td></tr><tr><td>SEP</td><td>Morning Glory</td></tr><tr><td>OCT</td><td>Marigold</td></tr><tr><td>NOV</td><td>Chrysanthemum</td></tr><tr><td>DEC</td><td>Holly</td></tr></table>\n",
                "part": 0,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340296,
                "title": "## Birth Flowers",
                "score": 0.030536130536130537,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Pairing Options\n\n\n![The image displays a gold lotus-shaped cufflink. Accompanying text lists birth flowers (daisy, rose, lotus) for customizable mixed-pair cufflinks, allowing selection of same or different months at no extra charge.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/febdba03d8d265f2c991e83ca345aa821f9480b96b0a04792a69a9fecb0239be.jpg)",
                "part": 4,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340312,
                "title": "## Pairing Options",
                "score": 0.029850746268656716,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Pairing Options\n\n\n![The image shows a gold-colored cufflink designed as an openwork rose. Accompanying text describes pairing options for birth flower cufflinks: matching pairs (same flower), mixed pairs (different flowers), with examples including daisy, rose, and lotus.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/2577b19ef94050c905f50dfb50c7b71ff5f448e533121d9898689be3ef397257.jpg)",
                "part": 3,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340311,
                "title": "## Pairing Options",
                "score": 0.02877846790890269,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Pairing Options\n\n\n![The image shows a delicate, hand-drawn botanical illustration of a leafy stem in muted green tones on a light background. It appears to be part of a birth flower-themed product listing, likely for cufflinks, featuring flowers like rose and lotus, with text about ordering options and a birth flower chart.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/5d4508960915f9f4946546ce7b3c51ddba8e6d4bb2ceaebe27a97b817b31b71b.jpg)\n\nOrdering for a group?\n\nMessage us for multiple pairsor custom quantities.",
                "part": 7,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340315,
                "title": "## Pairing Options",
                "score": 0.02877846790890269,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Pairing Options\n\nMatching Pair\n\nMixed Pair\n\nSame birth flower on both cufflinks\n\n\n![The image displays a pair of gold-colored daisy-shaped cufflinks, featuring intricate petal designs and textured centers. They are presented as “Birth Flower Cufflinks – Gold, Groom,” with options for matching or mixedbirth flower pairs.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/a6bac1f039e278b13d8205fba4245ec467a30f3ab7666595d7ca509932e32f67.jpg)\n\nTwo different birth flowers",
                "part": 1,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340309,
                "title": "## Pairing Options",
                "score": 0.01639344262295082,
                "source": "local"
            },
            {
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340316,
                "title": "# Birth Flower Chart",
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "# Birth Flower Chart\n\nCarnation\n\nDaffodil\n\n\n![The image displays a birth flower chart with 12 months (Jan–Dec), each paired with its corresponding flower: Carnation, Violet, Daffodil, Daisy, Hawthorne, Rose, Lotus, Poppy, Morning Glory, Marigold, Chrysanthemum, and Holly—illustrated in elegant line drawings.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/6e31cdfd143047bd276c2e48c33f23a18252f34f9f7da13197f54544e4a4ac04.jpg)",
                "part": 1,
                "score": 0.01639344262295082,
                "source": "local"
            },
            {
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340314,
                "title": "## Pairing Options",
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Pairing Options\n\n\n![The image displays a simple line drawing of a lotus flower, centered on a textured beige background. It appears in a context listing birth flowers (e.g., Daisy, Rose, Lotus, Carnation, Daffodil), likely part of a birth flower chart or product ordering guide.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/096aaed53d6fa05ea238abd833245986583c134d267eeec230938521601249c9.jpg)\n\nLotus\n\nChoose the same month or two different months — mixed pairs at no extra charge.",
                "part": 6,
                "score": 0.015625,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Product Photos\n\n\n![The image displays five pairs of gold-plated floral cufflinks—peonies, daisies, roses, cherry blossoms, and lotuses—arranged on a wooden surface with wedding accessories: a navy bowtie, white pocket square, floral boutonniere, and cards labeled “Groom,” “Best Man,” “Groomsmen,” and an inspirational quote.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/602771f5089e7cf9d62c65c155a0e2a7ca8fb5d49ddcf5f638a9b4744cfd152f.jpg)\n\nBirth Flower Cufflinks – Gold, Groom — photo 3",
                "part": 3,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340307,
                "title": "## Product Photos",
                "score": 0.015151515151515152,
                "source": "local"
            },
            {
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "# Birth Flower Chart\n\nRose  \nPoppy  \nMorning Glory  \nDEC  \nMarigold  \nChrysanthemum  \nBirth Flower Cufflinks – Gold, Groom — photo 5",
                "part": 2,
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340317,
                "title": "# Birth Flower Chart",
                "score": 0.014705882352941176,
                "source": "local"
            },
            {
                "item_name": "Birth Flower Cufflinks Gold Groom",
                "id": 469819117954340313,
                "title": "## Pairing Options",
                "file_title": "001_4565343414_cufflinks-gold-groom",
                "content": "## Pairing Options\n\n\n![The image shows a line drawing of a rose. It appears in a context listing birth flowers—daisy, rose, and lotus—with text offering customizable pairs (same or different months)and group orders.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/6217cf0f87be1b737a106b341667d8d6fa2ee32a1f8fce7b05812aecca7cc8ae.jpg)\n\nRose",
                "part": 5,
                "score": 0.014705882352941176,
                "source": "local"
            }
        ],
        "web_search_docs": [
            {
                "title": "6 Meaningful Ways to Personalise Father's Day Cufflinks With ImpressArt Stamps - The Bench",
                "content": "Add a delicate yet meaningful flourish to Dad’s cufflinks by stamping them with his birth flower—or those of his children or partner—using the ImpressArt Signature 4mm Birth Flower Stamp Set.\n\nEach flowercarries symbolic meaning and is tied to a birth month, making it a subtle but elegant form of storytelling through design. Whether you stamp a single bloom on each cufflink or layer multiple designs, this is a stunning way to blend beauty with significance.\n\nBirth Flower Meanings (Examples): [...] “Home”\n “London”\n “The Dales”\n “St. Ives 2002” 50.2084° N, 5.4909° W\n “Tuscany Trip”\n\nWhy it works:\n\nPlaces hold powerful memories—where he grew up, gotmarried, or went on a life-changing trip. Stamping the name of a location transforms a cufflink into a tiny time capsule.\n\nDesign Tip: Combine the place name with a symbol (e.g. ImpressArt’s mountain, or wave stamp) to visually represent the memory.\n\n## 6. Floral Tribute: Stamp His Story with Birth Month Flowers [...] Use number stamps to stamp a date that means the world to him. Ideas include:\n\n The date he became a father\n A wedding anniversary\n Birthdays of his children\n Even a cheeky reference like “Est. 1981”\n\nWhy itworks:\n\nDates are memory anchors. They’re precise, emotionally rich, and elegantly simple when stamped. Choose either full date format (DD/MM/YY) or abbreviated for style (MM.YY) depending on space and design.",
                "url": "https://www.cooksongold.com/blog/inspiration/6-meaningful-ways-to-personalise-fathers-day-cufflinks-with-impressart-stamps",
                "source": "web"
            },
            {
                "title": "Complete Guide to Cufflinks: Styles, Usage & Care Tips- Love, Georgie",
                "content": "3. Rinsing and Drying\n\n Water: After cleaning witha solution, rinse your cufflinks under lukewarm water to remove any residue of the cleaning agents. Make sure to close the drain or place a sieve to avoid losing them.\n Dry Thoroughly: Immediately dry your cufflinks with another soft, lint-free cloth. Ensure they are completely dry before storing to avoidany moisture-related damage.\n\n4. Preventative Care [...] 1. Align the Cuff: If you're using a French cuff, fold the cuff back so that the holes of bothsides of the shirt cuff align.  \n2. Insert the Cufflink: Slide the cufflinkthrough the aligned holes. For swivel bar cufflinks, ensure the bar is perpendicular to the post as you insert it.  \n3. Secure the Cufflink: Once through, stabilize the swivel bar to lie flat against the cuff, locking the cufflink in place. [...] Cufflinks are not only about style but also about history and tradition, encapsulating centuries of menswear evolution. They are a link to the past and a nod to the sophistication of modern attire, making them essential items in the wardrobe of any well-dressed individual.\n\n## How To PutOn Cufflinks\n\nUnderstanding the Art of Attaching Cufflinks\n\nCufflinks may seem daunting at first, but they are actually quite simple to use once you know the steps. Here’s a quick guide:",
                "url": "https://lovegeorgie.com/blogs/gift-guides/custom-cufflinks-101",
                "source": "web"
            }
        ]
    }
    result = node(init_state)
    logger.info(json_format(result))