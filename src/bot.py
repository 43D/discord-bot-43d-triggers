import re
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from src.database.db import RegrasDB
from src.mapas.mapa import mapa_links_padrao

db = RegrasDB()
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
data_list = []

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} está online!') # type: ignore
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f'Erro ao sincronizar comandos: {e}')
        
@bot.event
async def on_guild_join(guild: discord.Guild):
    config = db.get_config_by_guild(guild.id)
    if not config:
        db.add_config(
            guild_id=guild.id,
            enable_fatos=False,
            random_user_enable=False,
            random_taxa=1.5,
            all_channel_enable=True,
            enable_security=True
        )
        [db.set_url_config(guild.id, m["link"], m["tipo"]) for m in mapa_links_padrao]
        print(f"Configuração padrão criada para guild {guild.id}")
    
@bot.event
async def on_message(message: discord.Message):
    guild = message.guild
    regras = db.get_regras_by_guild(guild.id if guild else 0)
    for _, canal_id, regex, cargo_id in regras:
        if message.channel.id == canal_id:
            if re.search(regex, message.content) or regex.upper() in message.content.upper():
                cargo_mention = f"<@&{cargo_id}>"
                await message.channel.send(cargo_mention)
                break  # Só marca uma vez por mensagem
    await bot.process_commands(message)
    
@bot.tree.command(name="add", description="Adiciona um item à lista")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(
    canal="Canal onde a regra será aplicada",
    regex="Regex para filtrar mensagens ou texto puro",
    cargo="Cargo a ser mencionado quando a regex for encontrada"
)
async def add(interaction: discord.Interaction, canal: discord.TextChannel, regex: str, cargo: discord.Role):
    db.add_regra(interaction.guild_id, canal.id, regex, cargo.id)
    await interaction.response.send_message(
        f"Regra salva para {canal.mention} com regex `{regex}` e cargo {cargo.mention}"
    )

@bot.tree.command(name="list", description="lista as regras salvas")
@app_commands.checks.has_permissions(administrator=True)
async def list_rules(interaction: discord.Interaction):
    regras = db.get_regras_by_guild(interaction.guild_id)
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
    db.remove_regra(interaction.guild_id, id)
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
    db.update_config(
        guild_id=interaction.guild_id,enable_fatos=enable_fatos,random_user_enable=random_user_enable,
        random_taxa=random_taxa,all_channel_enable=all_channel_enable,enable_security=True
    )
    await interaction.response.send_message("Configurações atualizadas com sucesso!")

@bot.tree.command(name="list_fatos_configs", description="Mostra as configs do fatos_check para este servidor")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_configs(interaction: discord.Interaction):
    config = db.get_config_by_guild(interaction.guild_id)
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

    db.set_user_config(
        user_id=usuario.id, guild_id=interaction.guild_id, nome=usuario.display_name,
        taxa=drop_rate, checking=win_rate, deny=enable
    )
    await interaction.response.send_message(f"Configuração do usuário {usuario.mention} atualizada com sucesso!")
    
@bot.tree.command(name="list_fatos_users", description="Lista as configs dos usuários do fatos_check para este servidor")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_users(interaction: discord.Interaction):
    users = db.get_users_by_guild(interaction.guild_id)
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
    db.remove_user_config(user_id=usuario.id, guild_id=interaction.guild_id)
    await interaction.response.send_message(f"Usuário {usuario.mention} removido das configurações do fatos_check.", ephemeral=True)
    
@bot.tree.command(name="set_fatos_channel", description="Adiciona ou atualiza um canal na configuração do fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(canal="Canal a ser adicionado ou atualizado", ativo="Ativar ou desativar o canal para fatos_check")
@app_commands.choices(ativo=[
    app_commands.Choice(name="Ativar", value=1),
    app_commands.Choice(name="Desativar", value=0)
])
async def set_fatos_channel(interaction: discord.Interaction, canal: discord.TextChannel, ativo: int):
    db.set_channel_config(id_channel=canal.id, id_guild=interaction.guild_id, allow=ativo)
    await interaction.response.send_message(f"Canal {canal.mention} {'ativado' if ativo else 'desativado'} para fatos_check.")

@bot.tree.command(name="list_fatos_channel", description="Lista os canais configurados para fatos_check")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_channel(interaction: discord.Interaction):
    canais = db.get_channels_by_guild(interaction.guild_id)
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
    db.remove_channel_config(id_channel=canal.id, id_guild=interaction.guild_id)
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
    
    exists = db.check_url_exists(guild_id, url, tipo_value)
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
    
    db.set_url_config(id_guild=guild_id, url=url, tipo=tipo_value)
    await interaction.response.send_message("Imagem registrada com sucesso!", ephemeral=False)
    
@bot.tree.command(name="remove_fatos_image_url", description="Remove um imagem da configuração do fatos_check")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(id="Imagem/url a ser removido (pege id em /list_fatos_urls)")
async def remove_fatos_image_url(interaction: discord.Interaction, id: int):
    guild_id = str(interaction.guild_id)
    db.remove_url_config(id=id, id_guild=guild_id)
    await interaction.response.send_message(f"Imagem removido das configurações do fatos_check.")

@bot.tree.command(name="list_fatos_image_url", description="Liste as imagem da configuradas no fatos_check")
@app_commands.checks.has_permissions(administrator=True)
async def list_fatos_image_url(interaction: discord.Interaction):
    guild_id = str(interaction.guild_id)
    res = db.get_url_by_guild(guild_id)
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
    [db.set_url_config(interaction.guild_id, m["link"], m["tipo"]) for m in mapa_links_padrao]
    await interaction.response.send_message("Resetado!", ephemeral=True)
