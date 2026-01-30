"""
========================================
权限检查模块
========================================

模块说明：
- 统一的权限验证服务
- 基于角色的访问控制 (RBAC)
- 资源级别的细粒度权限管理
- JWT 令牌验证

核心功能：
1. 用户认证 - JWT 令牌验证
2. 角色检查 - 基于用户角色的权限控制
3. 资源权限 - 文档、项目级别的访问控制
4. 权限缓存 - Redis 缓存提升性能

========================================
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from functools import wraps

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from loguru import logger

from core.config import settings


# =========================================
# 枚举定义
# =========================================

class UserRole(str, Enum):
    """
    用户角色枚举

    权限从高到低：
    - ADMIN: 系统管理员，拥有所有权限
    - MANAGER: 项目经理，可管理项目和文档
    - ENGINEER: 工程师，可上传和查询文档
    - VIEWER: 访客，只读权限
    """
    ADMIN = "admin"
    MANAGER = "manager"
    ENGINEER = "engineer"
    VIEWER = "viewer"


class PermissionLevel(str, Enum):
    """
    文档权限级别

    访问限制从低到高：
    - PUBLIC: 公开，所有人可访问
    - INTERNAL: 内部，登录用户可访问
    - CONFIDENTIAL: 机密，需要特定权限
    - RESTRICTED: 受限，仅管理员可访问
    """
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class ResourceType(str, Enum):
    """资源类型"""
    DOCUMENT = "document"
    PROJECT = "project"
    COLLECTION = "collection"
    AGENT = "agent"


class ActionType(str, Enum):
    """操作类型"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    SHARE = "share"
    ADMIN = "admin"


# =========================================
# 角色权限映射
# =========================================

# 角色对应的权限级别（可访问的最高级别）
ROLE_PERMISSION_MAP: Dict[UserRole, List[PermissionLevel]] = {
    UserRole.ADMIN: [
        PermissionLevel.PUBLIC,
        PermissionLevel.INTERNAL,
        PermissionLevel.CONFIDENTIAL,
        PermissionLevel.RESTRICTED
    ],
    UserRole.MANAGER: [
        PermissionLevel.PUBLIC,
        PermissionLevel.INTERNAL,
        PermissionLevel.CONFIDENTIAL
    ],
    UserRole.ENGINEER: [
        PermissionLevel.PUBLIC,
        PermissionLevel.INTERNAL
    ],
    UserRole.VIEWER: [
        PermissionLevel.PUBLIC
    ]
}

# 角色对应的操作权限
ROLE_ACTION_MAP: Dict[UserRole, List[ActionType]] = {
    UserRole.ADMIN: [
        ActionType.READ,
        ActionType.WRITE,
        ActionType.DELETE,
        ActionType.SHARE,
        ActionType.ADMIN
    ],
    UserRole.MANAGER: [
        ActionType.READ,
        ActionType.WRITE,
        ActionType.DELETE,
        ActionType.SHARE
    ],
    UserRole.ENGINEER: [
        ActionType.READ,
        ActionType.WRITE
    ],
    UserRole.VIEWER: [
        ActionType.READ
    ]
}


# =========================================
# JWT 配置
# =========================================

# 从配置获取，如果没有则使用默认值
JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', 'your-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = getattr(settings, 'JWT_EXPIRE_HOURS', 24)


# =========================================
# 安全依赖
# =========================================

security = HTTPBearer(auto_error=False)


# =========================================
# 权限检查器类
# =========================================

class PermissionChecker:
    """
    权限检查器

    提供统一的权限验证接口，支持：
    - JWT 令牌验证
    - 角色检查
    - 资源级别权限控制
    - 权限缓存
    """

    def __init__(self):
        """初始化权限检查器"""
        self._cache = {}  # 简单内存缓存，生产环境应使用 Redis
        self._cache_ttl = 300  # 缓存有效期（秒）

    # =========================================
    # JWT 令牌操作
    # =========================================

    def create_access_token(
        self,
        user_id: str,
        username: str,
        role: UserRole,
        extra_data: Optional[Dict] = None
    ) -> str:
        """
        创建 JWT 访问令牌

        参数：
            user_id: 用户ID
            username: 用户名
            role: 用户角色
            extra_data: 额外数据

        返回：
            JWT 令牌字符串
        """
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)

        payload = {
            "sub": user_id,
            "username": username,
            "role": role.value if isinstance(role, UserRole) else role,
            "exp": expire,
            "iat": datetime.utcnow()
        }

        if extra_data:
            payload.update(extra_data)

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        logger.debug(f"为用户 {username} 创建访问令牌")

        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证 JWT 令牌

        参数：
            token: JWT 令牌

        返回：
            令牌载荷（如果有效），否则返回 None
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            logger.warning(f"JWT 验证失败: {e}")
            return None

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        解码 JWT 令牌（带异常）

        参数：
            token: JWT 令牌

        返回：
            令牌载荷

        异常：
            HTTPException: 令牌无效或过期
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="令牌已过期")
        except JWTError:
            raise HTTPException(status_code=401, detail="无效的令牌")

    # =========================================
    # 用户认证
    # =========================================

    async def get_current_user(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Optional[Dict[str, Any]]:
        """
        获取当前用户（FastAPI 依赖）

        参数：
            credentials: HTTP 授权凭证

        返回：
            用户信息字典，未认证返回 None
        """
        if not credentials:
            return None

        token = credentials.credentials
        payload = self.verify_token(token)

        if not payload:
            return None

        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "role": UserRole(payload.get("role", "viewer")),
            "exp": payload.get("exp")
        }

    async def get_current_user_required(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        """
        获取当前用户（必须登录）

        参数：
            credentials: HTTP 授权凭证

        返回：
            用户信息字典

        异常：
            HTTPException: 未登录
        """
        if not credentials:
            raise HTTPException(status_code=401, detail="未提供认证令牌")

        user = await self.get_current_user(credentials)

        if not user:
            raise HTTPException(status_code=401, detail="认证失败")

        return user

    # =========================================
    # 角色检查
    # =========================================

    def check_role(
        self,
        user_role: UserRole,
        required_role: UserRole
    ) -> bool:
        """
        检查用户角色是否满足要求

        参数：
            user_role: 用户当前角色
            required_role: 所需角色

        返回：
            是否满足权限要求
        """
        role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.MANAGER: 3,
            UserRole.ENGINEER: 2,
            UserRole.VIEWER: 1
        }

        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    def require_role(self, required_role: UserRole):
        """
        角色检查装饰器

        用法：
            @permission_checker.require_role(UserRole.MANAGER)
            async def admin_endpoint():
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 从 kwargs 中获取用户信息
                current_user = kwargs.get('current_user')

                if not current_user:
                    raise HTTPException(status_code=401, detail="未登录")

                user_role = current_user.get('role')
                if not self.check_role(user_role, required_role):
                    raise HTTPException(
                        status_code=403,
                        detail=f"权限不足，需要 {required_role.value} 或更高角色"
                    )

                return await func(*args, **kwargs)
            return wrapper
        return decorator

    # =========================================
    # 资源权限检查
    # =========================================

    def check_permission_level(
        self,
        user_role: UserRole,
        resource_level: PermissionLevel
    ) -> bool:
        """
        检查用户是否有权访问指定级别的资源

        参数：
            user_role: 用户角色
            resource_level: 资源权限级别

        返回：
            是否有权限
        """
        allowed_levels = ROLE_PERMISSION_MAP.get(user_role, [])
        return resource_level in allowed_levels

    def check_action(
        self,
        user_role: UserRole,
        action: ActionType
    ) -> bool:
        """
        检查用户是否有权执行指定操作

        参数：
            user_role: 用户角色
            action: 操作类型

        返回：
            是否有权限
        """
        allowed_actions = ROLE_ACTION_MAP.get(user_role, [])
        return action in allowed_actions

    def check_resource_access(
        self,
        user_id: str,
        user_role: UserRole,
        resource_type: ResourceType,
        resource_id: str,
        action: ActionType,
        resource_level: PermissionLevel = PermissionLevel.INTERNAL
    ) -> bool:
        """
        检查用户对特定资源的访问权限

        参数：
            user_id: 用户ID
            user_role: 用户角色
            resource_type: 资源类型
            resource_id: 资源ID
            action: 操作类型
            resource_level: 资源权限级别

        返回：
            是否有权限
        """
        # 管理员有所有权限
        if user_role == UserRole.ADMIN:
            return True

        # 检查操作权限
        if not self.check_action(user_role, action):
            logger.debug(
                f"用户 {user_id} 无权执行 {action.value} 操作"
            )
            return False

        # 检查资源级别权限
        if not self.check_permission_level(user_role, resource_level):
            logger.debug(
                f"用户 {user_id} 无权访问 {resource_level.value} 级别资源"
            )
            return False

        # TODO: 检查用户对特定资源的细粒度权限
        # 这里可以查询 UserPermission 表获取更细粒度的权限

        return True

    # =========================================
    # 权限验证装饰器
    # =========================================

    def require_permission(
        self,
        resource_type: ResourceType,
        action: ActionType,
        resource_level: PermissionLevel = PermissionLevel.INTERNAL
    ):
        """
        权限验证装饰器

        用法：
            @permission_checker.require_permission(
                ResourceType.DOCUMENT,
                ActionType.WRITE,
                PermissionLevel.INTERNAL
            )
            async def create_document():
                pass
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                current_user = kwargs.get('current_user')

                if not current_user:
                    raise HTTPException(status_code=401, detail="未登录")

                user_id = current_user.get('user_id')
                user_role = current_user.get('role')

                # 获取资源 ID（从路径参数或请求体）
                resource_id = kwargs.get('resource_id') or kwargs.get('id')

                has_permission = self.check_resource_access(
                    user_id=user_id,
                    user_role=user_role,
                    resource_type=resource_type,
                    resource_id=resource_id or "",
                    action=action,
                    resource_level=resource_level
                )

                if not has_permission:
                    raise HTTPException(
                        status_code=403,
                        detail="权限不足，无法执行此操作"
                    )

                return await func(*args, **kwargs)
            return wrapper
        return decorator

    # =========================================
    # 缓存操作
    # =========================================

    def _get_cache_key(self, user_id: str, resource_type: str, resource_id: str) -> str:
        """生成缓存键"""
        return f"perm:{user_id}:{resource_type}:{resource_id}"

    def cache_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        has_permission: bool
    ):
        """缓存权限结果"""
        key = self._get_cache_key(user_id, resource_type, resource_id)
        self._cache[key] = {
            "value": has_permission,
            "expires_at": datetime.utcnow() + timedelta(seconds=self._cache_ttl)
        }

    def get_cached_permission(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str
    ) -> Optional[bool]:
        """获取缓存的权限结果"""
        key = self._get_cache_key(user_id, resource_type, resource_id)
        cached = self._cache.get(key)

        if not cached:
            return None

        if datetime.utcnow() > cached["expires_at"]:
            del self._cache[key]
            return None

        return cached["value"]

    def clear_user_cache(self, user_id: str):
        """清除用户的所有权限缓存"""
        keys_to_delete = [
            k for k in self._cache.keys()
            if k.startswith(f"perm:{user_id}:")
        ]
        for key in keys_to_delete:
            del self._cache[key]

        logger.debug(f"已清除用户 {user_id} 的权限缓存")


# =========================================
# 全局实例
# =========================================

permission_checker = PermissionChecker()


# =========================================
# FastAPI 依赖函数
# =========================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[Dict[str, Any]]:
    """获取当前用户（可选）"""
    return await permission_checker.get_current_user(credentials)


async def get_current_user_required(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """获取当前用户（必须）"""
    return await permission_checker.get_current_user_required(credentials)


def require_role(role: UserRole):
    """
    角色检查依赖

    用法：
        @router.get("/admin")
        async def admin_endpoint(
            current_user: Dict = Depends(require_role(UserRole.ADMIN))
        ):
            pass
    """
    async def role_checker(
        credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> Dict[str, Any]:
        user = await permission_checker.get_current_user_required(credentials)

        if not permission_checker.check_role(user['role'], role):
            raise HTTPException(
                status_code=403,
                detail=f"权限不足，需要 {role.value} 或更高角色"
            )

        return user

    return role_checker


# =========================================
# 使用示例
# =========================================
"""
from fastapi import APIRouter, Depends
from services.permission.permission_checker import (
    permission_checker,
    get_current_user,
    get_current_user_required,
    require_role,
    UserRole,
    PermissionLevel,
    ResourceType,
    ActionType
)

router = APIRouter()


# 1. 可选认证 - 未登录用户也可访问
@router.get("/public")
async def public_endpoint(current_user = Depends(get_current_user)):
    if current_user:
        return {"message": f"欢迎, {current_user['username']}"}
    return {"message": "欢迎, 访客"}


# 2. 必须认证 - 必须登录才能访问
@router.get("/protected")
async def protected_endpoint(current_user = Depends(get_current_user_required)):
    return {"message": f"欢迎, {current_user['username']}"}


# 3. 角色检查 - 需要特定角色
@router.get("/admin")
async def admin_endpoint(current_user = Depends(require_role(UserRole.ADMIN))):
    return {"message": "管理员专属"}


# 4. 使用装饰器进行权限检查
@router.post("/documents")
@permission_checker.require_permission(
    ResourceType.DOCUMENT,
    ActionType.WRITE,
    PermissionLevel.INTERNAL
)
async def create_document(current_user = Depends(get_current_user_required)):
    return {"message": "文档创建成功"}


# 5. 创建令牌（登录接口）
@router.post("/login")
async def login(username: str, password: str):
    # 验证用户名密码（省略）
    user_id = "user_123"
    role = UserRole.ENGINEER

    token = permission_checker.create_access_token(
        user_id=user_id,
        username=username,
        role=role
    )

    return {"access_token": token, "token_type": "bearer"}


# 6. 手动检查权限
@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    current_user = Depends(get_current_user_required)
):
    # 检查用户是否有权访问该文档
    has_permission = permission_checker.check_resource_access(
        user_id=current_user['user_id'],
        user_role=current_user['role'],
        resource_type=ResourceType.DOCUMENT,
        resource_id=doc_id,
        action=ActionType.READ,
        resource_level=PermissionLevel.INTERNAL
    )

    if not has_permission:
        raise HTTPException(status_code=403, detail="无权访问该文档")

    return {"doc_id": doc_id, "content": "..."}
"""
