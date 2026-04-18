import asyncio, re, httpx, base64
from telethon import TelegramClient, events
from telegram import Bot
from dotenv import load_dotenv
import os

load_dotenv()


API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
TELEFONE = os.getenv("TELEFONE")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CANAL = int(os.getenv("CANAL_ID"))
AMAZON_TAG = os.getenv("AMAZON_TAG")
SHOPEE_ID = os.getenv("SHOPEE_ID")
ML_ID = os.getenv("ML_ID")
ML_TOOL = os.getenv("ML_TOOL")
ALIEXPRESS_SK = os.getenv("ALIEXPRESS_SK")


CANAIS_MONITORAR = [
    "SamuelF3lipePromo",
]

bot = Bot(token=TOKEN)
mensagens_enviadas = set()

async def expandir_link(url):
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
            resp = await client.head(url)
            return str(resp.url)
    except:
        return url

async def converter_link_async(url):
    if "amzn.to" in url or "s.shopee.com.br" in url or "mercadolivre.com/s/" in url or "s.click.aliexpress.com" in url or "meli.la" in url:
        url = await expandir_link(url)

    if "amazon" in url or "amzn" in url:
        url = re.sub(r'([?&])tag=[^&]+', '', url)
        url = re.sub(r'[?&]$', '', url)
        if "?" in url:
            return f"{url}&tag={AMAZON_TAG}"
        else:
            return f"{url}?tag={AMAZON_TAG}"
    elif "shopee" in url or "s.shopee" in url:
        url = url.split("?")[0]
        return f"{url}?af_id={SHOPEE_ID}"
    elif "mercadolivre" in url or "mercadolibre" in url or "mlb" in url or "meli.la" in url or "mercadolivre.com/social" in url:
        url = url.split("?")[0]
        return f"{url}?matt_word={ML_ID}&matt_tool={ML_TOOL}"
    elif "aliexpress" in url:
        url = url.split("?")[0]
        return f"{url}?aff_fcid={ALIEXPRESS_SK}&tt=CPS_NORMAL&aff_fsk={ALIEXPRESS_SK}&sk={ALIEXPRESS_SK}"
    return url

async def converter_todos_links(texto):
    urls = re.findall(r'https?://\S+', texto)
    tasks = []
    urls_limpas = []
    for url in urls:
        url_limpa = re.sub(r'[\)\]\>\"\,]+$', '', url)
        urls_limpas.append(url_limpa)
        tasks.append(converter_link_async(url_limpa))

    novos = await asyncio.gather(*tasks)

    for url_limpa, novo in zip(urls_limpas, novos):
        texto = texto.replace(url_limpa, novo)
    return texto

async def enviar_whatsapp(texto, foto_bytes=None):
    try:
        payload = {"texto": texto}
        if foto_bytes:
            payload["imagem"] = base64.b64encode(foto_bytes).decode('utf-8')
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post("http://localhost:3000/repostar", json=payload)
            print(f"WhatsApp respondeu: {resp.status_code}")
    except Exception as e:
        print(f"Erro ao enviar no WhatsApp: {e}")

async def repostar(msg_id, texto, foto_bytes=None):
    if msg_id in mensagens_enviadas:
        return
    mensagens_enviadas.add(msg_id)

    texto_convertido = await converter_todos_links(texto)
    try:
        if foto_bytes:
            await bot.send_photo(
                chat_id=CANAL,
                photo=foto_bytes,
                caption=texto_convertido
            )
        else:
            await bot.send_message(
                chat_id=CANAL,
                text=texto_convertido
            )
        print(f"Repostado Telegram: {texto_convertido[:60]}...")
    except Exception as e:
        print(f"Erro ao repostar no Telegram: {e}")

    await enviar_whatsapp(texto_convertido, foto_bytes)

async def main():
    print("Iniciando cliente Telegram...")
    client = TelegramClient("sessao_bot", API_ID, API_HASH)
    await client.start(phone=TELEFONE)
    print("Conectado! Monitorando canais...")

    @client.on(events.NewMessage(chats=CANAIS_MONITORAR, incoming=True))
    async def handler(event):
        msg = event.message
        texto = msg.message or ""

        foto_bytes = None
        if msg.photo:
            foto_bytes = await msg.download_media(bytes)

        if not texto and not foto_bytes:
            return

        await repostar(msg.id, texto, foto_bytes)

    @client.on(events.MessageEdited(chats=CANAIS_MONITORAR))
    async def handler_editado(event):
        msg = event.message
        texto = msg.message or ""

        foto_bytes = None
        if msg.photo:
            foto_bytes = await msg.download_media(bytes)

        if not texto and not foto_bytes:
            return

        await repostar(msg.id, texto, foto_bytes)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
