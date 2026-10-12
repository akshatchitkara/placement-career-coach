"""Page registry so any page can offer a 'go to the next step' button.

Pages run inside `st.navigation`, which knows the page objects. They are stored in session
state on every run. Outside the full app (for example the headless page tests) the registry is
empty, and `go_button` draws nothing, so a page never depends on it to work.
"""

import streamlit as st

_KEY = "_pcc_pages"


def register_pages(pages: dict[str, st.Page]) -> None:
    st.session_state[_KEY] = pages


def has_navigation() -> bool:
    return bool(st.session_state.get(_KEY))


def go_button(label: str, target: str, *, key: str, primary: bool = False) -> None:
    pages = st.session_state.get(_KEY)
    if not pages or target not in pages:
        return
    if st.button(label, key=key, type="primary" if primary else "secondary"):
        st.switch_page(pages[target])
