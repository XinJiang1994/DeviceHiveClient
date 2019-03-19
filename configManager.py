import configparser
class ConfigManager():
    def __init__(self):
        self.cf = configparser.ConfigParser()
        self.cf.read('config.ini')
        # cf.read(filename)

    def getConfigValue(self, name):
        value = self.cf.get("config", name)
        return value
    def getCmdValue(self, name):
        value = self.cf.get("cmd", name)
        return value

    def setConfigValue(self, name, value):
        cfg = self.cf.set("config", name, value)
        fp = open(r'config.ini', 'w')
        cfg.write(fp)
