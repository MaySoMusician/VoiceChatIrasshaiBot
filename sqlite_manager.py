import sqlite3
import debug
import settings

class sqlite_manager:

    def __init__(self, api_manager, client):
        self.dbname = "data/voiceroid.db"
        self.connection = sqlite3.connect(self.dbname)
        self.create_table()
        self.api_manager = api_manager
        self.discord_client = client

    def create_table(self):
        cursor = self.connection.cursor()
        debug.log('create voice')
        cursor.execute(
            'create table if not exists voice (id tinytext, voice tinytext default "sumire", pitch decimal default 1.0, range decimal default 1.0, rate decimal default 1.0, volume decimal default 1.0, txt text)')
        cursor.execute('create table if not exists xml (id tinytext, xml text)')
        debug.log('create xml')
        self.connection.commit()

    def set_xml(self, id, xml):
        if self.api_manager.is_xml(xml):
            debug.log("set xml {0}".format(id))
            self.delete_voice(id)
            c = self.connection.cursor()
            if self.has_xml(id):
                c.execute('update xml set xml=? where id=?', (xml, id))
                debug.log('update xml')
            else:
                c.execute('insert into xml (id, xml) values (?, ?)', (id, xml))
                debug.log('insert xml')
            self.connection.commit()

    def get_xml(self, id):
        c = self.connection.cursor()
        c.execute('select xml from xml where id=?', (id,))
        result = c.fetchmany(1)[0][0]
        return result

    def set_voice(self, id, param):
        self.set_value(id, 'voice', param)

    def set_rate(self, id, param):
        self.set_value(id, 'rate', param)

    def set_range(self, id, param):
        self.set_value(id, 'range', param)

    def set_pitch(self, id, param):
        self.set_value(id, 'pitch', param)

    def set_volume(self, id, param):
        self.set_value(id, 'volume', param)

    def set_text(self, id, param):
        self.set_value(id, 'txt', param)

    def reset(self, id):
        debug.log("reset db {0}".format(id))
        self.delete_voice(id)
        self.delete_xml(id)
        self.set_default(id)

    def delete_voice(self, id):
        debug.log("delete voice {0}".format(id))
        c = self.connection.cursor()
        c.execute('delete from voice where id=?', (id,))
        self.connection.commit()

    def delete_xml(self, id):
        debug.log("delete xml {0}".format(id))
        c = self.connection.cursor()
        c.execute('delete from xml where id=?', (id,))
        self.connection.commit()

    def set_value(self, id, column_name, value):
        debug.log("set {0} id:{1} value:{2}".format(column_name,id,value))
        self.delete_xml(id)
        c = self.connection.cursor()
        if self.has_value(id):
            c.execute('update voice set {0}=? where id=?'.format(column_name), (value, id))
        else:
            c.execute('insert into voice (id, {0}) values (?, ?)'.format(column_name), (id, value))
        self.connection.commit()

    def set_default(self, id):
        xpc_jp = self.discord_client.get_server(settings.xpc_jp)
        user = xpc_jp.get_member(id)
        self.set_text(id, '{0}さんいらっしゃい'.format(user.name))


    def get_row(self, id):
        if not self.has_value(id):
            debug.log('{0} doesn\'t have value'.format(id))
            self.set_default(id)


        c = self.connection.cursor()
        c.execute('select * from voice where id=?', (id,))
        row = c.fetchmany(1)[0]
        debug.log('{0} has value'.format(id))
        return row


    def has_value(self, id):
        c = self.connection.cursor()
        c.execute('select count(*) from voice where id=?', (id,))
        return c.fetchall()[0][0] > 0

    def has_xml(self, id):
        c = self.connection.cursor()
        c.execute('select count(*) from xml where id=?', (id,))

        if c.fetchall()[0][0] > 0:
            debug.log("{0} has xml".format(id))
            return True
        else:
            debug.log('{0} doesn\'t have xml'.format(id))
            return False
