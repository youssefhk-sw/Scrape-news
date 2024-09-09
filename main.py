import asyncio
import logging
import time

from src.scraper import Scraper
from src.handle_errors import ErrorHandler
from src.database_manager import ManageDB
from src.cleaner import Cleaner
from src.buffering import Buffering

# channels dictionary hold channels tou want to scrape with its base url , rss feed and language used
channels = {
    "example": {
        "base_url": "https://www.example.com/",
        "rss_url": "http://www.example.com/feed",
        "language": "english",
    },
}


async def find_channel_name(channel_url: str):
    for key, value in channels.items():
        if channel_url == value['base_url']:
            return key
    return ""


async def manager(data: dict):
    global channels
    channels['delay'] = time.time() + 120
    data_content = data['data']
    channel_name = await find_channel_name(data_content['channel_url'])
    logging.info(f"Find channel {channel_name} with url {data_content['channel_url']}")
    # clean news data
    data['data']['news'] = await Cleaner.handel_news_garbage(data_content)
    for news in data['data']['news']:
        if news.get("media") == 'Nothings':
            logging.info(f"Image for {news.get('link')} not saved")
        else:
            news['media_path'] = await Scraper.save_image(news.get("media"), channel_name)
            logging.info(f"Image {news['media_path']} is saved successfully")
    # Update channel news number
    await ManageDB.update_number_of_news(channel_name, data_content['number_of_news'])
    # save news to database
    await ManageDB.save_news(data, channel_name)


async def create_scrapers():
    # scrapers list contains coroutines to scrape every channel
    scrapers = []
    for item in channels.values():
        scrapers.append(Scraper.get_news((item['base_url'], item['rss_url'])))
    logging.info("Created Scrapers successfully")
    return await asyncio.gather(*scrapers)


async def insert_channels():
    # Insert channels to database
    channels_info = []
    for name, channel in channels.items():
        channels_info.append(
            {
                'name': name,
                'base_url': channel['base_url'],
                'rss_url': channel['rss_url'],
                'language': channel['language']
            }
        )
    await ManageDB.add_channels(channels_info)


async def main():
    await ManageDB.create_tables()
    await Buffering.open_buffers()
    await insert_channels()
    try:
        result = await create_scrapers()

        # Check data status
        for data in result:
            if data['status']:
                await manager(data)
            else:
                error = data['data']['error']
                if error == 403:
                    content = await ErrorHandler.handle_403(data['data']['work_on'])
                    if content:
                        await Scraper.get_rss_data(content, (data['data']['channel_url'], data['data']['work_on']))
                    else:
                        await ErrorHandler.not_handled_websites(data)
                elif error == 404:
                    await ErrorHandler.not_handled_websites(data)
                else:
                    await ErrorHandler.not_handled_websites(data)
    except Exception as e:
        logging.error(f"Exception: {e}", exc_info=True)
    finally:
        await Buffering.close_buffers()
if __name__ == "__main__":
    asyncio.run(main())
