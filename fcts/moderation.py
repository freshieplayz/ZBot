from discord.ext import commands
import discord, re, datetime, random, json, os, typing, importlib, string, asyncio, copy
from fcts import checks, args

importlib.reload(checks)
importlib.reload(args)

class ModeratorCog(commands.Cog):
    """Here you will find everything you need to moderate your server. Please note that most of the commands are reserved for certain members only."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "moderation"
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr

    @commands.command(name="slowmode")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.check(checks.can_slowmode)
    async def slowmode(self,ctx,time=None):
        """Keep your chat cool
Slowmode works up to one message every 6h (21600s)

..Example slowmode 10

..Example slowmode off

..Doc moderator.html#slowmode"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-slowmode"))
            return
        if time==None:
            return await ctx.send(str(await self.translate(ctx.guild.id,"modo","slowmode-info")).format(ctx.channel.slowmode_delay))
        if time.isnumeric():
            time = int(time)
        if time == 'off' or time==0:
            #await ctx.bot.http.request(discord.http.Route('PATCH', '/channels/{cid}', cid=ctx.channel.id), json={'rate_limit_per_user':0})
            await ctx.channel.edit(slowmode_delay=0)
            message = await self.translate(ctx.guild.id,"modo","slowmode-0")
            log = str(await self.translate(ctx.guild.id,"logs","slowmode-disabled")).format(channel=ctx.channel.mention)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"slowmode",log,ctx.author)
        elif type(time)==int:
            if time>21600:
                message = await self.translate(ctx.guild.id,"modo","slowmode-1")
            else:
                #await ctx.bot.http.request(discord.http.Route('PATCH', '/channels/{cid}', cid=ctx.channel.id), json={'rate_limit_per_user':time})
                await ctx.channel.edit(slowmode_delay=time)
                message = str(await self.translate(ctx.guild.id,"modo","slowmode-2")).format(ctx.channel.mention,time)
                log = str(await self.translate(ctx.guild.id,"logs","slowmode-enabled")).format(channel=ctx.channel.mention,seconds=time)
                await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"slowmode",log,ctx.author)
        else:
                message = await self.translate(ctx.guild.id,"modo","slowmode-3")
        await ctx.send(message)


    @commands.command(name="clear")
    @commands.cooldown(4, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_clear)
    async def clear(self,ctx,number:int,*,params=''):
        """Keep your chat clean
        <number> : number of messages to check
        Available parameters :
            <@user> : list of users to check (just mention them)
            ('-f' or) '+f' : delete if the message  (does not) contain any file
            ('-l' or) '+l' : delete if the message (does not) contain any link
            ('-p' or) '+p' : delete if the message is (not) pinned
            ('-i' or) '+i' : delete if the message (does not) contain a Discord invite
        By default, the bot will not delete pinned messages

..Example clear 120

..Example clear 10 @someone

..Example clear 50 +f +l -p

..Doc moderator.html#clear"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.translate(ctx.guild.id,"modo","need-manage-messages"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.translate(ctx.guild.id,"modo","need-read-history"))
            return
        if number<1:
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","clear-1"))+" "+self.bot.cogs['EmojiCog'].customEmojis["owo"])
            return
        if len(params)==0:
            return await self.clear_simple(ctx,number)
        #file
        if "-f" in params:
            files = 0
        elif "+f" in params:
            files = 2
        else:
            files = 1
        #link
        if "-l" in params:
            links = 0
        elif "+l" in params:
            links = 2
        else:
            links = 1
        #pinned
        if '-p' in params:
            pinned = 0
        elif "+p" in params:
            pinned = 2
        else:
            pinned = 1
        #invite
        if '-i' in params:
            invites = 0
        elif "+i" in params:
            invites = 2
        else:
            invites = 1
        # 0: does  -  2: does not  -  1: why do we care?
        def check(m):
            i = self.bot.cogs["UtilitiesCog"].sync_check_discord_invite(m.content)
            r = self.bot.cogs["UtilitiesCog"].sync_check_any_link(m.content)
            c1 = c2 = c3 = c4 = True
            if pinned != 1:
                if (m.pinned and pinned==0) or (not m.pinned and pinned==2):
                    c1 = False
            else:
                c1 = not m.pinned
            if files != 1:
                if (m.attachments != [] and files==0) or (m.attachments==[] and files==2):
                    c2 = False
            if links != 1:
                if (r == None and links==2) or (r != None and links==0):
                    c3 = False
            if invites != 1:
                if (i == None and invites==2) or (i != None and invites==0):
                    c4 = False
            #return ((m.pinned == pinned) or ((m.attachments != []) == files) or ((r != None) == links)) and m.author in users
            mentions = re.findall(r'<@!?\d{16,18}>', ctx.message.content)
            if str(ctx.bot.user.id) in ctx.prefix:
                mentions.remove(ctx.bot.user.id)
            if mentions != [] and m.author != None:
                return c1 and c2 and c3 and c4 and m.author.id in mentions
            else:
                return c1 and c2 and c3 and c4
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=number, check=check)
            await ctx.send(str(await self.translate(ctx.guild,"modo","clear-0")).format(len(deleted)),delete_after=2.0)
            if len(deleted) > 0:
                log = str(await self.translate(ctx.guild.id,"logs","clear")).format(channel=ctx.channel.mention,number=len(deleted))
                await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)

    async def clear_simple(self,ctx,number):
        def check(m):
            return not m.pinned
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=number, check=check)
            await ctx.send(str(await self.translate(ctx.guild,"modo","clear-0")).format(len(deleted)),delete_after=2.0)
            log = str(await self.translate(ctx.guild.id,"logs","clear")).format(channel=ctx.channel.mention,number=len(deleted))
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        except discord.errors.NotFound:
            await ctx.send(await self.translate(ctx.guild,"modo","clear-nt-found"))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)


    @commands.command(name="kick")
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_kick)
    async def kick(self,ctx,user:discord.Member,*,reason="Unspecified"):
        """Kick a member from this server

..Example kick @someone Not nice enough to stay here        

..Doc moderator.html#kick"""
        try:
            if not ctx.channel.permissions_for(ctx.guild.me).kick_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-kick"))
                return
            async def user_can_kick(user): 
                try:
                    return await self.bot.cogs["ServerCog"].staff_finder(user,"kick")
                except commands.errors.CommandError:
                    pass
                return False
            if user==ctx.guild.me or (self.bot.database_online and await user_can_kick(user)):
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).kick_members:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            if user.roles[-1].position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
                return
            if user.id not in self.bot.cogs['WelcomerCog'].no_message:
                try:
                    if reason == "Unspecified":
                        await user.send(str(await self.translate(ctx.guild.id,"modo","kick-noreason")).format(ctx.guild.name))
                    else:
                        await user.send(str(await self.translate(ctx.guild.id,"modo","kick-reason")).format(ctx.guild.name,reason))
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    pass
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.kick(user,reason=reason)
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="kick",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","kick")).format(user,reason))
            log = str(await self.translate(ctx.guild.id,"logs","kick")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"kick",log,ctx.author)
        except discord.errors.Forbidden:
            await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
        await self.bot.cogs['Events'].add_event('kick')


    @commands.command(name="warn")
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_warn)
    async def warn(self,ctx,user:discord.Member,*,message):
        """Send a warning to a member

..Example warn @someone Please just stop, next one is a mute duh

..Doc moderator.html#warn"""
        try:
            async def user_can_warn(user): 
                try:
                    return await self.bot.cogs["ServerCog"].staff_finder(user,"warn")
                except commands.errors.CommandError:
                    pass
                return False
            if user==ctx.guild.me or (self.bot.database_online and await user_can_warn(user)):
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
            if user.bot and not user.id==423928230840500254:
                await ctx.send(await self.translate(ctx.guild.id,"modo","warn-bot"))
                return
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            return
        try:
            try:
                await user.send(str(await self.translate(ctx.guild.id,"modo","warn-mp")).format(ctx.guild.name,message))
            except:
                pass
            message = await self.bot.cogs["UtilitiesCog"].clear_msg(message,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="warn",ModID=ctx.author.id,Reason=message,date=datetime.datetime.now()).create_id(caseIDs)
                caseID = "'Unsaved'"
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                else:
                    await ctx.send(str(await self.translate(ctx.guild.id,"modo","warn-1")).format(user,message))
                log = str(await self.translate(ctx.guild.id,"logs","warn")).format(member=user,reason=message,case=caseID)
                await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"warn",log,ctx.author)
            else:
                await ctx.send(await self.translate(ctx.guild.id,'modo','warn-but-db'))
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    async def get_muted_role(self,guild):
        opt = await self.bot.cogs['ServerCog'].find_staff(guild.id,'muted_role')
        if not isinstance(opt,int):
            return discord.utils.get(guild.roles,name="muted")
        return guild.get_role(opt)

    async def mute_event(self, member:discord.Member, author:discord.Member, reason:str, caseID:int, duration:str=None):
        role = await self.get_muted_role(member.guild)
        await member.add_roles(role,reason=reason)
        log = str(await self.translate(member.guild.id,"logs","mute-on" if duration==None else "tempmute-on")).format(member=member,reason=reason,case=caseID,duration=duration)
        await self.bot.cogs["Events"].send_logs_per_server(member.guild,"mute",log,author)

    async def check_mute_context(self,ctx,role,user):
        if role in user.roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","already-mute"))
            return False
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return False
        if role == None:
            role = await ctx.guild.create_role(name="muted")
            # await self.bot.cogs['ModeratorCog'].configure_muted_role(ctx.guild, role)
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-role-created", p=ctx.prefix))
            return True
        if role.position > ctx.guild.me.roles[-1].position:
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-high"))
            return False
        return True

    @commands.command(name="mute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def mute(self,ctx,user:discord.Member,time:commands.Greedy[args.tempdelta],*,reason="Unspecified"):
        """Mute someone. 
When someone is muted, the bot adds the role "muted" to them
You can also mute this member for a defined duration, then use the following format:
`XXm` : XX minutes
`XXh` : XX hours
`XXd` : XX days
`XXw` : XX weeks

..Example mute @someone 1d 3h Reason is becuz he's a bad guy

..Example mute @someone Plz respect me

..Doc moderator.html#mute-unmute"""
        duration = sum(time)
        if duration>0:
            f_duration = await self.bot.cogs['TimeCog'].time_delta(duration,lang=await self.translate(ctx.guild,'current_lang','current'),form='temp',precision=0)
        else:
            f_duration = None
        try:
            async def user_can_mute(user): 
                try:
                    return await self.bot.cogs["ServerCog"].staff_finder(user,"mute")
                except commands.errors.CommandError:
                    pass
                return False
            if user==ctx.guild.me or (self.bot.database_online and await user_can_mute(user)):
                await ctx.send(str(await self.translate(ctx.guild.id,"modo","staff-mute"))+random.choice([':confused:',':upside_down:',self.bot.cogs['EmojiCog'].customEmojis['wat'],':no_mouth:',self.bot.cogs['EmojiCog'].customEmojis['owo'],':thinking:',]))
                return
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            return
        role = await self.get_muted_role(ctx.guild)
        if not await self.check_mute_context(ctx, role, user):
            return
        if role is None:
            role = await self.get_muted_role(ctx.guild)
        if role is None:
            self.bot.log.warn(f"[muted_role] Unable to get role for guild {ctx.guild.id}")
            await ctx.send(await self.translate(ctx.guild.id, "modo", "no-mute"))
            return
        caseID = "'Unsaved'"
        try:
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                if f_duration==None:
                    case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="mute",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                else:
                    case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="tempmute",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now(),duration=duration).create_id(caseIDs)
                    await self.bot.cogs['Events'].add_task('mute',duration,user.id,ctx.guild.id)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            if user.id not in self.bot.cogs['WelcomerCog'].no_message:
                try:
                    if f_duration == None:
                        await user.send(await self.translate(ctx.guild.id,"modo","mute-notemp", server=ctx.guild.name, reason=reason))
                    else:
                        await user.send(await self.translate(ctx.guild.id,"modo","mute-temp", server=ctx.guild.name, reason=reason, duration=f_duration))
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    pass
            if f_duration==None:
                await self.mute_event(user,ctx.author,reason,caseID)
                await ctx.send(str(await self.translate(ctx.guild.id,"modo","mute-1")).format(user,reason))
            else:
                await self.mute_event(user,ctx.author,reason,caseID,f_duration)
                await ctx.send(str(await self.translate(ctx.guild.id,"modo","tempmute-1")).format(user,reason,f_duration))
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)


    async def unmute_event(self,guild,user,author):
        role = await self.get_muted_role(guild)
        if role==None or not role in user.roles:
            return
        if author==guild.me:
            await user.remove_roles(role,reason=await self.translate(guild.id,"logs","d-autounmute"))
        else:
            await user.remove_roles(role,reason=str(await self.translate(guild.id,"logs","d-unmute")).format(author))
        log = str(await self.translate(guild.id,"logs","mute-off")).format(member=user)
        await self.bot.cogs["Events"].send_logs_per_server(guild,"mute",log,author)

    @commands.command(name="unmute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def unmute(self, ctx:commands.Context, *, user:discord.Member):
        """Unmute someone
This will remove the role 'muted' for the targeted member

..Example unmute @someone

..Doc moderator.html#mute-unmute"""
        role = await self.get_muted_role(ctx.guild)
        if role not in user.roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","already-unmute"))
            return
        if role == None:
            await ctx.send(await self.translate(ctx.guild.id,"modo","no-mute"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return
        if role.position >= ctx.guild.me.roles[-1].position:
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-high"))
            return
        try:
            await self.unmute_event(ctx.guild,user,ctx.author)
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","unmute-1")).format(user))
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @commands.command(name="mute-config")
    @commands.cooldown(1,15, commands.BucketType.guild)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def mute_config(self, ctx:commands.Context):
        """Auto configure the muted role for you
        Useful if you want to have a base for a properly working muted role
        Warning: the process may break some things in your server, depending on how you configured your channel permissions.

        ..Doc moderator.html#mute-unmute
        """
        role = await self.get_muted_role(ctx.guild)
        create = role is None
        role, count = await self.configure_muted_role(ctx.guild, role)
        if role is None or count >= len(ctx.guild.voice_channels+ctx.guild.text_channels):
            await ctx.send(await self.translate(ctx.guild.id, "modo", "mute-config-err"))
        elif create:
            await ctx.send(await self.translate(ctx.guild.id, "modo", "mute-config-success", c=count))
        else:
            await ctx.send(await self.translate(ctx.guild.id, "modo", "mute-config-success2", c=count))


    @commands.command(name="ban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_ban)
    async def ban(self,ctx,user:args.user,time:commands.Greedy[args.tempdelta],days_to_delete:typing.Optional[int]=0,*,reason="Unspecified"):
        """Ban someone
The 'days_to_delete' option represents the number of days worth of messages to delete from the user in the guild, bewteen 0 and 7

..Example ban @someone 3d You're bad

..Example ban someone#1234 7 Spam isn't tolerated here

..Example ban someone_else DM advertising is against Discord ToS!!!

..Doc moderator.html#ban-unban
        """
        try:
            duration = sum(time)
            if duration>0:
                f_duration = await self.bot.cogs['TimeCog'].time_delta(duration,lang=await self.translate(ctx.guild,'current_lang','current'),form='temp',precision=0)
            else:
                f_duration = None
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
            if user in ctx.guild.members:
                member = ctx.guild.get_member(user.id)
                async def user_can_ban(user): 
                    try:
                        return await self.bot.cogs["ServerCog"].staff_finder(user,"ban")
                    except commands.errors.CommandError:
                        pass
                    return False
                if user==ctx.guild.me or (self.bot.database_online and await user_can_ban(member)):
                    await ctx.send(await self.translate(ctx.guild.id,"modo","staff-ban"))
                    return
                elif not self.bot.database_online and (ctx.channel.permissions_for(member).ban_members or user==ctx.guild.me):
                    await ctx.send(await self.translate(ctx.guild.id,"modo","staff-ban"))
                    return
                if member.roles[-1].position >= ctx.guild.me.roles[-1].position:
                    await ctx.send(await self.translate(ctx.guild.id,"modo","ban-1"))
                    return
            if user in self.bot.users and user.id not in self.bot.cogs['WelcomerCog'].no_message:
                try:
                    if reason == "Unspecified":
                        await user.send(str(await self.translate(ctx.guild.id,"modo","ban-noreason")).format(ctx.guild.name))
                    else:
                        await user.send(str(await self.translate(ctx.guild.id,"modo","ban-reason")).format(ctx.guild.name,reason))
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    pass
            if not days_to_delete in range(8):
                days_to_delete = 0
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.ban(user,reason=reason,delete_message_days=days_to_delete)
            if f_duration==None:
                self.bot.log.info("L'utilisateur {} a été banni du serveur {} pour la raison {}".format(user.id,ctx.guild.id,reason))
            else:
                self.bot.log.info("L'utilisateur {} a été banni du serveur {} pour la raison {} pendant {}".format(user.id,ctx.guild.id,reason,f_duration))
            await self.bot.cogs['Events'].add_event('ban')
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                if f_duration==None:
                    case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="ban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                else:
                    case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="tempban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now(),duration=duration).create_id(caseIDs)
                    await self.bot.cogs['Events'].add_task('ban',duration,user.id,ctx.guild.id)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
            if f_duration==None:
                await ctx.send(str( await self.translate(ctx.guild.id,"modo","ban")).format(user,reason))
                log = str(await self.translate(ctx.guild.id,"logs","ban")).format(member=user,reason=reason,case=caseID)
            else:
                await ctx.send(str( await self.translate(ctx.guild.id,"modo","tempban")).format(user,f_duration,reason))
                log = str(await self.translate(ctx.guild.id,"logs","tempban")).format(member=user,reason=reason,case=caseID,duration=f_duration)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"ban",log,ctx.author)
        except discord.errors.Forbidden:
            await ctx.send(await self.translate(ctx.guild.id,"modo","ban-1"))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    async def unban_event(self,guild,user,author):
        if not guild.me.guild_permissions.ban_members:
            return
        await guild.unban(user,reason=str(await self.translate(guild.id,"logs","d-unban")).format(author))
        log = str(await self.translate(guild.id,"logs","unban")).format(member=user,reason="automod")
        await self.bot.cogs["Events"].send_logs_per_server(guild,"ban",log,author)

    @commands.command(name="unban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_ban)
    async def unban(self,ctx,user,*,reason="Unspecified"):
        """Unban someone

..Example !unban 486896267788812288 Nice enough

..Doc moderator.html#ban-unban"""
        try:
            backup = user
            try:
                user = await commands.UserConverter().convert(ctx,user)
            except:
                if user.isnumeric():
                    try:
                        user = await self.bot.fetch_user(int(user))
                        del backup
                    except:
                        await ctx.send(str(await self.translate(ctx.guild.id,"modo","cant-find-user")).format(backup))
                        return
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
            banned_list = [x[1] for x in await ctx.guild.bans()]
            if user not in banned_list:
                await ctx.send(await self.translate(ctx.guild.id,"modo","ban-user-here"))
                return
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.unban(user,reason=reason)
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="unban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","unban")).format(user))
            log = str(await self.translate(ctx.guild.id,"logs","unban")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"ban",log,ctx.author)
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @commands.command(name="softban")
    @commands.guild_only()
    @commands.check(checks.can_kick)
    async def softban(self,ctx,user:discord.Member,reason="Unspecified"):
        """Kick a member and lets Discord delete all his messages up to 7 days old.
Permissions for using this command are the same as for the kick

..Example softban @someone No spam pls

..Doc moderator.html#softban"""
        try:
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
            async def user_can_kick(user): 
                try:
                    return await self.bot.cogs["ServerCog"].staff_finder(user,"kick")
                except commands.errors.CommandError:
                    pass
                return False
            if user==ctx.guild.me or (self.bot.database_online and await user_can_kick(user)):
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).kick_members:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            if user.roles[-1].position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
                return
            try:
                if reason == "Unspecified":
                    await user.send(str(await self.translate(ctx.guild.id,"modo","kick-noreason")).format(ctx.guild.name))
                else:
                    await user.send(str(await self.translate(ctx.guild.id,"modo","kick-reason")).format(ctx.guild.name,reason))
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                pass
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.ban(user,reason=reason,delete_message_days=7)
            await user.unban()
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="softban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","kick")).format(user,reason))
            log = str(await self.translate(ctx.guild.id,"logs","softban")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"softban",log,ctx.author)
        except discord.errors.Forbidden:
            await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)


    @commands.command(name="banlist")
    @commands.guild_only()
    @commands.check(checks.has_admin)
    async def banlist(self,ctx,reasons:bool=True):
        """Check the list of currently banned members.
The 'reasons' parameter is used to display the ban reasons.

You must be an administrator of this server to use this command.

..Doc moderator.html#banlist"""
        if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
        try:
            liste = await ctx.guild.bans()
        except:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
        desc = list()
        if len(liste)==0:
            desc.append(await self.translate(ctx.guild.id,"modo","no-bans"))
        if reasons:
            for case in liste[:45]:
                desc.append("{}  *({})*".format(case[1],case[0]))
            if len(liste)>45:
                title = await self.translate(ctx.guild.id,"modo","ban-list-title-1")
            else:
                title = await self.translate(ctx.guild.id,"modo","ban-list-title-0")
        else:
            for case in liste[:60]:
                desc.append("{}".format(case[1]))
            if len(liste)>60:
                title = await self.translate(ctx.guild.id,"modo","ban-list-title-2")
            else:
                title = await self.translate(ctx.guild.id,"modo","ban-list-title-0")
        embed = ctx.bot.cogs['EmbedCog'].Embed(title=str(title).format(ctx.guild.name), color=self.bot.cogs["ServerCog"].embed_color, desc="\n".join(desc), time=ctx.message.created_at)
        await embed.create_footer(ctx)
        try:
            await ctx.send(embed=embed.discord_embed(),delete_after=15)
        except discord.errors.HTTPException as e:
            if e.code==400:
                await ctx.send(await self.translate(ctx.guild.id,"modo","ban-list-error"))


    @commands.group(name="emoji",aliases=['emojis'])
    @commands.guild_only()
    @commands.cooldown(5,20, commands.BucketType.guild)
    async def emoji_group(self,ctx):
        """Manage your emoji
        Administrator permission is required"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['emoji'])

    @emoji_group.command(name="rename")
    @commands.check(checks.has_admin)
    async def emoji_rename(self,ctx,emoji:discord.Emoji,name):
        """Rename an emoji"""
        if emoji.guild != ctx.guild:
            await ctx.send(await self.translate(ctx.guild.id,"modo","wrong-guild"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_emojis:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-emoji"))
            return
        await emoji.edit(name=name)
        await ctx.send(str(await self.translate(ctx.guild.id,"modo","emoji-renamed")).format(emoji))

    @emoji_group.command(name="restrict")
    @commands.check(checks.has_admin)
    async def emoji_restrict(self,ctx,emoji:discord.Emoji,*,roles):
        """Restrict the use of an emoji to certain roles"""
        if emoji.guild != ctx.guild:
            await ctx.send(await self.translate(ctx.guild.id,"modo","wrong-guild"))
            return
        r = list()
        if not ctx.channel.permissions_for(ctx.guild.me).manage_emojis:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-emoji"))
            return
        for role in roles.split(","):
            role = role.strip()
            if role == "everyone":
                role = "@everyone"
            try:
                role = await commands.RoleConverter().convert(ctx,role)
            except commands.errors.BadArgument:
                msg = await self.translate(ctx.guild.id,"server","change-3")
                await ctx.send(msg.format(role))
                return
            r.append(role)
        await emoji.edit(name=emoji.name,roles=r)
        await ctx.send(str(await self.translate(ctx.guild.id,"modo","emoji-valid")).format(emoji,", ".join([x.name for x in r])))

    @emoji_group.command(name="clear")
    @commands.check(checks.has_manage_msg)
    async def emoji_clear(self,ctx,message:discord.Message):
        """Remove all reactions under a message"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            return await ctx.send(await self.translate(ctx.guild.id,'modo','need-manage-messages'))
        await message.clear_reactions()
        try:
            await ctx.message.delete()
        except:
            pass
    
    @emoji_group.command(name="info")
    @commands.check(checks.has_manage_msg)
    async def emoji_info(self,ctx,emoji:discord.Emoji):
        """Get info about an emoji
        This is only an alias or `info emoji`"""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + "info emoji " + str(emoji.id)
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @emoji_group.command(name="list")
    async def emoji_list(self,ctx):
        """List every emoji of your server"""
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.translate(ctx.guild.id,"fun","no-embed-perm"))
        structure = await self.translate(ctx.guild.id,"modo","em-list")
        date = ctx.bot.cogs['TimeCog'].date
        lang = await self.translate(ctx.guild.id,"current_lang","current")
        priv = "**"+await self.translate(ctx.guild.id,"modo","em-private")+"**"
        title = str(await self.translate(ctx.guild.id,"modo","em-list-title")).format(ctx.guild.name)
        try:
            emotes = [structure.format(x,x.name,await date(x.created_at,lang,year=True,hour=False,digital=True),priv if len(x.roles)>0 else '') for x in ctx.guild.emojis if not x.animated]
            emotes += [structure.format(x,x.name,await date(x.created_at,lang,year=True,hour=False,digital=True),priv if len(x.roles)>0 else '') for x in ctx.guild.emojis if x.animated]
            emotes = emotes
            nbr = len(emotes)
            for x in range(0,nbr,50):
                fields = list()
                for i in range(x, min(x+50,nbr), 10):
                    l = list()
                    for x in emotes[i:i+10]:
                        l.append(x)
                    fields.append({'name':"{}-{}".format(i+1,i+10 if i+10<nbr else nbr), 'value':"\n".join(l), 'inline':False})
                embed = await ctx.bot.cogs['EmbedCog'].Embed(title=title,fields=fields,color=self.bot.cogs["ServerCog"].embed_color).create_footer(ctx)
                await ctx.send(embed=embed.discord_embed())
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_command_error(ctx,e)


    @commands.group(name="role", aliases=["roles"])
    @commands.guild_only()
    async def main_role(self,ctx):
        """A few commands to manage roles"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['role'])
    
    @main_role.command(name="color",aliases=['colour'])
    @commands.check(checks.has_manage_roles)
    async def role_color(self,ctx,role:discord.Role,color:discord.Color):
        """Change a color of a role"""
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return
        if role.position >= ctx.guild.me.roles[-1].position:
            await ctx.send(await self.translate(ctx.guild.id,"modo","role-high",r=role.name))
            return
        await role.edit(colour=color,reason="Asked by {}".format(ctx.author))
        await ctx.send(str(await self.translate(ctx.guild.id,'modo','role-color')).format(role.name))
    
    @main_role.command(name="list")
    @commands.cooldown(5,30,commands.BucketType.guild)
    async def role_list(self,ctx,*,role:discord.Role):
        """Send the list of members in a role"""
        if not (await checks.has_manage_roles(ctx) or await checks.has_manage_guild(ctx) or await checks.has_manage_msg(ctx)):
            await ctx.send(await self.translate(ctx.guild.id, "modo","missing-user-perms"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.translate(ctx.guild.id,'fun','no-embed-perm'))
        tr_nbr = await self.translate(ctx.guild.id,'stats_infos','role-3')
        tr_mbr = await self.translate(ctx.guild.id,"keywords","membres")
        txt = str()
        fields = list()
        fields.append({'name':tr_nbr.capitalize(),'value':str(len(role.members))})
        nbr = len(role.members)
        if nbr<=200:
            for i in range(nbr):
                txt += role.members[i].mention+" "
                if i<nbr-1 and len(txt+role.members[i+1].mention)>1000:
                    fields.append({'name':tr_mbr.capitalize(),'value':txt})
                    txt = str()
            if len(txt)>0:
                fields.append({'name':tr_mbr.capitalize(),'value':txt})
        emb = await self.bot.cogs['EmbedCog'].Embed(title=role.name,fields=fields,color=role.color).update_timestamp().create_footer(ctx)
        await ctx.send(embed=emb.discord_embed())
    
    @main_role.command(name="server-list",aliases=["glist"])
    @commands.cooldown(5,30,commands.BucketType.guild)
    async def role_glist(self, ctx:commands.Context):
        """Check the list of every role"""
        if not (await checks.has_manage_roles(ctx) or await checks.has_manage_guild(ctx) or await checks.has_manage_msg(ctx)):
            await ctx.send(await self.translate(ctx.guild.id, "modo","missing-user-perms"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.translate(ctx.guild.id,'fun','no-embed-perm'))
        tr_mbr = await self.translate(ctx.guild.id,"keywords","membres")
        title = await self.translate(ctx.guild.id,"modo","roles-list")
        desc = list()
        count = 0
        for role in ctx.guild.roles[1:]:
            txt = "{} - {} {}".format(role.mention, len(role.members), tr_mbr)
            if count+len(txt) > 2040:
                emb = await self.bot.cogs['EmbedCog'].Embed(title=title,desc="\n".join(desc),color=ctx.guild.me.color).update_timestamp().create_footer(ctx)
                await ctx.send(embed=emb)
                desc.clear()
                count = 0
            desc.append(txt)
            count += len(txt)+2
        if count>0:
            emb = await self.bot.cogs['EmbedCog'].Embed(title=title,desc="\n".join(desc),color=ctx.guild.me.color).update_timestamp().create_footer(ctx)
            await ctx.send(embed=emb)

    
    @main_role.command(name="info")
    @commands.check(checks.has_manage_msg)
    async def role_info(self,ctx,role:discord.Role):
        """Get info about a role
        This is only an alias or `info role`"""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + "info role " + str(role.id)
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @main_role.command(name="give", aliases=["add"])
    @commands.check(checks.has_manage_roles)
    async def roles_give(self,ctx,role:discord.Role,users:commands.Greedy[typing.Union[discord.Role,discord.Member]]):
        """Give a role to a list of roles/members
        Users list may be either members or roles, or even only one member"""
        if len(users)==0:
            raise commands.MissingRequiredArgument(self.roles_give.clean_params['users'])
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","give_roles-4",r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","give_roles-higher"))
        answer = list()
        n_users = set()
        error_count = 0
        for item in users:
            if isinstance(item,discord.Member):
                n_users.add(item)
            else:
                for m in item.members:
                    n_users.add(m)
        for user in n_users:
            await user.add_roles(role,reason="Asked by {}".format(ctx.author))
        answer.append(await self.translate(ctx.guild.id,"modo","give_roles-2",c=len(n_users)-error_count,m=len(n_users)))
        await ctx.send("\n".join(answer))

    @main_role.command(name="remove")
    @commands.check(checks.has_manage_roles)
    async def roles_remove(self,ctx,role:discord.Role,users:commands.Greedy[typing.Union[discord.Role,discord.Member]]):
        """Remove a role to a list of roles/members
        Users list may be either members or roles, or even only one member"""
        if len(users)==0:
            raise commands.MissingRequiredArgument(self.roles_remove.clean_params['users'])
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","give_roles-4",r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","give_roles-higher"))
        answer = list()
        n_users = set()
        error_count = 0
        for item in users:
            if isinstance(item,discord.Member):
                n_users.add(item)
            else:
                for m in item.members:
                    n_users.add(m)
        for user in n_users:
            await user.remove_roles(role,reason="Asked by {}".format(ctx.author))
        answer.append(await self.translate(ctx.guild.id,"modo","remove_roles-1",c=len(n_users)-error_count,m=len(n_users)))
        await ctx.send("\n".join(answer))


    @commands.command(name="pin")
    @commands.check(checks.has_manage_msg)
    async def pin_msg(self,ctx,msg:int):
        """Pin a message
ID corresponds to the Identifier of the message"""
        if ctx.guild!=None and not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.translate(ctx.channel,"modo","cant-pin"))
            return
        try:
            message = await ctx.channel.fetch_message(msg)
        except Exception as e:
            await ctx.send(str(await self.translate(ctx.channel,"modo","pin-error")).format(e))
            return
        try:
            await message.pin()
        except Exception as e:
            await ctx.send(str(await self.translate(ctx.channel,"modo","pin-error-3")).format(e))
            return
    
    @commands.command(name='unhoist')
    @commands.guild_only()
    @commands.check(checks.has_manage_nicknames)
    async def unhoist(self,ctx,chars=None):
        """Remove the special characters from usernames"""
        count = 0
        if not ctx.channel.permissions_for(ctx.guild.me).manage_nicknames:
            return await ctx.send(await self.translate(ctx.guild.id,'modo','missing-manage-nick'))
        if chars==None:
            def check(username):
                while username < '0':
                    username = username[1:]
                    if len(username)==0:
                        username = "z unhoisted"
                return username
        else:
            chars = chars.lower()
            def check(username):
                while username[0].lower() in chars+' ':
                    username = username[1:]
                return username
        for member in ctx.guild.members:
            try:
                new = check(member.display_name)
                if new!=member.display_name:
                    if not self.bot.beta:
                        await member.edit(nick=new)
                    count += 1
            except:
                pass
        await ctx.send(await self.translate(ctx.guild.id,'modo','unhoisted',c=count))
    
    @commands.command(name="destop")
    @commands.guild_only()
    @commands.check(checks.can_clear)
    @commands.cooldown(2, 30, commands.BucketType.channel)
    async def destop(self, ctx:commands.Context, message:discord.Message):
        """Clear every message between now and another message
        Message can be either ID or url
        Limited to 1,000 messages
        
        ..Example destop https://discordapp.com/channels/356067272730607628/488769306524385301/740249890201796688
        
        ..Doc moderator.html#clear"""
        if message.guild != ctx.guild:
            await ctx.send(await self.translate(ctx.guild.id, "modo", "destop-guild"))
            return
        if not message.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.translate(ctx.guild.id, "modo", "need-manage-messages"))
            return
        if not message.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.translate(ctx.guild.id, "modo", "need-read-history"))
            return
        check = lambda x: not x.pinned
        if message.created_at < datetime.datetime.utcnow() - datetime.timedelta(days=21):
            await ctx.send(await self.translate(ctx.guild.id, "modo", "destop-old", days=21))
            return
        messages = await message.channel.purge(after=message, limit=1000, oldest_first=False)
        await message.delete()
        messages.append(message)
        txt = (await self.translate(ctx.guild.id, "modo", "clear-0")).format(len(messages))
        await ctx.send(txt, delete_after=2.0)
        log = str(await self.translate(ctx.guild.id,"logs","clear")).format(channel=message.channel.mention,number=len(messages))
        await self.bot.get_cog("Events").send_logs_per_server(ctx.guild, "clear", log, ctx.author)
    

    async def find_verify_question(self,ctx:commands.Context) -> (str,str):
        """Find a question/answer for a verification question"""
        raw_info = await self.translate(ctx.guild,'modo','verify_questions')
        q = random.choice(raw_info)
        a = q[1]
        q = q[0]
        if a.startswith('_'):
            if a=='_special_servername':
                isascii = lambda s: len(s) == len(s.encode())
                if isascii(ctx.guild.name):
                    a = ctx.guild.name
                else:
                    return await self.find_verify_question(ctx)
            elif a=='_special_userdiscrim':
                a = ctx.author.discriminator
        return q,a

    @commands.command(name="verify")
    @commands.guild_only()
    @commands.check(checks.verify_role_exists)
    @commands.cooldown(5,120,commands.BucketType.user)
    async def verify_urself(self,ctx:commands.Context):
        """Verify yourself and loose the role"""
        roles_raw = await ctx.bot.cogs['ServerCog'].find_staff(ctx.guild.id,"verification_role")
        roles = [r for r in [ctx.guild.get_role(int(x)) for x in roles_raw.split(';') if x.isnumeric] if r!=None]
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
        txt = str()
        for role in roles:
            if role.position > ctx.guild.me.roles[-1].position:
                txt += await self.translate(ctx.guild.id,"modo","verify-role-high",r=role.name) + "\n"
        if len(txt)>0:
            return await ctx.send(txt)
        del txt

        q,a = await self.find_verify_question(ctx)
        qu_msg = await ctx.send(ctx.author.mention+': '+q)
        await asyncio.sleep(random.random()*1.3)
        async def del_msg(msg:discord.Message):
            try:
                await msg.delete()
            except:
                pass
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        try:
            msg = await ctx.bot.wait_for('message', check=check, timeout=15)
        except asyncio.TimeoutError:
            await del_msg(qu_msg)
        else:
            if msg.content.lower() == a.lower():
                await del_msg(msg)
                try:
                    await ctx.author.remove_roles(*roles,reason="Verified")
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)
            await del_msg(qu_msg)



    async def configure_muted_role(self, guild: discord.Guild, role: discord.Role = None):
        """Ajoute le rôle muted au serveur, avec les permissions nécessaires"""
        if not guild.me.guild_permissions.manage_roles:
            return None, 0
        if role is None:
            role = await guild.create_role(name="muted")
        count = 0
        try:
            for x in guild.by_category():
                category, channelslist = x[0], x[1]
                for channel in channelslist:
                    if channel is None:
                        continue
                    if len(channel.changed_roles) != 0 and not channel.permissions_synced:
                        try:
                            await channel.set_permissions(role, send_messages=False)
                            for r in channel.changed_roles:
                                if r.permissions.send_messages:
                                    obj = channel.overwrites_for(r)
                                    obj.send_messages = None
                                    await channel.set_permissions(r, overwrite=obj)
                        except discord.errors.Forbidden:
                            count += 1
                if category is not None and category.permissions_for(guild.me).manage_roles:
                    await category.set_permissions(role, send_messages=False)
            await self.bot.cogs['ServerCog'].modify_server(guild.id, values=[('muted_role',role.id)])
            return role, count
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e, None)
            return role, len(guild.channels)


def setup(bot):
    bot.add_cog(ModeratorCog(bot))
