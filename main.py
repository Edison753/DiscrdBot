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

# Playlists (global para cada servidor)
playlists = {}


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


@bot.command()
async def create_playlist(ctx, playlist_name: str):
    guild_id = ctx.guild.id
    if guild_id not in playlists:
        playlists[guild_id] = {}

    if playlist_name in playlists[guild_id]:
        await ctx.send(f"A playlist **{playlist_name}** já existe!")
    else:
        playlists[guild_id][playlist_name] = []
        await ctx.send(f"Playlist **{playlist_name}** criada com sucesso!")


@bot.command()
async def add_to_playlist(ctx, playlist_name: str, *, query: str):
    guild_id = ctx.guild.id
    if guild_id not in playlists or playlist_name not in playlists[guild_id]:
        await ctx.send(
            (f"A playlist **{playlist_name}** não existe. "
                f"Use `!create_playlist` para criá-la.")
        )
        return

    # Configurações do yt_dlp para busca
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
            playlists[guild_id][playlist_name].append(song_data)
            await ctx.send(
                f"Música **{song_data['title']}** adicionada à playlist "
                f"**{playlist_name}**!"
            )
    except Exception as e:
        await ctx.send(f"Erro ao adicionar música à playlist: {str(e)}")


@bot.command()
async def show_playlist(ctx, playlist_name: str):
    guild_id = ctx.guild.id
    if guild_id not in playlists or playlist_name not in playlists[guild_id]:
        await ctx.send(f"A playlist **{playlist_name}** não existe.")
        return

    playlist = playlists[guild_id][playlist_name]
    if not playlist:
        await ctx.send(f"A playlist **{playlist_name}** está vazia.")
    else:
        song_list = [
            f"{i + 1}. {song['title']}" for i, song in enumerate(playlist)]
        await ctx.send(
            f"Playlist **{playlist_name}**:\n" + "\n".join(song_list))


@bot.command()
async def play_playlist(ctx, playlist_name: str):
    guild_id = ctx.guild.id
    if guild_id not in playlists or playlist_name not in playlists[guild_id]:
        await ctx.send(f"A playlist **{playlist_name}** não existe.")
        return

    playlist = playlists[guild_id][playlist_name]
    if not playlist:
        await ctx.send(f"A playlist **{playlist_name}** está vazia.")
        return

    if not ctx.author.voice:
        await ctx.send(
            "Você precisa estar em um canal de voz para usar este comando!")
        return

    voice_channel = ctx.author.voice.channel
    if not ctx.voice_client:
        vc = await voice_channel.connect()
    else:
        vc = ctx.voice_client

    # Adiciona todas as músicas da playlist à fila
    if guild_id not in music_queues:
        music_queues[guild_id] = deque()

    for song in playlist:
        music_queues[guild_id].append(song)

    await ctx.send(f"Tocando a playlist **{playlist_name}**!")
    if not vc.is_playing():
        play_next(vc, guild_id)


# Comando para deletar uma música de uma playlist
@bot.command()
async def delete_song(ctx, playlist_name: str):
    guild_id = ctx.guild.id
    if guild_id not in playlists or playlist_name not in playlists[guild_id]:
        await ctx.send(f"A playlist **{playlist_name}** não existe.")
        return

    playlist = playlists[guild_id][playlist_name]
    if not playlist:
        await ctx.send(f"A playlist **{playlist_name}** está vazia.")
        return

    # Exibe as músicas da playlist enumeradas
    song_list = [
        f"{i + 1}. {song['title']}" for i, song in enumerate(playlist)]
    await ctx.send(f"Playlist **{playlist_name}**:\n" + "\n".join(song_list))
    await ctx.send("Digite o número da música que você deseja deletar:")

    # Aguarda a resposta do usuário
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        response = await bot.wait_for("message", check=check, timeout=30.0)
        choice = int(response.content)

        if choice < 1 or choice > len(playlist):
            await ctx.send("Número inválido. Operação cancelada.")
            return

        selected_song = playlist[choice - 1]

        # Confirmação de exclusão
        await ctx.send(
            f"Você deseja deletar **{selected_song['title']}**? "
            f"(Responda com `sim` ou `não`)")

        confirmation = await bot.wait_for("message", check=check, timeout=30.0)
        if confirmation.content.lower() == "sim":
            del playlist[choice - 1]
            await ctx.send(
                f"Música **{selected_song['title']}** deletada da playlist **"
                f"{playlist_name}**.")
        else:
            await ctx.send("Operação cancelada.")
    except ValueError:
        await ctx.send("Por favor, digite um número válido.")
    except TimeoutError:
        await ctx.send("Tempo esgotado. Operação cancelada.")


# Comando para selecionar e tocar uma playlist
@bot.command()
async def show_all_playlists(ctx):
    guild_id = ctx.guild.id
    if guild_id not in playlists or not playlists[guild_id]:
        await ctx.send("Não há playlists disponíveis no momento.")
        return

    # Exibe todas as playlists enumeradas
    playlist_names = list(playlists[guild_id].keys())
    enumerated_playlists = [
        f"{i + 1}. {name}" for i, name in enumerate(playlist_names)]
    await ctx.send(
        "Playlists disponíveis:\n" + "\n".join(enumerated_playlists))
    await ctx.send("Digite o número da playlist que você deseja tocar:")

    # Aguarda a resposta do usuário
    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    try:
        response = await bot.wait_for("message", check=check, timeout=30.0)
        choice = int(response.content)

        if choice < 1 or choice > len(playlist_names):
            await ctx.send("Número inválido. Operação cancelada.")
            return

        selected_playlist_name = playlist_names[choice - 1]
        await ctx.send(
            f"Você deseja tocar a playlist **{selected_playlist_name}**?"
            f"(Responda com `sim` ou `não`)")

        confirmation = await bot.wait_for("message", check=check, timeout=30.0)
        if confirmation.content.lower() == "sim":
            await play_playlist(ctx, selected_playlist_name)
        else:
            await ctx.send("Operação cancelada.")
    except ValueError:
        await ctx.send("Por favor, digite um número válido.")
    except TimeoutError:
        await ctx.send("Tempo esgotado. Operação cancelada.")


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
