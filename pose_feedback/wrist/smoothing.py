from typing import Optional


class AsymmetricEMA:
    def __init__(self, alpha_increase: float = 0.5, alpha_decrease: float = 0.2):
        self.alpha_increase = alpha_increase
        self.alpha_decrease = alpha_decrease
        self.value: Optional[float] = None

    def update(self, x: float) -> float:
        if self.value is None:
            self.value = x
            return self.value
        alpha = self.alpha_increase if x > self.value else self.alpha_decrease
        self.value = alpha * x + (1.0 - alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = None


class ResultHolder:
    def __init__(self, max_hold_seconds: float = 0.3):
        self.max_hold_seconds = max_hold_seconds
        self.last_valid_result: Optional[dict] = None
        self.last_valid_time_sec: Optional[float] = None

    def update(self, result: dict, current_time_sec: float) -> dict:
        if result.get("valid"):
            current = dict(result)
            current["is_held"] = False
            current["hold_duration_sec"] = 0.0
            self.last_valid_result = dict(current)
            self.last_valid_time_sec = current_time_sec
            return current
        if self.last_valid_result is not None and self.last_valid_time_sec is not None:
            hold_duration = current_time_sec - self.last_valid_time_sec
            if hold_duration <= self.max_hold_seconds:
                held = dict(self.last_valid_result)
                held["is_held"] = True
                held["hold_duration_sec"] = hold_duration
                held["global_invalid_reason"] = result.get("global_invalid_reason")
                return held
        return result

    def reset(self) -> None:
        self.last_valid_result = None
        self.last_valid_time_sec = None
