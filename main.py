from currency_bot import CurrencyBot
from config import TOKEN

def main():
    bot = CurrencyBot(TOKEN)  # Создание экземпляра бота
    bot.run()  # Запуск бота

if __name__ == '__main__':
    main()
