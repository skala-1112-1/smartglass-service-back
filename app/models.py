from sqlalchemy import Column, Integer, String, Text, Boolean
from app.database import Base

class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    machine_id = Column(String(50), nullable=False, index=True)
    item_index = Column(Integer, nullable=False)
    todo = Column(Text, nullable=False)
    done = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Checklist(id={self.id}, machine_id='{self.machine_id}', item_index={self.item_index}, done={self.done})>"

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "item_index": self.item_index,
            "todo": self.todo,
            "done": self.done,
            "summary": self.summary
        }