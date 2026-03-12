import asyncio
import os
import discord
from src.util.AudioUtils import get_audio_duration
from src.entity.SoundEffectListMemory import SoundEffectListMemory
from src.bot import AUDIO_MANAGER, bot, DB

FFMPEG_PATH = os.path.join(os.path.dirname(__file__), 'bin', 'ffmpeg').replace('src/audio/', '').replace('src\\audio\\', '')
if os.name == 'nt':  # Windows
    FFMPEG_PATH += '.exe'
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
            if isinstance(manager, SoundEffectListMemory):
                manager.update_audio_task(
                    bot.loop.create_task(play_sound_effects_loop(vc, guild_id))
                )
            else:
                ...
            return
        except Exception as e:
            print(f"[Guild {guild_id}] Falha na reconexão: {e}")

    AUDIO_MANAGER.set_channel_id(guild_id, 0)
    DB.set_osaka_call_register(guild_id, 0, 0)  
    print(f"[Guild {guild_id}] Falha ao reconectar após {max_retries} tentativas")

async def play_sound_effects_loop(voice_client: discord.VoiceClient, guild_id: int):
    try:
        while voice_client.is_connected():
            manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
            if not isinstance(manager, SoundEffectListMemory):
                print(f"[Guild {guild_id}] Manager de áudio não encontrado, encerrando loop")
                return
            current_manager = manager
            if not voice_client.is_playing() and not voice_client.is_paused():
                if current_manager.audio_event_is_set():
                    current_manager.audio_event_clear()
                audio_filepath = AUDIO_MANAGER.get_next_song(guild_id)
                print(f"Caminho do áudio: {audio_filepath}")

                current_manager.audio_player_clear()
                def after_callback(error):
                    if error:
                        print(f"[Guild {guild_id}] Erro no áudio: {error}")
                    bot.loop.call_soon_threadsafe(current_manager.audio_player_ending)
                
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
                    DB.set_osaka_ban_list(current_manager.guild_id, current_manager.audio_ban_list)
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
        print(f"[Guild {guild_id}] Conexão de voz fechada (code {e.code}): {e}")
        AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
        await attempt_voice_reconnect(guild_id)
    except Exception as e:
        print(f"[Guild {guild_id}] Erro no loop de áudio: {e}")
    finally:
        if voice_client.is_playing():
            voice_client.stop()
        AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
        print(f"[Guild {guild_id}] Cleanup do áudio concluído")

async def play_songs_yt_loop(voice_client: discord.VoiceClient, guild_id: int):
    ...