import discord, random, time, asyncio, io, imageio, importlib, re, os, operator, platform, typing, aiohttp
from discord.ext import commands
from math import ceil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk
from urllib.request import urlopen, Request

from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)

class XPCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.cache = dict() # {ID : [date, xp]}
        self.levels = [0]
        self.embed_color = discord.Colour(0xffcf50)
        self.table = 'xp_beta' if bot.beta else 'xp'
        self.cooldown = 30
        self.minimal_size = 5
        self.spam_rate = 0.20
        self.xp_per_char = 0.11
        self.max_xp_per_msg = 60
        self.file = 'xp'
        self.xp_channels_cache = dict()
        bot.add_listener(self.add_xp,'on_message')
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
        self.types = ['global','mee6']
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
        self.table = 'xp_beta' if self.bot.beta else 'xp'
        await self.bdd_load_cache()

    async def add_xp(self,msg):
        """Attribue un certain nombre d'xp à un message"""
        if msg.author.bot or msg.guild==None or not self.bot.xp_enabled:
            return
        if not await self.check_noxp(msg) or await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'xp_type')==1:
            return 
        if len(self.cache)==0:
            await self.bdd_load_cache()
        if msg.author.id in self.cache.keys():
            if time.time() - self.cache[msg.author.id][0] < self.cooldown:
                return
        s = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'enable_xp')
        if not s:
            return
        content = msg.clean_content
        if len(content)<self.minimal_size or await self.check_spam(content) or await self.check_cmd(msg):
            return
        giv_points = await self.calc_xp(msg)
        if msg.author.id in self.cache.keys():
            prev_points = self.cache[msg.author.id][1]
        else:
            prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points,'add')
        self.cache[msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl = await self.calc_level(self.cache[msg.author.id][1])
        if 1 < (await self.calc_level(prev_points))[0] < new_lvl[0]:
            await self.send_levelup(msg,new_lvl)
            await self.give_rr(msg.author,new_lvl[0],await self.rr_list_role(msg.guild.id))

    async def check_noxp(self,msg):
        """Check if this channel/user can get xp"""
        if msg.guild == None:
            return False
        if msg.guild.id in self.xp_channels_cache.keys():
            if msg.channel.id in self.xp_channels_cache[msg.guild.id]:
                return False
        else:
            chans = await self.bot.cogs["ServerCog"].find_staff(msg.guild.id,'noxp_channels')
            if chans != None:
                chans = [int(x) for x in chans.split(';') if x.isnumeric()]
                if msg.channel.id in chans:
                    return False
            else:
                chans = []
            self.xp_channels_cache[msg.guild.id] = chans
        return True


    async def send_levelup(self,msg,lvl):
        """Envoie le message de levelup"""
        if msg.guild!=None and not msg.channel.permissions_for(msg.guild.me).send_messages:
            return
        text = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'levelup_msg')
        if text==None or len(text)==0:
            text = await self.translate(msg.guild.id,'xp','default_levelup')
        await msg.channel.send(text.format_map(self.bot.SafeDict(user=msg.author.mention,level=lvl[0])))
        
    async def check_cmd(self,msg):
        """Vérifie si un message est une commande"""
        pr = await self.bot.get_prefix(msg)
        is_cmd = False
        for p in pr:
            is_cmd = is_cmd or msg.content.startswith(p)
        return is_cmd

    async def check_spam(self,text):
        """Vérifie si un text contient du spam"""
        d = dict()
        for c in text:
            if c in d.keys():
                d[c] += 1
            else:
                d[c] = 1
        for v in d.values():
            if v/len(text) > self.spam_rate:
                return True
        return False

    async def calc_xp(self,msg):
        """Calcule le nombre d'xp correspondant à un message"""
        content = msg.clean_content
        matches = re.finditer(r"<a?(:\w+:)\d+>", content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0),match.group(1))
        matches = re.finditer(r'((?:http|www)[^\s]+)', content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0),"")
        return min(round(len(content)*self.xp_per_char), self.max_xp_per_msg)

    async def calc_level(self,xp):
        """Calcule le niveau correspondant à un nombre d'xp"""
        if xp==0:
            return [0,ceil(20*20**(353/647)*1**(1000/647)),0]
        lvl = ceil(0.05*xp**0.647)
        next_step = xp
        while ceil(0.05*next_step**0.647)==lvl:
            next_step += 1
        return [lvl,next_step,ceil(20*20**(353/647)*(lvl-1)**(1000/647))]
        # Niveau actuel - XP total pour le prochain niveau - XP total pour le niveau actuel

    async def give_rr(self,member:discord.Member,level:int,rr_list:list,remove=False):
        """Give (and remove?) roles rewards to a member"""
        c = 0
        has_roles = [x.id for x in member.roles]
        for role in [x for x in rr_list if x['level']<=level and x['role'] not in has_roles]:
            try:
                r = member.guild.get_role(role['role'])
                if r==None:
                    continue
                await member.add_roles(r,reason="Role reward (lvl {})".format(role['level']))
                c += 1
            except Exception as e:
                if self.bot.beta:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                pass
        if not remove:
            return c
        for role in [x for x in rr_list if x['level']>level and x['role'] in has_roles]:
            try:
                r = member.guild.get_role(role['role'])
                if r==None:
                    continue
                await member.remove_roles(r,reason="Role reward (lvl {})".format(role['level']))
                c += 1
            except Exception as e:
                if self.bot.beta:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                pass
        return c

    async def bdd_set_xp(self,userID,points,Type='add'):
        """Ajoute/reset de l'xp à un utilisateur dans la database générale"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            if Type=='add':
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = xp + '{p}';".format(t=self.table,p=points,u=userID))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = '{p}';".format(t=self.table,p=points,u=userID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def bdd_get_xp(self,userID):
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT `xp` FROM `{}` WHERE `userID`={}".format(self.table,userID))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            if len(liste)==1:
                if userID in self.cache.keys():
                    self.cache[userID][1] = liste[0]['xp']
                else:
                    self.cache[userID] = [round(time.time())-60,liste[0]['xp']]
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
    
    async def bdd_get_nber(self):
        """Get the number of ranked users"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = False)
            query = ("SELECT COUNT(*) FROM `{}` WHERE `banned`=0".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            if liste!=None and len(liste)==1:
                return liste[0][0]
            return 0
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_load_cache(self):
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            self.bot.log.info("Chargement du cache XP")
            query = ("SELECT `userID`,`xp` FROM `{}` WHERE `banned`=0".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            for l in liste:
                self.cache[l['userID']] = [round(time.time())-60,l['xp']]
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_get_top(self,top:int,guild:discord.Guild=None):
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT * FROM `{}` order by `xp` desc".format(self.table))
            cursor.execute(query)
            liste = list()
            if guild==None:
                liste = [x for x in cursor][:top]
            else:
                ids = [x.id for x in guild.members]
                i = 0
                l2 = [x for x in cursor]
                while len(liste)<top and i<len(l2):
                    if l2[i]['userID'] in ids:
                        liste.append(l2[i])
                    i += 1
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
        
    async def bdd_get_rank(self,userID:int,guild:discord.Guild=None):
        """Get the rank of a user"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;".format(self.table))
            cursor.execute(query)
            userdata = list()
            i = 0
            if guild!=None:
                users = [x.id for x in guild.members]
            for x in cursor:
                if (guild!=None and x['userID'] in users) or guild==None:
                    i += 1
                if x['userID']== userID:
                    x['rank'] = i
                    userdata = x
                    break
            cursor.close()
            return userdata
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_total_xp(self):
        """Get the total number of earned xp"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT SUM(xp) FROM `{}`".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return round(liste[0]['SUM(xp)'])
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


    async def get_raw_image(self,url,size=282):
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        im = Image.open(io.BytesIO(urlopen(req).read()))
        return im

    async def calc_pos(self,text,font,x,y,align='center'):
        w,h = font.getsize(text)
        if align=='center':
            return x-w/2,y-h/2
        elif align=='right':
            return x-w,y-h/2

    async def create_card(self,user,style,xp,rank=[1,0],txt=['NIVEAU','RANG'],force_static=False,levels_info=None):
        """Crée la carte d'xp pour un utilisateur"""
        card = Image.open("../cards/model/{}.png".format(style))
        bar_colors = await self.get_xp_bar_color(user.id)
        if levels_info==None:
            levels_info = await self.calc_level(xp)
        colors = {'name':(124, 197, 118),'xp':(124, 197, 118),'NIVEAU':(255, 224, 77),'rank':(105, 157, 206),'bar':bar_colors}
        if style=='blurple':
            colors = {'name':(35,35,50),'xp':(235, 235, 255),'NIVEAU':(245, 245, 255),'rank':(255, 255, 255),'bar':(70, 83, 138)}
        if not user.is_avatar_animated() or force_static:
            pfp = await self.get_raw_image(user.avatar_url_as(format='png',size=256))
            img = await self.add_overlay(pfp.resize(size=(282,282)),user,card,xp,rank,txt,colors,levels_info)
            img.save('../cards/global/{}-{}-{}.png'.format(user.id,xp,rank[0]))
            return discord.File('../cards/global/{}-{}-{}.png'.format(user.id,xp,rank[0]))
        else:
            pfp = await self.get_raw_image(user.avatar_url_as(format='gif'))
            images = []
            duration = []
            for i in range(pfp.n_frames):
                pfp.seek(i)
                img = await self.add_overlay(pfp.resize(size=(282,282)),user,card,xp,rank,txt,colors,levels_info)
                images.append(img)
                duration.append(pfp.info['duration']/1000)
            card.close()
            imageio.mimwrite('../cards/global/{}-{}-{}.gif'.format(user.id,xp,rank[0]), images, format="GIF-PIL", duration=duration, subrectangles=True)
            return discord.File('../cards/global/{}-{}-{}.gif'.format(user.id,xp,rank[0]))

    async def add_overlay(self,pfp,user,card,xp,rank,txt,colors,levels_info):
        img = Image.new('RGBA', (card.width, card.height), color = (250,250,250,0))
        img.paste(pfp, (20, 29))
        img.paste(card, (0, 0), card)
        if platform.system()=='Darwin':
            verdana_name = 'Verdana.ttf'
        else:
            verdana_name = 'Veranda.ttf'
        name_fnt = ImageFont.truetype('Roboto-Medium.ttf', 40)
        xp_fnt = ImageFont.truetype(verdana_name, 24)
        NIVEAU_fnt = ImageFont.truetype(verdana_name, 42)
        levels_fnt = ImageFont.truetype(verdana_name, 65)
        rank_fnt = ImageFont.truetype(verdana_name,29)
        RANK_fnt = ImageFont.truetype(verdana_name,23)
        
        img = await self.add_xp_bar(img,xp-levels_info[2],levels_info[1]-levels_info[2],colors['bar'])
        d = ImageDraw.Draw(img)
        d.text(await self.calc_pos(user.name,name_fnt,610,68), user.name, font=name_fnt, fill=colors['name'])
        temp = '{} / {} xp ({}/{})'.format(xp-levels_info[2],levels_info[1]-levels_info[2],xp,levels_info[1])
        d.text((await self.calc_pos(temp,xp_fnt,625,237)), temp, font=xp_fnt, fill=colors['xp'])
        d.text((380,140), txt[0], font=NIVEAU_fnt, fill=colors['NIVEAU'])
        d.text((await self.calc_pos(str(levels_info[0]),levels_fnt,740,160,'right')), str(levels_info[0]), font=levels_fnt, fill=colors['xp'])
        temp = '{x[0]}/{x[1]}'.format(x=rank)
        d.text((await self.calc_pos(txt[1],RANK_fnt,893,147,'center')), txt[1], font=RANK_fnt, fill=colors['rank'])
        d.text((await self.calc_pos(temp,rank_fnt,893,180,'center')), temp, font=rank_fnt, fill=colors['rank'])
        return img

    async def add_xp_bar(self,img,xp,needed_xp,colors):
        """Colorize the xp bar"""
        error_rate = 25
        data = np.array(img)   # "data" is a height x width x 4 numpy array
        red, green, blue, alpha = data.T # Temporarily unpack the bands for readability

        # Replace white with red... (leaves alpha values alone...)
        white_areas = (abs(red)-180<error_rate) & (abs(blue)-180<error_rate) & (abs(green)-180<error_rate)
        white_areas[:298] = False & False & False
        max_x = round(298 + (980-298)*xp/needed_xp)
        white_areas[max_x:] = False & False & False
        #white_areas[298:980] = True & True & True
        data[..., :-1][white_areas.T] = colors # Transpose back needed
        return Image.fromarray(data)

    async def get_xp_bar_color(self,userID:int):
        return (45,180,105)

    @commands.command(name='rank')
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1,15,commands.BucketType.user)
    async def rank(self,ctx,*,user:args.user=None):
        """Display a user XP.
        If you don't send any user, I'll display your own XP
        """
        try:
            if user==None:
                user = ctx.author
            need_mee6 = ctx.guild!=None and await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')==1
            if need_mee6:
                if ctx.guild.get_member(159985870458322944)==None:
                    return await ctx.send(str(await self.translate(ctx.guild.id,'xp','no-mee6')).format(ctx.prefix))
                user = ctx.guild.get_member(user.id)
                if user==None:
                    return await ctx.send(await self.translate(ctx.channel,'xp','not-member'))
                xp = await self.mee6_get_player(user)
            else:
                xp = await self.bdd_get_xp(user.id)
            if xp==None or (isinstance(xp,list) and len(xp)==0):
                if ctx.author==user:
                    return await ctx.send(await self.translate(ctx.channel,'xp','1-no-xp'))
                return await ctx.send(await self.translate(ctx.channel,'xp','2-no-xp'))
            if not need_mee6:
                levels_info = None
                xp = xp[0]['xp']
                ranks_nb = await self.bdd_get_nber()
                rank = (await self.bdd_get_rank(user.id))['rank']
            else:
                levels_info = [xp['level'],xp['detailed_xp'][1]-xp['detailed_xp'][0]+xp['detailed_xp'][2],xp['detailed_xp'][2]-xp['detailed_xp'][0]]
                xp = xp['xp']
                ranks_nb = ctx.guild.member_count
                rank = await self.mee6_get_rank(user)+1
            if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).attach_files:
                await self.send_card(ctx,user,xp,rank,ranks_nb,levels_info)
            elif ctx.channel.permissions_for(ctx.guild.me).embed_links:
                await self.send_embed(ctx,user,xp,rank,ranks_nb,levels_info)
            else:
                await self.send_txt(ctx,user,xp,rank,ranks_nb,levels_info)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)
    
    async def send_card(self,ctx,user,xp,rank,ranks_nb,levels_info=None):
        try:
            await ctx.send(file=discord.File('../cards/global/{}-{}-{}.{}'.format(user.id,xp,rank,'gif' if user.is_avatar_animated() else 'png')))
        except FileNotFoundError:
            style = await self.bot.cogs['UtilitiesCog'].get_xp_style(user)
            txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
            await ctx.send(file=await self.create_card(user,style,xp,[rank,ranks_nb],txts,levels_info=levels_info))
            self.bot.log.debug("XP card for user {} ({}xp - style {})".format(user.id,xp,style))
    
    async def send_embed(self,ctx,user,xp,rank,ranks_nb,levels_info):
        txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
        if levels_info==None:
            levels_info = await self.calc_level(xp)
        fields = list()
        fields.append({'name':'XP','value':"{}/{}".format(xp,levels_info[1]),'inline':True})
        fields.append({'name':txts[0],'value':levels_info[0],'inline':True})
        fields.append({'name':txts[1],'value':"{}/{}".format(rank,ranks_nb),'inline':True})
        emb = self.bot.cogs['EmbedCog'].Embed(fields=fields,color=self.embed_color).set_author(user)
        await ctx.send(embed=emb.discord_embed())
    
    async def send_txt(self,ctx,user,xp,rank,ranks_nb,levels_info):
        txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
        if levels_info==None:
            levels_info = await self.calc_level(xp)
        msg = """__**{}**__
**XP** {}/{}
**{}** {}
**{}** {}/{}""".format(user.name,xp,levels_info[1],txts[0],levels_info[0],txts[1],rank,ranks_nb)
        await ctx.send(msg)


    async def create_top_main(self,ranks,nbr,page,ctx):
        txt = list()
        i = (page-1)*nbr
        for u in ranks[:nbr]:
            i +=1
            user = self.bot.get_user(u['user'])
            if user==None:
                try:
                    user = await self.bot.fetch_user(u['user'])
                except discord.NotFound:
                    user = await self.translate(ctx.channel,'xp','del-user')
            if isinstance(user,discord.User):
                user_name = await self.bot.cogs['UtilitiesCog'].remove_markdown(user.name.replace('|',''))
                if len(user_name)>18:
                    user_name = user_name[:15]+'...'
            l = await self.calc_level(u['xp'])
            txt.append('{} • **{} |** `lvl {}` **|** `xp {}`'.format(i,"__"+user_name+"__" if user==ctx.author else user_name,l[0],u['xp']))
        return txt,i

    @commands.command(name='top')
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def top(self,ctx,page:typing.Optional[int]=1,Type:args.LeaderboardType='global'):
        """Get the list of the highest levels
        Each page has 20 users"""
        need_mee6 =  ctx.guild!=None and await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')==1
        if not need_mee6:
            if Type=='global':
                ranks = await self.bdd_get_top(20*page)
                max_page = ceil(len(self.cache)/20)
            elif Type=='guild':
                ranks = await self.bdd_get_top(10000,guild=ctx.guild)
                max_page = ceil(len(ranks)/20)
        else:
            if ctx.guild.get_member(159985870458322944)==None:
                return await ctx.send(str(await self.translate(ctx.guild.id,'xp','no-mee6')).format(ctx.prefix))
            ranks = await self.mee6_get_top(ctx.guild,20*page)
            max_page = ceil(len(ranks)/20)
        if page<1:
            return await ctx.send(await self.translate(ctx.channel,"xp",'low-page'))
        elif page>max_page:
            return await ctx.send(await self.translate(ctx.channel,"xp",'high-page'))
        ranks = ranks[(page-1)*20:]
        if need_mee6:
            ranks = [{'user':x['id'],'xp':x['xp']} for x in ranks]
        else:
            ranks = [{'user':x['userID'],'xp':x['xp']} for x in ranks]
        nbr = 20
        txt,i = await self.create_top_main(ranks,nbr,page,ctx)
        while len("\n".join(txt))>1000 and nbr>0:
            nbr -= 1
            txt,i = await self.create_top_main(ranks,nbr,page,ctx)
            await asyncio.sleep(0.2)
        f_name = str(await self.translate(ctx.channel,'xp','top-name')).format((page-1)*20+1,i,page,max_page)
        # author
        if need_mee6:
            lvl = await self.mee6_get_player(ctx.author)
            if lvl==None:
                your_rank = {'name':"__"+await self.translate(ctx.channel,"xp","top-your")+"__",'value':await self.translate(ctx.guild.id,"xp","1-no-xp")}
            else:
                your_rank = {'name':"__"+await self.translate(ctx.channel,"xp","top-your")+"__", 'value':"**#{} |** `lvl {}` **|** `xp {}`".format(await self.mee6_get_rank(ctx.author)+1,lvl['level'],lvl['xp'])}
        else:
            rank = await self.bdd_get_rank(ctx.author.id,ctx.guild if Type=='guild' else None)
            if len(rank)==0:
                your_rank = {'name':"__"+await self.translate(ctx.channel,"xp","top-your")+"__",'value':await self.translate(ctx.guild,"xp","1-no-xp")}
            else:
                lvl = await self.calc_level(rank['xp'])
                lvl = lvl[0]
                your_rank = {'name':"__"+await self.translate(ctx.channel,"xp","top-your")+"__", 'value':"**#{} |** `lvl {}` **|** `xp {}`".format(rank['rank'],lvl,rank['xp'])}
        # title
        if Type=='guild':
            t = await self.translate(ctx.channel,'xp','top-title-2')
        else:
            t = await self.translate(ctx.channel,'xp','top-title-1')
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            emb = self.bot.cogs['EmbedCog'].Embed(title=t,fields=[{'name':f_name,'value':"\n".join(txt)},your_rank],color=self.embed_color,author_icon=self.bot.user.avatar_url_as(format='png')).create_footer(ctx.author)
            await ctx.send(embed=emb.discord_embed())
        else:
            await ctx.send(f_name+"\n\n"+'\n'.join(txt))


    async def clear_cards(self,all=False):
        """Delete outdated rank cards"""
        files =  os.listdir('../cards/global')
        done = list()
        for f in sorted([f.split('-')+['../cards/global/'+f] for f in files],key=operator.itemgetter(1),reverse=True):
            if f[0] in done:
                os.remove(f[3])
            else:
                done.append(f[0])



    async def gen_rr_id(self):
        return round(time.time()/2)

    async def rr_add_role(self,guild:int,role:int,level:int):
        """Add a role reward in the database"""
        cnx = self.bot.cnx
        cursor = cnx.cursor(dictionary = True)
        ID = await self.gen_rr_id()
        query = ("INSERT INTO `roles_rewards` (`ID`,`guild`,`role`,`level`) VALUES ('{i}','{g}','{r}','{l}');".format(i=ID,g=guild,r=role,l=level))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True
    
    async def rr_list_role(self,guild:int,level:int=-1):
        """List role rewards in the database"""
        cnx = self.bot.cnx
        cursor = cnx.cursor(dictionary = True)
        query = ("SELECT * FROM `roles_rewards` WHERE guild={g} ORDER BY level;".format(g=guild)) if level<0 else ("SELECT * FROM `roles_rewards` WHERE guild={g} AND level={l} ORDER BY level;".format(g=guild,l=level))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste
    
    async def rr_remove_role(self,ID:int):
        """Remove a role reward from the database"""
        cnx = self.bot.cnx
        cursor = cnx.cursor(dictionary = True)
        query = ("DELETE FROM `roles_rewards` WHERE `ID`={};".format(ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    @commands.group(name="roles_rewards",aliases=['rr'])
    @commands.guild_only()
    async def rr_main(self,ctx):
        """Manage your roles rewards like a boss"""
        pass
    
    @rr_main.command(name="add")
    @commands.check(checks.can_manage_server)
    async def rr_add(self,ctx,level:int,*,role:discord.Role):
        """Add a role reward
        This role will be given to every member who reaches the level"""
        try:
            l = await self.rr_list_role(ctx.guild.id)
            if len([x for x in l if x['level']==level])>0:
                return await ctx.send(await self.translate(ctx.guild.id,'xp','already-1-rr'))
            max_rr = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'rr_max_number')
            max_rr = self.bot.cogs["ServerCog"].default_opt['rr_max_number'] if max_rr==None else max_rr
            if len(l) >= max_rr:
                return await ctx.send(str(await self.translate(ctx.guild.id,'xp','too-many-rr')).format(len(l)))
            await self.rr_add_role(ctx.guild.id,role.id,level)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            await ctx.send(str(await self.translate(ctx.guild.id,'xp','rr-added')).format(role.name,level))
    
    @rr_main.command(name="list")
    @commands.check(checks.can_manage_server)
    async def rr_list(self,ctx):
        """List every roles rewards of your server"""
        try:
            l = await self.rr_list_role(ctx.guild.id)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            des = '\n'.join(["• <@&{}> : lvl {}".format(x['role'], x['level']) for x in l])
            max_rr = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'rr_max_number')
            max_rr = self.bot.cogs["ServerCog"].default_opt['rr_max_number'] if max_rr==None else max_rr
            title = str(await self.translate(ctx.guild.id,"xp",'rr_list')).format(len(l),max_rr)
            emb = self.bot.cogs['EmbedCog'].Embed(title=title,desc=des).update_timestamp().create_footer(ctx.author)
            await ctx.send(embed=emb.discord_embed())
    
    @rr_main.command(name="remove")
    @commands.check(checks.can_manage_server)
    async def rr_remove(self,ctx,level:int):
        """Remove a role reward
        When a member reaches this level, no role will be given anymore"""
        try:
            l = await self.rr_list_role(ctx.guild.id,level)
            if len(l)==0:
                return await ctx.send(await self.translate(ctx.guild.id,'xp','no-rr'))
            await self.rr_remove_role(l[0]['ID'])
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            await ctx.send(str(await self.translate(ctx.guild.id,'xp','rr-removed')).format(level))
    
    @rr_main.command(name="reload")
    @commands.check(checks.can_manage_server)
    @commands.cooldown(1,300,commands.BucketType.guild)
    async def rr_reload(self,ctx):
        """Refresh roles rewards for the whole server"""
        try:
            if not ctx.guild.me.guild_permissions.manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,'modo','cant-mute'))
            c = 0
            rr_list = await self.rr_list_role(ctx.guild.id)
            if await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')==1:
                if ctx.guild.get_member(159985870458322944)==None:
                    return await ctx.send(str(await self.translate(ctx.guild.id,'xp','no-mee6')).format(ctx.prefix))
                xps = [{'user':int(x['id']),'xp':x['xp'],'level':x['level']} for x in await self.mee6_get_top(ctx.guild,nb=1000000)]
            else:
                xps = [{'user':x['userID'],'xp':x['xp'],'level':(await self.calc_level(x['xp']))[0]} for x in await self.bdd_get_top(ctx.guild.member_count,ctx.guild)]
            for member in xps:
                m = ctx.guild.get_member(member['user'])
                if m!=None:
                    c += await self.give_rr(m,member['level'],rr_list,remove=True)
            await ctx.send(str(await self.translate(ctx.guild.id,'xp','rr-reload')).format(c,ctx.guild.member_count))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
    

    async def mee6_reload_rr(self,guild):
        """Reloads every role rewards from a guild using MEE6 xp"""
        if await self.bot.cogs['ServerCog'].find_staff(guild.id,'xp_type')!=1 or guild.get_member(159985870458322944)==None:
            return -1
        c = [0,0]
        xps = [{'user':x['id'],'xp':x['xp'],'level':x['level']} for x in await self.mee6_get_top(guild,nb=1000000)]
        rr_list = await self.rr_list_role(guild.id)
        for member in xps:
            m = guild.get_member(int(member['user']))
            if m==None:
                continue
            temp = await self.give_rr(m,member['level'],rr_list,remove=True)
            c[1] += temp
            if temp>0:
                c[0] += 1
        return c

    async def mee6_get_top(self,guild:discord.Guild,nb:int=1000):
        """Get the leaderboard of a guild using MEE6 levels plugin"""
        if guild.get_member(159985870458322944)==None:
            raise Exception
        nb = min(guild.member_count,nb)
        async with aiohttp.ClientSession() as session:
            i = 0
            result = list()
            while i<=ceil(nb/100):
                async with session.get(f'https://mee6.xyz/api/plugins/levels/leaderboard/{guild.id}?page={i}') as resp:
                    try:
                        result += (await resp.json())['players']
                    except Exception as e:
                        await self.bot.cogs['ErrorsCog'].senf_err_msg(f"Error on `mee6_get_top`: url https://mee6.xyz/api/plugins/levels/leaderboard/{guild.id}?page={i}")
                        raise e
                i += 1
        return result[:nb]

    async def mee6_get_player(self,user:discord.Member):
        """Get the xp of a player using MEE6 levels plugin"""
        if user.guild.get_member(159985870458322944)==None:
            raise Exception
        async with aiohttp.ClientSession() as session:
            i = 0
            js = {'players':[]}
            while len([x for x in js['players'] if x['id']==str(user.id)])==0 and i<=ceil(user.guild.member_count/100):
                async with session.get(f'https://mee6.xyz/api/plugins/levels/leaderboard/{user.guild.id}?page={i}') as resp:
                    js = await resp.json()
                i += 1
        try:
            return [x for x in js['players'] if x['id']==str(user.id)][0]
        except IndexError:
            return None
    
    async def mee6_get_rank(self,user:discord.Member):
        """Get the rank of a player in a guild"""
        if user.guild.get_member(159985870458322944)==None:
            raise Exception
        async with aiohttp.ClientSession() as session:
            i = 0
            pos = 0
            while i<=ceil(user.guild.member_count/100):
                async with session.get(f'https://mee6.xyz/api/plugins/levels/leaderboard/{user.guild.id}?page={i}') as resp:
                    l = [x['id'] for x in (await resp.json())['players']]
                    if str(user.id) in l:
                        return pos+l.index(str(user.id))
                i += 1
                pos += 100
        return user.guild.member_count


def setup(bot):
    bot.add_cog(XPCog(bot))