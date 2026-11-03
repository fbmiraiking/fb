"""Bulk-sync the standard catalog from std.samr.gov.cn.

The default mode is catalog-only: it reads list pages and upserts standard
metadata without fetching one detail page per standard. This makes an initial
~80k-row import practical. Pass ``--details`` to also fetch detail pages and
version relations (much slower, roughly one request per standard).

Examples:

    python -m scripts.sync_all_standards
    python -m scripts.sync_all_standards --interval 1.5
    python -m scripts.sync_all_standards --details --limit 500
"""

import argparse
import logging
from collections.abc import Iterator

from app.core.config import Settings
from app.db.session import SessionLocal
from app.sync.base import StandardListItem
from app.sync.service import SyncMode, run_sync
from app.sync.std_samr import StdSamrDataSource


class ProgressSource(StdSamrDataSource):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.seen = 0

    def fetch_list(self) -> Iterator[StandardListItem]:
        for item in super().fetch_list():
            self.seen += 1
            if self.seen % 1000 == 0:
                print(f"[sync_all] listed {self.seen} standards...", flush=True)
            yield item


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between HTTP requests (default: 1.0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum list items to process; 0 means the whole catalog",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Also fetch detail pages and relations (slow)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings(
        sync_request_interval_seconds=max(0.0, args.interval),
        sync_max_items_per_run=0,
    )
    source = ProgressSource(settings)
    db = SessionLocal()
    try:
        task, mode = run_sync(
            db,
            source,
            mode=SyncMode.FULL,
            settings=settings,
            max_items=max(0, args.limit),
            include_details=args.details,
        )
        db.refresh(task)
        print(
            f"[sync_all] task={task.id} mode={mode.value} status={task.status.value} "
            f"total={task.total_count} success={task.success_count} "
            f"failed={task.failed_count}",
            flush=True,
        )
        if task.error_message:
            print(f"[sync_all] note: {task.error_message}", flush=True)
        return 0 if task.success_count else 1
    finally:
        source.close()
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
