import asyncio
from random import shuffle as shuffle_r, randint
import re
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from src.entity.AudioList import AudioListManager
from src.entity.SoundEffectListMemory import SoundEffectListMemory
from src.entity.JukeboxListMemory import JukeboxListMemory
from src.balanceador.ProcessadorHistoricoManager import ProcessadorHistoricoManager
from src.database.db import RegrasDB, MessagesDB
from src.mapas.mapa import mapa_links_padrao
from src.util.ProcessMensage import ProcessMensage
from src.util.ProcessOsaka import ProcessOsaka
from src.acl.YoutubeAcl import search_ytdlp_async
import sys
from urllib.parse import urlparse, parse_qs

DB = RegrasDB()

AUDIO_MANAGER = AudioListManager.from_db(DB.get_all_osaka_call_registers())
for manager_temp in AUDIO_MANAGER.audio_manager.values():
    lista = DB.get_osaka_ban_list(manager_temp.guild_id)
    AUDIO_MANAGER.set_sounds_ban_list(manager_temp.guild_id, lista)

processMsg = ProcessMensage(DB)
historico_manager = ProcessadorHistoricoManager(DB, 3)
messagesDB = MessagesDB()
osakaBot = ProcessOsaka(messagesDB, DB)

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
from src.audio.AudioPlayer import play_sound_effects_loop, play_songs_yt_loop, display_audio_queue

async def stdin_listener():
    """Listener simples de stdin: imprime cada linha lida."""
    loop = asyncio.get_running_loop()
    print("stdin listener iniciado")
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:  # EOF
                print("stdin: EOF recebido, encerrando listener")
                break
            command = line.rstrip()
            print(f"stdin: {command}")
            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    executable='/bin/bash'  # usa bash como shell
                )
                stdout, stderr = await proc.communicate()
                if stdout:
                    print(stdout.decode().rstrip())
                if stderr:
                    print(stderr.decode().rstrip(), file=sys.stderr)
                print(f"stdin: comando finalizado com exit code {proc.returncode}")
            except Exception as exec_err:
                print(f"Erro ao executar comando: {exec_err}")
        except Exception as e:
            print(f"Erro no stdin listener: {e}")
            await asyncio.sleep(1)

async def check_reconnecting():
    for manager in AUDIO_MANAGER.audio_manager.values():
        guild = bot.get_guild(manager.guild_id)
        channel_id = manager.get_manager().channel_id
        if not guild or not channel_id:
            continue

        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            continue

        perms = channel.permissions_for(guild.me)
        if not (perms and perms.connect and perms.speak):
            print(f"[Reconectar] Sem permissão para conectar/falar em guild={manager.guild_id} channel={channel_id}")
            continue
        try:
            vc = await channel.connect()
            print(f"[Reconectar] Conectado em guild={manager.guild_id} channel={channel_id}")
            if manager.check_audio_jukebox_empty():
                manager.set_audio_source("SOUND_EFFECT")

            mm = manager.get_manager()
            print("check_reconnecting: reiniciando loop de áudio da jukebox")
            if isinstance(mm, SoundEffectListMemory):
                mm.update_audio_task(
                    asyncio.create_task(play_sound_effects_loop(vc, manager.guild_id))
                )
            elif isinstance(manager, JukeboxListMemory) and len(manager.queue) > 0:
                manager.update_audio_task(
                    asyncio.create_task(play_songs_yt_loop(vc, manager.guild_id))
                )
        except Exception as e:
            print(f"[Reconectar] Falha ao conectar em guild={manager.guild_id} channel={channel_id}: {e}")

    
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} está online!') # type: ignore
    try:
        await bot.tree.sync()
        asyncio.create_task(stdin_listener())
        asyncio.create_task(check_reconnecting())
    except Exception as e:
        print(f'Erro ao sincronizar comandos: {e}')
        
@bot.event
async def on_guild_join(guild: discord.Guild):
    config = DB.get_config_by_guild(guild.id)
    
    if not config:
        DB.add_config(
            guild_id=guild.id,
            enable_fatos=False,
            random_user_enable=False,
            random_taxa=1.5,
            all_channel_enable=True,
            enable_security=True
        )
        [DB.set_url_config(guild.id, m["link"], m["tipo"]) for m in mapa_links_padrao]
        print(f"Configuração padrão criada para guild {guild.id}")

        
@bot.event
async def on_message(message: discord.Message):
    skip = False
    guild = message.guild
    regras = DB.get_regras_by_guild(guild.id if guild else 0)
    enable_osaka = DB.get_configs_by_tag(guild.id if guild else 0, "osaka_enable")
    
    for _, canal_id, regex, cargo_id in regras:
        if message.channel.id == canal_id:
            if re.search(regex, message.content) or regex.upper() in message.content.upper():
                cargo_mention = f"<@&{cargo_id}>"
                skip = True
                await message.channel.send(cargo_mention)
                return
            
    is_mentioned = bot.user in message.mentions if bot.user else False
    bot_user_id = bot.user.id if bot.user else 0
            
    await processMsg.process(message, skip, bot_user_id, is_mentioned)
    if enable_osaka and enable_osaka == "1" and message.author.id != bot_user_id:
        await osakaBot.process(message, is_mentioned)
    await bot.process_commands(message)
    
@bot.tree.command(name="add", description="Adiciona um item à lista")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    canal="Canal onde a regra será aplicada",
    regex="Regex para filtrar mensagens ou texto puro",
    cargo="Cargo a ser mencionado quando a regex for encontrada"
)
async def add(interaction: discord.Interaction, canal: discord.TextChannel, regex: str, cargo: discord.Role):
    DB.add_regra(interaction.guild_id, canal.id, regex, cargo.id)
    await interaction.response.send_message(
        f"Regra salva para {canal.mention} com regex `{regex}` e cargo {cargo.mention}"
    )

@bot.tree.command(name="list", description="lista as regras salvas")
@app_commands.checks.has_permissions(administrator=True)
async def list_rules(interaction: discord.Interaction):
    regras = DB.get_regras_by_guild(interaction.guild_id)
    if not regras:
        await interaction.response.send_message("Nenhuma regra cadastrada para este servidor.", ephemeral=True)
        return
    
    tabela = "**Canal | Regex | Cargo**\n"
    for id, canal_id, regex, cargo_id in regras:
        canal_mention = f"<#{canal_id}>"
        cargo_mention = f"<@&{cargo_id}>"
        tabela += f"{id} | {canal_mention} | `{regex}` | {cargo_mention}\n"

    await interaction.response.send_message(tabela)

@bot.tree.command(name="remove", description="Remove um item da lista por id")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(id="ID da regra a ser removida")
async def remove(interaction: discord.Interaction, id: int):
    DB.remove_regra(interaction.guild_id, id)
    await interaction.response.send_message(f"Regra com id `{id}` removida.")
    
@bot.tree.command(name="set_fatos_configs", description="Atualiza as configs do fatos_check para este servidor")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    enable_fatos="Ativar ou desativar o FatosCheckUp",
    random_user_enable="Ativar ou desativar usuários aleatórios",
    random_taxa="Taxa de drop para usuários aleatórios (0-100)",
    all_channel_enable="Observar todos os canais"
)
@app_commands.choices(
    enable_fatos=[
        app_commands.Choice(name="Ativar", value=1),
        app_commands.Choice(name="Desativar", value=0)
    ],
    random_user_enable=[
        app_commands.Choice(name="Ativar", value=1),
        app_commands.Choice(name="Desativar", value=0)
    ],
    all_channel_enable=[
        app_commands.Choice(name="Ativar", value=1),
        app_commands.Choice(name="Desativar", value=0)
    ]
)
async def set_fatos_configs(interaction: discord.Interaction,enable_fatos: int,random_user_enable: int,random_taxa: float,all_channel_enable: int):
    print(interaction.guild_id, enable_fatos, random_user_enable, random_taxa, all_channel_enable)
    DB.update_config(
        guild_id=interaction.guild_id,enable_fatos=enable_fatos,random_user_enable=random_user_enable,
        random_taxa=random_taxa,all_channel_enable=all_channel_enable,enable_security=True
    )
    await interaction.response.send_message("Configurações atualizadas com sucesso!")

@bot.tree.command(name="list_fatos_configs", description="Mostra as configs do fatos_check para este servidor")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_configs(interaction: discord.Interaction):
    config = DB.get_config_by_guild(interaction.guild_id)
    if not config:
        await interaction.response.send_message("Nenhuma configuração encontrada para este servidor.", ephemeral=True)
        return

    embed = discord.Embed(title="Configurações do Fatos",  color=discord.Color.yellow())
    embed.add_field(name="FatosCheckUp Ativo", value=str(bool(config[1])), inline=False)
    embed.add_field(name="Usuários aleatórios", value=str(bool(config[2])), inline=False)
    embed.add_field(name="DropRate para usuário aleatório", value=str(config[3]), inline=False)
    embed.add_field(name="Observar todos os canais", value=str(bool(config[4])), inline=False)
    embed.add_field(name="Configurações somente para ADM", value=str(bool(config[5])), inline=False)

    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="set_fatos_user", description="Configura um usuário para fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(usuario="Usuário a ser configurado",
    enable="Ativar ou desativar o usuário para fatos_check",
    drop_rate="Taxa de drop do usuário (chances que a mensagem pode receber um resposta) (0.0-100)",
    win_rate="Taxa de vitória (REAL) do usuário (0.01-99.99)"
)
@app_commands.choices(
    enable=[
        app_commands.Choice(name="Desativar", value=1),
        app_commands.Choice(name="Ativar", value=0)
    ]
)
async def set_fatos_user(interaction: discord.Interaction, usuario: discord.Member, enable: int, drop_rate: float, win_rate: float = 50.0):
    if drop_rate < 0 or drop_rate > 100:
        await interaction.response.send_message("O drop_rate deve ser entre 0.0 e 100.", ephemeral=True)
        return
    if win_rate < 0.01 or win_rate > 99.99:
        await interaction.response.send_message("O win_rate deve ser entre 0.01 e 99.99", ephemeral=True)
        return

    DB.set_user_config(
        user_id=usuario.id, guild_id=interaction.guild_id, nome=usuario.display_name,
        taxa=drop_rate, checking=win_rate, deny=enable
    )
    await interaction.response.send_message(f"Configuração do usuário {usuario.mention} atualizada com sucesso!")
    
@bot.tree.command(name="list_fatos_users", description="Lista as configs dos usuários do fatos_check para este servidor")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_users(interaction: discord.Interaction):
    users = DB.get_users_by_guild(interaction.guild_id)
    if not users:
        await interaction.response.send_message("Nenhum usuário configurado para este servidor.", ephemeral=True)
        return

    ativos = []
    desativados = []
    for _, user_id, _, _, taxa, checking, deny in users:
        linha = f"(<@{user_id}>) | DropRate: `{taxa}` | WinRate: `{checking}`"
        ativos.append(linha) if deny == 0 else desativados.append(linha)

    embed = discord.Embed(title="Configuração dos Usuários FatosCheck", color=discord.Color.yellow())
    embed.add_field(name="Ativos", value="\n" if ativos else "Nenhum usuário ativo.", inline=False)
    [embed.add_field(name="", value=ativo, inline=False) for ativo in ativos]
    embed.add_field(name="Desativados", value="\n" if desativados else "Nenhum usuário desativado.", inline=False)
    [embed.add_field(name="", value=desativado, inline=False) for desativado in desativados]
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="remove_fatos_user", description="Remove um usuário da configuração do fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(usuario="Usuário a ser removido das configs")
async def remove_fatos_user(interaction: discord.Interaction, usuario: discord.Member):
    DB.remove_user_config(user_id=usuario.id, guild_id=interaction.guild_id)
    await interaction.response.send_message(f"Usuário {usuario.mention} removido das configurações do fatos_check.", ephemeral=True)
    
@bot.tree.command(name="set_fatos_channel", description="Adiciona ou atualiza um canal na configuração do fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal a ser adicionado ou atualizado", ativo="Ativar ou desativar o canal para fatos_check")
@app_commands.choices(ativo=[
    app_commands.Choice(name="Ativar", value=1),
    app_commands.Choice(name="Desativar", value=0)
])
async def set_fatos_channel(interaction: discord.Interaction, canal: discord.TextChannel, ativo: int):
    DB.set_channel_config(id_channel=canal.id, id_guild=interaction.guild_id, allow=ativo)
    await interaction.response.send_message(f"Canal {canal.mention} {'ativado' if ativo else 'desativado'} para fatos_check.")

@bot.tree.command(name="list_fatos_channel", description="Lista os canais configurados para fatos_check")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_channel(interaction: discord.Interaction):
    canais = DB.get_channels_by_guild(interaction.guild_id)
    if not canais:
        await interaction.response.send_message("Nenhum canal configurado para fatos_check.", ephemeral=True)
        return
    ativos = []
    desativos = []
    for id_channel, allow in canais:
        canal_mention = f"<#{id_channel}>"
        ativos.append(canal_mention) if allow else desativos.append(canal_mention)
        
    embed = discord.Embed(title="Canais configurados para FatosCheck", color=discord.Color.yellow())
    embed.add_field(name="Ativos", value="\n" if ativos else "Nenhum canal ativo.", inline=False)
    [embed.add_field(name="", value=ati, inline=False) for ati in ativos]
    embed.add_field(name="Desativados", value="\n" if desativos else "Nenhum canal desativado.", inline=False)
    [embed.add_field(name="", value=desa, inline=False) for desa in desativos]
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_fatos_channel", description="Remove um canal da configuração do fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal a ser removido")
async def remove_fatos_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    DB.remove_channel_config(id_channel=canal.id, id_guild=interaction.guild_id)
    await interaction.response.send_message(f"Canal {canal.mention} removido das configurações do fatos_check.")
    
@bot.tree.command(name="set_fatos_image_url", description="Adicione uma URL de imagem para o banco de dados")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(url="URL da imagem", tipo="Real o Fake?")
@app_commands.choices(tipo=[
    app_commands.Choice(name="REAL", value="REAL"),
    app_commands.Choice(name="FAKE", value="FAKE"),
])
async def set_fatos_image_url(interaction: discord.Interaction, url: str, tipo: app_commands.Choice[str]):
    guild_id = str(interaction.guild_id)
    tipo_value = tipo.value
    
    exists = DB.check_url_exists(guild_id, url, tipo_value)
    if exists:
        await interaction.response.send_message("Esta URL já está registrada para este servidor!", ephemeral=True)
        return
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if not content_type.startswith("image/"):
                    await interaction.response.send_message("A URL não aponta para uma imagem!", ephemeral=True)
                    return
    except Exception as e:
        print(f"Erro na requisição: {e}")
        await interaction.response.send_message("Erro ao validar a URL!", ephemeral=True)
        return
    
    DB.set_url_config(id_guild=guild_id, url=url, tipo=tipo_value)
    await interaction.response.send_message("Imagem registrada com sucesso!", ephemeral=False)
    
@bot.tree.command(name="remove_fatos_image_url", description="Remove um imagem da configuração do fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(id="Imagem/url a ser removido (pege id em /list_fatos_urls)")
async def remove_fatos_image_url(interaction: discord.Interaction, id: int):
    guild_id = str(interaction.guild_id)
    DB.remove_url_config(id=id, id_guild=guild_id)
    await interaction.response.send_message(f"Imagem removido das configurações do fatos_check.")

@bot.tree.command(name="list_fatos_image_url", description="Liste as imagem da configuradas no fatos_check")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_image_url(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    res = DB.get_url_by_guild(guild_id)
    if not res:
        await interaction.response.send_message("Nenhuma imagem registrada para este servidor.", ephemeral=True)
        return

    real = []
    fake = []
    for id, guild_id, link, tipo in res:
        real.append(f"**ID:** {id} | **Link:** {link}") if tipo == "REAL" else fake.append(f"**ID:** {id} | **Link:** {link}")
    
    embed = discord.Embed( title="Imagens registradas para FatosCheck", color=discord.Color.yellow())
    embed.add_field(name="Real fotos", value="\n" if real else "Nenhum imagem do tipo REAL.", inline=False)
    [embed.add_field(name="", value=a, inline=False) for a in real]
    embed.add_field(name="Fake fotos", value="\n" if fake else "Nenhum imagem do tipo FAKE.", inline=False)
    [embed.add_field(name="", value=f, inline=False) for f in fake]
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="reset_fatos_image_url_to_default", description="Restaure as configs de image_url para padrão")
@app_commands.checks.has_permissions(administrator=True)
async def reset_fatos_image_url_to_default(interaction: discord.Interaction):
    [DB.set_url_config(interaction.guild_id, m["link"], m["tipo"]) for m in mapa_links_padrao]
    await interaction.response.send_message("Resetado!", ephemeral=True)

@bot.tree.command(name="set_osaka_configs", description="Configure essa copia de osaka")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(enable="Ativar osaka 2", rate="Taxa de drop do osaka (0-100)", tipo="Modus operandi do osaka")
@app_commands.choices(enable=[
    app_commands.Choice(name="Ativado", value=1),
    app_commands.Choice(name="Desativado", value=2)
])
@app_commands.choices(tipo=[
    app_commands.Choice(name="Todos", value="ALL"),
    app_commands.Choice(name="Lista Branca", value="WHITE"),
    app_commands.Choice(name="Lista negra", value="DENY")
])
async def set_osaka_configs(interaction: discord.Interaction, enable: app_commands.Choice[int], rate: float, tipo: app_commands.Choice[str]):
    guild_id = str(interaction.guild_id)
    enable_value = enable.value
    tipo_value = tipo.value
    if rate < 0 or rate > 100:
        await interaction.response.send_message("A taxa de drop deve ser entre 0.0 e 100.", ephemeral=True)
        return
    
    DB.set_config_by_tag(guild_id=guild_id, tag="osaka_enable", value=enable_value)
    DB.set_config_by_tag(guild_id=guild_id, tag="osaka_mode", value=tipo_value)
    DB.set_config_by_tag(guild_id=guild_id, tag="osaka_rate", value=rate)

    
    if enable_value == 1:
        await historico_manager.adicionar_guild(interaction.guild)
    
    await interaction.response.send_message("Configurações atualizadas com sucesso!", ephemeral=False)

@bot.tree.command(name="get_osaka_configs", description="Mostra as configs do osaka 2 para este servidor")
@app_commands.checks.has_permissions(administrator=True)
async def get_osaka_configs(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    enable = DB.get_configs_by_tag(guild_id, "osaka_enable")
    modus_op = DB.get_configs_by_tag(guild_id, "osaka_mode")
    rate = DB.get_configs_by_tag(guild_id, "osaka_rate")
    
    if enable is None or modus_op is None or rate is None:
        await interaction.response.send_message("Nenhuma configuração encontrada para este servidor.", ephemeral=True)
        return
    
    embed = discord.Embed(title="Configurações do osaka 2", color=discord.Color.yellow())
    embed.add_field(name="Ativado", value=str(bool(enable)), inline=False)
    embed.add_field(name="Modo Operacional", value=modus_op, inline=False)
    embed.add_field(name="Taxa de Drop", value=str(rate), inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="set_osaka_channel", description="Configure os canais para osaka")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal a ser adicionado ou atualizado", lista="Coloque na lista branca ou negra")
@app_commands.choices(lista=[
    app_commands.Choice(name="Lista Branca", value=0),
    app_commands.Choice(name="Lista Negra", value=1)
])
async def set_osaka_channel(interaction: discord.Interaction, canal: discord.TextChannel, lista: app_commands.Choice[int]):
    lista_value = lista.value
    DB.set_osaka_channel_config(id_channel=canal.id, id_guild=interaction.guild_id, allow=lista_value)
    if DB.get_configs_by_tag(interaction.guild_id, "osaka_enable") == 1:
        await historico_manager.adicionar_guild(interaction.guild)
    await interaction.response.send_message(f"Canal {canal.mention} configurado.")

@bot.tree.command(name="list_osaka_channel", description="Lista os canais configurados para osaka")
@app_commands.checks.has_permissions(administrator=True)
async def list_osaka_channel(interaction: discord.Interaction):
    canais = DB.get_osaka_channels_by_guild(interaction.guild_id)
    if not canais:
        await interaction.response.send_message("Nenhum canal configurado para fatos_check.", ephemeral=True)
        return
    lista_negra = []
    lista_branca = []
    for id_channel, allow in canais:
        canal_mention = f"<#{id_channel}>"
        lista_negra.append(canal_mention) if allow else lista_branca.append(canal_mention)
        
    embed = discord.Embed(title="Canais configurados para osaka", color=discord.Color.yellow())
    embed.add_field(name="Lista Negra (ignora quando modo DENY ativado)", value="\n" if lista_negra else "Nenhum canal negado.", inline=False)
    [embed.add_field(name="", value=ati, inline=False) for ati in lista_negra]
    embed.add_field(name="Lista Branca (Durante o modo WHITE, somente esses canais seram usados)", value="\n" if lista_branca else "Nenhum canal desativado.", inline=False)
    [embed.add_field(name="", value=desa, inline=False) for desa in lista_branca]
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="remove_osaka_channel", description="Remove um canal da configuração do osaka")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal a ser removido")
async def remove_osaka_channel(interaction: discord.Interaction, canal: discord.TextChannel):
    DB.remove_osaka_channels_by_guild(id_channel=canal.id, id_guild=interaction.guild_id)
    await interaction.response.send_message(f"Canal {canal.mention} removido das configurações do osaka.")
    
@bot.tree.command(name="call", description="Fazer o bot entrar no seu canal de voz")
@app_commands.checks.has_permissions(administrator=True)
async def call(interaction: discord.Interaction):
    await interaction.response.defer()

    if not interaction.guild:
        await interaction.followup.send("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        await interaction.followup.send("Não foi possível encontrar suas informações no servidor.", ephemeral=True)
        return
    
    voice_state = member.voice
    if not voice_state or not voice_state.channel:
        await interaction.followup.send("Você precisa estar em um canal de voz.", ephemeral=True)
        return

    channel = voice_state.channel
    perms = channel.permissions_for(interaction.guild.me) if interaction.guild else None
    if perms and (not perms.connect or not perms.speak):
        await interaction.followup.send("Não tenho permissão para conectar/falar neste canal.", ephemeral=True)
        return

    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.followup.send("ID do servidor não encontrado.", ephemeral=True)
        return
    
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if voice_client and not isinstance(voice_client, discord.VoiceClient):
        await interaction.followup.send("Cliente de voz incompatível.", ephemeral=True)
        return

    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, SoundEffectListMemory):
        await interaction.followup.send("Bot ocupado com Jukebox.", ephemeral=False)
        return

    AUDIO_MANAGER.set_channel_id(guild_id, channel.id)
    DB.set_osaka_call_register(guild_id, channel.id, 1)

    if voice_client and voice_client.is_connected():
        if voice_client.channel.id == channel.id:
            await interaction.followup.send(f"Já estou em {channel.mention}.", ephemeral=True)
            return
        await voice_client.move_to(channel)
        await interaction.followup.send(f"Movido para {channel.mention}.")
        print("Call: move")
        AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
    else:
        voice_client = await channel.connect()
        await interaction.followup.send(f"Entrei em {channel.mention}.")
    print("Call")
    manager.update_audio_task(
        bot.loop.create_task(play_sound_effects_loop(voice_client, guild_id))
    )

@bot.tree.command(name="disconnect", description="Desconectar o bot do canal de voz")
@app_commands.checks.has_permissions(administrator=True)
async def disconnect(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client if interaction.guild else None
    guild_id = interaction.guild_id
    DB.set_osaka_call_register(guild_id, 0, 0)

    if voice_client and not isinstance(voice_client, discord.VoiceClient):
        await interaction.response.send_message("Cliente de voz incompatível.", ephemeral=True)
        return

    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("Não estou em nenhum canal de voz.", ephemeral=True)
        return
    
    if not guild_id:
        await interaction.response.send_message("ID do servidor não encontrado.", ephemeral=True)
        return
    print("Disconnect: desconectando do canal de voz, asas")
    AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
    await voice_client.disconnect()
    await interaction.response.send_message("Desconectado do canal de voz.")

@bot.tree.command(name="reconnect", description="Reconectar o bot no canal de voz atual")
@app_commands.checks.has_permissions(administrator=True)
async def reconnect(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    voice_client = interaction.guild.voice_client
    if not voice_client or not isinstance(voice_client, discord.VoiceClient):
        await interaction.response.send_message("Não estou conectado em nenhum canal.", ephemeral=True)
        return
    
    channel = voice_client.channel
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.response.send_message("ID do servidor não encontrado.", ephemeral=True)
        return
    
    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    print("reconnect: delete - desconectando para reconectar no mesmo canal, ")
    manager.delete_audio_task()
    await voice_client.disconnect()
    await asyncio.sleep(1.0)
    
    new_voice_client = await channel.connect()
    await interaction.response.send_message(f"Reconectado em {channel.mention}.")
    AUDIO_MANAGER.set_channel_id(guild_id, channel.id)
    DB.set_osaka_call_register(guild_id, channel.id, 1)
    print("reconnect: reiniciando loop de áudio da jukebox")
    if isinstance(manager, SoundEffectListMemory):
        manager.update_audio_task(
            bot.loop.create_task(play_sound_effects_loop(new_voice_client, guild_id))
        )
    else:
        manager.update_audio_task(
            bot.loop.create_task(play_songs_yt_loop(new_voice_client, guild_id))
        )

@bot.tree.command(name="next-sound-effect", description="Pula para o próximo Efeito Sonoro")
async def next_sound_effect(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.response.send_message("Comando só disponível em servidores.", ephemeral=True)
        return
    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, SoundEffectListMemory):
        await interaction.response.send_message("Este comando só pode ser usado quando o bot estiver em modo de Efeitos Sonoros.", ephemeral=True)
        return
    
    if manager.audio_tasks is None:
        await interaction.response.send_message("Nenhuma reprodução ativa neste servidor.", ephemeral=True)
        return
    
    # tenta parar o áudio atual (se estiver tocando) para forçar o after_callback
    voice_client = interaction.guild.voice_client if interaction.guild else None
    if voice_client and isinstance(voice_client, discord.VoiceClient) and voice_client.is_playing():
        voice_client.stop()
    # seta o evento de skip (se existir) para interromper o delay
    if manager.audio_skip_events:
        manager.audio_skip_events.set()
        print(f"[Guild {guild_id}] Evento de skip setado para avançar para o próximo áudio")
    await interaction.response.send_message("Pulando para o próximo áudio...", ephemeral=False)

@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    if not bot.user or member.id != bot.user.id:
        return
    
    if before.channel and after.channel and before.channel.id != after.channel.id:
        guild_id = member.guild.id
        print(f"[Guild {guild_id}] Bot movido de {before.channel.name} para {after.channel.name}")
        
        AUDIO_MANAGER.set_channel_id(guild_id, after.channel.id)
        DB.set_osaka_call_register(guild_id, after.channel.id, 1)
        
        manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
        if manager.audio_tasks:
            print(f"[Guild {guild_id}] Áudio continua no novo canal")
    
    elif before.channel and not after.channel:
        guild_id = member.guild.id
        print(f"[Guild {guild_id}] Bot foi desconectado/kickado de {before.channel.name}")
        AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
        DB.set_osaka_call_register(guild_id, 0, 0)

def get_yt_url_id(texto: str) -> str:
    valor = texto.strip()
    if not valor:
        return valor

    candidato = valor
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", candidato):
        if not candidato.startswith(("youtube.com/", "www.youtube.com/", "m.youtube.com/", "music.youtube.com/", "youtu.be/")):
            return valor
        candidato = "https://" + candidato

    try:
        parsed = urlparse(candidato)
        host = (parsed.netloc or "").lower()
        path = parsed.path or ""

        if host in {"youtu.be", "www.youtu.be"}:
            vid = path.lstrip("/").split("/")[0]
            return vid if vid else valor

        if host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
            if path == "/watch":
                vid = parse_qs(parsed.query).get("v", [None])[0]
                return vid if vid else valor

            if path.startswith("/shorts/"):
                vid = path.split("/shorts/", 1)[1].split("/", 1)[0]
                return vid if vid else valor

        return valor
    except Exception:
        return valor

@bot.tree.command(name="play", description="Sons da plataforma vermelha.")
@app_commands.describe(song_query="URL ou título da música a ser tocada")
async def play(interaction: discord.Interaction, song_query: str):
    await interaction.response.defer()

    if not interaction.guild:
        await interaction.followup.send("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        await interaction.followup.send("Não foi possível encontrar suas informações no servidor.", ephemeral=True)
        return
    
    voice_state = member.voice
    if not voice_state or not voice_state.channel:
        await interaction.followup.send("Você precisa estar em um canal de voz.", ephemeral=True)
        return

    channel = voice_state.channel
    perms = channel.permissions_for(interaction.guild.me) if interaction.guild else None
    if perms and (not perms.connect or not perms.speak):
        await interaction.followup.send("Não tenho permissão para conectar/falar neste canal.", ephemeral=True)
        return

    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.followup.send("ID do servidor não encontrado.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client if interaction.guild else None
    if voice_client and not isinstance(voice_client, discord.VoiceClient):
        await interaction.followup.send("Cliente de voz incompatível.", ephemeral=True)
        return

    AUDIO_MANAGER.set_audio_source(guild_id, "JUKEBOX")
    AUDIO_MANAGER.set_channel_id(guild_id, channel.id)
    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, JukeboxListMemory):
        await interaction.followup.send("Problema secreto da secreta.", ephemeral=True)
        return
    DB.set_osaka_call_register(guild_id, channel.id, 1)

    if not manager.channel_id_msg:
        manager.channel_id_msg = interaction.channel_id

    is_playlist = "list=" in song_query or "/playlist" in song_query
    query =  song_query if is_playlist else f"ytsearch1:{song_query}"
    tracks = await search_ytdlp_async(query, is_playlist)

    if not tracks or len(tracks) < 1:
        await interaction.followup.send("Nenhum resultado encontrado.")
        return
    
    for track in tracks:
        url = track.id
        if manager.song_is_currently_playing(url) or manager.song_is_in_queue(url):
            await interaction.followup.send("A música solicitada já está tocando ou na fila.", ephemeral=True)
            return
        
    await display_audio_queue(tracks[0], interaction, True)
    [manager.add_song_to_queue(track) for track in tracks]

    isPlaying = manager.audio_tasks is not None
    if voice_client and voice_client.is_connected():
        if voice_client.channel.id != channel.id:
            await voice_client.move_to(channel)
            await interaction.followup.send(f"Movido para {channel.mention}.")
    else:
        voice_client = await channel.connect()
        await interaction.followup.send(f"Entrei em {channel.mention}.")
    
    await display_audio_queue(tracks[0], interaction, True)
    if not isPlaying:
        print("play: iniciando loop de áudio da jukebox")
        manager.update_audio_task(
            bot.loop.create_task(play_songs_yt_loop(voice_client, guild_id))
        )
    
@bot.tree.command(name="shuffle", description="Aleatoriza a fila de músicas da plataforma vermelha.")
async def shuffle(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.followup.send("ID do servidor não encontrado.", ephemeral=True)
        return

    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, JukeboxListMemory):
        await interaction.response.send_message("Este comando só pode ser usado quando o bot estiver em modo de Jukebox.", ephemeral=True)
        return
    
    if len(manager.queue) < 2:
        await interaction.response.send_message("É necessário ter pelo menos 2 músicas na fila para embaralhar.", ephemeral=True)
        return
    
    current_song = manager.current_song
    for _ in range(0, randint(2, 15)):
        shuffle_r(manager.queue)

    if current_song:
        manager.queue.insert(0, current_song)

    await interaction.response.send_message("Fila embaralhada!", ephemeral=False)

@bot.tree.command(name="clear_queue", description="Limpa a fila de músicas da plataforma vermelha.")
async def clear_queue(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.followup.send("ID do servidor não encontrado.", ephemeral=True)
        return

    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, JukeboxListMemory):
        await interaction.response.send_message("Este comando só pode ser usado quando o bot estiver em modo de Jukebox.", ephemeral=True)
        return
    
    AUDIO_MANAGER.delete_manager_by_guild_id(guild_id)
    await interaction.response.send_message("Fila limpa e bot desconectado do canal de voz.", ephemeral=False)

@bot.tree.command(name="queue", description="Mostra a fila de músicas da plataforma vermelha.")
async def queue(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.followup.send("ID do servidor não encontrado.", ephemeral=True)
        return

    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, JukeboxListMemory):
        await interaction.response.send_message("Este comando só pode ser usado quando o bot estiver em modo de Jukebox.", ephemeral=True)
        return
    
    if not manager.current_song and len(manager.queue) == 0:
        await interaction.response.send_message("Nenhuma música está tocando e a fila está vazia.", ephemeral=True)
        return
    
    embed = discord.Embed(title="Fila de Músicas da Plataforma Vermelha", color=discord.Color.red())
    if manager.current_song:
        embed.add_field(name="Tocando Agora", value=f"**{manager.current_song.title}**", inline=False)

    if len(manager.queue) > 0:
        queue_list = ""
        for idx, song in enumerate(list(manager.queue)[:10]):
            queue_list += f"**{idx + 1}. {song.title}**\n"
        if len(manager.queue) > 10:
            queue_list += f"...e mais {len(manager.queue) - 10} músicas na fila."
        embed.add_field(name="Próximas na Fila", value=queue_list, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="skip", description="Pula para a próxima música da plataforma vermelha.")
async def skip(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("Este comando só pode ser usado em servidores.", ephemeral=True)
        return
    
    guild_id = interaction.guild_id
    if not guild_id:
        await interaction.followup.send("ID do servidor não encontrado.", ephemeral=True)
        return

    manager = AUDIO_MANAGER.get_manager_by_guild_id(guild_id)
    if not isinstance(manager, JukeboxListMemory):
        await interaction.response.send_message("Este comando só pode ser usado quando o bot estiver em modo de Jukebox.", ephemeral=True)
        return
    
    if not manager.current_song and len(manager.queue) == 0:
        await interaction.response.send_message("Nenhuma música está tocando e a fila está vazia.", ephemeral=True)
        return

    voice_client = interaction.guild.voice_client if interaction.guild else None
    if not isinstance(voice_client, discord.VoiceClient) or not voice_client.is_connected():
        await interaction.response.send_message("Não estou conectado em um canal de voz.", ephemeral=True)
        return
    
    if not voice_client or not voice_client.is_connected():
        await interaction.response.send_message("Não estou conectado em um canal de voz.", ephemeral=True)
        return

    if voice_client.is_paused():
        voice_client.resume()

    if voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("Pulando para a próxima música...", ephemeral=False)
    else:
        await interaction.response.send_message("Não há música tocando no momento.", ephemeral=True)