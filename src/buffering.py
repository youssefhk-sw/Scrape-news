import json
import csv
from enum import Enum
import logging
import os
import src.logging_config

logger = logging.getLogger("Buffering")


class JSONBuffer:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.buffer = []
        self.is_open = True
        self.load_file()

    def __create_file(self):
        with open(self.file_path, 'w', encoding='utf-8'):
            pass

    def load_file(self):
        """Loads the content of the file to the buffer"""
        exist = os.path.exists(self.file_path)
        try:
            if exist:
                with open(self.file_path, 'r', encoding='utf-8') as file:
                    self.buffer = json.load(file)
            else:
                self.__create_file()
                self.buffer = []
        except json.JSONDecodeError:
            self.buffer = []

    def add_item(self, item):
        """Add item to the buffer"""
        if not self.is_open:
            raise Exception(f"Buffer is close, no item added")
        self.buffer.append(item)

    def get_buffer(self):
        return self.buffer

    def close(self):
        if self.is_open:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                json.dump(self.buffer, file, indent=2)
                self.is_open = False
        else:
            print("Buffer is closed")

    def is_close(self):
        return not self.is_open


class CSVBuffer:
    def __init__(self, file_path, headers: list):
        self.file_path = file_path
        self.headers = headers
        self.buffer = []
        self.is_open = True
        self.load_file()

    def __create_file(self):
        with open(self.file_path, 'w', encoding='utf-8'):
            pass

    def load_file(self):
        """Loads the content of the file to the buffer"""
        exist = os.path.exists(self.file_path)
        if exist:
            with open(self.file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    self.buffer.append(row)
        else:
            self.__create_file()
            self.buffer = []

    def add_item(self, item: dict):
        """Add item to the buffer"""
        if not self.is_open:
            raise Exception(f"Buffer is close, no item added")
        if not (list(item.keys()) == self.headers):
            raise Exception(f"The item {item} Not respect default headers `{self.headers}`")
        self.buffer.append(item)

    def get_buffer(self):
        return self.buffer

    def is_close(self):
        return not self.is_open

    def close(self):
        if self.is_open:
            with open(self.file_path, 'w', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=self.headers)
                writer.writeheader()
                for item in self.buffer:
                    writer.writerow(item)
            self.is_open = False
        else:
            logger.info(f"Buffer<{self.file_path}> is closed")


class Buffering:

    class Files(Enum):
        NOT_CLEANED_NEWS = "files/news_not_cleaned.json"
        USER_AGENT = "files/user_agents.json"
        COOKIES = "files/cookies.json"
        NOT_HANDLED_URLS = 'files/not_handled_urls.csv'
    # Buffers
    not_cleaned_news_buffer: JSONBuffer = None
    user_agent_buffer: JSONBuffer = None
    cookies_buffer: JSONBuffer = None
    not_handled_urls_buffer: CSVBuffer = None

    @staticmethod
    async def open_buffers():
        if not os.path.exists('files'):
            os.makedirs('files')
        try:
            logger.info("Opening Buffers")
            Buffering.not_cleaned_news_buffer = JSONBuffer(Buffering.Files.NOT_CLEANED_NEWS.value)
            logger.info("`not_cleaned_news_buffer` is opened")
            Buffering.cookies_buffer = JSONBuffer(Buffering.Files.COOKIES.value)
            logger.info("`cookies_buffer` is opened")
            Buffering.user_agent_buffer = JSONBuffer(Buffering.Files.USER_AGENT.value)
            logger.info("`user_agent_buffer` is opened")
            headers = ['URL', 'Status code', 'Time of fail', 'Time of resent']
            Buffering.not_handled_urls_buffer = CSVBuffer(Buffering.Files.NOT_HANDLED_URLS.value, headers)
        except Exception as e:
            logger.error(f"Exception: {e}", exc_info=True)
            if Buffering.not_cleaned_news_buffer:
                Buffering.not_cleaned_news_buffer.close()
            if Buffering.cookies_buffer:
                Buffering.cookies_buffer.close()
            if Buffering.user_agent_buffer:
                Buffering.user_agent_buffer.close()
            if Buffering.not_handled_urls_buffer:
                Buffering.not_handled_urls_buffer.close()
            logger.debug("All Buffers are close")

    @staticmethod
    async def close_buffers():
        if Buffering.not_cleaned_news_buffer.is_open:
            Buffering.not_cleaned_news_buffer.close()
        if Buffering.cookies_buffer.is_open:
            Buffering.cookies_buffer.close()
        if Buffering.user_agent_buffer.is_open:
            Buffering.user_agent_buffer.close()
        if Buffering.not_handled_urls_buffer.is_open:
            Buffering.not_handled_urls_buffer.close()
        logger.debug("All Buffers are close")
