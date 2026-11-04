"""
Zermelo API client — Project ZRN
ByteBell Software

Fetches a student's schedule by student number.
Zermelo REST API docs: https://zermelo.atlassian.net/wiki/spaces/DEV/overview
"""

import requests
import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ZermeloClient:
    BASE_URL = "https://{school}.zportal.nl/api/v3"

    def __init__(self, school: str, token: str):
        self.school = school
        self.token = token
        self.base_url = self.BASE_URL.format(school=school)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}/{endpoint}"
        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            logger.error("Zermelo API timeout")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"Zermelo API HTTP error: {e}")
            raise

    def get_student_info(self, leerlingnummer: str) -> Optional[dict]:
        """Fetch basic info for a student."""
        try:
            data = self._get("users", params={"code": leerlingnummer})
            users = data.get("response", {}).get("data", [])
            return users[0] if users else None
        except Exception as e:
            logger.error(f"Failed to fetch student info: {e}")
            return None

    def get_schedule_today(self, leerlingnummer: str) -> list[dict]:
        """Fetch today's schedule."""
        return self.get_schedule(leerlingnummer, days=0)

    def get_schedule(self, leerlingnummer: str, days: int = 0) -> list[dict]:
        """
        Fetch the schedule.
        days=0 -> today, days=1 -> tomorrow, etc.
        """
        now = datetime.datetime.now()
        target = now + datetime.timedelta(days=days)

        # Start and end of the day as Unix timestamps
        start = int(datetime.datetime(
            target.year, target.month, target.day, 0, 0, 0
        ).timestamp())
        end = int(datetime.datetime(
            target.year, target.month, target.day, 23, 59, 59
        ).timestamp())

        try:
            data = self._get("appointments", params={
                "user": leerlingnummer,
                "start": start,
                "end": end,
                "valid": True,
                "fields": "id,start,end,startTimeSlot,endTimeSlot,subjects,teachers,locations,groups,cancelled,type",
            })
            appointments = data.get("response", {}).get("data", [])
            # Sort by start time, filter out cancelled lessons
            lessons = [a for a in appointments if not a.get("cancelled", False)]
            lessons.sort(key=lambda x: x.get("start", 0))
            return self._format_lessons(lessons)
        except Exception as e:
            logger.error(f"Failed to fetch schedule: {e}")
            return []

    def _format_lessons(self, appointments: list) -> list[dict]:
        """Convert raw Zermelo data into a readable format."""
        result = []
        for i, apt in enumerate(appointments, 1):
            start_ts = apt.get("start", 0)
            end_ts = apt.get("end", 0)
            start_dt = datetime.datetime.fromtimestamp(start_ts)
            end_dt = datetime.datetime.fromtimestamp(end_ts)

            result.append({
                "lesuur": apt.get("startTimeSlot", i),
                "label": f"Les {apt.get('startTimeSlot', i)}",
                "vak": ", ".join(apt.get("subjects", [])) or "—",
                "docent": ", ".join(apt.get("teachers", [])) or "—",
                "lokaal": ", ".join(apt.get("locations", [])) or "—",
                "groep": ", ".join(apt.get("groups", [])) or "—",
                "start": start_dt.strftime("%H:%M"),
                "einde": end_dt.strftime("%H:%M"),
                "geannuleerd": apt.get("cancelled", False),
            })
        return result
