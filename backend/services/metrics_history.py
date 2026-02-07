from datetime import datetime
import random
from collections import deque

class MetricsHistory:
    def __init__(self, max_len=20):
        self.history = deque(maxlen=max_len)
        self._populate_initial_data()

    def _populate_initial_data(self):
        current_time = datetime.now().timestamp()
        for i in range(20):
            t = current_time - (20 - i)
            self.history.append({
                "timestamp": datetime.fromtimestamp(t).isoformat(),
                "cpu": round(random.uniform(20, 60), 1),
                "memory": round(random.uniform(40, 80), 1)
            })

    def add_mock_point(self):
        point = {
            "timestamp": datetime.now().isoformat(),
            "cpu": round(random.uniform(20, 80), 1),
            "memory": round(random.uniform(40, 90), 1)
        }
        self.history.append(point)
        return point

    def get_data(self):
        return list(self.history)

history_service = MetricsHistory()
