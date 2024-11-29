from currency_bot import CurrencyBot
from config import TOKEN

if __name__ == '__main__':
    bot = CurrencyBot(TOKEN)  # Создание экземпляра бота
    bot.run()  # Запуск бота
