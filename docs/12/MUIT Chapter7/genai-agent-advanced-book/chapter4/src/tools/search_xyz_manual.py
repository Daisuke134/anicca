from elasticsearch import Elasticsearch
from langchain.tools import tool
from pydantic import BaseModel, Field

from src.custom_logger import setup_logger
from src.models import SearchOutput

# 検索結果の最大取得数
MAX_SEARCH_RESULTS = 3

logger = setup_logger(__file__)


# 入力スキーマを定義するクラス
class SearchKeywordInput(BaseModel):
    keywords: str = Field(description="全文検索用のキーワード")


# LangChainのtoolデコレーターを使って、検索機能をツール化
@tool(args_schema=SearchKeywordInput)
def search_xyz_manual(keywords: str) -> list[SearchOutput]:
    """
    XYZシステムのドキュメントを調査する関数。
    エラーコードや固有名詞が質問に含まれる場合は、この関数を使ってキーワード検索を行う。
    """

    logger.info(f"Searching XYZ manual by keyword: {keywords}")

    # Elasticsearchのインスタンスを作成して、ローカルのElasticsearchに接続
    es = Elasticsearch("http://localhost:9200")

    # 検索対象のインデックスを指定
    index_name = "documents"

    # 検索クエリを作成。'content' フィールドに対してキーワードで全文検索を行う
    keyword_query = {"query": {"match": {"content": keywords}}}

    # Elasticsearchに検索クエリを送信し、結果を 'response' に格納
    response = es.search(index=index_name, body=keyword_query)

    logger.info(f"Search results: {len(response['hits']['hits'])} hits")

    # 検索結果を格納するリスト
    outputs = []

    # 検索結果からヒットしたドキュメントを1つずつ処理
    for hit in response["hits"]["hits"][:MAX_SEARCH_RESULTS]:
        # カスタムモデルSearchOutputのfrom_hitメソッドを使って、検索結果をオブジェクト化しリストに追加
        outputs.append(SearchOutput.from_hit(hit))

    logger.info("Finished searching XYZ manual by keyword")

    # 検索結果のリストを返す
    return outputs
