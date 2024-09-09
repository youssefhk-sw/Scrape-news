import time, httpx, random
from typing import Union
from playwright import async_api
from src.buffering import JSONBuffer, Buffering, CSVBuffer
from os import environ
import logging
import src.logging_config

logger = logging.getLogger("ErrorHandler")


class ErrorHandler:
    CONTENT = None
    chrome_path = "path/to/chrome.exe"

    @staticmethod
    def get_request_id(with_proxy: bool = False, previous_ua: str = None, previous_proxy: dict = None):
        """
        This function return dictionary contains headers and proxy keys
        headers: represent the headers used by the request, for now just we integrate user-agent
        proxy: is the proxy by the request will send the request

        """
        number_of_proxies = 2
        headers = {}
        proxy = None
        if not Buffering.user_agent_buffer:
            Buffering.user_agent_buffer = JSONBuffer('files/user_agents.json')
        user_agents = Buffering.user_agent_buffer.get_buffer()
        if previous_ua is None:
            headers['user-agent'] = random.choice(user_agents)
        else:
            headers['user-agent'] = random.choice(list(filter(lambda x: x != previous_ua, user_agents)))
        if with_proxy:
            if previous_proxy is None:
                num = random.choice(range(1, number_of_proxies))
                host = environ.get(f"PROXY{num}")
                username = environ.get(f"USERNAME{num}")
                password = environ.get(f"PASSWORD{num}")
                port = environ.get(f"PORT{num}")
            else:
                for i in range(1, number_of_proxies+1):
                    if previous_proxy['host'] != environ.get(f"PROXY{i}"):
                        host = environ.get(f"PROXY{i}")
                        username = environ.get(f"USERNAME{i}")
                        password = environ.get(f"PASSWORD{i}")
                        port = environ.get(f"PORT{i}")
                        break
            proxy = {
                'host': host,
                'port': port,
                'username': username,
                'password': password,
            }
        return {
            'headers': headers,
            'proxy': proxy,
        }


    @staticmethod
    async def handle_server_echec(url: tuple, request: Union[httpx.Request, None] = None, n_requests: int = 5, delay: float = 3, url_type: str = 'rss') -> dict:
        """
        Handle the server echec get it by the status code 500~5011, by make request until the server response
        with a delay and n_request.
        delay: how much can I wait until make other request.
        n_request: how much of request can make to that server
        It returns dictionary with two case different:
        case1: the error handle. It returns the data get it from the website
        case2: the error still showed. It returns an error data, that give you a view of what happen

        """
        if not request:
            request = httpx.Request(url=url[-1], method="GET")
        with httpx.Client() as client:
            logger.info(f"start 5xx status code handle for `{url[-1]}`")
            for i in range(n_requests):
                response = client.send(request)
                if response.status_code == 200 and url_type == 'rss':
                    logger.info(f"5xx status handled. Make {i}-request to {url}")
                    return {
                        'status': True,
                        'data': {
                            'content': response.content,
                            'requests_sent': i,
                            'delay': delay,
                        }
                    }
                elif response.status_code in range(500, 506):
                    time.sleep(delay)
                    continue
                else:
                    break
        logger.debug(f"5xx status for {url[-1]} not handled after {i}-request")
        return {
            'status': False,
            'data': {
                'work_on': url[-1],
                'date': time.time(),
                'error': response.status_code,
                'user_agent': response.request.headers['user-agent'],
                'delay': delay,
                'requests_sent': n_requests,
            }
        }

    @staticmethod
    async def handle_403(url: str):
        """This function handle the error 403, by make a request with a legitimate cookies"""
        logger.info(f"Handling the error 403 for {url}")
        cookies = await ErrorHandler.get_cookies(url, Buffering.cookies_buffer)
        if cookies is None:
            logger.error(f"No cookies to handle 403 error for url:<{url}>")
            return None
        try:
            async with httpx.AsyncClient(cookies=cookies['cookies'], follow_redirects=True) as client:

                logger.info(f"Sending request to {url} with cookies")
                response = await client.get(url, timeout=5)
                logger.info(f"Status code <{response.status_code}, {url}>")
                # ErrorHandler.CONTENT used when the first time we get the cookies we get also the content of the page
                # to avoid repetition
                if response.status_code != 200:
                    if ErrorHandler.CONTENT:
                        return ErrorHandler.CONTENT
                    logger.info("Using Headless browser to get the content")
                    return await ErrorHandler.get_content(url)
            logger.info(f"403 status code handled for {url}")
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Exception when handling 403 error for {url}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_base_url(url: str) -> str:
        """
        Get the base url for url, for example:
        https://www.exmaple.com/users/user1/profile.html -> https://www.example.com
        :param url: log url
        :return: the base url
        """
        from urllib import parse
        url_parser = parse.urlparse(url)
        return url_parser.scheme + '://' + url_parser.hostname + '/'

    @staticmethod
    def __min_expires_cookies(cookies: dict):
        """
        calculate the expired time of a cookies, by the take the min expired of all the cookie
        :param cookies: dict object that content the cookies
        :return: the min expired time of those cookies related to that website
        """
        return min(filter(lambda v: v, [cookie[-1] for cookie in cookies.values()]))

    @staticmethod
    async def get_content(url: str):
        """
        Get page content, using playwright
        :param url: scraped website
        :return: the content of the page
        """
        try:
            async with async_api.async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path=ErrorHandler.chrome_path,
                    headless=True
                )
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(url, timeout=60000)
                await page.wait_for_selector("body")
                content_ = await page.content()
            return content_
        except async_api.Error as e:
            logger.error(f"Exception from `get_content` for url:<{url}>: {e}")

    @staticmethod
    async def get_new_cookies(url: str):
        """ Use playwright to get cookies from the website
        :param url: from where we get the cookies
        :return: dict object that contents all the cookies 'name' and 'value'
        """
        try:
            async with async_api.async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    executable_path=ErrorHandler.chrome_path,
                    headless=True,
                )
                context = await browser.new_context()
                page = await context.new_page()
                await page.goto(url, timeout=60000)
                await page.wait_for_selector("body")
                ErrorHandler.CONTENT = await page.content()
                new_cookies = {cookie['name']: [cookie['value'], cookie['expires']] for cookie in await context.cookies()}
            return new_cookies
        except async_api.Error as e:
            logger.error(f"Exception from `get_new_cookies` for url:<{url}>: {e}")
            return None

    @staticmethod
    async def get_cookies(url: str, buffer: JSONBuffer):

        """This function check the cookies if exist in the cookies_buffer that related to 'cookies.json' file
        if the cookies exist and the expired time calculated by __min_expires_cookies > time.time(), use it
        else we get the cookies and also if the buffer is empty
        :param url: website from where we get the cookies
        :param buffer: the buffer used to store all the cookies used by the program, 'cookies_buffer'
        :return: buffer, used to save the data in 'cookies.json' file and close the buffer"""

        buffer_content = buffer.get_buffer()
        base_url = ErrorHandler.get_base_url(url)
        get_cookies_try = 3
        if buffer_content:
            favorable_item = list(filter(lambda item: item['url'] == base_url, buffer_content))
            if not favorable_item:
                logger.info(f"No cookies favorable for {base_url}")
            else:
                logger.info("Cookies exist in the buffer")
                logger.info("Check expired time")
                if favorable_item[0]['expires'] > time.time():
                    logger.info("Cookies not expired")
                    return favorable_item[0]
                else:
                    logger.info("Cookies expired")
                    buffer.buffer.remove(favorable_item[0])
        else:
            logger.info("Nothing in the buffer")
            logger.info(f"No cookies favorable for {base_url}")

        logger.info(f"Get new cookies")
        new_cookies = await ErrorHandler.get_new_cookies(url)
        while not new_cookies and get_cookies_try != 0:
            new_cookies = await ErrorHandler.get_new_cookies(url)
            get_cookies_try -= 1
        if not new_cookies:
            logger.error(f"No cookies get it for url:<{url}>")
            return None
        expires = ErrorHandler.__min_expires_cookies(new_cookies)
        new_cookies = {key: value[0] for key, value in new_cookies.items()}
        cookies_buffer_item = {'url': base_url, 'cookies': new_cookies, 'expires': expires}
        buffer.add_item(cookies_buffer_item)
        logger.info(f"{base_url} cookies added to the buffer")
        return cookies_buffer_item

    @staticmethod
    async def not_handled_websites(data: dict, after: float = 500):
        """
        The websites that return error status code and not reach its data. this function
        save the state of those website in a csv file, for later test
        :param data: Error data returned by the Scraper
        :param after: much of time wait to resent request again
        """
        logger.error(
            f"{data['data']['work_on']} status saved in `not_handled_urls.csv` with status code <{data['data']['error']}> test after {after}")
        item = {
            'URL': data['data']['work_on'],
            'Status code': data['data']['error'],
            'Time of fail': data['data']['date'],
            'Time of resent': time.time() + after,
        }
        if not Buffering.not_handled_urls_buffer:
            headers = ['URL', 'Status code', 'Time of fail', 'Time of resent']
            Buffering.not_handled_urls_buffer = CSVBuffer('not_handled_urls.csv', headers)
        Buffering.not_handled_urls_buffer.add_item(item)


