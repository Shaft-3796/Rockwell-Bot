import json
import time
from discord.ext import commands
from discord.ext import tasks
import discord
from github import Github
import datetime
from webserver import keep_alive

# Ini
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='r-', intents=intents, help_command=None)
data = {}
config = {}
alert = {}
g = Github("GITHUB TOKEN")
repo = g.get_user().get_repo("RockwellFiles")
activity = discord.Activity(type=discord.ActivityType.custom, state="Killing survivors")
bot.change_presence(activity=activity)
logId = (855746724148412436, 861537071177138196)

# Functions
def buildKey(message):
    return str(message.guild.id) + str(message.channel.id) + str(message.author.id)


async def send(author, message):
    try:
        await author.send(message)
    except:
        pass


async def updateFiles():
    # update file
    json_data = json.dumps(data, indent=2)
    writeFiles("data.json", json_data)
    json_data = json.dumps(config, indent=2)
    writeFiles("config.json", json_data)
    json_data = json.dumps(alert, indent=2)
    writeFiles("alert.json", json_data)


def createFiles(name, content):
    if not fileExist(name):
        repo.create_file(name, "CREATION", content)


def deleteFiles(name):
    if fileExist(name):
        content = repo.get_contents(name)
        repo.delete_file(content.path, "REMOVE", content.sha)


def writeFiles(name, content):
    deleteFiles(name)
    createFiles(name, content)


def fileExist(name):
    for file in repo.get_contents(""):
        if file.name == name:
            return True
    return False


def readFile(name):
    if fileExist(name):
        for file in repo.get_contents(""):
            if file.name == name:
                return file.decoded_content
    return ""


def parse(toParse):
    toParse = toParse.replace(">", "")
    toParse = toParse.replace("<#", "")
    toParse = toParse.replace("<@!", "")
    return toParse


def checkForContent(message):
    maxSize = int(config[str(message.guild.id) + "config"][2])
    return len(message.content) > maxSize

#Logs
async def dispatchLog(log):
    footer = "logged at : " + str(datetime.datetime.now())
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="Rockwell Logger")
    embed.add_field(name="Log",
                    value=log,
                    inline=True)
    embed.set_footer(text=footer)
    guild = bot.get_guild(logId[0])
    for channel in guild.channels:
        if channel.id == logId[1]:
            chan = channel
            break
    await chan.send(embed=embed)




# Events
@bot.event
async def on_ready():
    # Broadcast
    print("Rockwell came back to life !!")

    # Data & config file assert
    createFiles("data.json", "{}")
    createFiles("config.json", "{}")
    createFiles("alert.json", "{}")

    # Data & config build
    json_data = readFile("data.json")
    if json_data != "":
        global data
        data = json.loads(json_data)

    json_data = readFile("config.json")
    if json_data != "":
        global config
        config = json.loads(json_data)

    json_data = readFile("alert.json")
    if json_data != "":
        global alert
        alert = json.loads(json_data)

    # Config assert
    for guild in bot.guilds:
        if not str(guild.id) in config:
            config[str(guild.id)] = []
        if not str(str(guild.id) + "config") in config:
            config[str(guild.id) + "config"] = ["7", "24", "1000"]
    await updateFiles()

    await dispatchLog("Rockwell Ready")


@bot.event
async def on_message(message):
    # IF NOT BOT
    if not message.author.bot:
        # IF NOT ADMINISTRATOR
        if not message.author.guild_permissions.administrator:

            # Ini
            guildId = str(message.guild.id)
            channelId = str(message.channel.id)
            msgTime = int(round(time.time()))
            key = buildKey(message)

            if not channelId in config[guildId]:
                return

            # IF KEY EXIST
            if key in data:
                # IF USER CAN'T SEND
                nextAllowedTime = int(data[key]) + (3600 * int(config[str(message.guild.id) + "config"][1]))
                if nextAllowedTime > msgTime and not message.author.guild_permissions.administrator:
                    """
                    CASE 1 USER CAN'T SEND
                    """
                    await message.delete()
                    footer = "Prochain message autorisé : " + str(datetime.datetime.fromtimestamp(nextAllowedTime))
                    embed = discord.Embed(title=" ", color=0xec14f0)
                    embed.set_author(name="Rockwell")
                    embed.add_field(name="Vous ne pouvez pas poster de message !",
                                    value="Vous devez attendre avant de poster un message à nouveau !",
                                    inline=True)
                    embed.set_footer(text=footer)
                    await message.author.send(embed=embed)
                    await dispatchLog("Deleted message of " + message.author.name + " in " + message.guild.name + " reason : too early")
                    return

            # IF MESSAGE IS TOO LONG
            elif checkForContent(message):
                """
                CASE 2 MESSAGE TOO LONG
                """
                await message.delete()
                val = "Votre message a excédé la limite de " + config[str(message.guild.id) + "config"][
                    2] + " caractères ! Il vous sera renvoyé !"
                embed = discord.Embed(title=" ", color=0xec14f0)
                embed.set_author(name="Rockwell")
                embed.add_field(name="Message supprimé !",
                                value=val,
                                inline=True)
                await message.author.send(embed=embed)

                await send(message.author, message.content)
                await dispatchLog("Deleted message of " + message.author.name + " in " + message.guild.name + " reason : too long")
                return

            """
            CASE 3 PERFORMED
            """

            # DELETE ALL
            if str(message.channel.id) in config[guildId] and not message.author.guild_permissions.administrator:
                first = 0
                async for msg in message.channel.history(limit=200):
                    if msg.author == message.author:
                        if first > 0:
                            await msg.delete()
                        first += 1

            # update
            data[key] = str(msgTime)
            await updateFiles()
            await dispatchLog("Performed message of " + message.author.name + " in " + message.guild.name)


        else:
            await bot.process_commands(message)


# Commands
@bot.command()
async def add(ctx, *args):
    if len(args) == 0:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="Vous devez entrer l'identifiant ou le nom précèdé d'un # du chanel à ajouter, après votre commande",
                        inline=True)
        embed.set_footer(text="//add [channel-id]")
        await ctx.send(embed=embed)
        await dispatchLog("Error in command add of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : no id")
        return

    cn = parse(args[0])
    for chan in bot.get_guild(ctx.guild.id).channels:
        if cn == str(chan.id):
            if cn in config[str(ctx.guild.id)]:
                channel = discord.utils.get(ctx.guild.channels, id=int(cn))
                channelName = channel.name
                embed = discord.Embed(title=" ", color=0xec14f0)
                embed.set_author(name="Rockwell")
                embed.add_field(name="Erreur de commande !",
                                value="Le channel " + channelName + " existe déjà dans la liste des channels protégés !",
                                inline=True)
                await ctx.send(embed=embed)
                await dispatchLog("Error in command add of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : channel already in")
                return
            config[str(ctx.guild.id)].append(cn)
            await updateFiles()
            channel = discord.utils.get(ctx.guild.channels, id=int(cn))
            channelName = channel.name
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Commande exécutée !",
                            value="Le channel " + channelName + " a été ajouté dans la liste des channels protégés !",
                            inline=True)
            await ctx.send(embed=embed)
            await dispatchLog("Performed command add of " + ctx.message.author.name + " in " + ctx.guild.name)
            return
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="Rockwell")
    embed.add_field(name="Erreur de commande !",
                    value="Le channel n'existe pas !",
                    inline=True)
    await ctx.send(embed=embed)
    await dispatchLog("Error in command add of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : channel doesn't exist")


@bot.command()
async def remove(ctx, *args):
    if len(args) == 0:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="Vous devez entrer l'identifiant ou le nom précèdé d'un # du chanel à supprimer, après votre commande",
                        inline=True)
        embed.set_footer(text="//remove [channel-id]")
        await ctx.send(embed=embed)
        await dispatchLog("Error in command remove of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : no id")
        return

    cn = parse(args[0])
    for chan in bot.get_guild(ctx.guild.id).channels:
        if cn == str(chan.id):
            if not cn in config[str(ctx.guild.id)]:
                channel = discord.utils.get(ctx.guild.channels, id=int(cn))
                channelName = channel.name
                embed = discord.Embed(title=" ", color=0xec14f0)
                embed.set_author(name="Rockwell")
                embed.add_field(name="Erreur de commande !",
                                value="Le channel " + channelName + " n'est déjà pas dans la liste des channels protégés !",
                                inline=True)
                await ctx.send(embed=embed)
                await dispatchLog("Error in command remove of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : channel already not in")
                return
            config[str(ctx.guild.id)].remove(cn)
            await updateFiles()
            channel = discord.utils.get(ctx.guild.channels, id=int(cn))
            channelName = channel.name
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Commande exécutée !",
                            value="Le channel " + channelName + " a été supprimé dans la liste des channels protégés !",
                            inline=True)
            await ctx.send(embed=embed)
            await dispatchLog("Performed command remove of " + ctx.message.author.name + " in " + ctx.guild.name)
            return
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="Rockwell")
    embed.add_field(name="Erreur de commande !",
                    value="Le channel n'existe pas !",
                    inline=True)
    await ctx.send(embed=embed)
    await dispatchLog("Error in command remove of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : channel doesn't exist")


@bot.command()
async def info(ctx):
    channels = "Vous n'avez pas de channels protégés"
    firstTime = True

    for chan in config[str(ctx.guild.id)]:
        if firstTime:
            channels = ""
            firstTime = False

        channel = discord.utils.get(ctx.guild.channels, id=int(chan))
        channelName = channel.name
        channels += "\n" + channelName

    users = ""
    modified = False

    for u in ctx.guild.members:
        if str(u.id) in alert:
            users += "\n" + u.name
            modified = True

    if not modified:
        users = "Vous n'avez pas d'utilisateurs alertés "

    configuration = "Alert : " + config[str(ctx.guild.id) + "config"][0] + " jours.\n" + "Message : " + \
                    config[str(ctx.guild.id) + "config"][1] + " heures.\n" + "Size : " + \
                    config[str(ctx.guild.id) + "config"][2] + " caractères."

    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="Rockwell")
    embed.add_field(name="Informations du bot !",
                    value="Voici la configuration actuelle du bot :",
                    inline=True)
    embed.add_field(name="Liste des channels protégés :",
                    value=channels,
                    inline=False)
    embed.add_field(name="Liste des utilisateurs alertés :",
                    value=users,
                    inline=False)
    embed.add_field(name="Configuration du bot :",
                    value=configuration,
                    inline=False)
    embed.set_footer(text="contact : Shaft#3796")
    await ctx.send(embed=embed)
    await dispatchLog("Performed command info of " + ctx.message.author.name + " in " + ctx.guild.name)


@bot.command()
async def help(ctx):
    embed = discord.Embed(title=" ", color=0xec14f0)
    embed.set_author(name="Commandes :")
    embed.add_field(name="//info",
                    value="Affiche les informations sur la configuration du bot ainsi que les channels protégés et utilisateurs alertés",
                    inline=True)
    embed.add_field(name="//add [channel-id]",
                    value="Ajoute un channel à la liste des channels protégés, Exemple : //add 854633053078159389 ou //add #général",
                    inline=False)
    embed.add_field(name="//remove [channel-id]",
                    value="Supprime un channel de la liste des channels protégés, Exemple : //remove 854633053078159389 ou //remove #général",
                    inline=False)
    embed.add_field(name="//alert [user-id] [date (optional)]",
                    value="Setup l'alerte automatique d'un joueur pour le renouvellement de son VIP, vous devez entrer l'identifiant ou le nom précèdé d'un @ de l'utilisateur ainsi que la date si vous le souhaitez après votre commande ! Si vous n'indiquez pas de date, cette dernière sera fixée à 30 jours à partir du moment ou vous utiliserez la commande, la date doit etre donnée en unix epoch time, le convertisseur est disponible ici : https://www.epochconverter.com/ pour plus de détails me contacter : Shaft#3796",
                    inline=False)
    embed.add_field(name="//calm [user-id]",
                    value="Enlève l'alerte automatique d'un joueur pour le renouvellement de son VIP.",
                    inline=False)
    embed.add_field(name="//config [config-line] [value]",
                    value="Commande pour configurer le bot ! Voici la liste des lignes de configuration :\n//config alert [value]\n Indique le nombre de jours pour alerter les Vip avant l'expiration, la valeur doit donc être indiquée en jours.\n//config message [value]\n Indique le nombre d'heures entre chaques messages des utilisateurs dans les channels de vente, la valeur doit donc être indiquée en heures.\n//config size [value]\n Indique le nombre de caractères max des messages dans les channels de vente.",
                    inline=False)
    embed.set_footer(text="contact : Shaft#3796")
    await ctx.send(embed=embed)
    await dispatchLog("Performed command help of " + ctx.message.author.name + " in " + ctx.guild.name)


@bot.command()
async def alert(ctx, *args):
    # Pre check
    if len(args) == 0:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="//help pour plus de détails",
                        inline=True)
        embed.set_footer(text="//alert [user-id] [date]")
        await ctx.send(embed=embed)
        await dispatchLog("Error in command alert of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : no args")
        return

    un = parse(args[0])
    user = ""
    for u in ctx.guild.members:
        if str(u.id) == str(un):
            user = u
            break

    if not user == "":

        if not str(user.id) in alert:
            t = int(round(time.time())) + 2629743
            if len(args) == 2:
                try:
                    t = int(args[1])
                except:
                    t = int(round(time.time())) + 2629743

            alert[str(user.id)] = str(t)
            await updateFiles()

            val = "L'utilisateur " + user.name + " va recevoir ses alertes, la prochaine aura lieu " + \
                  config[str(ctx.guild.id) + "config"][0] + " jours avant le " + str(datetime.datetime.fromtimestamp(t))
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Commande exécutée",
                            value=val,
                            inline=True)
            await ctx.send(embed=embed)
            await dispatchLog("Performed command alert of " + ctx.message.author.name + " in " + ctx.guild.name)
            return
        else:
            val = "L'utilisateur " + user.name + " reçoit déjà des alertes !"
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Commande exécutée",
                            value=val,
                            inline=True)
            await ctx.send(embed=embed)
            await dispatchLog("Error in command alert of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : user already recieve alerts")
            return

    else:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="L'utilisateur n'existe pas !",
                        inline=True)
        await ctx.send(embed=embed)
        await dispatchLog("Error in command alert of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : user doesn't exist")


@bot.command()
async def calm(ctx, *args):
    # Pre check
    if len(args) == 0:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="Vous devez entrer l'identifiant ou le nom précèdé d'un @ de l'utilisateur après votre commande !",
                        inline=True)
        embed.set_footer(text="//calm [user-id]")
        await ctx.send(embed=embed)
        await dispatchLog("Error in command calm of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : no args")
        return

    un = parse(args[0])
    user = ""
    for u in ctx.guild.members:
        if str(u.id) == str(un):
            user = u
            break

    if not user == "":

        if str(user.id) in alert:

            alert.pop(str(user.id))
            await updateFiles()
            val = "L'utilisateur " + user.name + " ne recevera plus d'alertes !"
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Commande exécutée",
                            value=val,
                            inline=True)
            await ctx.send(embed=embed)
            await dispatchLog("Performed command calm of " + ctx.message.author.name + " in " + ctx.guild.name)
            return
        else:
            val = "L'utilisateur " + user.name + " ne reçoit pas d'alertes !"
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Commande exécutée",
                            value=val,
                            inline=True)
            await ctx.send(embed=embed)
            await dispatchLog("Error in command calm of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : user doesn't recieve alerts")
            return

    else:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="L'utilisateur n'existe pas !",
                        inline=True)
        await ctx.send(embed=embed)
        await dispatchLog("Error in command calm of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : user doesn't exist")


@bot.command()
async def config(ctx, *args):
    # Pre check
    if len(args) <= 1:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="Il vous manques des paramètres, //help pour plus de détails !",
                        inline=True)
        embed.set_footer(text="//config [config-line] [value]")
        await ctx.send(embed=embed)
        await dispatchLog("error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : miss args")
        return

    if args[0] == "alert":
        try:
            value = int(args[1])
        except:
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Erreur de commande !",
                            value="La valeur indiquée doit être un nombre, //help pour plus de détails !",
                            inline=True)
            embed.set_footer(text="//config [config-line] [value]")
            await ctx.send(embed=embed)
            await dispatchLog("error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : alert" + " reason : arg not int")
            return
        config[str(ctx.guild.id) + "config"][0] = str(value)
        msg = "Les vip seront alertés " + str(value) + " jours avant l'expiration de leurs grades"
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Commande exécutée !",
                        value=msg,
                        inline=True)
        await ctx.send(embed=embed)
        await dispatchLog("Performed command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : alert")


    elif args[0] == "message":
        try:
            value = int(args[1])
        except:
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Erreur de commande !",
                            value="La valeur indiquée doit être un nombre, //help pour plus de détails !",
                            inline=True)
            embed.set_footer(text="//config [config-line] [value]")
            await ctx.send(embed=embed)
            await dispatchLog("error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : message" + " reason : arg not int")
            return
        config[str(ctx.guild.id) + "config"][1] = str(value)
        msg = "Les utilisateurs pourront poster des messages toute les " + str(value) + " heures par channels protégés"
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Commande exécutée !",
                        value=msg,
                        inline=True)
        await ctx.send(embed=embed)
        await dispatchLog("Performed command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : message")

    elif args[0] == "size":
        try:
            value = int(args[1])
        except:
            embed = discord.Embed(title=" ", color=0xec14f0)
            embed.set_author(name="Rockwell")
            embed.add_field(name="Erreur de commande !",
                            value="La valeur indiquée doit être un nombre, //help pour plus de détails !",
                            inline=True)
            embed.set_footer(text="//config [config-line] [value]")
            await ctx.send(embed=embed)
            await dispatchLog("error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : size" + " reason : arg not int")
            return
        config[str(ctx.guild.id) + "config"][2] = str(value)
        msg = "Les utilisateurs aurront une limite de " + str(
            value) + " caractères par messages dans les channels protégés !"
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Commande exécutée !",
                        value=msg,
                        inline=True)
        await ctx.send(embed=embed)
        await dispatchLog("Performed command config of " + ctx.message.author.name + " in " + ctx.guild.name + " with object : size")

    else:
        embed = discord.Embed(title=" ", color=0xec14f0)
        embed.set_author(name="Rockwell")
        embed.add_field(name="Erreur de commande !",
                        value="La ligne de configuration indiquée est incorrecte, //help pour plus de détails !",
                        inline=True)
        embed.set_footer(text="//config [config-line] [value]")
        await ctx.send(embed=embed)
        await dispatchLog("error in command config of " + ctx.message.author.name + " in " + ctx.guild.name + " reason : wrong config line")

    await updateFiles()


# TASK

# update alert
@tasks.loop(seconds=60)
async def myLoop():
    # LOOKING FOR USER FROM ID
    for guild in bot.guilds:
        for user in guild.members:
            if str(user.id) in alert:
                nextAlert = int(alert[str(user.id)]) - (86400 * int(config[str(guild.id) + "config"][0]))
                if round(time.time()) > nextAlert:
                    alert[str(user.id)] = str(round(time.time()) + 2629743)
                    await updateFiles()
                    embed = discord.Embed(title=" ", color=0xec14f0)
                    embed.set_author(name="Rockwell")
                    embed.add_field(name="Bonjour à toi !",
                                    value="Ton Vip va expirer dans moins de " + config[str(guild.id) + "config"][
                                        0] + " ! Pense à le renouveler et merci de ton soutien aux serveurs !",
                                    inline=True)
                    try:
                        await user.send(embed=embed)
                    except:
                        pass
                    await dispatchLog("Alerted " + user.name)


myLoop.start()

keep_alive()
# Run
bot.run("TOKEN")
