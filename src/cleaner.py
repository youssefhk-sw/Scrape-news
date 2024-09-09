import asyncio
import time
import re
import logging
import json
import src.logging_config
from src.buffering import Buffering, JSONBuffer
logger = logging.getLogger("Cleaner")


class Cleaner:
    @staticmethod
    async def patter_check(news: dict[str, str]):
        """
        Check match of data scraped to the patterns, to filter cleand data and clean it
        :param news: dict object that contains news informations like: title, description, ect
        :return: dict object contains result that show the state of every element in the news, and news
        """
        clean_result = dict()
        patterns = {
            'title': r"^.+$",
            'link': r"^(https?://[a-z0-9-]+)(\.[a-z0-9-]+)+(:\d+)?(/[^ ]*)?$",
            'publish_date': r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
            'description': r"^.+$",
            'media': r"^(https?://[a-z0-9-]+)(\.[a-z0-9-]+)+(:\d+)?(/[^ ]*)?$",
        }
        logger.info(f"Test cleaning of -> {Cleaner.__news_hash(news)}")
        for key, value in news.items():
            if not value:
                news[key] = "Nothings"
                logger.info(f"{key.capitalize()} is Not clean")
            else:
                match = re.match(patterns[key], value)
                if match:
                    logger.info(f"{key.capitalize()} is clean")
                    logger.info("Eliminate html tags and html tags decoder")
                    news[key] = Cleaner.eliminate_html_tags(Cleaner.eliminate_html_tag_decoder(value))
                    clean_result[key] = 'clean'
                else:
                    logger.info(f"{key.capitalize()} is Not clean")
                    logger.info("Eliminate html tags and html tags decoder")
                    content = Cleaner.eliminate_html_tags(Cleaner.eliminate_html_tag_decoder(value))
                    cleaned_element = re.match(patterns[key], content)
                    if cleaned_element:
                        logger.info(f"The {key.capitalize()} is cleaned successfully")
                        news[key] = cleaned_element.group(0)
                        clean_result[key] = 'clean'
                    else:
                        logger.info(f"The {key.capitalize()} is Not cleaned")
                        logger.info(f"The {key.capitalize()} is -> {value}")
                        clean_result[key] = 'not_clean'
        return {
            'result': clean_result,
            'news': news,
        }

    @staticmethod
    def eliminate_html_tags(text: str):
        """
        some news websites in the rss file the content has some html tags. Use this function to eliminate
        those tags let the text.
        :param text: string object
        :return: cleaned text
        """
        from lxml import html
        element = html.fromstring(text)
        cleaned_text = element.xpath("//p[1]/text()")
        return cleaned_text[0]

    @staticmethod
    async def save_no_cleaned_news(garbage: dict):
        """
        News that has titles for example not match the patterns, use this function to save them in a file
        for later cleaning
        :param garbage: no clean news
        """
        if not Buffering.not_cleaned_news_buffer:
            Buffering.not_cleaned_news_buffer = JSONBuffer(Buffering.Files.NOT_CLEANED_NEWS.value)
        logger.error(f"Add garbage news: `{Cleaner.__news_hash(garbage['garbage_news'])}`")
        Buffering.not_cleaned_news_buffer.add_item(garbage)
        logger.info(f"NOT CLEANED NEWS BUFFER: {Buffering.not_cleaned_news_buffer.get_buffer()}")
    @staticmethod
    async def handel_news_garbage(data: dict):
        """
        from a group of news this function eliminate the garbage news and return only cleaned ones
        :param data: dict object has the form of data returned by Scraper
        :return: cleaned news in data
        """
        def revise_data(news: list, garbage_news: list):
            e = 0
            while e < len(news):
                if news[e] in garbage_news:
                    news.remove(news[e])
                else:
                    e += 1
            return news

        garbage_tasks = []
        garbage_news = []
        for news in data['news']:
            result = await Cleaner.patter_check(news)
            if not all(result['result'].values()):
                garbage = {
                    'garbage_news': result['news'],
                    'cleaned_at': time.time(),
                    'channel': data['data']['channel'],
                    'hash': Cleaner.__news_hash(result['news']),
                }
                logger.debug(f"Garbage news added : {garbage}")
                garbage_tasks.append(Cleaner.save_no_cleaned_news(garbage))
                garbage_news.append(news)
            if garbage_tasks:
                await asyncio.gather(*garbage_tasks)
        return revise_data(data['news'], garbage_news)

    @staticmethod
    def eliminate_html_tag_decoder(text: str):
        import html
        return html.unescape(text)

    @staticmethod
    def __news_hash(news: dict) -> str:
        """
        This function hash news object
        :param news: dict object to hash it
        :return: sha256 hash code of news
        """
        news_to_hash = news
        from hashlib import sha256
        hash_code = sha256(json.dumps(news_to_hash).encode())
        return hash_code.hexdigest()
