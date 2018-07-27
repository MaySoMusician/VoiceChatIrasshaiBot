import discord
import queue
import settings
import asyncio
import traceback
import re
import sqlite_manager
import api_manager
import debug

count = 0
client = discord.Client()
q = queue.Queue()
api_manager = api_manager.api_manager()
sqlite_manager = sqlite_manager.sqlite_manager(api_manager)

settings.reload_setting()


async def run_queue():
    global q
    global voice
    debug.log("start_queue")
    while True:
        while q.empty():
            await asyncio.sleep(1)
        item = q.get()
        try:
            await hello(item[0], item[1])
        except Exception as e:
            debug.log('error:type {0} args:{1} error:{2}'.format(type(e), e.args, str(e)))
            pass


async def hello(id, channel):
    global client
    name = (await client.get_user_info(id)).display_name
    if sqlite_manager.has_xml(id):
        xml = sqlite_manager.get_xml(id)
    else:
        data = sqlite_manager.get_row(id)
        voice = data[1]
        pitch = data[2]
        range = data[3]
        rate = data[4]
        volume = data[5]
        text = data[6].format(name)
        xml = api_manager.to_xml(voice, pitch, range, rate, volume, text)
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
    if connecting is None:
        debug.log('join vc {0}:{1}'.format(channel.name,channel.id))
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
    debug.log('name:{0} id:{1}'.format(client.user.name,client.user.id))


@client.event
async def on_voice_state_update(before, after):
    if not is_join_vc(before, after):
        return
    if after.server.id == settings.xpc_jp:
        debug.log("join {0}:{1} in {2}:{3}".format(after.name, after.id, after.voice.voice_channel.name,after.voice.voice_channel.id))
        global q
        item = (after.id, after.voice.voice_channel)
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


def AllowChannel (channel):
    if channel.is_private:
        return True
    if not(channel.server.id in settings.ignore_server):
        return True
    return False

def execute_command(message):
    success = False
    message_text = message.content
    if message_text.startswith('./satoshi'):
        id = message.author.id
        set_voice_r = re.search(r'^./satoshi setvoice (?P<name>.*)$', message_text)
        if set_voice_r:
            name = set_voice_r.group('name')
            if name in ['nozomi', 'seiji', 'akari', 'anzu', 'hiroshi', 'kaho', 'koutarou', 'maki', 'nanako', 'osamu',
                        'sumire']:
                success = sqlite_manager.set_voice(id, name)
        set_prosody_r = re.search(
            r'^./satoshi set(?P<var>(pitch|range|rate|volume)) (?P<param>([0-9](\.[0-9]{1,2})?))$', message_text)
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
        set_text_r = re.search(r'^./satoshi settext (?P<text>(\w|\W)*)$', message_text)
        if set_text_r:
            text = set_text_r.group('text')
            if len(text) < 256:
                success = sqlite_manager.set_text(id, text)
        reset_r = re.match(r'./satoshi reset', message_text)
        if reset_r:
            success = sqlite_manager.reset(id)
        set_xml_r = re.search(r'^./satoshi setxml (?P<xml>(\w|\W)*)$', message_text)
        if set_xml_r:
            success = sqlite_manager.set_xml(id, set_xml_r.group('xml'))
    return success

@client.event
async def on_message(message):
    if message.channel.is_private:
       success =  execute_command()
       if success:
           debug.log('receive_command {0}'.format(message.content))
           await client.add_reaction(message, '✅')
    if message.channel.server.id == settings.xpc_jp:
        execute_command()
        if success:
            debug.log('receive_command {0}'.format(message.content))
            await client.add_reaction(message, '✅')




loop = asyncio.get_event_loop()
asyncio.ensure_future(run_queue())
asyncio.ensure_future(client.run(settings.discord_token))
loop.run_forever()
