"""Trade templates — multi-trade global registry."""

from app.domain.trades.registry import (
    TradeContext,
    TradeTemplate,
    get_trade_template,
    list_trade_options,
    resolve_trade_context,
)

__all__ = [
    "TradeContext",
    "TradeTemplate",
    "get_trade_template",
    "list_trade_options",
    "resolve_trade_context",
]
