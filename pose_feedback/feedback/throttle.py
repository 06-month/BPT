class FeedbackThrottle:
    def __init__(self, min_interval_seconds: float = 1.0):
        self.min_interval_seconds = min_interval_seconds
        self.last_feedback_time: dict[str, float] = {}

    def should_fire(self, feedback_type: str, current_time_sec: float) -> bool:
        last = self.last_feedback_time.get(feedback_type, -1e9)
        if current_time_sec - last >= self.min_interval_seconds:
            self.last_feedback_time[feedback_type] = current_time_sec
            return True
        return False

    def reset(self) -> None:
        self.last_feedback_time = {}
