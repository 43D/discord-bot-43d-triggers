import asyncio
import os
import discord
from src.entity.YouTube.YouTubeEntity import YouTubeMetadata, YouTubeMetadataLazy
from src.util.AudioUtils import get_audio_duration
from src.entity.SoundEffectListMemory import SoundEffectListMemory
from src.entity.JukeboxListMemory import JukeboxListMemory
from src.bot import AUDIO_MANAGER, bot, DB
from src.acl.YoutubeAcl import search_ytdlp_async

FFMPEG_PATH = os.path.join(os.path.dirname(__file__), 'bin', 'ffmpeg').replace('src/audio/', '').replace('src\\audio\\', '')
print(FFMPEG_PATH)

async def attempt_voice_reconnect(guild_id: int, max_retries: int = 3):
    """Tenta reconectar ao canal de voz após desconexão"""
    guild = bot.get_guild(guild_id)
    if not guild: return
    
    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    
    if not manager.channel_id or manager.channel_id < 1:
        register = DB.get_osaka_call_register(guild_id)
        if not register or not register[1]:  # channel_id
            print(f"[Guild {guild_id}] Sem canal registrado para reconexão")
            return
        AUDIO_MANAGER.set_channel_id(guild_id, register[1])
    if not manager.channel_id or manager.channel_id < 1:
        return
    channel = guild.get_channel(manager.channel_id)
    if not channel or not isinstance(channel, discord.VoiceChannel):
        return
    
    for attempt in range(max_retries):
        try:
            print(f"[Guild {guild_id}] Tentativa de reconexão {attempt + 1}/{max_retries}")
            await asyncio.sleep(2 ** attempt)  # Backoff exponencial
            vc = await channel.connect()
            print(f"[Guild {guild_id}] Reconectado com sucesso!")
            print("attempt_voice_reconnect")
            if isinstance(manager, SoundEffectListMemory):
                manager.update_audio_task(
                    bot.loop.create_task(play_sound_effects_loop(vc, guild_id))
                )
            else:
                manager.update_audio_task(
                    bot.loop.create_task(play_songs_yt_loop(vc, guild_id))
                )
            return
        except Exception as e:
            print(f"[Guild {guild_id}] Falha na reconexão: {e}")

    AUDIO_MANAGER.set_channel_id(guild_id, 0)
    DB.set_osaka_call_register(guild_id, 0, 0)  
    print(f"[Guild {guild_id}] Falha ao reconectar após {max_retries} tentativas")

async def play_sound_effects_loop(voice_client: discord.VoiceClient, guild_id: int):
    try:
        while voice_client.is_connected() and AUDIO_MANAGER.get_audio_source(guild_id) == "SOUND_EFFECT":
            manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
            if not isinstance(manager, SoundEffectListMemory):
                print(f"[Guild {guild_id}] Manager de áudio não encontrado, encerrando loop")
                return
            current_manager = manager
            if not voice_client.is_playing() and not voice_client.is_paused():
                if current_manager.audio_event_is_set():
                    current_manager.audio_event_clear()
                current_manager.audio_player_clear()

                def after_callback(error):
                    if error:
                        print(f"[Guild {guild_id}] Erro no áudio: {error}")
                    bot.loop.call_soon_threadsafe(current_manager.audio_player_ending)

                audio_filepath = AUDIO_MANAGER.get_next_song(guild_id)
                print(f"Caminho do áudio: {audio_filepath}")

                try:
                    audio_source = discord.FFmpegOpusAudio(
                        audio_filepath,
                        executable=FFMPEG_PATH,
                        before_options='-nostdin',
                        options='-vn'
                    )
                    
                    voice_client.play(audio_source, after=after_callback)
                    print(f"[Guild {guild_id}] Tocando áudio...", audio_filepath)
                    
                    try:
    
                        await current_manager.audio_player_await(get_audio_duration(audio_filepath))
                    except asyncio.TimeoutError:
                        print(f"[Guild {guild_id}] Timeout ao aguardar término do áudio")
                        if voice_client.is_playing():
                            voice_client.stop()
                        continue
                    await DB.set_osaka_ban_list_async(current_manager.guild_id, current_manager.audio_ban_list)
                    await current_manager.await_event()
                    
                except Exception as audio_error:
                    print(f"[Guild {guild_id}] Erro ao criar/tocar áudio: {audio_error}")
                    await asyncio.sleep(2.0)
                continue
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        print(f"[Guild {guild_id}] Loop de áudio cancelado")
        if voice_client.is_playing():
            voice_client.stop()
        await asyncio.sleep(2)
        raise
    except discord.errors.ConnectionClosed as e:
        print(f"[Guild {guild_id}] ==Conexão de voz fechada (code {e.code}): {e}")
        AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
        await attempt_voice_reconnect(guild_id)
    except Exception as e:
        print(f"[Guild {guild_id}] Erro no loop de áudio: {e}")
    finally:
        print(f"[Guild {guild_id}] Cleanup do áudio concluídowasdssadasd")
        manager = AUDIO_MANAGER.get_by_guild_id(guild_id)
        if manager.audio_source == "SOUND_EFFECT":
            if voice_client.is_playing():
                voice_client.stop()
            AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
            print(f"[Guild {guild_id}] Cleanup do áudio concluído")

async def play_songs_yt_loop(voice_client: discord.VoiceClient, guild_id: int):
    manager = None
    try:
        while voice_client.is_connected() and AUDIO_MANAGER.get_audio_source(guild_id) == "JUKEBOX":
            await asyncio.sleep(2)
            manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
            if not isinstance(manager, JukeboxListMemory):
                print(f"[Guild {guild_id}] Manager de áudio não encontrado, encerrando loop2")
                return
            current_manager = manager

            if not voice_client.is_playing() and not voice_client.is_paused():
                if current_manager.audio_event_is_set():
                    current_manager.audio_event_clear()
                current_manager.audio_player_clear()

                def after_callback(error):
                    print("After call")
                    if error:
                        print(f"[Guild {guild_id}] Erro no áudio: {error}")
                    bot.loop.call_soon_threadsafe(current_manager.audio_player_ending)

                song_entries = manager.get_next_song()
                if not song_entries:
                    manager.finish()
                    AUDIO_MANAGER.set_audio_source(guild_id, "SOUND_EFFECT")
                    break
                
                if isinstance(song_entries, YouTubeMetadataLazy):
                    res = await search_ytdlp_async(f"ytsearch1:{song_entries.id}")
                    if not res or len(res) < 1:
                        print(f"[Guild {guild_id}] Nenhum resultado encontrado para {song_entries.id}")
                        continue
                    song_entries = res[0]

                try:
                    audio_source = discord.FFmpegOpusAudio(
                        song_entries.url,
                        executable=FFMPEG_PATH,
                        before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                        options='-vn'
                    )
                    manager.current_song = song_entries
                    voice_client.play(audio_source, after=after_callback)
                    print(f"[Guild {guild_id}] Tocando áudio...", song_entries.webpage_url if isinstance(song_entries, YouTubeMetadata) else song_entries.url)
                    try:
                        await display_audio_queue(song_entries, None, False, guild_id, current_manager.channel_id_msg)
                        await current_manager.audio_player_await(float(song_entries.duration or 0))
                    except asyncio.TimeoutError:
                        print(f"[Guild {guild_id}] Timeout ao aguardar término do áudio")
                        if voice_client.is_playing():
                            voice_client.stop()
                        continue
                except Exception as audio_error:
                    print(f"[Guild {guild_id}] Erro ao criar/tocar áudio: {audio_error}")
                    await asyncio.sleep(2.0)
                continue

    except asyncio.CancelledError as e:
        print(e)
        print(f"[Guild {guild_id}] Loop de áudio cancelado")
        raise
    except discord.errors.ConnectionClosed as e:
        print(f"[Guild {guild_id}] Conexão de voz fechada (code {e.code}): {e}")
        print(f"dsfdsfdsfsdf")
        AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
        if manager and isinstance(manager, JukeboxListMemory):
            manager.finish()
        AUDIO_MANAGER.set_audio_source(guild_id, "SOUND_EFFECT")
        await attempt_voice_reconnect(guild_id)
    except Exception as e:
        print(f"[Guild {guild_id}] Erro no loop de áudio: {e}")
    finally:
        gerencia = AUDIO_MANAGER.get_by_guild_id(guild_id)
        if gerencia.audio_source == "JUKEBOX":
            if voice_client.is_playing():
                voice_client.stop()
            AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
            if manager and isinstance(manager, JukeboxListMemory):
                manager.finish()
            AUDIO_MANAGER.set_audio_source(guild_id, "SOUND_EFFECT")
            print(f"[Guild {guild_id}] Cleanup do áudio concluído")
            await attempt_voice_reconnect(guild_id)

async def display_audio_queue(song_entries: YouTubeMetadata | YouTubeMetadataLazy, interaction: discord.Interaction | None, ephemeral: bool = False, guild_id: int | None = None, channel_id: int | None = None):
    webpage_url = song_entries.webpage_url if isinstance(song_entries, YouTubeMetadata) else song_entries.url
    thumbnail_URL = song_entries.thumbnails[-1].url if song_entries.thumbnails else None

    hours, remainder = divmod(int(song_entries.duration or 0), 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

    embed = discord.Embed(
        title=song_entries.title,
        url=webpage_url or None,
        color=discord.Color.red()
    )
    embed.set_author(name=song_entries.channel)
    embed.add_field(name="Duração", value=duration_str, inline=True)
    msg = "> Add queue" if ephemeral else "> play now"
    embed.add_field(name="", value=msg, inline=True)
    if thumbnail_URL:
        embed.set_thumbnail(url=thumbnail_URL)

    if interaction:
        await interaction.followup.send(embed=embed, ephemeral=ephemeral)
        return
    
    if guild_id and channel_id:
        guild = bot.get_guild(guild_id)
        if not guild: return
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        await channel.send(embed=embed)