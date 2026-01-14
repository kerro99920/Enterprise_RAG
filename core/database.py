"""
数据库连接和会话管理
====================

统一管理：
- SQLAlchemy Engine / SessionLocal
- FastAPI 依赖的 `get_db`
- 简单的初始化与健康检查
"""

from typing import Generator, Any
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from core.config import settings
from models import Base, get_all_models

# 配置日志
logger = logging.getLogger(__name__)


# 创建数据库引擎
engine = create_engine(
    settings.postgres_url,
    echo=settings.DEBUG,  # 调试模式下打印SQL语句
    pool_size=10,  # 连接池大小（可按需调整）
    max_overflow=20,  # 连接池溢出大小
    pool_pre_ping=True,  # 连接前检查是否可用
    pool_recycle=3600,  # 1小时后回收连接
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（用于 FastAPI 依赖注入）

    使用示例:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    初始化数据库：创建所有表。

    注意：生产环境中通常建议使用迁移工具（如 Alembic），
    这里更适合作为开发环境或一次性初始化脚本。
    """
    try:
        # 确保所有模型已被导入并注册到 Base.metadata
        _ = get_all_models()

        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:  # noqa: BLE001
        logger.error(f"数据库初始化失败: {e}")
        raise


def check_db_connection() -> bool:
    """
    检查数据库连接是否正常
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("数据库连接正常")
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"数据库连接失败: {e}")
        return False


class DatabaseManager:
    """数据库管理器 - 提供便捷的数据库操作方法"""

    def __init__(self) -> None:
        self.engine = engine
        self.SessionLocal = SessionLocal

    def get_session(self) -> Session:
        """获取新的数据库会话"""
        return self.SessionLocal()

    def execute_raw_sql(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        """
        执行原始SQL

        Args:
            sql: SQL语句
            params: 参数字典

        Returns:
            查询结果
        """
        with self.get_session() as db:
            result = db.execute(text(sql), params or {})
            db.commit()
            return result

    def bulk_insert(self, model_class: type, data_list: list[dict[str, Any]]) -> int:
        """
        批量插入数据

        Args:
            model_class: 模型类
            data_list: 数据列表 [dict, dict, ...]

        Returns:
            插入的记录数
        """
        with self.get_session() as db:
            try:
                objects = [model_class(**data) for data in data_list]
                db.bulk_save_objects(objects)
                db.commit()
                logger.info(f"批量插入 {len(data_list)} 条记录到 {model_class.__tablename__}")
                return len(data_list)
            except Exception as e:  # noqa: BLE001
                db.rollback()
                logger.error(f"批量插入失败: {e}")
                raise

    def truncate_table(self, table_name: str) -> None:
        """
        清空表数据

        Args:
            table_name: 表名
        """
        with self.get_session() as db:
            try:
                db.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                db.commit()
                logger.info(f"表 {table_name} 已清空")
            except Exception as e:  # noqa: BLE001
                db.rollback()
                logger.error(f"清空表失败: {e}")
                raise


# 创建全局数据库管理器实例
db_manager = DatabaseManager()

