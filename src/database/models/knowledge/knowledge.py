from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, Integer, String, Text

from src.database.models.knowledge._base import _KnowledgeBase as Base


class Knowledge(Base):
    """
    Represents a chunk of text from the knowledge base, along with its vector embedding.
    """

    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=True)
    headline = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)

    def __repr__(self):
        return f"<KnowledgeChunk(id={self.id}, source='{self.source}', headline='{self.headline[:20]}...')>"
