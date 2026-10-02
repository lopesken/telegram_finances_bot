import asyncio

import functions_framework

from finance_bot.runtime import obter_runtime, processar_update


@functions_framework.http
def telegram_webhook(request):
    if request.method != "POST":
        return ("Método não permitido", 405)

    dados_update = request.get_json(silent=True)
    if not isinstance(dados_update, dict):
        return ("Corpo JSON inválido", 400)

    application, event_loop, startup_future = obter_runtime()
    startup_future.result()

    update_future = asyncio.run_coroutine_threadsafe(
        processar_update(application, dados_update), event_loop
    )
    update_future.result()

    return ("OK", 200)
