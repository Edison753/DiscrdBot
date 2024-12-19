import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
import os


# Carrega o token do arquivo .env
load_dotenv(".env")
TOKEN: str = os.getenv("TOKEN")

# Configura os intents e inicializa o bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    print(f'O {bot.user} está online!')


# Comando para tocar uma música
@bot.command()
async def play(ctx, url: str):
    # Verifica se o usuário está em um canal de voz
    if not ctx.author.voice:
        await ctx.send(
            "Você precisa estar em um canal de voz para usar este comando!")
        return

    # Conecta o bot ao canal de voz do usuário
    voice_channel = ctx.author.voice.channel
    if not ctx.voice_client:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    # Obtém o URL de stream
    ydl_opts = {"format": "bestaudio/best", "quiet": True}
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info["url"]
        song_title = info.get("title", "música")

    # Reproduz o áudio diretamente
    vc.play(discord.FFmpegPCMAudio(stream_url), after=lambda e: print(
        f"{song_title} acabou de tocar!", e))
    vc.source = discord.PCMVolumeTransformer(vc.source)
    vc.source.volume = 0.05

    await ctx.send(f"Tocando agora: **{song_title}**")


# Comando para desconectar o bot do canal de voz
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Desconectado do canal de voz.")
    else:
        await ctx.send("Eu não estou em nenhum canal de voz.")


bot.run(TOKEN)
