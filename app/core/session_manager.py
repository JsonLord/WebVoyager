import os
import shutil
import uuid
from typing import Dict, Optional
from app.core.browser import BrowserService

class SessionManager:
    def __init__(self, base_user_data_dir: str = "sessions", browser_service: Optional[BrowserService] = None):
        self.base_user_data_dir = base_user_data_dir
        self.browser_service = browser_service or BrowserService()
        self.sessions: Dict[str, dict] = {}

        if not os.path.exists(self.base_user_data_dir):
            os.makedirs(self.base_user_data_dir)

    def create_session(self, session_id: Optional[str] = None) -> str:
        if not session_id:
            session_id = str(uuid.uuid4())

        if session_id in self.sessions:
            return session_id

        user_data_dir = os.path.abspath(os.path.join(self.base_user_data_dir, session_id))
        driver = self.browser_service.create_driver(user_data_dir=user_data_dir)

        self.sessions[session_id] = {
            "driver": driver,
            "user_data_dir": user_data_dir
        }
        return session_id

    def get_driver(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            return session["driver"]
        return None

    def close_session(self, session_id: str):
        session = self.sessions.pop(session_id, None)
        if session:
            try:
                session["driver"].quit()
            except Exception as e:
                print(f"Error closing driver for session {session_id}: {e}")

    def delete_session(self, session_id: str):
        self.close_session(session_id)
        user_data_dir = os.path.join(self.base_user_data_dir, session_id)
        if os.path.exists(user_data_dir):
            shutil.rmtree(user_data_dir)

    def close_all(self):
        for session_id in list(self.sessions.keys()):
            self.close_session(session_id)
