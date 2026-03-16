import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
_app = None


def init_scheduler(app):
    """Initialize the APScheduler with the Flask app."""
    global _app
    _app = app

    with app.app_context():
        from app.models import SystemConfig
        hour = _get_config_int('scan_hour', app.config.get('SCAN_HOUR', 2))
        minute = _get_config_int('scan_minute', app.config.get('SCAN_MINUTE', 0))
        enabled = _get_config_bool('scan_enabled', True)

    if enabled:
        scheduler.add_job(
            _scheduled_scan,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_scan',
            replace_existing=True,
        )
        logger.info(f'Scheduled daily scan at {hour:02d}:{minute:02d}')

    if not scheduler.running:
        scheduler.start()
        logger.info('Scheduler started')


def reschedule_scan():
    """Re-apply scheduler settings from database config."""
    if not _app:
        return

    with _app.app_context():
        hour = _get_config_int('scan_hour', 2)
        minute = _get_config_int('scan_minute', 0)
        enabled = _get_config_bool('scan_enabled', True)

    if enabled:
        scheduler.add_job(
            _scheduled_scan,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='daily_scan',
            replace_existing=True,
        )
        logger.info(f'Rescheduled daily scan at {hour:02d}:{minute:02d}')
    else:
        try:
            scheduler.remove_job('daily_scan')
            logger.info('Daily scan disabled')
        except Exception:
            pass


def _scheduled_scan():
    """Execute scheduled scan for all projects."""
    if not _app:
        return
    from app.services.scan_service import scan_all_projects
    logger.info('Starting scheduled scan...')
    scan_all_projects(_app)


def _get_config_int(key: str, default: int) -> int:
    from app.models import SystemConfig
    config = SystemConfig.query.filter_by(key=key).first()
    if config and config.value:
        try:
            return int(config.value)
        except ValueError:
            pass
    return default


def _get_config_bool(key: str, default: bool) -> bool:
    from app.models import SystemConfig
    config = SystemConfig.query.filter_by(key=key).first()
    if config and config.value:
        return config.value.lower() in ('true', '1', 'yes')
    return default
