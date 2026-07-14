"""
数据模型和业务逻辑。

Task 数据类封装了任务的所有属性和常用的展示逻辑。
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Task:
    """一个待办任务。"""

    id: int
    title: str
    done: bool = False
    priority: str = "medium"
    due_date: Optional[date] = None
    created_at: Optional[date] = None

    @property
    def is_overdue(self) -> bool:
        """是否已过期。"""
        if self.done or self.due_date is None:
            return False
        return self.due_date < date.today()

    @property
    def is_due_today(self) -> bool:
        """是否今天截止。"""
        if self.due_date is None:
            return False
        return self.due_date == date.today()

    @property
    def days_remaining(self) -> Optional[int]:
        """剩余天数（负数表示过期天数）。"""
        if self.due_date is None:
            return None
        return (self.due_date - date.today()).days

    @property
    def status_icon(self) -> str:
        """状态图标。"""
        return "✅" if self.done else "⬜"

    @property
    def due_display(self) -> str:
        """截止日期格式化显示。"""
        if self.due_date is None:
            return ""
        if self.done:
            return f"截止: {self.due_date}"

        delta = self.days_remaining
        if delta is None:
            return ""
        if delta < 0:
            return f"截止: {self.due_date} ⚠️ 已过期 {-delta} 天"
        elif delta == 0:
            return f"截止: {self.due_date} ⚠️ 今天截止!"
        elif delta == 1:
            return f"截止: {self.due_date} (明天)"
        elif delta <= 7:
            return f"截止: {self.due_date} (还有 {delta} 天)"
        else:
            return f"截止: {self.due_date} (还有 {delta} 天)"

    @classmethod
    def from_row(cls, row) -> "Task":
        """从数据库行创建 Task 实例。"""
        due_date = None
        if row["due_date"]:
            due_date = datetime.strptime(row["due_date"], "%Y-%m-%d").date()

        created_at = None
        if row["created_at"]:
            # created_at 可能是 ISO 格式，尝试解析
            try:
                created_at = datetime.fromisoformat(row["created_at"]).date()
            except ValueError:
                created_at = datetime.strptime(
                    row["created_at"], "%Y-%m-%d %H:%M:%S"
                ).date()

        return cls(
            id=row["id"],
            title=row["title"],
            done=bool(row["done"]),
            priority=row["priority"],
            due_date=due_date,
            created_at=created_at,
        )

    def to_dict(self) -> dict:
        """转换为字典（用于 JSON/CSV 导出）。"""
        return {
            "id": self.id,
            "title": self.title,
            "done": self.done,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
