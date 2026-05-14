from traceline.redaction import redact_text


def test_redacts_common_secret_shapes() -> None:
    result = redact_text(
        "Authorization: Bearer sk_live_abc token=secret123 "
        "postgres://user:pass@localhost/db"
    )

    assert result.changed is True
    assert "sk_live_abc" not in result.text
    assert "secret123" not in result.text
    assert "postgres://user:pass" not in result.text
    assert result.text.count("[REDACTED]") == 3
