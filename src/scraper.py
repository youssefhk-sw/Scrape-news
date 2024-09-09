import feedparser
import httpx
import time
from lxml import html
from urllib import parse
from datetime import datetime
import src.logging_config
import logging
from src.handle_errors import ErrorHandler
logger = logging.getLogger("Scraper")


class Scraper:
    number_of_image = 0
    @staticmethod
    def __convert_date_to_utc(date: str):
        """
        This function convert a date any in timezone to UTC
        :param date: str object represent the date scraped
        :return: str object the UTC date associate to date
        """
        import pytz

        def check_format(format_: str):
            try:
                datetime.strptime(date, format_)
                return True
            except ValueError:
                return False

        standard_format = "%Y-%m-%d %H:%M:%S"
        date_format = "%a, %d %b %Y %H:%M:%S"
        if check_format(standard_format):
            return date
        if 'GMT' in date:
            date = date.replace('GMT', '').strip()
            return datetime.strptime(date, date_format).strftime(standard_format)
        local_time = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z')
        utc_time = local_time.astimezone(pytz.utc)
        formatted_utc_time = utc_time.strftime(standard_format)
        return utc_time.strftime(formatted_utc_time)

    @staticmethod
    async def get_rss_data(content, channel_rss: tuple):
        """
        Function that parse the RSS file to retrieve the data
        :param content: bytes object that contains RSS feed
        :param channel_rss: a tuple with two elements `rss url` and `base url of the channel`
        :return: dict object that contains the status of the data and news.
        """
        news = []
        rss_feed = feedparser.parse(content)
        rss_url = channel_rss[-1]
        for entry in rss_feed.entries:
            if entry.get('media_thumbnail', None):
                logger.info("Media exist in the RSS feed")
                media = entry.media_thumbnail[0].get('url')
            else:
                media = await Scraper.get_media(entry.link, channel_rss[0])
            news.append(
                {
                    'title': entry.title,
                    'link': entry.link,
                    'publish_date': Scraper.__convert_date_to_utc(entry.published),
                    'description': entry.summary,
                    'media': media,
                },
            )
        logger.info(f"Scrape news successfully from {rss_url}")
        return {
            'status': True,
            'data': {
                'work_on': rss_url,
                'channel_url': channel_rss[0],
                'date': time.time(),
                'number_of_news': len(rss_feed.entries),
                'news': news,
            }
        }

    @staticmethod
    async def get_media(article_url: str, base_url: str):
        """
        Some RSS files did not integrate base image of the article, this function used to get the image
        from the article.
        :param article_url: the URL where to get the image
        :param base_url: this parameter used to joined with link of the image
        :return: image url
        """
        logger.info(f"Start getting media from the article page <{article_url}>")
        content = await ErrorHandler.handle_403(article_url)
        if content:
            doc = html.fromstring(content)
            media_url = doc.xpath("//img[1]/@src")
            if media_url:
                logger.info(f"Get media successfully for url:<{article_url}> ")
                return parse.urljoin(base_url, media_url[0])
            logger.debug(f"Media no get it for url:<{article_url}>")
            return None
        logger.debug(f"Media no get it for url:<{article_url}>")
        return None

    @staticmethod
    async def get_news(rss_url: tuple, headers=None, proxy=None) -> dict:
        """
        This function sed request to the rss url -> rss_url[1] a check the status code of the response to return
        the dict object either with status True that mean this dict has news data or False mean there are a problem.
        :param rss_url: a tuple with two elements `rss url` and `base url of the channel`
        :param headers: request headers
        :param proxy: used to send request using proxy
        :return: the state of the data and news data if the status key is True
        """
        try:
            response = httpx.get(rss_url[-1], headers=headers, follow_redirects=True, timeout=60)
            if response.status_code != 200:
                logger.debug(f"News did not scraped from {rss_url[-1]}, status code<{response.status_code}>")
                return {
                    'status': False,
                    'data': {
                        'channel_url': rss_url[0],
                        'work_on': rss_url[-1],
                        'date': time.time(),
                        'error': response.status_code,
                        'user_agent': response.request.headers['user-agent'],
                        'proxy': proxy,
                    }
                }
            return await Scraper.get_rss_data(response.content, rss_url)
        except httpx.HTTPError as e:
            logger.error(f"Exception: {e}")
            return {
                    'status': False,
                    'data': {
                        'channel_url': rss_url[0],
                        'work_on': rss_url[-1],
                        'date': time.time(),
                        'error': 0,
                    }
                }

    @staticmethod
    async def save_image(image_link: str, channel_name: str):
        import os
        directory_exist = os.path.exists(f"images/{channel_name}")
        try:
            response = httpx.get(image_link)
            logger.info(f"Saving image for <{image_link}> with status code {response.status_code}")
            if not directory_exist:
                os.makedirs(f"images/{channel_name}")
                Scraper.number_of_image = 0
            else:
                Scraper.number_of_image = len(os.listdir(f"images/{channel_name}"))
            Scraper.number_of_image += 1
            with open(f'images/{channel_name}/image_{Scraper.number_of_image}.png', 'wb') as image:
                image.write(response.content)
            return f"{os.path.abspath('images/')}/{channel_name}/image_{Scraper.number_of_image}.png".replace('\\', '/')
        except httpx.HTTPError as e:
            logger.error(f"Image link:<{image_link}> not added Exception : {e}")
            return None
