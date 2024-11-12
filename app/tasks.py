from flask import current_app
from sqlalchemy import text
from .database import db_session
import schedule
import time
import threading

def refresh_materialized_views():
    """Refresh all materialized views concurrently"""
    with current_app.app_context():
        with db_session() as session:
            session.execute(text("""
                REFRESH MATERIALIZED VIEW CONCURRENTLY detection_accuracy_stats_mv;
                REFRESH MATERIALIZED VIEW CONCURRENTLY review_metrics_mv;
            """))

def start_view_refresh_scheduler():
    """Start the background scheduler for view refreshes"""
    schedule.every(1).hour.do(refresh_materialized_views)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()