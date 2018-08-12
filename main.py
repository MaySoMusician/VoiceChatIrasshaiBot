import discord
import queue
import settings
import asyncio
import re
import sqlite_manager
import api_manager
import debug


class Program(discord.Client):
    def __init__(self):
        super().__init__()
        self.api_manager = api_manager.api_manager()
        self.sqlite_manager = sqlite_manager.sqlite_manager(api_manager, self)
        self.queue = queue.Queue()

    def run(self, token):
        self.loop.create_task(self.run_queue())
        super().run(token)

    async def run_queue(self):
        debug.log('start run queue')

        while True:
            count = 0
            if self.queue.empty():
                await asyncio.sleep(1)
                count += 1
                if count > 5:
                    if self.is_voice_connected(self.xpc_jp):
                        voice = self.voice_client_in(self.xpc_jp)
                        await voice.disconnect()
            else:
                item = self.queue.get()
                try:
                    await self.speak(item[0], item[1])
                except Exception as e:
                    debug.log(e)

    async def speak(self, xml, channel):
        self.api_manager.download(xml)
        if self.is_voice_connected(self.xpc_jp):
            voice_client = self.voice_client_in(self.xpc_jp)
            if voice_client.channel.id != channel.id:
                await voice_client.disconnect()
                voice_client = await self.join_voice_channel(channel)
        else:
            voice_client = await self.join_voice_channel(channel)
        player = voice_client.create_ffmpeg_player('data/wavfile.wav')
        player.start()
        while not player.is_done():
            await asyncio.sleep(1)

    @asyncio.coroutine
    def on_message(self, message):
        if message.channel.is_private:
            if message.content.startswith('./satoshi'):
                yield from self.execute_command(message)
            return

        if message.channel.server.id == settings.xpc_jp:
            if message.content.startswith('./satoshi'):
                yield from self.execute_command(message)
            return

    def set_voice(self, user_id, voice):
        self.sqlite_manager.set_voice(user_id, voice)
        return True

    def set_pitch(self, user_id, param):
        if 0.50 <= param and param <= 2.00:
            self.sqlite_manager.set_pitch(user_id, param)
            return True
        else:
            return False

    def set_range(self, user_id, param):
        if 0.00 <= param and param <= 2.00:
            self.sqlite_manager.set_range(user_id, param)
            return True
        else:
            return False

    def set_rate(self, user_id, param):
        if 0.50 <= param and param <= 4.00:
            self.sqlite_manager.set_rate(user_id, param)
            return True
        else:
            return False

    def set_volume(self, user_id, param):
        if 0.00 <= param and param <= 2.00:
            self.sqlite_manager.set_volume(user_id, param)
            return True
        else:
            return False

    def set_text(self, user_id, text):
        if len(text) < 256:
            self.sqlite_manager.set_text(user_id, text)
            return True
        else:
            return False

    def reset(self, user_id):
        self.sqlite_manager.reset(user_id)
        return True

    def set_xml(self, user_id, xml):
        if len(xml) < 512:
            self.sqlite_manager.set_xml(user_id, xml)
            return True
        else:
            return False

    def say(self, user_id, text, channel):
        if len(text) >= 255:
            return False
        if channel.id not in settings.freetalk_text_vc:
            return False
        if self.sqlite_manager.has_value(user_id):
            row = self.sqlite_manager.get_row(user_id)
            voice = row[1]
            pitch = row[2]
            range = row[3]
            rate = row[4]
            volume = row[5]
        else:
            voice = 'sumire'
            pitch = 1
            range = 1
            rate = 1
            volume = 1
        xml = self.api_manager.to_xml(voice, pitch, range, rate, volume, text)
        vc_id = settings.freetalk_text_vc[channel.id]
        vc = self.get_channel(vc_id)
        item = (xml, vc)
        self.queue.put(item)
        return True

    def get_vc_setting(self, user, channel):
        if self.sqlite_manager.has_xml(user.id):
            message = '現在の{0}さんの設定です\n' \
                      '```asciidoc\n' \
                      '{1}' \
                      '```/satoshi getvcsetting'.format(user.mention, sqlite_manager.get_xml(user.id))
        else:
            row = self.sqlite_manager.get_row(user.id)
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
        yield from self.send_message(channel, message)
        return True

    def execute_command(self, message):
        success = False
        message_text = message.content
        user_id = message.author.id

        set_voice_r = re.search(
            r'^\./satoshi +setvoice +(?P<name>(nozomi|seiji|akari|anzu|hiroshi|kaho|koutarou|maki|nanako|osamu|sumire))$',
            message_text)
        if set_voice_r:
            voice = set_voice_r.group('name')
            success = self.set_voice(user_id, voice)

        set_prosody_r = re.search(
            r'^\./satoshi +set(?P<var>(pitch|range|rate|volume)) +(?P<param>([0-9](\.[0-9]{1,2})?))$', message_text)
        if set_prosody_r:
            var = set_prosody_r.group('var')
            param = float(set_prosody_r.group('param'))
            if var == 'pitch':
                success = self.set_pitch(user_id, param)
            elif var == 'range':
                success = self.set_range(user_id, param)
            elif var == 'rate':
                success = self.set_rate(user_id, param)
            elif var == 'volume':
                success = self.set_volume(user_id, param)

        set_text_r = re.search(r'^\./satoshi *settext (?P<text>(\w|\W)*)$', message_text)
        if set_text_r:
            text = set_text_r.group('text')
            success = self.set_text(user_id, text)

        reset_r = re.match(r'^\./satoshi reset$', message_text)
        if reset_r:
            success = self.reset(user_id)

        set_xml_r = re.search(r'^\./satoshi setxml (?P<xml>(\w|\W)*)$', message_text)
        if set_text_r:
            success = self.set_xml(user_id, set_xml_r.group('xml'))

        say_r = re.search(r'^\./satoshi say (?P<text>(\w|\W)*)$', message_text)
        if say_r:
            success = self.say(user_id, say_r.group('text'), message.channel)

        get_value_r = re.match(r'^\./satoshi getvcsetting$', message_text)
        if get_value_r:
            success = self.get_vc_setting(message.author, message.channel)

        if success:
            yield from self.add_reaction(message, '✅')

    @asyncio.coroutine
    def on_voice_state_update(self, before, after):
        if not self.is_join_vc(before, after):
            return
        if after.server.id == settings.xpc_jp:
            debug.log("join {0}:{1} in {2}:{3}".format(after.name, after.id, after.voice.voice_channel.name,
                                                       after.voice.voice_channel.id))
            if self.sqlite_manager.has_xml(after.id):
                item = (self.sqlite_manager.get_xml(after.id), after.voice.voice_channel)
            else:
                row = self.sqlite_manager.get_row(after.id)
                voice = row[1]
                pitch = row[2]
                range = row[3]
                rate = row[4]
                volume = row[5]
                text = row[6].format(after.name)
                xml = self.api_manager.to_xml(voice, pitch, range, rate, volume, text)
                item = (xml, after.voice.voice_channel)
            self.queue.put(item)

    def is_join_vc(self, before, after):
        if after.id == self.user.id:
            return False
        if before.voice.voice_channel == after.voice.voice_channel:
            return False
        if after.voice.voice_channel is None:
            return False
        if after.voice.voice_channel.id in settings.ignore_vc:
            return False
        return True

    @asyncio.coroutine
    def on_ready(self):
        debug.log('ready')
        debug.log('name:{0} id:{1}'.format(self.user.name, self.user.id))
        self.xpc_jp = self.get_server(settings.xpc_jp)


settings.reload_setting()
program = Program()
program.run(settings.discord_token)
