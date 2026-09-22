import logging
from systemd.journal import JournalHandler


journal_handler = JournalHandler(SYSLOG_IDENTIFIER="rlx-web")
formatter = logging.Formatter("[%(levelname)s] %(module)s: %(message)s")
journal_handler.setFormatter(formatter)
journal_handler.setLevel(logging.INFO)
logging.basicConfig(handlers=[journal_handler], level=logging.INFO)

logger = logging.getLogger("rlx-web")
