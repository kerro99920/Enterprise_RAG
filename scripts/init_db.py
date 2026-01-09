"""
========================================
完整数据库初始化脚本
========================================

📚 功能说明：
- 初始化PostgreSQL数据库（创建所有表）
- 初始化Milvus向量数据库（创建三层向量库）
- 初始化Redis缓存
- 创建初始管理员账号

🎯 使用场景：
- 首次部署系统时运行
- 开发环境搭建时运行

运行方式：
    python scripts/init_db.py

========================================
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, get_all_models, User
from core.config import settings
from core.logger import logger
from core.constants import UserRole, PermissionLevel
from scripts.init_milvus import init_milvus, check_milvus_status
from services.cache import redis_client
from passlib.context import CryptContext

# 密码加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def init_postgresql():
    """
    初始化PostgreSQL数据库

    🏗️ 创建所有数据表：
    - documents（文档表）
    - document_chunks（文档分块表）
    - document_metadata（文档元数据表）
    - query_logs（查询日志表）
    - query_feedbacks（查询反馈表）
    - users（用户表）
    - user_permissions（用户权限表）
    - user_search_history（用户搜索历史表）
    """

    logger.info("=" * 60)
    logger.info("开始初始化PostgreSQL数据库")
    logger.info("=" * 60)

    try:
        # 创建数据库引擎
        logger.info(f"\n连接到PostgreSQL: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")

        engine = create_engine(
            settings.postgres_url,
            echo=False,  # 设为True可以看到SQL语句
            pool_pre_ping=True,  # 连接前先ping，确保连接有效
            pool_size=10,
            max_overflow=20
        )

        # 测试连接
        with engine.connect() as conn:
            logger.info("✓ 数据库连接成功")

        # 获取所有模型
        models = get_all_models()
        logger.info(f"\n将创建 {len(models)} 个数据表:")
        for model in models:
            logger.info(f"  - {model.__tablename__}")

        # 创建所有表
        logger.info("\n开始创建数据表...")
        Base.metadata.create_all(engine)

        logger.info("\n✓ 所有数据表创建成功！")

        # 验证表是否创建成功
        logger.info("\n验证表创建结果...")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        logger.info(f"\n已创建的表（共 {len(table_names)} 个）：")
        for table_name in sorted(table_names):
            logger.info(f"  ✓ {table_name}")

        logger.info("\n" + "=" * 60)
        logger.info("✓ PostgreSQL数据库初始化完成！")
        logger.info("=" * 60)

        return engine

    except Exception as e:
        logger.error(f"\n✗ PostgreSQL初始化失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def create_admin_user(engine):
    """
    创建初始管理员账号

    📋 默认管理员信息：
    - 用户名: admin
    - 密码: admin123（首次登录后请修改）
    - 角色: ADMIN
    """

    logger.info("\n" + "=" * 60)
    logger.info("创建初始管理员账号")
    logger.info("=" * 60)

    try:
        # 创建Session
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        # 检查是否已存在管理员
        existing_admin = session.query(User).filter(
            User.username == "admin"
        ).first()

        if existing_admin:
            logger.warning("\n管理员账号已存在，跳过创建")
            logger.info(f"用户名: {existing_admin.username}")
            logger.info(f"邮箱: {existing_admin.email}")
            session.close()
            return True

        # 创建管理员账号
        admin_user = User(
            username="admin",
            email="admin@example.com",
            full_name="系统管理员",
            password_hash=pwd_context.hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
            default_permission_level=PermissionLevel.CONFIDENTIAL
        )

        session.add(admin_user)
        session.commit()

        logger.info("\n✓ 管理员账号创建成功！")
        logger.info("\n📋 登录信息：")
        logger.info(f"  用户名: admin")
        logger.info(f"  密码: admin123")
        logger.info(f"  邮箱: admin@example.com")
        logger.info("\n⚠️  重要提示：首次登录后请立即修改密码！")

        session.close()
        return True

    except Exception as e:
        logger.error(f"\n✗ 创建管理员账号失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_redis():
    """
    测试Redis连接
    """

    logger.info("\n" + "=" * 60)
    logger.info("测试Redis连接")
    logger.info("=" * 60)

    try:
        # 测试连接
        if redis_client.ping():
            logger.info("\n✓ Redis连接成功")

            # 获取Redis信息
            info = redis_client.get_info()
            logger.info(f"\n📊 Redis信息：")
            logger.info(f"  版本: {info.get('redis_version', 'N/A')}")
            logger.info(f"  内存使用: {info.get('used_memory_human', 'N/A')}")
            logger.info(f"  连接客户端: {info.get('connected_clients', 'N/A')}")

            # 测试写入
            test_key = "test:init"
            redis_client.set(test_key, "Hello Redis!", expire=60)
            value = redis_client.get(test_key)

            if value == "Hello Redis!":
                logger.info("\n✓ Redis读写测试成功")
                redis_client.delete(test_key)

            logger.info("\n" + "=" * 60)
            logger.info("✓ Redis测试通过！")
            logger.info("=" * 60)

            return True
        else:
            logger.error("\n✗ Redis连接失败")
            return False

    except Exception as e:
        logger.error(f"\n✗ Redis测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def init_all_databases():
    """
    初始化所有数据库

    🔄 执行流程：
    1. 初始化PostgreSQL（创建表）
    2. 创建管理员账号
    3. 初始化Milvus（创建向量库）
    4. 测试Redis连接
    """

    print("\n" + "=" * 60)
    print("🚀 企业级RAG系统 - 数据库初始化工具")
    print("=" * 60)

    print("\n即将初始化以下数据库：")
    print("  1. PostgreSQL - 关系数据库")
    print("  2. Milvus - 向量数据库")
    print("  3. Redis - 缓存数据库")

    confirm = input("\n确认开始初始化？(y/n): ").strip().lower()

    if confirm != 'y':
        print("已取消初始化")
        return False

    print("\n开始初始化...\n")

    success = True

    # 1. 初始化PostgreSQL
    engine = init_postgresql()
    if not engine:
        logger.error("PostgreSQL初始化失败，终止初始化流程")
        return False

    # 2. 创建管理员账号
    if not create_admin_user(engine):
        logger.warning("管理员账号创建失败，但继续初始化流程")
        success = False

    # 3. 初始化Milvus
    if not init_milvus():
        logger.error("Milvus初始化失败")
        success = False

    # 4. 测试Redis
    if not test_redis():
        logger.warning("Redis测试失败，但不影响其他功能")
        success = False

    # 总结
    print("\n" + "=" * 60)
    if success:
        print("✓ 所有数据库初始化完成！")
        print("=" * 60)

        print("\n📊 初始化摘要：")
        print("  ✓ PostgreSQL - 所有表创建成功")
        print("  ✓ 管理员账号 - 创建成功")
        print("  ✓ Milvus - 三层向量库创建成功")
        print("  ✓ Redis - 连接正常")

        print("\n🎉 系统已准备就绪，可以开始使用！")

        print("\n📝 后续步骤：")
        print("  1. 启动API服务: uvicorn app.main:app --reload")
        print("  2. 上传文档到 data/raw_docs/ 目录")
        print("  3. 运行文档处理脚本: python scripts/ingest_docs.py")
        print("  4. 使用管理员账号登录系统")

    else:
        print("⚠️  部分数据库初始化失败")
        print("=" * 60)
        print("\n请检查错误日志，修复问题后重试")

    print("")
    return success


def check_all_databases():
    """
    检查所有数据库状态
    """

    print("\n" + "=" * 60)
    print("检查数据库状态")
    print("=" * 60)

    # 1. 检查PostgreSQL
    print("\n1. PostgreSQL:")
    print("-" * 60)
    try:
        engine = create_engine(settings.postgres_url)
        with engine.connect() as conn:
            print("  ✓ 连接成功")

            from sqlalchemy import inspect
            inspector = inspect(engine)
            table_names = inspector.get_table_names()
            print(f"  ✓ 数据表数量: {len(table_names)}")

    except Exception as e:
        print(f"  ✗ 连接失败: {str(e)}")

    # 2. 检查Milvus
    print("\n2. Milvus:")
    print("-" * 60)
    check_milvus_status()

    # 3. 检查Redis
    print("\n3. Redis:")
    print("-" * 60)
    if redis_client.ping():
        print("  ✓ 连接成功")
        info = redis_client.get_info()
        print(f"  ✓ 版本: {info.get('redis_version', 'N/A')}")
    else:
        print("  ✗ 连接失败")

    print("\n" + "=" * 60)


def main():
    """
    主函数：提供交互式菜单
    """

    print("\n" + "=" * 60)
    print("数据库管理工具")
    print("=" * 60)

    print("\n请选择操作：")
    print("1. 初始化所有数据库（首次部署使用）")
    print("2. 只初始化PostgreSQL")
    print("3. 只初始化Milvus")
    print("4. 检查所有数据库状态")
    print("5. 创建管理员账号")
    print("0. 退出")

    choice = input("\n请输入选项（0-5）: ").strip()

    if choice == "1":
        init_all_databases()
    elif choice == "2":
        engine = init_postgresql()
        if engine:
            create_admin_user(engine)
    elif choice == "3":
        init_milvus()
    elif choice == "4":
        check_all_databases()
    elif choice == "5":
        engine = create_engine(settings.postgres_url)
        create_admin_user(engine)
    elif choice == "0":
        print("退出")
    else:
        print("无效的选项")


if __name__ == "__main__":
    main()

# =========================================
# 💡 使用示例
# =========================================
"""
# 1. 首次初始化（推荐）
python scripts/init_db.py
# 选择选项 1

# 2. 检查状态
python scripts/init_db.py
# 选择选项 4

# 3. 在代码中直接调用
from scripts.init_db import init_all_databases

success = init_all_databases()
if success:
    print("初始化成功")
"""