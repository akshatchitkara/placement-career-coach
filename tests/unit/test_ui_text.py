from pcc.ui.text import escape_md, safe_md

ZWSP = "\u200b"


def test_dollar_signs_are_escaped_so_markdown_does_not_read_them_as_maths():
    assert safe_md("$group by customer with a $sum") == "\\$group by customer with a \\$sum"


def test_text_without_dollars_is_left_alone():
    plain = "Use chmod 644 on `notes.txt` (see C:\\temp)"
    assert safe_md(plain) == plain


def test_backslashes_are_kept_when_dollars_are_escaped():
    assert safe_md("echo $HOME\\n") == "echo \\$HOME\\\\n"


def test_empty_text():
    assert safe_md("") == ""
    assert escape_md("") == ""


def test_typed_text_cannot_become_a_link_image_or_heading():
    assert escape_md("![x](y)") == "\\!\\[x\\]\\(y\\)"
    assert escape_md("# Title *bold* _it_") == "\\# Title \\*bold\\* \\_it\\_"


def test_web_and_email_addresses_are_broken_so_they_do_not_auto_link():
    assert escape_md("[click](http://evil.example)") == (
        f"\\[click\\]\\(http:{ZWSP}//evil\\.example\\)"
    )
    assert escape_md("see HTTPS://x.example") == f"see HTTPS:{ZWSP}//x\\.example"
    assert escape_md("www.evil.example") == f"www{ZWSP}\\.evil\\.example"
    assert escape_md("me@evil.example") == f"me@{ZWSP}evil\\.example"


def test_plain_names_are_unchanged_apart_from_punctuation():
    assert escape_md("Asha Rao") == "Asha Rao"
    assert escape_md("Zoë 李雷") == "Zoë 李雷"
    assert escape_md("Chandni (Chitkara) Sr.") == "Chandni \\(Chitkara\\) Sr\\."
