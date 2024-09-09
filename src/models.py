import sqlalchemy as sa
import sqlalchemy.orm as so
from datetime import datetime
from typing import List

class Base(so.DeclarativeBase):
    pass


class News(Base):
    __tablename__ = "news"
    news_id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String, nullable=True)
    description: so.Mapped[str] = so.mapped_column(sa.String, nullable=True)
    publish_date: so.Mapped[datetime] = so.mapped_column(sa.DateTime, nullable=True)
    saved_date: so.Mapped[datetime] = so.mapped_column(sa.DateTime, nullable=True)
    channel_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey("channels.channel_id"), nullable=True)
    link: so.Mapped[str] = so.mapped_column(sa.String, nullable=True, unique=True)
    base_image_link: so.Mapped[str] = so.mapped_column(sa.String, nullable=True)
    base_image_path: so.Mapped[str] = so.mapped_column(sa.String, nullable=True)
    channel: so.Mapped["Channel"] = so.relationship("Channel", back_populates="news", foreign_keys=[channel_id])

    def __repr__(self):
        return f"News-{self.news_id}"


class Channel(Base):
    __tablename__ = "channels"
    channel_id: so.Mapped[int] = so.mapped_column(sa.Integer, primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String, unique=True)
    base_url: so.Mapped[str] = so.mapped_column(sa.String)
    rss_url: so.Mapped[str] = so.mapped_column(sa.String)
    number_of_news: so.Mapped[int] = so.mapped_column(sa.Integer, default=0)
    language: so.Mapped[str] = so.mapped_column(sa.String, nullable=True)
    news: so.Mapped[List["News"]] = so.relationship("News", back_populates="channel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"Channel-{self.channel_id}"

