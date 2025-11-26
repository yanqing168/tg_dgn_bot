"""
配置管理模块
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""
    
    # Telegram Bot
    bot_token: str
    bot_owner_id: int = 0  # Bot Owner 用户 ID（用于管理面板权限验证）
    use_webhook: bool = False
    bot_service_host: str = "0.0.0.0"
    bot_service_port: int = 8080
    bot_webhook_url: str = Field(default="", validation_alias="BOT_WEBHOOK_URL")
    bot_instance_name: str = "primary"
    
    # USDT TRC20 支付
    usdt_trc20_receive_addr: str
    
    # HMAC 签名
    webhook_secret: str
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    
    # 订单设置
    order_timeout_minutes: int = 30
    base_price_decimal_places: int = 3
    
    # TRON API (可选)
    tron_api_url: str = ""
    tron_api_key: str = ""
    tron_explorer: str = "tronscan"  # tronscan | oklink
    
    # 地址查询限频（分钟）
    address_query_rate_limit_minutes: int = 1

    # USDT 汇率看板配置
    usdt_rates_cache_ttl: int = 3600  # Redis 缓存 TTL（秒）
    usdt_rate_bank_markup: float = 0.0
    usdt_rate_alipay_markup: float = 0.001
    usdt_rate_wechat_markup: float = 0.002

    # 能量API配置
    energy_api_username: str = ""
    energy_api_password: str = ""
    energy_api_base_url: str = "https://trxno.com"
    energy_api_backup_url: str = "https://trxfast.com"
    
    # 能量代理地址（TRX直转模式）
    energy_rent_address: str = ""  # 时长能量收TRX地址
    energy_package_address: str = ""  # 笔数套餐收USDT地址
    energy_flash_address: str = ""  # 闪兑收USDT地址
    
    # TRX兑换配置
    trx_exchange_receive_address: str = ""  # 收USDT地址
    trx_exchange_send_address: str = ""  # 发TRX地址
    trx_exchange_private_key: str = ""  # 发TRX私钥（生产环境填写）
    trx_exchange_qrcode_file_id: str = ""  # 收款二维码 Telegram file_id
    trx_exchange_default_rate: float = 3.05  # 默认汇率（1 USDT = X TRX）
    trx_exchange_test_mode: bool = True  # 测试模式（不实际转账）
    
    # 免费克隆功能文案
    free_clone_message: str = (
        "🎁 <b>免费克隆服务</b>\n\n"
        "本 Bot 支持免费克隆功能！\n\n"
        "📋 <b>服务内容：</b>\n"
        "• 克隆 Telegram 群组\n"
        "• 克隆频道内容\n"
        "• 批量导入成员\n\n"
        "💡 <b>申请方式：</b>\n"
        "需要使用此服务，请联系客服申请。\n\n"
        "👨‍💼 客服将为您提供详细的使用指南和技术支持。"
    )
    
    # 欢迎语配置
    welcome_message: str = (
        "👋 欢迎使用 TG DGN Bot！\n\n"
        "🤖 <b>你的 Telegram 数字服务助手</b>\n\n"
        "我们提供以下服务：\n"
        "💎 Premium 会员直充\n"
        "⚡ TRON 能量兑换\n"
        "🔍 波场地址查询\n"
        "🎁 免费克隆服务\n"
        "💰 USDT 余额管理\n\n"
        "请选择下方功能开始使用 👇"
    )
    
    # 引流按钮配置（支持多行，每行最多2个按钮）
    # 格式：[{"text": "按钮文字", "url": "链接"}, ...]
    # url 可选，不填则为 callback_data
    promotion_buttons: str = (
        '[{"text": "💎 开通会员", "callback": "menu_premium"},'
        '{"text": "👤 个人中心", "callback": "menu_profile"}],'
        '[{"text": "⚡ 能量兑换", "callback": "menu_energy"},'
        '{"text": "🔍 地址查询", "callback": "menu_address_query"}],'
        '[{"text": "🎁 免费克隆", "callback": "menu_clone"},'
        '{"text": "👨‍💼 联系客服", "callback": "menu_support"}]'
    )
    
    # 客服联系方式配置
    support_contact: str = "@your_support_bot"  # 客服 Telegram 账号
    
    # FastAPI 管理后台配置（Stage 6-7）
    api_base_url: str = "http://localhost:8000"
    api_key: str = ""
    env: str = "dev"
    
    # API服务配置
    api_host: str = "0.0.0.0"
    api_port: int = 8001
    api_keys: list = []
    log_level: str = "INFO"
    log_json_format: bool = False
    database_url: str = Field(default="sqlite:///./data/bot.db", validation_alias="DATABASE_URL")

    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()
