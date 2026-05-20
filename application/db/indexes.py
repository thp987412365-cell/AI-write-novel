import pymongo
import logging
from application.db.mongo import get_database

logger = logging.getLogger(__name__)

async def init_novel_indexes():
    """初始化novels集合的索引。"""
    try:
        db = get_database()
        novels_collection = db["novels"]
        
        logger.info("正在初始化'novels'集合的索引...")
        
        indexes = [
            # 单字段索引
            pymongo.IndexModel([("title", pymongo.ASCENDING)]),
            pymongo.IndexModel([("status", pymongo.ASCENDING)]),
            pymongo.IndexModel([("tags", pymongo.ASCENDING)]),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
            pymongo.IndexModel([("is_deleted", pymongo.ASCENDING)]),
            
            # 书架列表：按is_deleted过滤，按updated_at降序排序
            pymongo.IndexModel([
                ("is_deleted", pymongo.ASCENDING),
                ("updated_at", pymongo.DESCENDING)
            ]),
            
            # 标题搜索：按is_deleted过滤，按标题排序或查询
            pymongo.IndexModel([
                ("is_deleted", pymongo.ASCENDING),
                ("title", pymongo.ASCENDING)
            ]),
        ]
        
        await novels_collection.create_indexes(indexes)
        logger.info("成功初始化'novels'集合的索引。")
    except Exception as e:
        logger.error(f"初始化novel索引失败：{e}")


async def init_volume_indexes():
    """初始化volumes集合的索引。"""
    try:
        db = get_database()
        volumes_collection = db["volumes"]

        logger.info("正在初始化'volumes'集合的索引...")

        indexes = [
            # 单字段索引：按小说过滤拉取全书卷列表
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING)]),

            # 唯一组合索引：保证同一小说内卷序号不重复
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("order_index", pymongo.ASCENDING)],
                unique=True
            ),

            # 读优化组合索引：未删除卷按序号排列的常用查询
            pymongo.IndexModel([
                ("novel_id", pymongo.ASCENDING),
                ("is_deleted", pymongo.ASCENDING),
                ("order_index", pymongo.ASCENDING)
            ]),

            # 按最近更新时间检索
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]

        await volumes_collection.create_indexes(indexes)
        logger.info("成功初始化'volumes'集合的索引。")
    except Exception as e:
        logger.error(f"初始化volume索引失败：{e}")


async def init_faction_indexes():
    """初始化factions集合的索引。"""
    try:
        db = get_database()
        factions_collection = db["factions"]

        logger.info("正在初始化'factions'集合的索引...")

        indexes = [
            # 唯一组合索引：保证同一小说内 faction_id 不重复
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("faction_id", pymongo.ASCENDING)],
                unique=True
            ),

            # 按层级类型过滤（用于按 core / major_volume 等召回）
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("level_type", pymongo.ASCENDING)]
            ),

            # 按父级阵营查子阵营
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("parent_faction_id", pymongo.ASCENDING)]
            ),

            # 按名称检索阵营
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("name", pymongo.ASCENDING)]
            ),

            # 读优化：未删除阵营按排序权重排列
            pymongo.IndexModel([
                ("novel_id", pymongo.ASCENDING),
                ("is_deleted", pymongo.ASCENDING),
                ("sort_order", pymongo.ASCENDING)
            ]),

            # 按最近更新时间检索
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]

        await factions_collection.create_indexes(indexes)
        logger.info("成功初始化'factions'集合的索引。")
    except Exception as e:
        logger.error(f"初始化faction索引失败：{e}")


async def init_chapter_indexes():
    try:
        db = get_database()
        coll = db["chapters"]
        logger.info("正在初始化'chapters'集合的索引...")
        indexes = [
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("chapter_index", pymongo.ASCENDING)],
                unique=True
            ),
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("volume_id", pymongo.ASCENDING), ("sort_order", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("status", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("is_deleted", pymongo.ASCENDING), ("sort_order", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'chapters'集合的索引。")
    except Exception as e:
        logger.error(f"初始化chapter索引失败：{e}")


async def init_character_indexes():
    try:
        db = get_database()
        coll = db["characters"]
        logger.info("正在初始化'characters'集合的索引...")
        indexes = [
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("char_id", pymongo.ASCENDING)],
                unique=True
            ),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("role", pymongo.ASCENDING)]),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("faction_id", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("is_deleted", pymongo.ASCENDING), ("sort_order", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'characters'集合的索引。")
    except Exception as e:
        logger.error(f"初始化character索引失败：{e}")


async def init_location_indexes():
    try:
        db = get_database()
        coll = db["locations"]
        logger.info("正在初始化'locations'集合的索引...")
        indexes = [
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("name", pymongo.ASCENDING)],
                unique=True
            ),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("type", pymongo.ASCENDING)]),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("parent_location_id", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("is_deleted", pymongo.ASCENDING), ("sort_order", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'locations'集合的索引。")
    except Exception as e:
        logger.error(f"初始化location索引失败：{e}")


async def init_item_indexes():
    try:
        db = get_database()
        coll = db["items"]
        logger.info("正在初始化'items'集合的索引...")
        indexes = [
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("name", pymongo.ASCENDING)],
                unique=True
            ),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("type", pymongo.ASCENDING)]),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("rarity", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("is_deleted", pymongo.ASCENDING), ("sort_order", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'items'集合的索引。")
    except Exception as e:
        logger.error(f"初始化item索引失败：{e}")


async def init_rule_indexes():
    try:
        db = get_database()
        coll = db["rules"]
        logger.info("正在初始化'rules'集合的索引...")
        indexes = [
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("name", pymongo.ASCENDING)],
                unique=True
            ),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING), ("category", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("is_deleted", pymongo.ASCENDING), ("sort_order", pymongo.ASCENDING)]
            ),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'rules'集合的索引。")
    except Exception as e:
        logger.error(f"初始化rule索引失败：{e}")


async def init_knowledge_docs_indexes():
    """初始化 knowledge_docs 集合的索引。"""
    try:
        db = get_database()
        coll = db["knowledge_docs"]
        logger.info("正在初始化'knowledge_docs'集合的索引...")
        indexes = [
            pymongo.IndexModel([("title", pymongo.ASCENDING)]),
            pymongo.IndexModel(
                [("is_deleted", pymongo.ASCENDING), ("updated_at", pymongo.DESCENDING)]
            ),
            pymongo.IndexModel([("updated_at", pymongo.DESCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'knowledge_docs'集合的索引。")
    except Exception as e:
        logger.error(f"初始化knowledge_docs索引失败：{e}")


async def init_novel_knowledge_links_indexes():
    """初始化 novel_knowledge_links 集合的索引。"""
    try:
        db = get_database()
        coll = db["novel_knowledge_links"]
        logger.info("正在初始化'novel_knowledge_links'集合的索引...")
        indexes = [
            pymongo.IndexModel(
                [("novel_id", pymongo.ASCENDING), ("doc_id", pymongo.ASCENDING)],
                unique=True,
            ),
            pymongo.IndexModel([("novel_id", pymongo.ASCENDING)]),
            pymongo.IndexModel([("doc_id", pymongo.ASCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'novel_knowledge_links'集合的索引。")
    except Exception as e:
        logger.error(f"初始化novel_knowledge_links索引失败：{e}")


async def init_llm_call_logs_indexes():
    """初始化 llm_call_logs 集合的索引。"""
    try:
        db = get_database()
        coll = db["llm_call_logs"]
        logger.info("正在初始化'llm_call_logs'集合的索引...")
        indexes = [
            pymongo.IndexModel([("created_at", pymongo.DESCENDING)]),
            pymongo.IndexModel([("provider", pymongo.ASCENDING)]),
            pymongo.IndexModel([("model", pymongo.ASCENDING)]),
            pymongo.IndexModel([("success", pymongo.ASCENDING)]),
        ]
        await coll.create_indexes(indexes)
        logger.info("成功初始化'llm_call_logs'集合的索引。")
    except Exception as e:
        logger.error(f"初始化llm_call_logs索引失败：{e}")


async def init_all_indexes():
    """初始化所有数据库索引。"""
    await init_novel_indexes()
    await init_volume_indexes()
    await init_faction_indexes()
    await init_chapter_indexes()
    await init_character_indexes()
    await init_location_indexes()
    await init_item_indexes()
    await init_rule_indexes()
    await init_knowledge_docs_indexes()
    await init_novel_knowledge_links_indexes()
    await init_llm_call_logs_indexes()
