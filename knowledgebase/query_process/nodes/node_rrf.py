from knowledgebase.query_process.base import NodeBase
from knowledgebase.query_process.state import QueryGraphState
from knowledgebase.tool.json_format import json_format
from knowledgebase.tool.logger import logger

class NodeRrf(NodeBase):
    """
    节点功能：Reciprocal Rank Fusion
    将本地多路召回的结果（向量、HyDE）进行加权融合排序。
    Web结果没有chunk id，也不应和店铺自己的商品资料同等排名，留到rerank阶段再加入。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_rrf"

    def process(self, state: QueryGraphState):
        embedding_chunks = state.get("embedding_chunks") or []
        hyde_embedding_chunks = state.get("hyde_embedding_chunks") or []

        # 设定权重值，就是分子可以自己定
        weighted_embedding_chunks = [
            (embedding_chunks, 1),
            (hyde_embedding_chunks, 1)
        ]

        # 我们的目的是想把两个列表当中的chunk放到一个容器里面
        # 如果有相同的，那么这个容器当中放一个就可以
        # 每个chunk都要有自己的排名分数，相同的chunk分数要加起来

        rrf_dict = {} # 以chunk的id为键，以整个chunk为值
        for chunks, weight in weighted_embedding_chunks:
            for idx, chunk in enumerate(chunks, start=1):
                score = weight / (60 + idx)
                chunk_id = chunk.get("id")

                if chunk_id in rrf_dict:
                    # 有重复
                    rrf_dict[chunk_id]["score"] += score
                else:
                    # 没有重复，复制一份再改分数，不覆盖上游chunk原来的相似度分数
                    rrf_dict[chunk_id] = {**chunk, "score": score}
        
        rrf_chunks = sorted(rrf_dict.values(), key=lambda x: x["score"], reverse=True) # 不影响原地
        return {
            "rrf_chunks": rrf_chunks
        }

if __name__ == "__main__":
    node = NodeRrf()
    init_state = {
        "embedding_chunks": [
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\nMatching Pair\n\nMixed Pair\n\nSame birth flower on both cufflinks\n\n\n![The image displays a pair of gold-colored daisy-shaped cufflinks, featuring intricate petal designs and textured centers. They are presented as “Birth Flower Cufflinks – Gold, Groom,” with options for matching or mixedbirth flower pairs.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/a6bac1f039e278b13d8205fba4245ec467a30f3ab7666595d7ca509932e32f67.jpg)\n\nTwo different birth flowers",
            "part": 1,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340309,
            "title": "## Pairing Options",
            "score": 0.7478879690170288,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Product Highlights\n\n• One pair — 2 cufflinks included\n\n• Choose from our 12-monthBirth Flower Collection\n\n• Each cufflink can feature its own birth flower\n\n• Create a matching pair or combine two meaningful months\n\n• Openwork floral design with a polished gold-plated finish\n\n• Approx. 15 mm / 0.59in face diameter",
            "part": 1,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340289,
            "title": "## Product Highlights",
            "score": 0.746461033821106,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Product Overview\n\nPersonalized birth flower cufflinks designed to turn meaningful birth months into a distinctive gold-plated keepsake for the groom, husband, dad, or someone special.\n\nEach cufflink features an openwork floral design representing a meaningful birth month",
            "part": 1,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340287,
            "title": "## Product Overview",
            "score": 0.7430075407028198,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Please Note\n\n• This listing includes one pair of cufflinks.\n\n• Birth flower traditions can vary; this listing follows the fixed Birth Flower Collection shown above.\n\n• Matching and mixed-monthpairs are available at the same price.\n\n• The floral designs are fixed as shown in the listing photos.\n\n• Slight variations in appearance may occur due to lighting, viewing angle, and screen settings.",
            "part": 1,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340294,
            "title": "## Please Note",
            "score": 0.7429928183555603,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Birth Flowers\n\nChoose Birth Flower 1 (first cufflink) and Birth Flower 2 (second cufflink). Same month twice = matching pair; two months = mixed pair.\n\n<table><tr><td>Month</td><td>Flower</td></tr><tr><td>JAN</td><td>Carnation</td></tr><tr><td>FEB</td><td>Violet</td></tr><tr><td>MAR</td><td>Daffodil</td></tr><tr><td>APR</td><td>Daisy</td></tr><tr><td>MAY</td><td>Hawthorn</td></tr><tr><td>JUN</td><td>Rose</td></tr><tr><td>JUL</td><td>Lotus</td></tr><tr><td>AUG</td><td>Poppy</td></tr><tr><td>SEP</td><td>Morning Glory</td></tr><tr><td>OCT</td><td>Marigold</td></tr><tr><td>NOV</td><td>Chrysanthemum</td></tr><tr><td>DEC</td><td>Holly</td></tr></table>\n",
            "part": 0,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340296,
            "title": "## Birth Flowers",
            "score": 0.7394857406616211,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Product Photos\n\n\n![The image displays five pairs of gold-plated floral cufflinks—peonies, daisies, roses, cherry blossoms, and lotuses—arranged on a wooden surface with wedding accessories: a navy bowtie, white pocket square, floral boutonniere, and cards labeled “Groom,” “Best Man,” “Groomsmen,” and an inspirational quote.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/602771f5089e7cf9d62c65c155a0e2a7ca8fb5d49ddcf5f638a9b4744cfd152f.jpg)\n\nBirth Flower Cufflinks – Gold, Groom — photo 3",
            "part": 3,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340307,
            "title": "## Product Photos",
            "score": 0.7375146746635437,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image displays a gold lotus-shaped cufflink. Accompanying text lists birth flowers (daisy, rose, lotus) for customizable mixed-pair cufflinks, allowing selection of same or different months at no extra charge.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/febdba03d8d265f2c991e83ca345aa821f9480b96b0a04792a69a9fecb0239be.jpg)",
            "part": 4,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340312,
            "title": "## Pairing Options",
            "score": 0.5143609046936035,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "# Birth Flower Chart\n\nRose  \nPoppy  \nMorning Glory  \nDEC  \nMarigold  \nChrysanthemum  \nBirth Flower Cufflinks – Gold, Groom — photo 5",
            "part": 2,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340317,
            "title": "# Birth Flower Chart",
            "score": 0.5135523676872253,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image shows a gold-colored cufflink designed as an openwork rose. Accompanying text describes pairing options for birth flower cufflinks: matching pairs (same flower), mixed pairs (different flowers), with examples including daisy, rose, and lotus.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/2577b19ef94050c905f50dfb50c7b71ff5f448e533121d9898689be3ef397257.jpg)",
            "part": 3,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340311,
            "title": "## Pairing Options",
            "score": 0.5106713175773621,
            "source": "local"
        },
        {
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image shows a delicate, hand-drawn botanical illustration of a leafy stem in muted green tones on a light background. It appears to be part of a birth flower-themed product listing, likely for cufflinks, featuring flowers like rose and lotus, with text about ordering options and a birth flower chart.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/5d4508960915f9f4946546ce7b3c51ddba8e6d4bb2ceaebe27a97b817b31b71b.jpg)\n\nOrdering for a group?\n\nMessage us for multiple pairsor custom quantities.",
            "part": 7,
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340315,
            "title": "## Pairing Options",
            "score": 0.5062788724899292,
            "source": "local"
        }
        ],
        "hyde_embedding_chunks": [
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340316,
            "title": "# Birth Flower Chart",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "# Birth Flower Chart\n\nCarnation\n\nDaffodil\n\n\n![The image displays a birth flower chart with 12 months (Jan–Dec), each paired with its corresponding flower: Carnation, Violet, Daffodil, Daisy, Hawthorne, Rose, Lotus, Poppy, Morning Glory, Marigold, Chrysanthemum, and Holly—illustrated in elegant line drawings.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/6e31cdfd143047bd276c2e48c33f23a18252f34f9f7da13197f54544e4a4ac04.jpg)",
            "part": 1,
            "score": 0.8599097728729248,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340289,
            "title": "## Product Highlights",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Product Highlights\n\n• One pair — 2 cufflinks included\n\n• Choose from our 12-monthBirth Flower Collection\n\n• Each cufflink can feature its own birth flower\n\n• Create a matching pair or combine two meaningful months\n\n• Openwork floral design with a polished gold-plated finish\n\n• Approx. 15 mm / 0.59in face diameter",
            "part": 1,
            "score": 0.8411452770233154,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340287,
            "title": "## Product Overview",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Product Overview\n\nPersonalized birth flower cufflinks designed to turn meaningful birth months into a distinctive gold-plated keepsake for the groom, husband, dad, or someone special.\n\nEach cufflink features an openwork floral design representing a meaningful birth month",
            "part": 1,
            "score": 0.8375951647758484,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340314,
            "title": "## Pairing Options",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image displays a simple line drawing of a lotus flower, centered on a textured beige background. It appears in a context listing birth flowers (e.g., Daisy, Rose, Lotus, Carnation, Daffodil), likely part of a birth flower chart or product ordering guide.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/096aaed53d6fa05ea238abd833245986583c134d267eeec230938521601249c9.jpg)\n\nLotus\n\nChoose the same month or two different months — mixed pairs at no extra charge.",
            "part": 6,
            "score": 0.8347292542457581,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340294,
            "title": "## Please Note",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Please Note\n\n• This listing includes one pair of cufflinks.\n\n• Birth flower traditions can vary; this listing follows the fixed Birth Flower Collection shown above.\n\n• Matching and mixed-monthpairs are available at the same price.\n\n• The floral designs are fixed as shown in the listing photos.\n\n• Slight variations in appearance may occur due to lighting, viewing angle, and screen settings.",
            "part": 1,
            "score": 0.8330034017562866,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340296,
            "title": "## Birth Flowers",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Birth Flowers\n\nChoose Birth Flower 1 (first cufflink) and Birth Flower 2 (second cufflink). Same month twice = matching pair; two months = mixed pair.\n\n<table><tr><td>Month</td><td>Flower</td></tr><tr><td>JAN</td><td>Carnation</td></tr><tr><td>FEB</td><td>Violet</td></tr><tr><td>MAR</td><td>Daffodil</td></tr><tr><td>APR</td><td>Daisy</td></tr><tr><td>MAY</td><td>Hawthorn</td></tr><tr><td>JUN</td><td>Rose</td></tr><tr><td>JUL</td><td>Lotus</td></tr><tr><td>AUG</td><td>Poppy</td></tr><tr><td>SEP</td><td>Morning Glory</td></tr><tr><td>OCT</td><td>Marigold</td></tr><tr><td>NOV</td><td>Chrysanthemum</td></tr><tr><td>DEC</td><td>Holly</td></tr></table>\n",
            "part": 0,
            "score": 0.7233679890632629,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340312,
            "title": "## Pairing Options",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image displays a gold lotus-shaped cufflink. Accompanying text lists birth flowers (daisy, rose, lotus) for customizable mixed-pair cufflinks, allowing selection of same or different months at no extra charge.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/febdba03d8d265f2c991e83ca345aa821f9480b96b0a04792a69a9fecb0239be.jpg)",
            "part": 4,
            "score": 0.7089486122131348,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340313,
            "title": "## Pairing Options",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image shows a line drawing of a rose. It appears in a context listing birth flowers—daisy, rose, and lotus—with text offering customizable pairs (same or different months)and group orders.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/6217cf0f87be1b737a106b341667d8d6fa2ee32a1f8fce7b05812aecca7cc8ae.jpg)\n\nRose",
            "part": 5,
            "score": 0.7013437151908875,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340315,
            "title": "## Pairing Options",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image shows a delicate, hand-drawn botanical illustration of a leafy stem in muted green tones on a light background. It appears to be part of a birth flower-themed product listing, likely for cufflinks, featuring flowers like rose and lotus, with text about ordering options and a birth flower chart.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/5d4508960915f9f4946546ce7b3c51ddba8e6d4bb2ceaebe27a97b817b31b71b.jpg)\n\nOrdering for a group?\n\nMessage us for multiple pairsor custom quantities.",
            "part": 7,
            "score": 0.6957018971443176,
            "source": "local"
        },
        {
            "item_name": "Birth Flower Cufflinks Gold Groom",
            "id": 469819117954340311,
            "title": "## Pairing Options",
            "file_title": "001_4565343414_cufflinks-gold-groom",
            "content": "## Pairing Options\n\n\n![The image shows a gold-colored cufflink designed as an openwork rose. Accompanying text describes pairing options for birth flower cufflinks: matching pairs (same flower), mixed pairs (different flowers), with examples including daisy, rose, and lotus.](http://127.0.0.1:9000/etsy-kb/upload-images/001_4565343414_cufflinks-gold-groom/2577b19ef94050c905f50dfb50c7b71ff5f448e533121d9898689be3ef397257.jpg)",
            "part": 3,
            "score": 0.6943075060844421,
            "source": "local"
        }
        ],
    }
    result = node(init_state)
    logger.info(json_format(result))