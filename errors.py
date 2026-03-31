"""
Centralized Error Messages for ViraBot
Provides consistent, localized error messages across all handlers
"""

# Standard error messages (all languages)
import contextlib

ERROR_MESSAGES = {
    "generic_error": {
        "tr": "⚠️ Bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
        "en": "⚠️ An error occurred. Please try again later.",
        "ru": "⚠️ Произошла ошибка. Попробуйте позже.",
    },
    "network_error": {
        "tr": "🌐 Bağlantı hatası. İnternet bağlantınızı kontrol edin.",
        "en": "🌐 Connection error. Please check your internet.",
        "ru": "🌐 Ошибка соединения. Проверьте интернет.",
    },
    "timeout_error": {
        "tr": "⏱️ İstek zaman aşımına uğradı. Tekrar deneyin.",
        "en": "⏱️ Request timed out. Please try again.",
        "ru": "⏱️ Время ожидания истекло. Попробуйте снова.",
    },
    "api_error": {
        "tr": "🔌 Servis şu anda kullanılamıyor.",
        "en": "🔌 Service is currently unavailable.",
        "ru": "🔌 Сервис временно недоступен.",
    },
    "permission_denied": {
        "tr": "🚫 Bu işlem için yetkiniz yok.",
        "en": "🚫 You don't have permission for this action.",
        "ru": "🚫 У вас нет прав для этого действия.",
    },
    "invalid_input": {
        "tr": "❌ Geçersiz giriş. Lütfen kontrol edin.",
        "en": "❌ Invalid input. Please check and try again.",
        "ru": "❌ Неверный ввод. Проверьте и попробуйте снова.",
    },
    "file_too_large": {
        "tr": "📦 Dosya çok büyük. Maksimum 50MB.",
        "en": "📦 File is too large. Maximum 50MB.",
        "ru": "📦 Файл слишком большой. Максимум 50МБ.",
    },
    "rate_limited": {
        "tr": "⏳ Çok fazla istek. Lütfen {seconds} saniye bekleyin.",
        "en": "⏳ Too many requests. Please wait {seconds} seconds.",
        "ru": "⏳ Слишком много запросов. Подождите {seconds} секунд.",
    },
    "not_found": {"tr": "🔍 Bulunamadı.", "en": "🔍 Not found.", "ru": "🔍 Не найдено."},
    "maintenance": {
        "tr": "🔧 Bakım modu. Kısa süre içinde geri döneceğiz.",
        "en": "🔧 Maintenance mode. We'll be back soon.",
        "ru": "🔧 Режим обслуживания. Скоро вернёмся.",
    },
    "cancelled_action": {"tr": "❌ İşlem iptal edildi.", "en": "❌ Action cancelled.", "ru": "❌ Действие отменено."},
    "database_error": {
        "tr": "💾 Veritabanı hatası. Lütfen tekrar deneyin.",
        "en": "💾 Database error. Please try again.",
        "ru": "💾 Ошибка базы данных. Попробуйте снова.",
    },
    "session_expired": {
        "tr": "⌛ Oturumunuz sona erdi. Lütfen baştan başlayın.",
        "en": "⌛ Your session has expired. Please start again.",
        "ru": "⌛ Сессия истекла. Начните заново.",
    },
}


def get_error_message(error_type: str, lang: str = "en", **kwargs) -> str:
    """
    Get localized error message.

    Args:
        error_type: Key from ERROR_MESSAGES
        lang: Language code (tr, en, ru)
        **kwargs: Format parameters (e.g., seconds=30)

    Returns:
        Formatted error message
    """
    if error_type not in ERROR_MESSAGES:
        error_type = "generic_error"

    messages = ERROR_MESSAGES[error_type]
    message = messages.get(lang, messages["en"])

    if kwargs:
        with contextlib.suppress(KeyError, ValueError):
            message = message.format(**kwargs)

    return message


def log_error_with_context(logger, error: Exception, context: dict) -> None:
    """
    Log error with standardized context.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Dict with user_id, handler_name, etc.
    """
    user_id = context.get("user_id", "unknown")
    handler = context.get("handler", "unknown")
    action = context.get("action", "unknown")

    logger.error(
        f"[{handler}] Error for user {user_id} during {action}: {type(error).__name__}: {error}", exc_info=True
    )
