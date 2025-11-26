"""Bot 管理员功能模块（lazy exports to avoid circular imports)."""

__all__ = ["admin_handler", "owner_only"]


def __getattr__(name):
    if name == "admin_handler":
        from .handler import admin_handler

        return admin_handler
    if name == "owner_only":
        from .middleware import owner_only

        return owner_only
    raise AttributeError(f"module 'src.bot_admin' has no attribute '{name}'")
