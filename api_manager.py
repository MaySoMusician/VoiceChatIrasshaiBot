import requests
import settings
import subprocess
import debug

class api_manager:
    def request(self, xml):
        endpoint = 'https://api.apigw.smt.docomo.ne.jp/aiTalk/v1/textToSpeech?APIKEY={0}'
        api_key = settings.api_key
        url = endpoint.format(api_key)
        data = xml.encode('utf-8')
        headers = {"Content-Type": "application/ssml+xml", "Accept": "audio/L16", "Content-Length": str(len(data))}
        return requests.post(url, data=data, headers=headers)

    def download(self, xml):
        debug.log("downloading")
        response = self.request(xml)
        fp = open('rawfile.raw', 'wb')
        fp.write(response.content)
        fp.close()
        cmd = 'sox -t raw -r 16k -e signed -b 16 -B -c 1  rawfile.raw wavfile.wav'
        subprocess.check_output(cmd, shell=True)

    def is_xml(self, xml):
        response = self.request(xml)
        if response.content != b'':
            debug.log('is_xml')
            return True
        else:
            debug.log('not_xml')
            return False

    def to_xml(self, voice, pitch, range, rate, volume, text):
        return '<?xml version="1.0" encoding="utf-8" ?>' \
               '<speak version="1.1">' \
               '<voice name="{0}">' \
               '<prosody pitch="{1}" range="{2}" rate="{3}" volume="{4}">{5}</prosody>' \
               '</voice>' \
               '</speak>'.format(voice, pitch, range, rate, volume, text)
