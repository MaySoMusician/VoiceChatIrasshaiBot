import json
import debug

def reload_setting():
    global api_key
    global discord_token
    global ignore_vc
    global xpc_jp
    debug.log("load setting")
    setting = open('data/setting.json','r')
    json_dict = json.load(setting)
    api_key = json_dict["api_key"]
    discord_token = json_dict["discord_token"]
    ignore_vc = json_dict["ignore_vc"]
    xpc_jp = json_dict["xpc_jp"]