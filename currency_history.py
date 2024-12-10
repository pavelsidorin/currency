from datetime import datetime
from typing import List, Dict, Optional, Any


class CurrencyHistory:
    """Класс для хранения истории курсов валюты."""

    def __init__(self, currency_code: str) -> None:
        """Инициализация объекта CurrencyHistory с заданным кодом валюты."""
        self.currency_code: str = currency_code  # Код валюты
        self.history: List[Dict[str, Any]] = []  # История курсов валюты

    def add_rate(self, rate: float) -> None:
        """Добавить новый курс в историю с меткой времени."""
        self.history.append({'rate': rate, 'timestamp': datetime.now()})

    def get_history(self) -> List[Dict[str, Any]]:
        """Вернуть список с историей курсов валюты."""
        return self.history

    def get_latest_rate(self) -> Optional[float]:
        """Вернуть последний курс из истории, если он есть."""
        if self.history:
            return self.history[-1]['rate']
        return None
