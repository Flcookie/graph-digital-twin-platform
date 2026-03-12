# kpi_calculator.py - Throughput, WIP, Flow Time, Utilization
# event-driven, no full history. Start=first LOAD, Finish=FINISH, Scrap=SCRAP

import datetime


def _parse_ts(time_str: str) -> float:
    return datetime.datetime.fromisoformat(time_str).timestamp()


class KpiCalculator:
    def __init__(
        self,
        observation_time_mode: str = "realtime",
        finish_events: list[str] | None = None,
        scrap_events: list[str] | None = None,
    ):
        # finish_events/scrap_events configurable. replay mode uses last_event_ts for obs_time
        self.finish_events = set(finish_events or ["FINISH"])
        self.scrap_events = set(scrap_events or ["SCRAP"])
        self.observation_time_mode = observation_time_mode

        self.finished_count = 0
        self.scrap_count = 0
        self.observation_start_ts = None
        self.last_event_ts = None

        # WIP
        self.current_wip = 0

        self.part_start_times = {}
        self.flow_times = []
        self._finished_or_failed_parts = set()  # avoid double-count

        # station utilization: state accumulation over time
        self.station_state = {}
        self._station_accumulated = {}

    def _is_station(self, component_id: str) -> bool:
        return component_id.startswith("station")

    def _ensure_station_state(self, station_id: str, event_ts: float):
        if station_id not in self.station_state:
            self.station_state[station_id] = {
                "current_state": "IDLE",
                "state_start_ts": event_ts,
            }
        if station_id not in self._station_accumulated:
            self._station_accumulated[station_id] = {
                "IDLE": 0.0, "LOADING": 0.0, "PROCESSING": 0.0,
                "UNLOADING": 0.0, "BLOCKED": 0.0, "FAILED": 0.0,
            }

    def _transition_station_state(self, station_id: str, new_state: str, event_ts: float):
        """Accumulate previous state duration on transition."""
        self._ensure_station_state(station_id, event_ts)
        s = self.station_state[station_id]
        acc = self._station_accumulated[station_id]
        prev_state = s["current_state"]
        duration = event_ts - s["state_start_ts"]
        acc[prev_state] = acc.get(prev_state, 0) + duration
        s["current_state"] = new_state
        s["state_start_ts"] = event_ts

    def on_event(self, event: dict) -> None:
        """Update KPI state from event."""
        time_str = event.get("time")
        if not time_str:
            return
        ts = _parse_ts(time_str)
        component_id = event.get("component_id", "")
        part_id = event.get("part_id", "")
        activity = event.get("activity", "")

        if self.observation_start_ts is None:
            self.observation_start_ts = ts
        self.last_event_ts = ts

        # WIP: +1 on first LOAD, -1 on FINISH/SCRAP
        if activity == "LOAD" and part_id not in self._finished_or_failed_parts and part_id not in self.part_start_times:
            self.current_wip += 1
            self.part_start_times[part_id] = ts
        # FINISH (at splitter5 etc, not station)
        if activity in self.finish_events:
            if part_id not in self._finished_or_failed_parts:
                self._finished_or_failed_parts.add(part_id)
                self.current_wip = max(0, self.current_wip - 1)
                if part_id in self.part_start_times:
                    self.flow_times.append(ts - self.part_start_times[part_id])
                    del self.part_start_times[part_id]
                self.finished_count += 1
        # SCRAP: WIP-1, not in throughput/flow_time
        if activity in self.scrap_events:
            if part_id not in self._finished_or_failed_parts:
                self._finished_or_failed_parts.add(part_id)
                self.current_wip = max(0, self.current_wip - 1)
                self.scrap_count += 1
                if part_id in self.part_start_times:
                    del self.part_start_times[part_id]

        # station state: LOAD->LOADING, PROCESS->PROCESSING, etc.
        if self._is_station(component_id):
            if activity == "LOAD":
                self._transition_station_state(component_id, "LOADING", ts)
            elif activity == "PROCESS":
                self._transition_station_state(component_id, "PROCESSING", ts)
            elif activity == "UNLOAD":
                self._transition_station_state(component_id, "UNLOADING", ts)
            elif activity == "TRANSFER":
                self._transition_station_state(component_id, "IDLE", ts)
            elif activity == "BLOCK":
                self._transition_station_state(component_id, "BLOCKED", ts)
            elif activity == "FAIL":
                self._transition_station_state(component_id, "FAILED", ts)
            # PASS: part passes through, no state change

    def get_snapshot(self) -> dict:
        """Current KPI snapshot."""
        if self.observation_time_mode == "replay":
            end_ts = self.last_event_ts if self.last_event_ts else datetime.datetime.now().timestamp()
        else:
            end_ts = datetime.datetime.now().timestamp()
        obs_time = max(0, (end_ts - self.observation_start_ts) if self.observation_start_ts else 0)
        throughput = self.finished_count / obs_time if obs_time > 0 else 0
        avg_flow = sum(self.flow_times) / len(self.flow_times) if self.flow_times else 0

        # utilization = processing_time / obs_time, state_probability = state_time / obs_time
        utilization = {}
        state_probability = {}
        for sid, acc in self._station_accumulated.items():
            s = self.station_state.get(sid, {})
            curr_state = s.get("current_state", "IDLE") if s else "IDLE"
            state_start = s.get("state_start_ts", end_ts) if s else end_ts
            curr_duration = end_ts - state_start if end_ts else 0

            # add current state duration
            full_times = {st: acc.get(st, 0) + (curr_duration if st == curr_state else 0) for st in acc}
            proc_time = full_times.get("PROCESSING", 0)
            util = proc_time / obs_time if obs_time > 0 else 0
            utilization[sid] = round(util, 4)

            # state_probability
            state_probability[sid] = {
                k.lower(): round(v / obs_time, 4) if obs_time > 0 else 0
                for k, v in full_times.items()
            }

        return {
            "throughput": round(throughput, 4),
            "finished_count": self.finished_count,
            "scrap_count": self.scrap_count,
            "observation_time_sec": round(obs_time, 1),
            "wip": self.current_wip,
            "avg_flow_time_sec": round(avg_flow, 2),
            "flow_time_count": len(self.flow_times),
            "utilization": utilization,
            "state_probability": state_probability,
        }
