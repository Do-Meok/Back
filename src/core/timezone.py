"""
프로젝트 전역에서 공용으로 쓰는 타임존 상수
"""

from datetime import timedelta, timezone

KST = timezone(timedelta(hours=9))  # 한국 표준시(UTC+9). 한국은 DST가 없어 고정 오프셋으로 충분
