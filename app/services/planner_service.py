from typing import List, Dict, Optional
from pydantic import BaseModel

class SubTask(BaseModel):
    id: int
    description: str
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None

class PlannerService:
    def __init__(self):
        self.plans: Dict[str, List[SubTask]] = {}

    def create_plan(self, session_id: str, plan_steps: List[str]):
        self.plans[session_id] = [
            SubTask(id=i, description=step) for i, step in enumerate(plan_steps)
        ]

    def update_task_status(self, session_id: str, task_id: int, status: str, result: Optional[str] = None):
        if session_id in self.plans:
            for task in self.plans[session_id]:
                if task.id == task_id:
                    task.status = status
                    if result:
                        task.result = result
                    break

    def get_plan(self, session_id: str) -> List[SubTask]:
        return self.plans.get(session_id, [])

    def format_plan_for_prompt(self, session_id: str) -> str:
        plan = self.get_plan(session_id)
        if not plan:
            return "No active plan."

        formatted = "Current Task Plan:\n"
        for task in plan:
            status_emoji = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(task.status, "❓")
            formatted += f"{task.id}. {status_emoji} {task.description}\n"
        return formatted
