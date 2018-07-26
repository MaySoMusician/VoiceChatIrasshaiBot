import sqlite3
import debug

class sqlite_manager:

    def __init__(self, api_manager):
        self.dbname = "voiceroid.db"
        self.connection = sqlite3.connect(self.dbname)
        self.create_table()
        self.api_manager = api_manager

    def create_table(self):
        cursor = self.connection.cursor()
        debug.log('create voice')
        cursor.execute(
            'create table if not exists voice (id tinytext, voice tinytext default "sumire", pitch decimal default 1.0, range decimal default 1.0, rate decimal default 1.0, volume decimal default 1.0, txt text default "{0}さんいらっしゃい")')
        cursor.execute('create table if not exists xml (id tinytext, xml text)')
        debug.log('create xml')
        self.connection.commit()

    def set_xml(self, id, xml):

        if self.api_manager.is_xml(xml):
            debug.log("set xml {0}".format(id))
            self.delete_voice(id)
            c = self.connection.cursor()
            if self.has_value(id):
                c.execute('update xml set xml=? where id=?', (xml, id))
            else:
                c.execute('insert into xml (id, xml) values (?, ?)', (id, xml))
            self.connection.commit()
            return True
        else:
            return False

    def get_xml(self, id):
        c = self.connection.cursor()
        c.execute('select xml from xml where id=?', (id,))
        result = c.fetchmany(1)[0][0]
        return result

    def set_voice(self, id, param):
        self.set_value(id, 'voice', param)
        return True

    def set_rate(self, id, param):
        self.set_value(id, 'rate', param)
        return True

    def set_range(self, id, param):
        self.set_value(id, 'range', param)
        return True

    def set_pitch(self, id, param):
        self.set_value(id, 'pitch', param)
        return True

    def set_volume(self, id, param):
        self.set_value(id, 'volume', param)
        return True

    def set_text(self, id, param):
        self.set_value(id, 'txt', param)
        return True

    def reset(self, id):
        debug.log("reset db {0}".format(id))
        self.delete_voice(id)
        self.delete_xml(id)
        return True

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


    def get_row(self, id):
        if self.has_value(id):
            c = self.connection.cursor()
            c.execute('select * from voice where id=?', (id,))
            row = c.fetchmany(1)[0]
            debug.log('{0} has value'.format(id))
            return row
        else:
            debug.log('{0} doesn\'t have value'.format(id))
            return (id, 'sumire', 1.0, 1.0, 1.0, 1.0, '{0}さんいらっしゃい')

    def has_value(self, id):
        c = self.connection.cursor()
        c.execute('select count(*) from voice where id=?', (id,))
        return c.fetchall()[0][0] > 0

    def has_xml(self, id):
        c = self.connection.cursor()
        c.execute('select count(*) from xml where id=?', (id,))
        return c.fetchall()[0][0] > 0
