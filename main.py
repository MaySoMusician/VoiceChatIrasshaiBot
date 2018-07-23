import os
import subprocess
import requests
import discord
import queue
import settings
import asyncio

count = 0
client = discord.Client()
q = queue.Queue()


def say(text, rate=1.0, pitch=1.0, volume=1.0):
    return '<?xml version="1.0" encoding="utf-8" ?>' \
           '<speak version="1.1">' \
           '<voice name="sumire">' \
           '<prosody rate="{0}" pitch="{1}" volume="{2}">{3}</prosody>' \
           '</voice>' \
           '</speak>'.format(rate, pitch, volume, text)


def download(text, count):
    endpoint = 'https://api.apigw.smt.docomo.ne.jp/aiTalk/v1/textToSpeech?APIKEY={0}'
    api_key = settings.api_key
    url = endpoint.format(api_key)
    xml = say(text, rate=1.4, pitch=1.1).encode('utf-8')
    headers = {"Content-Type": "application/ssml+xml", "Accept": "audio/L16", "Content-Length": str(len(xml))}
    response = requests.post(url, data=xml, headers=headers)
    fp = open('{0}.raw'.format(count), 'wb')
    fp.write(response.content)
    fp.close()
    cmd = 'sox -t raw -r 16k -e signed -b 16 -B -c 1  {0}.raw {0}.wav'.format(count)
    subprocess.check_output(cmd, shell=True)


async def run_queue():
    global q
    global voice
    print("start_queue")
    while True:
        while q.empty():
            await asyncio.sleep(1)
        item = q.get()
        await hello(item[0], item[1])
        #if q.empty():
            #await voice.disconnect()


async def hello(name, channel):
    global client
    global count
    download("{0}さんいらっしゃい".format(name), count)
    await join_vc(channel)
    global voice
    player = voice.create_ffmpeg_player('{0}.wav'.format(count))
    player.start()
    while not player.is_done():
        await asyncio.sleep(0.01)
    os.remove('{0}.wav'.format(count))
    os.remove('{0}.raw'.format(count))
    count += 1


async def join_vc(channel):
    global client
    global voice
    connecting = client.voice_client_in(channel.server)
    if connecting is None:
        voice = await client.join_voice_channel(channel)
    else:
        if connecting.channel.id is channel.id:
            voice = client.voice_client_in(channel.server)
        else:
            voice = connecting
            await voice.disconnect()
            voice = await client.join_voice_channel(channel)



@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.event
async def on_voice_state_update(before, after):
    if after.id == client.user.id:
        return
    if before.voice.voice_channel == after.voice.voice_channel:
        return
    if after.voice.voice_channel is None:
        return
    name = after.name if after.nick is None else after.nick
    print("join {0}:{1} in {2}:{3}".format(name, after.id, after.voice.voice_channel.name,
                                           after.voice.voice_channel.id))
    global q
    item = (name, after.voice.voice_channel)
    q.put(item)


loop = asyncio.get_event_loop()
asyncio.ensure_future(run_queue())
asyncio.ensure_future(client.run(settings.discord_token))
loop.run_forever()
