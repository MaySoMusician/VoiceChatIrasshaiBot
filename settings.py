import json
import debug

def reload_setting():
    global api_key
    global discord_token
    global ignore_vc
    global xpc_jp
    global freetalk_text_vc
    debug.log("load setting")
    with open('data/setting.json','r') as setting:
        json_dict = json.load(setting)
        api_key = json_dict["api_key"]
        discord_token = json_dict["discord_token"]
        ignore_vc = json_dict["ignore_vc"]
        xpc_jp = json_dict["xpc_jp"]
        freetalk_text_vc = json_dict["text_vc"]
