import os
import logging
import asyncio
from datetime import datetime, timedelta

import functions_framework
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Configuração de logs
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Carregar variáveis de ambiente do .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
NOME_PLANILHA = os.getenv("NOME_PLANILHA")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def conectar_planilha():
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open(NOME_PLANILHA).sheet1


def criar_aplicacao():
    if not TOKEN:
        raise ValueError("ERRO: TELEGRAM_TOKEN não foi configurado.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("semanal", relatorio_semanal))
    app.add_handler(CommandHandler("mensal", relatorio_mensal))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_lancamento)
    )
    return app


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = (
        "👋 **Bot de Controle Financeiro**\n\n"
        "**Como registrar lançamentos:**\n"
        "• **Despesa:** `Almoço 35.50` ou `Mercado 120`\n"
        "• **Receita:** `Salário +3000` ou `Pix +50`\n\n"
        "**Comandos de Relatório:**\n"
        "• `/semanal` - Resumo dos últimos 7 dias\n"
        "• `/mensal` - Resumo do mês atual"
    )
    await update.message.reply_text(texto, parse_mode="Markdown")


async def registrar_lancamento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_mensagem = update.message.text.strip()
    partes = texto_mensagem.rsplit(" ", 1)

    if len(partes) != 2:
        await update.message.reply_text(
            "⚠️ **Formato inválido!**\nUse: `Descrição Valor` (ex: `Lanche 25` ou `Freelance +200`)"
        )
        return

    descricao, valor_str = partes
    valor_str = valor_str.replace(",", ".")

    if valor_str.startswith("+"):
        tipo = "Receita"
        valor_str = valor_str.lstrip("+")
    else:
        tipo = "Despesa"

    try:
        valor = float(valor_str)
    except ValueError:
        await update.message.reply_text("⚠️ Por favor, insira um valor numérico válido.")
        return

    try:
        sheet = conectar_planilha()
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Insere na ordem: Data, Descrição, Valor, Tipo
        sheet.append_row([data_hora, descricao, valor, tipo])

        icone = "🟢" if tipo == "Receita" else "🔴"
        await update.message.reply_text(
            f"{icone} **{tipo} registrada!**\n"
            f"• **Descrição:** {descricao}\n"
            f"• **Valor:** R$ {valor:.2f}",
            parse_mode="Markdown",
        )
    except Exception as e:
        logging.error(f"Erro ao salvar: {e}")
        await update.message.reply_text("❌ Ocorreu um erro ao salvar na planilha.")


# --- RELATÓRIO SEMANAL ---
async def relatorio_semanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Calculando relatório semanal...")
    try:
        sheet = conectar_planilha()
        registros = sheet.get_all_values()

        if len(registros) <= 1:
            await update.message.reply_text("Nenhum lançamento encontrado.")
            return

        hoje = datetime.now()
        limite_semana = hoje - timedelta(days=7)

        total_receitas = 0.0
        total_despesas = 0.0

        # Pula a primeira linha (cabeçalho)
        for linha in registros[1:]:
            if len(linha) < 4:
                continue

            data_str, _, valor_str, tipo = linha[0], linha[1], linha[2], linha[3]

            try:
                # Extrai apenas a data (ignorando a hora caso exista)
                data_item = datetime.strptime(data_str.split(" ")[0], "%d/%m/%Y")
                valor = float(valor_str.replace(",", "."))

                if data_item >= limite_semana:
                    if tipo == "Receita":
                        total_receitas += valor
                    else:
                        total_despesas += valor
            except ValueError:
                continue

        saldo = total_receitas - total_despesas

        mensagem = (
            "📊 **Relatório dos Últimos 7 Dias**\n\n"
            f"🟢 **Receitas:** R$ {total_receitas:.2f}\n"
            f"🔴 **Despesas:** R$ {total_despesas:.2f}\n"
            f"---------------------------\n"
            f"💰 **Saldo da Semana:** R$ {saldo:.2f}"
        )
        await update.message.reply_text(mensagem, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Erro no relatório semanal: {e}")
        await update.message.reply_text("❌ Erro ao gerar o relatório semanal.")


# --- RELATÓRIO MENSAL ---
async def relatorio_mensal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Calculando relatório mensal...")
    try:
        sheet = conectar_planilha()
        registros = sheet.get_all_values()

        if len(registros) <= 1:
            await update.message.reply_text("Nenhum lançamento encontrado.")
            return

        hoje = datetime.now()
        mes_atual = hoje.month
        ano_atual = hoje.year

        total_receitas = 0.0
        total_despesas = 0.0

        for linha in registros[1:]:
            if len(linha) < 4:
                continue

            data_str, _, valor_str, tipo = linha[0], linha[1], linha[2], linha[3]

            try:
                data_item = datetime.strptime(data_str.split(" ")[0], "%d/%m/%Y")
                valor = float(valor_str.replace(",", "."))

                if data_item.month == mes_atual and data_item.year == ano_atual:
                    if tipo == "Receita":
                        total_receitas += valor
                    else:
                        total_despesas += valor
            except ValueError:
                continue

        saldo = total_receitas - total_despesas

        mensagem = (
            f"📅 **Relatório do Mês ({mes_atual:02d}/{ano_atual})**\n\n"
            f"🟢 **Receitas:** R$ {total_receitas:.2f}\n"
            f"🔴 **Despesas:** R$ {total_despesas:.2f}\n"
            f"---------------------------\n"
            f"💰 **Saldo do Mês:** R$ {saldo:.2f}"
        )
        await update.message.reply_text(mensagem, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Erro no relatório mensal: {e}")
        await update.message.reply_text("❌ Erro ao gerar o relatório mensal.")


async def processar_update(dados_update):
    app = criar_aplicacao()
    inicializada = False
    iniciada = False

    try:
        await app.initialize()
        inicializada = True
        await app.start()
        iniciada = True

        update = Update.de_json(dados_update, app.bot)
        await app.process_update(update)
    finally:
        try:
            if iniciada:
                await app.stop()
        finally:
            if inicializada:
                await app.shutdown()


@functions_framework.http
def telegram_webhook(request):
    """Recebe e processa um update enviado pelo webhook do Telegram."""
    if request.method != "POST":
        return ("Método não permitido", 405)

    dados_update = request.get_json(silent=True)
    if not isinstance(dados_update, dict):
        return ("Corpo JSON inválido", 400)

    asyncio.run(processar_update(dados_update))

    return ("", 200)