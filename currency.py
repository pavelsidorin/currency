class Currency:
    """Класс для представления валюты."""

    def __init__(self, name: str, code: str, rate: float) -> None:
        """Инициализация объекта Currency с заданными параметрами."""
        self.name = name  # Название валюты
        self.code = code  # Код валюты
        self.rate = rate  # Курс валюты

    def __str__(self) -> str:
        """Возвращает строкову с объектами Currency."""
        return f'{self.name} ({self.code}): {self.rate}'
