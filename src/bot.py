import re
import discord
from discord.ext import commands
from src.database.db import RegrasDB

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
        
@bot.tree.command(name="add", description="Adiciona um item à lista")
async def add(
    interaction: discord.Interaction,
    canal: discord.TextChannel,
    regex: str,
    cargo: discord.Role
):
    if isinstance(interaction.user, discord.User) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Você não tem permissão!", ephemeral=True)
        return
    db.add_regra(interaction.guild_id, canal.id, regex, cargo.id)
    await interaction.response.send_message(
        f"Regra salva para {canal.mention} com regex `{regex}` e cargo {cargo.mention}"
    )

@bot.tree.command(name="list", description="lista as regras salvas")
async def list_rules(interaction: discord.Interaction):
    if isinstance(interaction.user, discord.User) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Você não tem permissão!", ephemeral=True)
        return
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
async def remove(interaction: discord.Interaction, id: int):
    if isinstance(interaction.user, discord.User) or not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Você não tem permissão!", ephemeral=True)
        return
    db.remove_regra(interaction.guild_id, id)
    await interaction.response.send_message(f"Regra com id `{id}` removida.")
    
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