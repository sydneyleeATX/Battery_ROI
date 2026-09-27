from datetime import datetime
import pandas as pd
from backend.constants import HISTORICAL_LOAD_FILE

def get_historical_load(
    weather_zone: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """
    Return historical 15-minute load data for one ERCOT weather zone.

    Args:
        weather_zone:
            ERCOT weather-zone identifier, such as "BUSHIDG_COAST".

        start_date:
            Beginning of the requested time range.

        end_date:
            End of the requested time range.

    Returns:
        DataFrame with columns:

            timestamp
            weather_zone
            load_mw

        The date range is inclusive of start_date and exclusive of
        end_date.
    """

    if not isinstance(start_date, datetime):
        raise TypeError("start_date must be a datetime")

    if not isinstance(end_date, datetime):
        raise TypeError("end_date must be a datetime")

    if start_date >= end_date:
        raise ValueError(
            "start_date must be earlier than end_date"
        )

    weather_zone = weather_zone.strip()

    if not weather_zone:
        raise ValueError(
            "weather_zone cannot be empty"
        )

    if not HISTORICAL_LOAD_FILE.exists():
        raise FileNotFoundError(
            f"Historical load file not found: "
            f"{HISTORICAL_LOAD_FILE}"
        )

    load_data = pd.read_csv(
        HISTORICAL_LOAD_FILE,
        parse_dates=["timestamp"],
    )

    required_columns = {
        "timestamp",
        "weather_zone",
        "load_mw",
    }

    missing_columns = required_columns - set(load_data.columns)

    if missing_columns:
        raise ValueError(
            f"Historical load CSV is missing columns: "
            f"{sorted(missing_columns)}"
        )

    filtered_data = load_data[
        (load_data["weather_zone"] == weather_zone)
        & (load_data["timestamp"] >= start_date)
        & (load_data["timestamp"] < end_date)
    ].copy()

    filtered_data = filtered_data.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    return filtered_data[
        [
            "timestamp",
            "weather_zone",
            "load_mw",
        ]
    ]


def identify_peak_periods(load_data: pd.DataFrame):
    """
    Identify peak load periods from historical data.

    Args:
        load_data:
            DataFrame containing:
                timestamp
                weather_zone
                load_mw

    Returns:
        Dictionary containing:
            threshold_mw:
                95th-percentile load threshold.

            peak_intervals:
                Individual 15-minute observations above the
                peak threshold.

            peak_events:
                Consecutive peak intervals grouped into events.

            peak_timing:
                Summary of when peak intervals occur by hour.
    """

    # --------------------------------------------------
    # 1. Validate input
    # --------------------------------------------------

    required_columns = {
        "timestamp",
        "weather_zone",
        "load_mw",
    }

    missing_columns = required_columns - set(load_data.columns)

    if missing_columns:
        raise ValueError(
            f"load_data is missing columns: "
            f"{sorted(missing_columns)}"
        )

    if load_data.empty:
        raise ValueError(
            "load_data cannot be empty"
        )

    data = load_data.copy()

    data["timestamp"] = pd.to_datetime(
        data["timestamp"]
    )

    data["load_mw"] = pd.to_numeric(
        data["load_mw"]
    )

    # --------------------------------------------------
    # 2. Calculate peak threshold
    # --------------------------------------------------

    threshold_mw = data["load_mw"].quantile(0.95)

    # --------------------------------------------------
    # 3. Identify individual peak intervals
    # --------------------------------------------------

    data["is_peak"] = (
        data["load_mw"] >= threshold_mw
    )

    peak_intervals = data[
        data["is_peak"]
    ].copy()

    # --------------------------------------------------
    # 4. Identify consecutive peak events
    # --------------------------------------------------

    peak_intervals = peak_intervals.sort_values(
        ["weather_zone", "timestamp"]
    ).reset_index(drop=True)

    if not peak_intervals.empty:

        time_difference = (
            peak_intervals
            .groupby("weather_zone")["timestamp"]
            .diff()
        )

        # A new event begins whenever the gap between
        # observations is greater than 15 minutes.
        new_event = (
            time_difference
            .isna()
            | (time_difference > pd.Timedelta(minutes=15))
        )

        peak_intervals["event_id"] = (
            new_event
            .groupby(peak_intervals["weather_zone"])
            .cumsum()
        )

        peak_events = (
            peak_intervals
            .groupby(
                ["weather_zone", "event_id"],
                as_index=False
            )
            .agg(
                start_time=("timestamp", "min"),
                end_time=("timestamp", "max"),
                peak_load_mw=("load_mw", "max"),
                average_load_mw=("load_mw", "mean"),
                interval_count=("timestamp", "count"),
            )
        )

        # Each observation represents 15 minutes.
        peak_events["duration_hours"] = (
            peak_events["interval_count"] * 15 / 60
        )

    else:
        peak_events = pd.DataFrame(
            columns=[
                "weather_zone",
                "event_id",
                "start_time",
                "end_time",
                "peak_load_mw",
                "average_load_mw",
                "interval_count",
                "duration_hours",
            ]
        )

    # --------------------------------------------------
    # 5. Identify when peak intervals occur
    # --------------------------------------------------

    peak_timing = (
        peak_intervals.assign(
            hour=peak_intervals["timestamp"].dt.hour
        )
        .groupby(
            ["weather_zone", "hour"]
        )
        .size()
        .reset_index(
            name="peak_interval_count"
        )
    )

    # --------------------------------------------------
    # 6. Return results
    # --------------------------------------------------

    return {
        "threshold_mw": threshold_mw,
        "peak_intervals": peak_intervals,
        "peak_events": peak_events,
        "peak_timing": peak_timing,
    }
