import logging
import requests
from typing import Dict, Optional

from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

from config import CURRENCY_URL, TOKEN
from currency import Currency
from currency_history import CurrencyHistory

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class CurrencyBot:
    """Телеграм-бот для получения курсов валют и конвертации сумм."""

    def __init__(self, token: str) -> None:
        """Инициализация бота с заданным токеном."""
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher

        # Словарь для хранения истории курсов валют
        self.currency_histories: Dict[str, CurrencyHistory] = {}

        # Регистрация обработчиков команд
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("rates", self.get_rates))
        self.dispatcher.add_handler(CommandHandler("convert", self.convert_currency))
        self.dispatcher.add_handler(CommandHandler("history", self.get_history))
        self.dispatcher.add_handler(MessageHandler(Filters.command, self.get_currency_rate_by_command))

    def run(self) -> None:
        """Запуск бота."""
        self.updater.start_polling()
        logger.info("Бот запущен.")
        self.updater.idle()

    def start(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /start. Отправляет приветственное сообщение."""
        user = update.effective_user
        update.message.reply_markdown_v2(
            fr'Привет, {user.mention_markdown_v2()}\! Я могу предоставить текущие курсы валют и конвертировать суммы\. Используйте команду /rates для получения курсов, /convert для конвертации, или отправьте команду вида /USD, /EUR и т.д. для получения курса конкретной валюты\.',
            reply_markup=ForceReply(selective=True),
        )

    def fetch_currency_rates(self) -> Optional[Dict[str, Currency]]:
        """Получение текущих курсов валют с сайта ЦБ"""
        try:
            response = requests.get(CURRENCY_URL)
            response.raise_for_status()
            data = response.content.decode('windows-1251')  # Кодировка данных от ЦБ РФ
            from xml.etree import ElementTree as ET

            tree = ET.fromstring(data)
            currencies = {}
            for valute in tree.findall('Valute'):
                code = valute.find('CharCode').text
                name = valute.find('Name').text
                value = float(valute.find('Value').text.replace(',', '.'))
                nominal = int(valute.find('Nominal').text)
                rate = value / nominal
                currencies[code] = Currency(name, code, rate)

                # Обновляем историю для каждой валюты
                if code not in self.currency_histories:
                    self.currency_histories[code] = CurrencyHistory(code)
                self.currency_histories[code].add_rate(rate)

            return currencies
        except Exception as e:
            logger.error(f"Ошибка при получении курсов валют: {e}")
            return None

    def get_rates(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /rates. Отправляет текущие курсы валют в рублях."""
        currencies = self.fetch_currency_rates()
        if not currencies:
            update.message.reply_text("Не удалось получить курсы валют. Попробуйте позже.")
            return

        message = "Текущие курсы валют в рублях:\n"
        for currency in currencies.values():
            message += f"{currency}\n"
        update.message.reply_text(message)

    def get_currency_rate_by_command(self, update: Update, context: CallbackContext) -> None:
        """Универсальный обработчик для кода валюты."""
        try:
            # Извлекаем текст команды, например /USD
            command = update.message.text.strip('/').upper()

            # Проверяем, что команда состоит из 3 букв
            if len(command) != 3 or not command.isalpha():
                update.message.reply_text("Неизвестная команда.")
                return

            currencies = self.fetch_currency_rates()
            if not currencies:
                update.message.reply_text("Не удалось получить курс валюты. Попробуйте позже.")
                return

            currency: Optional[Currency] = currencies.get(command)
            if not currency:
                update.message.reply_text("Курс для данной валюты не найден.")
                return

            message = f"Текущий курс {currency.name} ({currency.code}): {currency.rate} RUB"
            update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /{command}: {e}")
            update.message.reply_text("Произошла ошибка при обработке запроса.")

    def get_history(self, update: Update, context: CallbackContext) -> None:
        """Обработчик команды /history. Отправляет историю курсов валют."""
        try:
            args = context.args
            if len(args) != 1:
                update.message.reply_text(
                    "Использование: /history <код валюты>\nПример: /history USD"
                )
                return

            currency_code = args[0].upper()

            if currency_code not in self.currency_histories:
                update.message.reply_text("История для данной валюты отсутствует.")
                return

            history = self.currency_histories[currency_code].get_history()
            if not history:
                update.message.reply_text("История пустая.")
                return

            message = f"История курсов {currency_code}:\n"
            for record in history:
                rate = record['rate']
                timestamp = record['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                message += f"{timestamp}: {rate} RUB\n"
            update.message.reply_text(message)
        except Exception as e:
            logger.error(f"Ошибка при обработке команды /history: {e}")
            update.message.reply_text("Произошла ошибка при получении истории курсов.")

    def convert_currency(self, update: Update, context: CallbackContext) -> None:
        """
        Обработчик команды /convert. Конвертирует сумму из одной валюты в другую.
        Использование: /convert (сумма) (из валюты) (в валюту)
        Пример: /convert 100 USD EUR
        """
        try:
            args = context.args
            if len(args) != 3:
                update.message.reply_text(
                    "Использование: /convert (сумма) (из валюты) (в валюту)\nПример: /convert 100 USD EUR"
                )
                return

            amount_str, from_currency_code, to_currency_code = args
            amount = float(amount_str)
            currencies = self.fetch_currency_rates()
            if not currencies:
                update.message.reply_text("Не удалось получить курсы валют")
                return

            from_currency: Optional[Currency] = currencies.get(from_currency_code.upper())
            to_currency: Optional[Currency] = currencies.get(to_currency_code.upper())

            if not from_currency or not to_currency:
                update.message.reply_text(
                    "Некорректный код валюты, используйте коды (например, USD, EUR)."
                )
                return

            # Конвертация суммы в рубли, затем в целевую валюту
            amount_in_rub = amount * from_currency.rate
            converted_amount = amount_in_rub / to_currency.rate
            update.message.reply_text(
                f"{amount} {from_currency.code} = {converted_amount:.2f} {to_currency.code}"
            )
        except ValueError:
            update.message.reply_text("Сумма должна быть числом")
        except Exception as e:
            logger.error("Ошибка")
            update.message.reply_text("Произошла ошибка")
