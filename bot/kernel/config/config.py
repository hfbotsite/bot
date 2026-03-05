"""
This module contains the configuration class
"""
import pytoml as toml
import os
import sys

class Config:
    def __init__(self, filename):
        if not os.path.isfile(filename):
            print("Bad config file")

        abspath = os.path.abspath(filename)
        
        self.filename = os.path.basename(abspath)
        self.path = os.path.dirname(abspath)
        self.toml_config = None
        

    def load(self):
        self.__parse_toml_file()


    def save(self):
        self.__save_toml_file()


    def __save_toml_file(self):
        path = os.path.join(self.path, self.filename)

        with open(path, 'r+') as file:
            try:
                file.truncate()
                toml.dump(self.toml_config, file)
            except toml.TomlError as e:
                print(e, "Something goes wrong?")
                sys.exit(0)


    def __parse_toml_file(self):
        path = os.path.join(self.path, self.filename)

        with open(path, 'rb') as file:
            try:
                self.toml_config = toml.load(file)
            except toml.TomlError as e:
                print(e, "Something goes wrong?")
                sys.exit(0)


    def get_value(self, table, key, default_val=None):
        return Config.__get_value(self.toml_config, table, key, default_val)


    def set_value(self, table, key, val):
        return Config.__set_value(self.toml_config, table, key, val)


    @staticmethod
    def __get_value(config, table, key, default_val):
        return config.get(table, default_val).get(key, default_val)


    @staticmethod
    def __set_value(config, table, key, val):
        config[table][key] = val
        toml.dumps(config)
