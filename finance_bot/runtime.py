import asyncio
import logging
import threading

import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from finance_bot.handlers import (
    registrar_lancamento,
    relatorio_mensal,
    relatorio_semanal,
    start,
)
from finance_bot.settings import TELEGRAM_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

_RUNTIME_LOCK = threading.Lock()
_EVENT_LOOP = None
_APPLICATION = None
_STARTUP_FUTURE = None


def criar_aplicacao():
    if not TELEGRAM_TOKEN:
        raise ValueError("ERRO: TELEGRAM_TOKEN não foi configurado.")

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("semanal", relatorio_semanal))
    application.add_handler(CommandHandler("mensal", relatorio_mensal))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_lancamento)
    )
    return application


def _executar_event_loop(event_loop):
    asyncio.set_event_loop(event_loop)
    event_loop.run_forever()


async def _inicializar_aplicacao(application):
    await application.initialize()
    await application.start()
    logging.info("Telegram application started")


def obter_runtime():
    global _EVENT_LOOP, _APPLICATION, _STARTUP_FUTURE

    with _RUNTIME_LOCK:
        if _APPLICATION is None:
            application = criar_aplicacao()
            event_loop = asyncio.new_event_loop()
            loop_thread = threading.Thread(
                target=_executar_event_loop,
                args=(event_loop,),
                name="telegram-event-loop",
                daemon=True,
            )
            loop_thread.start()

            _APPLICATION = application
            _EVENT_LOOP = event_loop
            _STARTUP_FUTURE = asyncio.run_coroutine_threadsafe(
                _inicializar_aplicacao(application), event_loop
            )

    return _APPLICATION, _EVENT_LOOP, _STARTUP_FUTURE


async def processar_update(application, dados_update):
    update = Update.de_json(dados_update, application.bot)
    await application.process_update(update)
