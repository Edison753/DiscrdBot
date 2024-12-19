import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
from dotenv import load_dotenv
from collections import deque
import os


# Carrega o token do arquivo .env
load_dotenv(".env")
TOKEN: str = os.getenv("TOKEN")

# Configura os intents e inicializa o bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Fila de músicas (global para cada servidor)
music_queues = {}


@bot.event
async def on_ready():
    print(f'O {bot.user} está online!')


def play_next(vc, guild_id):
    # Reproduz a próxima música na fila.
    if music_queues[guild_id]:
        next_song = music_queues[guild_id].popleft()
        vc.play(
            discord.FFmpegPCMAudio(next_song["url"]),
            after=lambda e: play_next(vc, guild_id),
        )
        vc.source = discord.PCMVolumeTransformer(vc.source)
        vc.source.volume = 0.5
        print(f"Reproduzindo: {next_song['title']}")
    else:
        print("Fila vazia. Desconectando do canal.")
        bot.loop.create_task(vc.disconnect())


# Adiciona uma música à fila ou inicia a reprodução
@bot.command()
async def play(ctx, *, query: str):
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

    # Inicializa a fila para o servidor, se ainda não existir
    guild_id = ctx.guild.id
    if guild_id not in music_queues:
        music_queues[guild_id] = deque()

    # Configurações para permitir busca por termos não so url
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "default_search": "ytsearch",
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0]

            song_data = {
                "url": info["url"],
                "title": info.get("title", "música"),
            }

            music_queues[guild_id].append(song_data)

            if not vc.is_playing():
                await ctx.send(
                    f"Iniciando reprodução de: **{song_data['title']}**")
                play_next(vc, guild_id)
            else:
                await ctx.send(
                    f"Música adicionada à fila: **{song_data['title']}**")
    except Exception as e:
        await ctx.send(f"Erro ao tentar adicionar música: {str(e)}")


# Comando para mostrar as músicas na fila
@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id not in music_queues or not music_queues[guild_id]:
        await ctx.send("A fila está vazia.")
        return

    queue_list = [f"{i + 1}. {song['title']}" for i, song in enumerate(
        music_queues[guild_id])]
    await ctx.send("Fila atual:\n" + "\n".join(queue_list))


# Comando para pular a música atual
@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Música atual pulada.")
    else:
        await ctx.send("Não há música tocando no momento.")


# Comando para pausar a música
@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Áudio pausado.")
    else:
        await ctx.send("Não há áudio tocando no momento.")


# Comando para retomar a música
@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Áudio retomado.")
    else:
        await ctx.send("O áudio não está pausado no momento.")


# Comando para desconectar o bot do canal de voz
@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Desconectado do canal de voz.")
    else:
        await ctx.send("Eu não estou em nenhum canal de voz.")


bot.run(TOKEN)
