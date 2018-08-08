import discord
import queue
import settings
import asyncio
import re
import sqlite_manager
import api_manager
import debug

client = discord.Client()
q = queue.Queue()
api_manager = api_manager.api_manager()
sqlite_manager = sqlite_manager.sqlite_manager(api_manager, client)

settings.reload_setting()


async def run_queue():
    global q
    debug.log("start_queue")
    while True:
        count = 0
        while q.empty():
            await asyncio.sleep(1)
            count += 1
            if count > 3600:
                if connecting_vc():
                    debug.log("connecting_vc")
                    await disconnect_vc()
        item = q.get()
        try:
            await hello(item[0], item[1])
        except Exception as e:
            debug.log('error:type {0} args:{1} error:{2}'.format(type(e), e.args, str(e)))
            raise (e)


def connecting_vc():
    global client
    xpc_jp = client.get_server(settings.xpc_jp)
    return client.is_voice_connected(xpc_jp)


async def disconnect_vc():
    global client
    xpc_jp = client.get_server(settings.xpc_jp)
    voice = client.voice_client_in(xpc_jp)
    debug.log('disconnect {0}'.format(voice.channel.name))
    await voice.disconnect()


async def hello(xml, channel):
    global client
    api_manager.download(xml)
    voice = await join_vc(channel)
    debug.log("load wav")
    player = voice.create_ffmpeg_player('data/wavfile.wav')
    debug.log("start")
    player.start()
    while not player.is_done():
        await asyncio.sleep(0.01)
    debug.log("end")


async def join_vc(channel):
    global client
    connecting = client.voice_client_in(channel.server)
    if not client.is_voice_connected(channel.server):
        debug.log('join vc {0}:{1}'.format(channel.name, channel.id))
        return await client.join_voice_channel(channel)
    else:
        if connecting.channel.id == channel.id:
            return connecting
        else:
            await connecting.disconnect()
            debug.log('join vc {0}:{1}'.format(channel.name, channel.id))
            return await client.join_voice_channel(channel)


@client.event
async def on_ready():
    debug.log('Logged in as')
    debug.log('name:{0} id:{1}'.format(client.user.name, client.user.id))


@client.event
async def on_voice_state_update(before, after):
    if not is_join_vc(before, after):
        return
    if after.server.id == settings.xpc_jp:
        debug.log("join {0}:{1} in {2}:{3}".format(after.name, after.id, after.voice.voice_channel.name,
                                                   after.voice.voice_channel.id))
        global q
        global sqlite_manager
        if sqlite_manager.has_xml(after.id):
            item = (sqlite_manager.get_xml(after.id), after.voice.voice_channel)
        else:
            row = sqlite_manager.get_row(after.id)
            voice = row[1]
            pitch = row[2]
            range = row[3]
            rate = row[4]
            volume = row[5]
            text = row[6].format(after.name)
            xml = api_manager.to_xml(voice, pitch, range, rate, volume, text)
            item = (xml, after.voice.voice_channel)
        q.put(item)


def is_join_vc(before, after):
    global client
    if after.id == client.user.id:
        return False
    if before.voice.voice_channel == after.voice.voice_channel:
        return False
    if after.voice.voice_channel is None:
        return False
    if after.voice.voice_channel.id in settings.ignore_vc:
        return False
    return True


def AllowChannel(channel):
    if channel.is_private:
        return True
    if not (channel.server.id in settings.ignore_server):
        return True
    return False


async def execute_command(message):
    success = False
    message_text = message.content
    id = message.author.id
    set_voice_r = re.search(r'^\./satoshi setvoice (?P<name>.*)$', message_text)
    if set_voice_r:
        name = set_voice_r.group('name')
        if name in ['nozomi', 'seiji', 'akari', 'anzu', 'hiroshi', 'kaho', 'koutarou', 'maki', 'nanako', 'osamu',
                    'sumire']:
            success = sqlite_manager.set_voice(id, name)
    set_prosody_r = re.search(
        r'^\./satoshi set(?P<var>(pitch|range|rate|volume)) (?P<param>([0-9](\.[0-9]{1,2})?))$', message_text)
    if set_prosody_r:
        var = set_prosody_r.group('var')
        param = float(set_prosody_r.group('param'))
        if var == 'pitch' and 0.50 <= param and param <= 2.00:
            success = sqlite_manager.set_pitch(id, param)
        if var == 'range' and 0.00 <= param and param <= 2.00:
            success = sqlite_manager.set_range(id, param)
        if var == 'rate' and 0.50 <= param and param <= 4.00:
            success = sqlite_manager.set_rate(id, param)
        if var == 'volume' and 0.00 <= param and param <= 2.00:
            success = sqlite_manager.set_volume(id, param)
    set_text_r = re.search(r'^\./satoshi settext (?P<text>(\w|\W)*)$', message_text)
    if set_text_r:
        text = set_text_r.group('text')
        if len(text) < 256:
            success = sqlite_manager.set_text(id, text)
    reset_r = re.match(r'\./satoshi reset', message_text)
    if reset_r:
        success = sqlite_manager.reset(id)
    set_xml_r = re.search(r'^\./satoshi setxml (?P<xml>(\w|\W)*)$', message_text)
    if set_xml_r:
        success = sqlite_manager.set_xml(id, set_xml_r.group('xml'))
    say_r = re.search(r'^\./satoshi say (?P<text>(\w|\W)*)$', message_text)
    if say_r:
        success = say(message.author.id, message.channel, say_r.group('text'))
    get_value_r = re.match(r'^\./satoshi getvcsetting$', message_text)
    if get_value_r:
        success = await get_value(message.author, message.channel)
    return success


async def get_value(user, channel):
    debug.log('load {0}\'s setting'.format(user.name))
    global sqlite_manager
    if sqlite_manager.has_xml(user.id):
        message = '現在の{0}さんの設定です\n' \
                  '```asciidoc\n' \
                  '{1}' \
                  '```/satoshi getvcsetting'.format(user.mention, sqlite_manager.get_xml(user.id))
    else:
        row = sqlite_manager.get_row(user.id)
        voice = row[1]
        pitch = row[2]
        range = row[3]
        rate = row[4]
        volume = row[5]
        text = row[6]
        message = '現在の{0}さんの設定です\n' \
                  '```asciidoc\n' \
                  'voice:: {1}\n' \
                  'pitch:: {2}\n' \
                  'range:: {3}\n' \
                  'rate:: {4}\n' \
                  'volume:: {5}\n' \
                  'text:: {6}\n' \
                  '```'.format(user.mention, voice, pitch, range, rate, volume, text)
    global client
    await client.send_message(channel, message)
    return True


def say(user_id, channel, text):
    if channel.id not in settings.freetalk_text_vc:
        return False
    global sqlite_manager
    global api_manager
    global client
    if sqlite_manager.has_value(user_id):
        row = sqlite_manager.get_row(user_id)
        voice = row[1]
        pitch = row[2]
        range = row[3]
        rate = row[4]
        volume = row[5]
    else:
        voice = 'sumire'
        voice = 1
        pitch = 1
        range = 1
        rate = 1
        volume = 1
    xml = api_manager.to_xml(voice, pitch, range, rate, volume, text)

    vc_id = settings.freetalk_text_vc[channel.id]
    vc = client.get_channel(vc_id)
    item = (xml, vc)
    global q
    q.put(item)
    return True


@client.event
async def on_message(message):
    if message.channel.is_private:
        # for directmessage
        if message.content.startswith('./satoshi'):
            success = await execute_command(message)
            if success:
                debug.log('receive_command {0} name:{1}'.format(message.content, message.author.name))
                await client.add_reaction(message, '✅')
        return

    if message.channel.server.id == settings.xpc_jp:
        # for xpc-jp
        if message.content.startswith('./satoshi'):
            success = await execute_command(message)
            if success:
                debug.log('receive_command {0} name:{1}'.format(message.content, message.author.name))
                await client.add_reaction(message, '✅')
        return


loop = asyncio.get_event_loop()
asyncio.ensure_future(run_queue())
asyncio.ensure_future(client.run(settings.discord_token))
loop.run_forever()
