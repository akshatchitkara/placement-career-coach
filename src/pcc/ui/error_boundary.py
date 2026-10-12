"""Wraps every page so a failure shows a calm, recoverable message instead of a stack trace."""

import functools
import logging
from collections.abc import Callable

import streamlit as st

from pcc.core.exceptions import PccError
from pcc.ui.navigation import go_button

logger = logging.getLogger(__name__)

GENERIC_MESSAGE = (
    "Something went wrong on this page. Your saved progress is safe. "
    "Reload the page to try again; if it keeps happening, restart the app."
)


def safe_page(render: Callable[[], None]) -> Callable[[], None]:
    """st.rerun and st.stop raise BaseException subclasses, so they pass through untouched."""

    @functools.wraps(render)
    def wrapper() -> None:
        try:
            render()
        except PccError as exc:  # expected, user-facing problems (bad input, wrong state, ...)
            st.error(str(exc))
        except Exception:
            logger.exception("page_failed page=%s", render.__module__.rsplit(".", 1)[-1])
            st.error(GENERIC_MESSAGE)
            go_button("Back to Home", "home", key="error_home", primary=True)

    return wrapper
