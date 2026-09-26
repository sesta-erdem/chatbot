class ProviderError(Exception):
    """LLM sağlayıcısından gelen genel hata."""


class ProviderUnavailableError(ProviderError):
    """Sağlayıcı geçici olarak kullanılamıyor."""


class ProviderRateLimitError(ProviderError):
    """Sağlayıcının kota/rate-limit sınırına ulaşıldı."""


class ProviderRequestError(ProviderError):
    """Sağlayıcı isteği kabul etmedi."""
