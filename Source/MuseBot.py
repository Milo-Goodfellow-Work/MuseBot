import discord
import re
import asyncio
import time
from discord.ext import tasks, commands

bot = commands.Bot(command_prefix="$Muse ", case_insensitive = True)
queue_dict = {}
task_dict = {}
active_dict = {}
break_store = 0

@bot.event
async def on_ready():
    print("We have logged in as {0.user}".format(bot))

@bot.event
async def on_guild_join(guild):
    queue_dict[guild] = []
    task_dict[guild] = []
    active_dict[guild] = False

class CustomHelpCommand(commands.MinimalHelpCommand):
    #'''
    #Send bot help runs whenever a user queries the "Help" command with no arguments.
    #First it create a discord.Embed object with a title of "User Level Commenads Help" and the color code 10472447 (A light shade of blue).
    #A set of every single command is collected followed by the destination of the help call.
    #The set of commands is iterated over. Each command is turned into an embed field with a name and description.
    #The final field, the Help field, is added to the embed.
    #The completed embed is then sent to the user
    #'''
    async def send_bot_help(self,command):
        help_message = discord.Embed(title="User Level Commands Help", color=10472447)
        user_level_cog = bot.get_cog("UserLevel")
        admin_level_cog = bot.get_cog("AdminLevel")
        command_list = set(user_level_cog.walk_commands()).union(set(admin_level_cog.walk_commands()))
        destination = self.get_destination()
        for i in command_list:
            help_message.add_field(name = i.name, value=i.brief, inline=False)

        help_message.add_field(name="Help", value="List all user level bot commands or get more specific details on one command", inline=False)
        await destination.send(embed=help_message)
        await destination.send("```All commands must be preceded by $Muse. To use muse the command $Muse Start must be performed```")

    #Gets the destination of the command then sends the user an error message
    async def on_help_command_error(self, ctx, error):
        destination = self.get_destination()
        await destination.send("```There was an error processing your request {}```".format(error))


    #Disables the send cog help command
    async def send_cog_help(self, ctx, command):
        pass


    #Sends the user the "command_not_found" help message
    async def command_not_found(self, command):
        help_message = '```The command "{}" could not be found```'.format(command)
        destination = self.get_destination()
        return help_message

    #Send specific command help
    async def send_command_help(self, command):
        help_message = discord.Embed(name="Command details", color=10472447)
        help_message.add_field(name = command.name, value=command.description, inline=False)
        destination = self.get_destination();
        await destination.send(embed=help_message)


class BaseEdits(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.original_help_command = bot.help_command
        bot.help_command = CustomHelpCommand(dm_help=True, alias="Help")
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.original_help_command

class TimeAssociateChannel:
    def __init__(self, time, channel, voice_channel):
        self.time = time
        self.channel = channel
        self.voice_channel = voice_channel


class UserLevel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue_cycle.start()
        self.check_servers.start()

    @commands.command(name='Queue', brief="List all performers", description="List all current performers and the person currently performing")
    async def queue(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                loop_run_num = 0
                return_message = "```The Queue Of Performers:\n"
                for i in queue_dict[ctx.guild]:
                    if loop_run_num > 0:
                        return_message += "{}\n".format(str(i.display_name))
                    else:
                        loop_run_num +=1
                        return_message += "{} <\n".format(str(i.display_name))

                return_message += "The symbol < signals who the current performer is\n```"
                await ctx.author.send(return_message)
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))

    @commands.command(name="Perform", brief="Add yourself to the queue", description="Add yourself to the current list of performers")
    async def join_queue(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                try:
                    queue_dict[ctx.guild].index(ctx.author)
                    await ctx.send("{} you are already in the queue!".format(ctx.author.mention))
                except:
                    queue_dict[ctx.guild].append(ctx.author)
                    await ctx.send("{} you have been added to the queue!".format(ctx.author.mention))
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))

    @commands.command(name="Leave", brief="Remove yourself from the queue", description="Remove yourself from the current list of performers")
    async def leave_queue(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                try:
                    user_queue_pos = queue_dict[ctx.guild].index(ctx.author)
                    del (queue_dict[ctx.guild])[user_queue_pos]
                    await ctx.send("{} you have been removed from the queue!".format(ctx.author.mention))
                except:
                    await ctx.send("{} you are not in the queue already!".format(ctx.author.mention))
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))

    @commands.command(name="Start", brief="Enable Muse", description="Turn on the Muse bot in its assigned channel")
    async def start(self, ctx):
        if "perform" in ctx.channel.name.lower():
            try:
                found = 0
                channel_list = ctx.guild.voice_channels
                for i in channel_list:
                    if "Performance" in i.name or "performance" in i.name:
                        if ctx.author.voice.channel == i:
                            await i.connect()
                            task_dict[ctx.guild] = TimeAssociateChannel(time = int(time.time()) + 210, channel = ctx.channel, voice_channel = i)
                            active_dict[ctx.guild] = True
                            found = 1
                        else:
                            found = 3

                    else:
                        pass

                if found == 1:
                    await ctx.send("{} Muse has joined the channel!".format(ctx.author.mention))
                    break_store = 0
                elif found == 0:
                    await ctx.send("{} Muse cannot find the performance channel :frowning:".format(ctx.author.mention))
                else:
                    await ctx.send("{} You're not in the performance channel".format(ctx.author.mention))

            except Exception as e:
                await ctx.send("{} Muse is already in the channel!".format(ctx.author.mention))

    @tasks.loop(seconds = 1)#600
    async def check_servers(self):
        guild_list = bot.guilds
        for i in guild_list:
            if i in task_dict:
                pass
            else:
                task_dict[i] = []
            if i in queue_dict:
                pass
            else:
                queue_dict[i] = []
            if i in active_dict:
                pass
            else:
                active_dict[i] = False



    @tasks.loop(seconds = 5)
    async def queue_cycle(self):
        try:
            sorted_dict = sorted(task_dict.items(), key = lambda given_val: (given_val[1].time - int(time.time())))[0]
            remaining_seconds = 0
            global break_store
            key = sorted_dict[0]
            time_channel = sorted_dict[1]
            if active_dict[time_channel.channel.guild] == True:
                for i in bot.voice_clients:
                    if i.guild == time_channel.channel.guild:
                        member_list = i.channel.members

                if queue_dict[key] != []:
                    await time_channel.channel.send("{}, it is now your turn!".format(queue_dict[key][0].mention))
                    for i in member_list:
                        if i != queue_dict[key][0]:
                            await i.edit(mute=True)

                        else:
                            await i.edit(mute=False)

                    remaining_seconds = int((time_channel.time-30) - int(time.time()))
                    print(remaining_seconds)
                    while remaining_seconds != 0:
                        remaining_seconds -= 1
                        await asyncio.sleep(1)
                        if break_store == 1:
                            print("CRINGE")
                            break

                    if break_store == 0:

                        queue_dict[key].append((queue_dict[key])[0])
                        del (queue_dict[key])[0]
                        await time_channel.channel.send("{} will be up to perform in 30 seconds!".format((queue_dict[key])[0].mention))
                        for i in member_list:
                            await i.edit(mute=False)

                        remaining_seconds = int(time_channel.time - int(time.time()))
                        print(remaining_seconds)
                        while remaining_seconds != 0:
                            remaining_seconds -= 1
                            await asyncio.sleep(1)
                            if break_store == 1:
                                break

                        if break_store == 0:
                            task_dict[key] = TimeAssociateChannel(time = time.time() + 210, channel = time_channel.channel, voice_channel = time_channel.voice_channel)

                        else:
                            break_store = 1

                    else:
                        break_store = 0
                else:
                    await time_channel.voice_channel.voice_client.disconnect()
                    queue_dict[time_channel.channel.guild] = []
                    active_dict[time_channel.channel.guild] = False
                    task_dict.pop(time_channel.channel.guild, None)
            else:
                pass

        except Exception as e:
            print(e)
            pass


    def cog_unload(self):
        self.queue_cycle.stop()
        self.check_servers.stop()

class AdminLevel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ForceSkip", brief="Force a skip of the current performer", description="Force a skip of the current performer in the list of performers (Requires MuseManager role)")
    async def force_skip(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                was_admin = 0
                for i in ctx.author.roles:
                    if i.name.lower() == "musemanager" or "event" in i.name.lower() or "events" in i.name.lower():
                        was_admin = 1
                    else:
                        pass
                if was_admin == 1:
                    break_store = 1
                    await ctx.send("{} Skip executed".format(ctx.author.mention))
                else:
                    await ctx.send("{} You don't have permission to execute this command".format(ctx.author.mention))
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))


    @commands.command(name="ForceKick", brief="Force a removal of the current performer", description="Force a removal of the current performer in the list of performers (Requires MuseManager role)")
    async def force_kick(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                was_admin = 0
                for i in ctx.author.roles:
                    if i.name.lower() == "musemanager" or "event" in i.name.lower() or "events" in i.name.lower():
                        was_admin = 1
                    else:
                        pass
                if was_admin == 1:
                    del (queue_dict[ctx.guild])[0]
                    break_store = 1
                    await ctx.send("{} Kick executed".format(ctx.author.mention))
                else:
                    await ctx.send("{} You don't have permission to execute this command".format(ctx.author.mention))
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))

    @commands.command(name="Truncate", brief="Empty the list of performers", description="Empty the list of performers (Requires MuseManager role)")
    async def truncate(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                was_admin = 0
                for i in ctx.author.roles:
                    if i.name.lower() == "musemanager" or "event" in i.name.lower() or "events" in i.name.lower():
                        was_admin = 1
                    else:
                        pass
                if was_admin == 1:
                    queue_dict[ctx.guild] = []
                    break_store = 1
                    await ctx.send("{} Truncate executed".format(ctx.author.mention))
                else:
                    await ctx.send("{} You don't have permission to execute this command".format(ctx.author.mention))
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))

    @commands.command(name="Stop", brief="Disable Muse", description="Turn off the Muse bot in its assigned channel, will truncate the performance queue (Requires MuseManager role)")
    async def stop(self, ctx):
        if "perform" in ctx.channel.name.lower():
            if active_dict[ctx.guild] == True:
                was_admin = 0
                for i in ctx.author.roles:
                    if i.name.lower() == "musemanager" or "event" in i.name.lower() or "events" in i.name.lower():
                        was_admin = 1
                    else:
                        pass
                if was_admin == 1:
                    try:
                        await ctx.voice_client.disconnect()
                        task_dict.pop(ctx.guild, None)
                        queue_dict[ctx.guild] = []
                        active_dict[ctx.guild] = True
                        break_store = 1
                        await ctx.send("{} Muse has left the channel!".format(ctx.author.mention))
                    except:
                        await ctx.send("{} Muse isn't in the channel!".format(ctx.author.mention))
                else:
                    await ctx.send("{} You don't have permission to execute this command".format(ctx.author.mention))
            else:
                await ctx.send("{} Muse isn't active".format(ctx.author.mention))

bot.add_cog(AdminLevel(bot))
bot.add_cog(UserLevel(bot))
bot.add_cog(BaseEdits(bot))


bot.run('YOUR TOKEN HERE');
