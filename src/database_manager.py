import asyncio

import sqlalchemy as sa
import sqlalchemy.orm as so
from os import environ
from dotenv import load_dotenv
from src.models import News, Channel, Base
import logging
from datetime import datetime
import src.logging_config
load_dotenv('./.env')
logger = logging.getLogger("DatabaseManager")


class ManageDB:
    uri = "sqlite:///news_db.db"
    engine = sa.create_engine(uri)
    Session = so.sessionmaker(bind=engine)
    session = Session()

    @staticmethod
    async def create_tables():
        Base.metadata.create_all(ManageDB.engine)

    @staticmethod
    async def save_news(data: dict, channel_name: str):
        channel = await ManageDB.get_channel(channel_name)
        news_objs = []
        for news in data['data']['news']:
            try:
                news_obj = News(
                        title=news.get('title'),
                        description=news.get('description'),
                        publish_date=datetime.strptime(news.get('publish_date'), "%Y-%m-%d %H:%M:%S"),
                        link=news.get('link'),
                        saved_date=datetime.now(),
                        channel_id=channel.channel_id,
                        base_image_link=news.get('media'),
                        base_image_path=news.get('media_path'),
                    )
                news_objs.append(news_obj)
                logger.info(f"Add News-{news.get('link')} successfully")
            except sa.exc.IntegrityError:
                logger.error(f"News-{news.get('link')} Exist")
        ManageDB.session.add_all(news_objs)
        ManageDB.session.commit()

    @staticmethod
    async def add_channel(channel_info: dict):
        if not await ManageDB.get_channel(channel_info['name']):
            channel = Channel(**channel_info)
            ManageDB.session.add(channel)
            logger.info(f"Channel-{channel_info['name']} added Successfully")
        else:
            logger.error(f"Channel-{channel_info['name']} Exist")

    @staticmethod
    async def add_channels(channels_info: list[dict]):
        channels_adders = []
        for channel_info in channels_info:
            channels_adders.append(ManageDB.add_channel(channel_info))
        await asyncio.gather(*channels_adders)
        ManageDB.session.commit()

    @staticmethod
    async def update_number_of_news(channel_name, number_of_news):
        channel = await ManageDB.get_channel(channel_name)
        if channel:
            logger.info(f"Update Number of news to {channel.channel_id}")
            logger.info(f"Channel {channel.channel_id} state: {so.object_session(channel).is_modified(channel)}")
            channel.number_of_news += number_of_news
            ManageDB.session.commit()
        else:
            logger.error(f"No channel has name {channel_name}")

    @staticmethod
    async def get_news_by_id(news_id: int):
        return ManageDB.session.get_one(News, news_id)

    @staticmethod
    async def get_news_by_publish_date(publish_date: str):
        format_ = "%Y-%m-%d %H:%M:%S"
        date_obj = datetime.strptime(publish_date, format_)
        items = ManageDB.session.query(News).filter_by(publish_date=date_obj).all()
        return items

    @staticmethod
    async def get_channel(channel_name: str):
        return ManageDB.session.query(Channel).filter_by(name=channel_name).first()

    @staticmethod
    async def close_session():
        if ManageDB.session.is_active:
            ManageDB.session.close()
            return
        logger.debug("Session is not Active")
