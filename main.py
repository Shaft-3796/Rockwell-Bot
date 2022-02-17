from datetime import datetime
import json
import os
import time
from discord.ext import commands
from discord.ext import tasks
import discord
from github import Github
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from webserver import keep_alive
import traceback


# Functions
def build_key(message):
    return str(message.guild.id) + str(message.channel.id) + str(message.author.id)


async def send(author, **kwargs):
    try:
        if "message" in kwargs and "file" in kwargs:
            await author.send(kwargs["message"], file=kwargs["file"])
        elif "message" in kwargs:
            await author.send(kwargs["message"])
        elif "file" in kwargs:
            await author.send(file=kwargs["file"])

    except:
        print("[INX log] error in sending a message to ", author.name)


async def update_files():
    # update file
    json_data = json.dumps(data, indent=2)
    write_file("data.json", json_data)
    json_data = json.dumps(config, indent=2)
    write_file("config.json", json_data)
    json_data = json.dumps(alerted, indent=2)
    write_file("alerted.json", json_data)


def create_file(name, content):
    if not file_exist(name):
        repo.create_file(name, "CREATION", content)


def delete_file(name):
    if file_exist(name):
        content = repo.get_contents(name)
        repo.delete_file(content.path, "REMOVE", content.sha)


def write_file(name, content):
    delete_file(name)
    create_file(name, content)


def file_exist(name):
    for file in repo.get_contents(""):
        if file.name == name:
            return True
    return False


def read_file(name):
    if file_exist(name):
        for file in repo.get_contents(""):
            if file.name == name:
                return file.decoded_content
    return ""


def parse(to_parse):
    to_parse = to_parse.replace(">", "")
    to_parse = to_parse.replace("<#", "")
    to_parse = to_parse.replace("<@!", "")
    return to_parse


def check_for_content(message):
    return len(message.content) > int(config[str(message.guild.id) + "config"][2])


def get_vip_image():
    get_images()
    with open('vip.png', 'rb') as f:
        return discord.File(f)


def get_vipm_image():
    get_images()
    with open('vipm.png', 'rb') as f:
        return discord.File(f)


def get_vipmm_image():
    get_images()
    with open('vipmm.png', 'rb') as f:
        return discord.File(f)


def get_breedmap_image():
    get_images()
    with open('breedmap.png', 'rb') as f:
        return discord.File(f)


def get_images(force=False):
    if not force:
        if os.path.isfile("vip.png") and os.path.isfile("vipm.png") and os.path.isfile("vipmm.png") and os.path.isfile(
                "breedmap.png") and os.path.isfile("cross.png"):
            return

    # DOWNLOAD
    open('vip.png', 'wb').write(read_file("vip.png"))
    open('vipm.png', 'wb').write(read_file("vipm.png"))
    open('vipmm.png', 'wb').write(read_file("vipmm.png"))
    open('breedmap.png', 'wb').write(read_file("breedmap.png"))


def to_timestamp(date):
    return time.mktime(datetime.strptime(date, "%d/%m/%Y").timetuple())


def get_worksheets(title, cell):
    done = False
    sheets = None
    while not done:
        try:
            sheets = client.open(title).worksheets()
            done = True
        except:
            done = False

    usable_sheets = []
    for worksheet in sheets:
        if worksheet.acell(cell).value == "TRUE":
            usable_sheets.append(worksheet)
    return usable_sheets


def safe_get_in(element, index):
    if index > len(element) - 1:
        return ""
    else:
        return str(element[index])


def generate_renewal_dates():
    offset = int(config[alert_guild_id + "config"][0])
    renewal_dates = []
    current = time.time()
    for i in range(offset + 1):
        renewal_dates.append(str(datetime.fromtimestamp(current + (86400 * i)).strftime("%d-%m-%Y")).replace("-", "/"))
    return renewal_dates


def get_users_to_alert():
    vip_to_alert = {}
    breed_to_alert = {}
    dates = generate_renewal_dates()

    # Sheet
    vip_sheets = get_worksheets(vip_name, vip_check_cell)
    breed_sheets = get_worksheets(breed_name, breed_check_cell)

    # VIP
    for worksheet in vip_sheets:
        vip_discord_id = worksheet.col_values(vip_id_col)
        vip_abo = worksheet.col_values(vip_abo_col)
        for date in dates:
            for cell in worksheet.findall(str(date)):
                if str(cell.col) == str(vip_end_col):
                    discord_id = str(safe_get_in(vip_discord_id, cell.row - 1))
                    end = str(cell.value)
                    if not discord_id == "":
                        if discord_id not in alerted:
                            vip_to_alert[discord_id] = {"ABO": str(safe_get_in(vip_abo, cell.row - 1)), "END": end}
                        else:
                            if not alerted[discord_id] == end:
                                vip_to_alert[discord_id] = {"ABO": str(safe_get_in(vip_abo, cell.row - 1)), "END": end}

    # BREED
    for worksheet in breed_sheets:
        breed_discord_id = worksheet.col_values(breed_id_col)
        for date in dates:
            for cell in worksheet.findall(str(date)):
                if str(cell.col) == str(breed_end_col):
                    discord_id = str(safe_get_in(breed_discord_id, cell.row - 1)) + "breed"
                    end = str(cell.value)
                    if not discord_id == "breed":
                        if discord_id not in alerted:
                            breed_to_alert[discord_id] = end
                        else:
                            if not alerted[discord_id] == end:
                                breed_to_alert[discord_id] = end
    return vip_to_alert, breed_to_alert


def get_expirations():
    expirations = {}
    vip_sheets = get_worksheets(vip_name, vip_check_cell)

    n1 = 0
    for worksheet in vip_sheets:
        print("Worksheet:", n1)
        n1 += 1
        vip_discord_id = worksheet.col_values(vip_id_col)
        vip_abo = worksheet.col_values(vip_abo_col)
        vip_steam_id = worksheet.col_values(vip_steam_id_col)
        cluster_col = {}
        map_col = {}
        n2 = 0
        for col in vip_cluster_cols:
            print("Col:", n2)
            n2 += 1
            cluster_col[col] = worksheet.col_values(vip_cluster_cols[col])
        for col in vip_map_cols:
            print("Col:", n2)
            n2 += 1
            map_col[col] = worksheet.col_values(vip_map_cols[col])
        n3 = 0
        for cell in worksheet.findall(str(datetime.fromtimestamp(time.time()).strftime("%d-%m-%Y")).replace("-", "/")):
            print("Cell:", n3)
            n3 += 1
            if str(cell.col) == str(vip_end_col):
                discord_id = str(safe_get_in(vip_discord_id, cell.row - 1))
                abo = str(safe_get_in(vip_abo, cell.row - 1))
                steam_id = str(safe_get_in(vip_steam_id, cell.row - 1))
                clusters = []
                maps = []
                for col in cluster_col:
                    value = str(safe_get_in(cluster_col[col], cell.row - 1))
                    if value == "TRUE":
                        clusters.append(col)
                for col in map_col:
                    value = str(safe_get_in(map_col[col], cell.row - 1))
                    if value == "TRUE":
                        maps.append(col)
                expirations[discord_id] = {"STEAM ID": steam_id, "ABO": abo, "CLUSTERS": clusters, "MAP": maps, }
        time.sleep(110)

    return expirations


async def get_user_object(user_id):
    try:
        user = int(user_id)
    except:
        user = user_id
    try:
        user = await bot.fetch_user(user)
        return user
    except:
        return "[Unknown user]"


async def alert():
    guild = bot.get_guild(alert_channel_id[0])
    channel = ""
    for channel in guild.channels:
        if channel.id == alert_channel_id[1]:
            break
    expirations = get_expirations()
    for expiration in expirations:
        expiration_data = expirations[expiration]
        clusters = ""
        a = True
        for cluster in expiration_data["CLUSTERS"]:
            if not a:
                clusters += " / "
            clusters += cluster
            a = False
        maps = ""
        a = True
        for ark_map in expiration_data["MAP"]:
            if not a:
                maps += " / "
            maps += ark_map
            a = False
        name = await get_user_object(expiration)
        try:
            name = name.name
        except:
            pass
        value = "Utilisateur : " + name + "\nId Steam : " + expiration_data["STEAM ID"] + "\nAbonnement : " + \
                expiration_data[
                    "ABO"] + "\nCluster : " + clusters + "\nMap(s) : " + maps
        footer = "Reagissez à ce message pour le marquer comme fait"
        embed = discord.Embed(title=" ", color=discord.Color.from_rgb(255, 0, 0))
        embed.set_author(name="INX bot Alert")
        embed.add_field(name="Cet utilisateur voit son grade expirer aujourd'hui !",
                        value=value,
                        inline=True)
        embed.set_footer(text=footer)
        await channel.send(embed=embed)

    alerted["everyday"] = {"LASTDAY": str(datetime.fromtimestamp(time.time()).strftime("%d-%m-%Y")).replace("-", "/")}
    await update_files()


async def delete_message(m):
    m.delete()

# Ini
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='r-', intents=intents, help_command=None)
data = {}
config = {}
alerted = {}
log_targets = {"main": (855746724148412436, 861537071177138196), "alert": (617764965847400448, 880539121767022622)}
alert_channel_id = (617764965847400448, 879469209841713172)

# Github
g = Github("github token")
repo = g.get_user().get_repo("RockwellFiles")

get_images()

# Connect to sheet
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
client = gspread.authorize(creds)

# Sheet's const
vip_name = "INX - ARK PVE (VIP / VIP +)"
breed_name = "INX - Breeding map"

vip_check_cell = "A1"
breed_check_cell = "B1"

vip_id_col = 2
vip_abo_col = 6
vip_end_col = 8
vip_steam_id_col = 5
vip_cluster_cols = {"Cluster 1": 9, "Cluster 2": 10, "Cluster 3": 11}
vip_map_cols = {"The Island": 12, "Ragnarock": 13, "Aberration": 14, "Extinction": 15, "Center": 16, "Valguero": 17,
                "Scorched": 18, "Iso": 19, "Lost": 20, "Fjord": 21, "Genesis 1": 22, "Genesis 2": 23, "Fjord T1": 24,
                "Genesis 2 T1": 25, "Undefined": 26, "Breedmap": 27}

breed_id_col = 3
breed_end_col = 8

# Alert config
alert_guild_id = "617764965847400448"


# Logs
async def dispatch_log(log, **kwargs):
    if "target" in kwargs:
        guild = bot.get_guild(log_targets[kwargs["target"]][0])
        channel_id = log_targets[kwargs["target"]][1]
    else:
        guild = bot.get_guild(log_targets["main"][0])
        channel_id = log_targets["main"][1]
    channel = ""
    for channel in guild.channels:
        if channel.id == channel_id:
            break
    if "embed" in kwargs:
        await channel.send(embed=kwargs["embed"])
        return
    color = 0xec14f0
    if "color" in kwargs:
        if kwargs["color"] == "green":
            color = 0x2ecc71
        elif kwargs["color"] == "red":
            color = 0xe74c3c
        elif kwargs["color"] == "orange":
            color = 0xe67e22
    footer = "logged at : " + str(datetime.now())
    embed = discord.Embed(title=" ", color=color)
    embed.set_author(name="INX bot Logger")
    embed.add_field(name="Log",
                    value=log,
                    inline=True)
    embed.set_footer(text=footer)
    await channel.send(embed=embed)


# Events
@bot.event
async def on_ready():
    # Data & config file assert
    create_file("data.json", "{}")
    create_file("config.json", "{}")
    create_file("alerted.json", "{}")

    # Data & config build
    json_data = read_file("data.json")
    if json_data != "":
        global data
        data = json.loads(json_data)

    json_data = read_file("config.json")
    if json_data != "":
        global config
        config = json.loads(json_data)

    json_data = read_file("alerted.json")
    if json_data != "":
        global alerted
        alerted = json.loads(json_data)

    # Config assert
    for guild in bot.guilds:
        if not str(guild.id) in config:
            config[str(guild.id)] = []
        if not str(str(guild.id) + "config") in config:
            config[str(guild.id) + "config"] = ["7", "24", "1000"]

    await update_files()
    await dispatch_log("INX bot Ready")
    print("INX bot came back to life !!")
    alert_loop.start()


@bot.event
async def on_message(message):
    # IF NOT BOT
    if not message.author.bot:
        # IF NOT ADMINISTRATOR
        if not message.author.guild_permissions.administrator:

            # Ini
            guild_id = str(message.guild.id)
            channel_id = str(message.channel.id)
            message_time = int(round(time.time()))
            key = build_key(message)

            if channel_id not in config[guild_id]:
                return

            # IF KEY EXIST
            if key in data:
                # IF USER CAN'T SEND
                next_allowed_time = int(data[key]) + (3600 * int(config[str(message.guild.id) + "config"][1]))
                if next_allowed_time > message_time and not message.author.guild_permissions.administrator:
                    """
                    CASE 1 USER CAN'T SEND
                    """
                    await delete_message(message)
                    footer = "Prochain message autorisé : " + str(datetime.fromtimestamp(next_allowed_time))
                    embed = discord.Embed(title=" ", color=discord.Color.from_rgb(255, 0, 0))
                    embed.set_author(name="INX bot")
                    embed.add_field(name="Vous ne pouvez pas poster de message !",
                                    value="Vous devez attendre avant de poster un message à nouveau ! Votre message "
                                          "va vous etre renvoyé",
                                    inline=True)
                    embed.set_footer(text=footer)
                    await message.author.send(embed=embed)
                    await send(message.author, message=message.content)
                    await dispatch_log(
                        "Deleted message of " + message.author.name + " in " + message.guild.name + " reason : too "
                                                                                                    "early")
                    return

            # IF MESSAGE IS TOO LONG
            if check_for_content(message):
                """
                CASE 2 MESSAGE TOO LONG
                """
                await delete_message(message)
                val = "Votre message a excédé la limite de " + config[str(message.guild.id) + "config"][
                    2] + " caractères ! Il vous sera renvoyé !"
                embed = discord.Embed(title=" ", color=discord.Color.from_rgb(255, 0, 0))
                embed.set_author(name="INX bot")
                embed.add_field(name="Message supprimé !",
                                value=val,
                                inline=True)
                await message.author.send(embed=embed)
                await send(message.author, message=message.content)
                await dispatch_log(
                    "Deleted message of " + message.author.name + " in " + message.guild.name + " reason : too long")
                return

            """
            CASE 3 PERFORMED
            """

            # DELETE ALL
            if str(message.channel.id) in config[guild_id] and not message.author.guild_permissions.administrator:
                first = 0
                async for msg in message.channel.history(limit=200):
                    if msg.author == message.author:
                        if first > 0:
                            await delete_message(msg)
                        first += 1

            # update
            data[key] = str(message_time)
            await update_files()
            await dispatch_log("Performed message of " + message.author.name + " in " + message.guild.name)

        else:
            await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    guild = bot.get_guild(alert_channel_id[0])
    channel = ""
    for channel in guild.channels:
        if channel.id == alert_channel_id[1]:
            break
    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return
    embed = message.embeds[0]
    embed.color = 0x2ecc71
    await message.edit(embed=embed)


@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(alert_channel_id[0])
    channel = ""
    for channel in guild.channels:
        if channel.id == alert_channel_id[1]:
            break
    try:
        message = await channel.fetch_message(payload.message_id)
    except:
        return
    embed = message.embeds[0]
    embed.color = discord.Color.from_rgb(255, 0, 0)
    await message.edit(embed=embed)


# Commands
@bot.command()
async def add(ctx, *args):
    if len(args) == 0:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Erreur de commande !",
                        value="Vous devez entrer l'identifiant ou le nom précèdé d'un # du chanel à ajouter, "
                              "après votre commande",
                        inline=True)
        embed.set_footer(text="r-add [channel-id]")
        await ctx.send(embed=embed)
        await dispatch_log(
            "Error in command add of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : no id")
        return

    cn = parse(args[0])
    for chan in bot.get_guild(ctx.guild.id).channels:
        if cn == str(chan.id):
            if cn in config[str(ctx.guild.id)]:
                channel = discord.utils.get(ctx.guild.channels, id=int(cn))
                channel_name = channel.name
                embed = discord.Embed(title=" ", color=0xec14f0)
                embed.set_author(name="INX bot")
                embed.add_field(name="Erreur de commande !",
                                value="Le channel " + channel_name + "existe déjà dans la liste des channels protégés "
                                                                     "!",
                                inline=True)
                await ctx.send(embed=embed)
                await dispatch_log(
                    "Error in command add of " + ctx.message.author.name + " in " + ctx.guild.name + "reason : "
                                                                                                     "channel already"
                                                                                                     " in")
                return
            config[str(ctx.guild.id)].append(cn)
            await update_files()
            channel = discord.utils.get(ctx.guild.channels, id=int(cn))
            channel_name = channel.name
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="INX bot")
            embed.add_field(name="Commande exécutée !",
                            value="Le channel " + channel_name + " a été ajouté dans la liste des channels protégés !",
                            inline=True)
            await ctx.send(embed=embed)
            await dispatch_log("Performed command add of " + ctx.message.author.name + " in " + ctx.guild.name)
            return
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="INX bot")
    embed.add_field(name="Erreur de commande !",
                    value="Le channel n'existe pas !",
                    inline=True)
    await ctx.send(embed=embed)
    await dispatch_log(
        "Error in command add of " + ctx.message.author.name + " in " + ctx.guild.name + "reason : channel doesn't "
                                                                                         "exist")


@bot.command()
async def remove(ctx, *args):
    if len(args) == 0:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Erreur de commande !",
                        value="Vous devez entrer l'identifiant ou le nom précèdé d'un # du chanel à supprimer, "
                              "après votre commande",
                        inline=True)
        embed.set_footer(text="r-remove [channel-id]")
        await ctx.send(embed=embed)
        await dispatch_log(
            "Error in command remove of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : no id")
        return

    cn = parse(args[0])
    for channel in bot.get_guild(ctx.guild.id).channels:
        if cn == str(channel.id):
            if cn not in config[str(ctx.guild.id)]:
                channel = discord.utils.get(ctx.guild.channels, id=int(cn))
                channel_name = channel.name
                embed = discord.Embed(title=" ", color=0xec14f0)
                embed.set_author(name="INX bot")
                embed.add_field(name="Erreur de commande !",
                                value="Le channel " + channel_name + "n'est déjà pas dans la liste des channels "
                                                                     "protégés !",
                                inline=True)
                await ctx.send(embed=embed)
                await dispatch_log(
                    "Error in command remove of " + ctx.message.author.name + " in " + ctx.guild.name + "reason : "
                                                                                                        "channel "
                                                                                                        "already not "
                                                                                                        "in")
                return
            config[str(ctx.guild.id)].remove(cn)
            await update_files()
            channel = discord.utils.get(ctx.guild.channels, id=int(cn))
            channel_name = channel.name
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="INX bot")
            embed.add_field(name="Commande exécutée !",
                            value="Le channel " + channel_name + " a été supprimé dans la liste des channels protégés !"
                            , inline=True)
            await ctx.send(embed=embed)
            await dispatch_log("Performed command remove of " + ctx.message.author.name + " in " + ctx.guild.name)
            return
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="INX bot")
    embed.add_field(name="Erreur de commande !",
                    value="Le channel n'existe pas !",
                    inline=True)
    await ctx.send(embed=embed)
    await dispatch_log(
        "Error in command remove of " + ctx.message.author.name + " in " + ctx.guild.name + "reason : channel doesn't "
                                                                                            "exist")


@bot.command()
async def info(ctx):
    channels = "Vous n'avez pas de channels protégés"
    a = True

    for chan in config[str(ctx.guild.id)]:
        if a:
            channels = ""
            a = False

        channel = discord.utils.get(ctx.guild.channels, id=int(chan))
        channel_name = channel.name
        channels += "\n" + channel_name

    configuration = "Alert : " + config[str(ctx.guild.id) + "config"][0] + " jours.\n" + "Message : " + \
                    config[str(ctx.guild.id) + "config"][1] + " heures.\n" + "Size : " + \
                    config[str(ctx.guild.id) + "config"][2] + " caractères."

    guild = ctx.guild
    users = ""
    for user in guild.members:
        if user.guild_permissions.administrator:
            users += user.name + "\n"

    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="INX bot")
    embed.add_field(name="Informations du bot !",
                    value="Voici la configuration actuelle du bot :",
                    inline=True)
    embed.add_field(name="Liste des channels protégés :",
                    value=channels,
                    inline=False)
    embed.add_field(name="Configuration du bot :",
                    value=configuration,
                    inline=False)
    embed.add_field(name="Administrateurs :",
                    value=users,
                    inline=False)
    embed.set_footer(text="contact : Shaft#3796")
    await ctx.send(embed=embed)
    await dispatch_log("Performed command info of " + ctx.message.author.name + " in " + ctx.guild.name)


@bot.command()
async def help(ctx):
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="Commandes :")
    embed.add_field(name="r-info",
                    value="Affiche les informations sur la configuration du bot ainsi que les channels protégés et "
                          "utilisateurs alertés",
                    inline=True)
    embed.add_field(name="r-add [channel-id]",
                    value="Ajoute un channel à la liste des channels protégés, Exemple : //add 854633053078159389 ou "
                          "r-add #général",
                    inline=False)
    embed.add_field(name="r-remove [channel-id]",
                    value="Supprime un channel de la liste des channels protégés, Exemple : //remove "
                          "854633053078159389 ou //remove #général",
                    inline=False)
    embed.add_field(name="r-config [config-line] [value]",
                    value="Commande pour configurer le bot ! Voici la liste des lignes de configuration :\n//config "
                          "alert [value]\n Indique le nombre de jours pour alerter les Vip avant l'expiration, "
                          "la valeur doit donc être indiquée en jours.\n//config message [value]\n Indique le nombre "
                          "d'heures entre chaques messages des utilisateurs dans les channels de vente, "
                          "la valeur doit donc être indiquée en heures.\n//config size [value]\n Indique le nombre de "
                          "caractères max des messages dans les channels de vente.",
                    inline=False)
    embed.set_footer(text="contact : Shaft#3796")
    await ctx.send(embed=embed)
    await dispatch_log("Performed command help of " + ctx.message.author.name + " in " + ctx.guild.name)


@bot.command()
async def config(ctx, *args):
    # Pre check
    if len(args) <= 1:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Erreur de commande !",
                        value="Il vous manques des paramètres, //help pour plus de détails !",
                        inline=True)
        embed.set_footer(text="r-config [config-line] [value]")
        await ctx.send(embed=embed)
        await dispatch_log(
            "error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : miss args")
        return

    if args[0] == "alert":
        try:
            value = int(args[1])
        except:
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="INX bot")
            embed.add_field(name="Erreur de commande !",
                            value="La valeur indiquée doit être un nombre, //help pour plus de détails !",
                            inline=True)
            embed.set_footer(text="r-config [config-line] [value]")
            await ctx.send(embed=embed)
            await dispatch_log(
                "error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + "with object : "
                                                                                                    "alert" + "reason "
                                                                                                              ": arg "
                                                                                                              "not "
                                                                                                              "int")
            return
        config[str(ctx.guild.id) + "config"][0] = str(value)
        msg = "Les vip seront alertés " + str(value) + " jours avant l'expiration de leurs grades"
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Commande exécutée !",
                        value=msg,
                        inline=True)
        await ctx.send(embed=embed)
        await dispatch_log(
            "Performed command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : alert")

    elif args[0] == "message":
        try:
            value = int(args[1])
        except:
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="INX bot")
            embed.add_field(name="Erreur de commande !",
                            value="La valeur indiquée doit être un nombre, //help pour plus de détails !",
                            inline=True)
            embed.set_footer(text="r-config [config-line] [value]")
            await ctx.send(embed=embed)
            await dispatch_log(
                "error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + "with object : "
                                                                                                    "message"
                                                                                                    "reason : arg not "
                                                                                                    "int")
            return
        config[str(ctx.guild.id) + "config"][1] = str(value)
        msg = "Les utilisateurs pourront poster des messages toute les " + str(value) + " heures par channels protégés"
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Commande exécutée !",
                        value=msg,
                        inline=True)
        await ctx.send(embed=embed)
        await dispatch_log(
            "Performed command config of " + ctx.message.author.name + " in " + ctx.guild.name + "with object : "
                                                                                                 "message")

    elif args[0] == "size":
        try:
            value = int(args[1])
        except:
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="INX bot")
            embed.add_field(name="Erreur de commande !",
                            value="La valeur indiquée doit être un nombre, //help pour plus de détails !",
                            inline=True)
            embed.set_footer(text="r-config [config-line] [value]")
            await ctx.send(embed=embed)
            await dispatch_log(
                "error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + "with object : "
                                                                                                    "size" + " reason"
                                                                                                             " : arg "
                                                                                                             "not int")
            return
        config[str(ctx.guild.id) + "config"][2] = str(value)
        msg = "Les utilisateurs aurront une limite de " + str(
            value) + " caractères par messages dans les channels protégés !"
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Commande exécutée !",
                        value=msg,
                        inline=True)
        await ctx.send(embed=embed)
        await dispatch_log(
            "Performed command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : size")

    else:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="INX bot")
        embed.add_field(name="Erreur de commande !",
                        value="La ligne de configuration indiquée est incorrecte, //help pour plus de détails !",
                        inline=True)
        embed.set_footer(text="r-config [config-line] [value]")
        await ctx.send(embed=embed)
        await dispatch_log(
            "error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + "reason : wrong "
                                                                                                "config line")

    await update_files()


# alert
@tasks.loop(seconds=3600)
async def alert_loop():
    if True:

        print("--- Running Alert Loop ---")
        if "everyday" in alerted and not alerted["everyday"]["LASTDAY"] == str(
                datetime.fromtimestamp(time.time()).strftime("%d-%m-%Y")).replace("-",
                                                                                  "/") or "everyday" not in alerted:
            print("--- Running everyday alert ---")
            await alert()
            time.sleep(200)
        print("--- Running alert task ---")
        start_time = time.time()
        finally_alerted = []
        user_to_alert = get_users_to_alert()
        print(user_to_alert)
        print("-     Getting images     -")
        get_images()
        print("-   Running vip alert    -")

        # Vip
        for user in user_to_alert[0]:
            user_object = await get_user_object(user)
            if not user_object == "[Unknown user]":
                user_end = user_to_alert[0][user]["END"]
                user_abo = user_to_alert[0][user]["ABO"]
                if user_abo == "VIP":
                    await send(user_object, file=get_vip_image(),
                               message=":red_circle: "
                                       "**--------------------------------------------------------------------** "
                                       ":red_circle:\nBonjour à toi survivant !\nTon grade **VIP** expire le **" +
                                       user_end + "**\n\n Tu peux le renouveler en faisant un ticket **Admin**\n*Ceci "
                                                  "est un message automatique merci de ne pas répondre*\n\n "
                                                  "**---------------------------------------------------------------------------**\n\n "
                                                  "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                  "\nTwitter ===> "
                                                  "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                  "https://inxserv.fr/\n")

                elif user_abo == "VIP+":
                    await send(user_object, file=get_vipm_image(),
                               message=":red_circle: "
                                       "**--------------------------------------------------------------------** "
                                       ":red_circle:\nBonjour à toi survivant !\nTon grade **VIP+** expire le **" +
                                       user_end + "**\n\n Tu peux le renouveler en faisant un ticket **Admin**\n*Ceci "
                                                  "est un message automatique merci de ne pas répondre*\n\n "
                                                  "**---------------------------------------------------------------------------**\n\n"
                                                  "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                  "\nTwitter ===> "
                                                  "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                  "https://inxserv.fr/\n")

                elif user_abo == "VIP++":
                    await send(user_object, file=get_vipmm_image(),
                               message=":red_circle: "
                                       "**--------------------------------------------------------------------** "
                                       ":red_circle:\nBonjour à toi survivant !\nTon grade **VIP++** expire le **" +
                                       user_end + "**\n\n Tu peux le renouveler en faisant un ticket **Admin**\n*Ceci "
                                                  "est un message automatique merci de ne pas répondre*\n\n "
                                                  "**---------------------------------------------------------------------------**\n\n"
                                                  "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                  "\nTwitter ===> "
                                                  "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                  "https://inxserv.fr/\n")

                alerted[user] = user_end
                finally_alerted.append([user_object.name, user_abo, user_end])

        print("-  Running breed alert   -")
        # Breed
        for user in user_to_alert[1]:
            userid = user.replace("breed", "")
            user_object = await get_user_object(userid)
            if not user_object == "[Unknown user]":
                user_end = user_to_alert[1][user]
                await send(user_object, file=get_breedmap_image(),
                           message=":red_circle: "
                                   "**--------------------------------------------------------------------** "
                                   ":red_circle:\nBonjour à toi survivant !\nTa **BREEDMAP** expire le **" +
                                   user_end + "**\n\n Tu peux la renouveler en faisant un ticket **Admin**\n*Ceci "
                                              "est un message automatique merci de ne pas répondre*\n\n "
                                              "**---------------------------------------------------------------------------**\n\n "
                                              "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                              "\nTwitter ===> "
                                              "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                              "https://inxserv.fr/\n")
                alerted[user] = user_end
                finally_alerted.append([user_object.name, "breedMap", user_end])

        await update_files()

        print("-------- Logging  --------")
        # Log
        value = "No alerts"
        a = True
        for field in finally_alerted:
            if a:
                value = ""
                a = False
            value += field[0] + " " + field[1] + " " + field[2] + "\n"

        footer = "logged at : " + str(datetime.now())
        embed = discord.Embed(title=" ", color=0x2ecc71)
        embed.set_author(name="INX bot Logger")
        embed.add_field(name="Successfully run alert task",
                        value=value,
                        inline=True)
        embed.set_footer(text=footer)
        if value == "No alerts":
            await dispatch_log("blank", embed=embed)
        else:
            await dispatch_log("blank", embed=embed, target="alert")
        end_time = time.time()
        print(str(end_time - start_time) + "s")

    else:
        try:
            print("--- Running Alert Loop ---")
            if "everyday" in alerted and not alerted["everyday"]["LASTDAY"] == str(
                    datetime.fromtimestamp(time.time()).strftime("%d-%m-%Y")).replace("-",
                                                                                      "/") or "everyday" not in alerted:
                print("--- Running everyday alert ---")
                await alert()
                time.sleep(200)
            print("--- Running alert task ---")
            start_time = time.time()
            finally_alerted = []
            user_to_alert = get_users_to_alert()
            print(user_to_alert)
            print("-     Getting images     -")
            get_images()
            print("-   Running vip alert    -")

            # Vip
            for user in user_to_alert[0]:
                user_object = await get_user_object(user)
                if not user_object == "[Unknown user]":
                    user_end = user_to_alert[0][user]["END"]
                    user_abo = user_to_alert[0][user]["ABO"]
                    if user_abo == "VIP":
                        await send(user_object, file=get_vip_image(),
                                   message=":red_circle: "
                                           "**--------------------------------------------------------------------** "
                                           ":red_circle:\nBonjour à toi survivant !\nTon grade **VIP** expire le **" +
                                           user_end + "**\n\n Tu peux le renouveler en faisant un ticket **Admin**\n*Ceci "
                                                      "est un message automatique merci de ne pas répondre*\n\n "
                                                      "**---------------------------------------------------------------------------**\n\n "
                                                      "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                      "\nTwitter ===> "
                                                      "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                      "https://inxserv.fr/\n")

                    elif user_abo == "VIP+":
                        await send(user_object, file=get_vipm_image(),
                                   message=":red_circle: "
                                           "**--------------------------------------------------------------------** "
                                           ":red_circle:\nBonjour à toi survivant !\nTon grade **VIP+** expire le **" +
                                           user_end + "**\n\n Tu peux le renouveler en faisant un ticket **Admin**\n*Ceci "
                                                      "est un message automatique merci de ne pas répondre*\n\n "
                                                      "**---------------------------------------------------------------------------**\n\n"
                                                      "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                      "\nTwitter ===> "
                                                      "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                      "https://inxserv.fr/\n")

                    elif user_abo == "VIP++":
                        await send(user_object, file=get_vipmm_image(),
                                   message=":red_circle: "
                                           "**--------------------------------------------------------------------** "
                                           ":red_circle:\nBonjour à toi survivant !\nTon grade **VIP++** expire le **" +
                                           user_end + "**\n\n Tu peux le renouveler en faisant un ticket **Admin**\n*Ceci "
                                                      "est un message automatique merci de ne pas répondre*\n\n "
                                                      "**---------------------------------------------------------------------------**\n\n"
                                                      "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                      "\nTwitter ===> "
                                                      "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                      "https://inxserv.fr/\n")

                    alerted[user] = user_end
                    finally_alerted.append([user_object.name, user_abo, user_end])

            print("-  Running breed alert   -")
            # Breed
            for user in user_to_alert[1]:
                userid = user.replace("breed", "")
                user_object = await get_user_object(userid)
                if not user_object == "[Unknown user]":
                    user_end = user_to_alert[1][user]
                    await send(user_object, file=get_breedmap_image(),
                               message=":red_circle: "
                                       "**--------------------------------------------------------------------** "
                                       ":red_circle:\nBonjour à toi survivant !\nTa **BREEDMAP** expire le **" +
                                       user_end + "**\n\n Tu peux la renouveler en faisant un ticket **Admin**\n*Ceci "
                                                  "est un message automatique merci de ne pas répondre*\n\n "
                                                  "**---------------------------------------------------------------------------**\n\n "
                                                  "SHOP INX   ===>  https://inxservarkshop.tebex.io/category/1428365"
                                                  "\nTwitter ===> "
                                                  "https://twitter.com/InxServ\nSITE WEB INX ===> "
                                                  "https://inxserv.fr/\n")
                    alerted[user] = user_end
                    finally_alerted.append([user_object.name, "breedMap", user_end])

            await update_files()

            print("-------- Logging  --------")
            # Log
            value = "No alerts"
            a = True
            for field in finally_alerted:
                if a:
                    value = ""
                    a = False
                value += field[0] + " " + field[1] + " " + field[2] + "\n"

            footer = "logged at : " + str(datetime.now())
            embed = discord.Embed(title=" ", color=0x2ecc71)
            embed.set_author(name="INX bot Logger")
            embed.add_field(name="Successfully run alert task",
                            value=value,
                            inline=True)
            embed.set_footer(text=footer)
            if value == "No alerts":
                await dispatch_log("blank", embed=embed)
            else:
                await dispatch_log("blank", embed=embed, target="alert")
            end_time = time.time()
            print(str(end_time - start_time) + "s")
        except Exception:
            print("[INX log] issue detected in alert loop")
            traceback.print_stack()


keep_alive()
# Run
bot.run("bot token")
