# The MIT License (MIT)
#
# Copyright (c) 2024 Scott Lau
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import logging

from sc_utilities import Singleton
from sc_utilities import log_init

log_init()

import pandas as pd
from sc_config import ConfigUtils
from sc_address_generator import PROJECT_NAME, __version__
import argparse
import requests
from bs4 import BeautifulSoup
import urllib
import urllib.parse
import os


class Runner(metaclass=Singleton):

    def __init__(self):
        project_name = PROJECT_NAME
        ConfigUtils.clear(project_name)
        self._config = ConfigUtils.get_config(project_name)
        # 生成的目标Excel文件存放路径
        self._target_directory = self._config.get("output.target_directory")
        # 目标文件名称
        self._target_filename = self._config.get("output.target_filename")
        self._target_sheet_name = self._config.get("output.target_sheet_name")

        self._api_url = self._config.get("env.api_url")
        self._api_key_city = self._config.get("env.api_key_city")
        self._api_value_city = self._config.get("env.api_value_city")
        self._api_key_path = self._config.get("env.api_key_path")
        self._api_value_path = self._config.get("env.api_value_path")
        self._api_key_method = self._config.get("env.api_key_method")
        self._api_value_method = self._config.get("env.api_value_method")
        self._api_content_type = self._config.get("env.api_content_type")
        self._api_rst_root_address = self._config.get("env.api_rst_root_address")
        self._api_rst_address = self._config.get("env.api_rst_address")
        self._api_name_address = self._config.get("env.api_name_address")
        self._api_name_full_address = self._config.get("env.api_name_full_address")
        self._api_rst_city = self._config.get("env.api_rst_city")
        self._api_name_city = self._config.get("env.api_name_city")
        self._api_rst_county = self._config.get("env.api_rst_county")
        self._api_name_county = self._config.get("env.api_name_county")
        self._api_rst_province = self._config.get("env.api_rst_province")
        self._api_name_province = self._config.get("env.api_name_province")
        self._api_name_json = self._config.get("env.api_name_json")
        generator_count = self._config.get("env.generator_count")
        self._generator_count = 10
        try:
            self._generator_count = int(generator_count)
        except Exception as e:
            logging.getLogger(__name__).warning("failed to parse config generator_count", exc_info=e)

    def run(self, *, args):
        logging.getLogger(__name__).info("arguments {}".format(args))
        logging.getLogger(__name__).info("program {} version {}".format(PROJECT_NAME, __version__))
        logging.getLogger(__name__).info("configurations {}".format(self._config.as_dict()))

        # 初始化 DataFrame
        df = pd.DataFrame(columns=[
            self._api_name_province,
            self._api_name_city,
            self._api_name_county,
            self._api_name_address,
            self._api_name_full_address,
            self._api_name_json,
        ])
        index = 0
        for index in range(self._generator_count):
            row = list()
            addr = self._generate_address()
            if addr is None:
                continue
            province = ""
            city = ""
            county = ""
            address = ""
            full_address = ""
            full_json = addr
            if self._api_rst_root_address not in addr.keys():
                continue
            root_addr_json = addr[self._api_rst_root_address]
            if root_addr_json is None:
                continue
            if self._api_rst_province in root_addr_json.keys():
                province = root_addr_json[self._api_rst_province]
            if self._api_rst_city in root_addr_json.keys():
                city = root_addr_json[self._api_rst_city]
            if self._api_rst_county in root_addr_json.keys():
                county = root_addr_json[self._api_rst_county]
            if self._api_rst_address in root_addr_json.keys():
                address = root_addr_json[self._api_rst_address]
            row.append(province)
            row.append(city)
            row.append(county)
            row.append(address)
            full_address = province + city + county + address
            row.append(full_address)
            row.append(full_json)
            df.loc[index] = row
            index = index + 1

        target_filename_full_path = os.path.join(self._target_directory, self._target_filename)
        # 如果文件已经存在，则删除
        if os.path.exists(target_filename_full_path):
            logging.getLogger(__name__).info("删除输出文件：%s ", target_filename_full_path)
            try:
                os.remove(target_filename_full_path)
            except Exception as e:
                logging.getLogger(__name__).error("删除输出文件 {} 失败：{} ".format(target_filename_full_path, e))
                return 1

        logging.getLogger(__name__).info("写输出文件：%s ", target_filename_full_path)
        with pd.ExcelWriter(target_filename_full_path) as excel_writer:
            df.to_excel(
                excel_writer=excel_writer,
                index=False,
                sheet_name=self._target_sheet_name,
            )
        return 0

    def _generate_address(self):
        headers = {
            "content-type": self._api_content_type,
            "cache-control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        json = {
            self._api_key_city: self._api_value_city,
            self._api_key_method: self._api_value_method,
            self._api_key_path: self._api_value_path,
        }
        response = requests.post(url=self._api_url, headers=headers, json=json)
        status_code = response.status_code
        if status_code != 200:
            logging.getLogger(__name__).error("请求失败，错误码：{0}".format(status_code))
            return None
        return response.json()


def main():
    try:
        parser = argparse.ArgumentParser(description='Python project')
        args = parser.parse_args()
        state = Runner().run(args=args)
    except Exception as e:
        logging.getLogger(__name__).exception('An error occurred.', exc_info=e)
        return 1
    else:
        return state
