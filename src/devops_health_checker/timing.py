import time


def measure_time(func, *args, **kwargs):
    start = time.perf_counter()

    try:
        result = func(*args, **kwargs)

        duration_ms = (
            time.perf_counter() - start
        ) * 1000

        return result, duration_ms

    except Exception:
        duration_ms = (
            time.perf_counter() - start
        ) * 1000

        raise