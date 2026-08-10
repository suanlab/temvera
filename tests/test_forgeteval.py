from temvera.forgeteval import ForgetEvalAdapter


def test_forgeteval_protocol_lifecycle() -> None:
    adapter = ForgetEvalAdapter()
    old_id = adapter.inscribe("Alice works at Google")
    assert old_id == 1
    adapter.inscribe("Parking validation is at the front desk")

    adapter.supersede("Alice works Google", "Alice works at Anthropic")
    recalled = " ".join(adapter.recall_texts("Where does Alice work?", k=10))
    assert "Anthropic" in recalled
    assert "Google" not in recalled

    assert adapter.release("Alice works Anthropic") == 1
    assert adapter.recall_texts("Alice work", k=10) == []


def test_forgeteval_reset_purge_and_deterministic_ties() -> None:
    adapter = ForgetEvalAdapter()
    adapter.inscribe("staging token alpha")
    adapter.inscribe("staging token beta")
    assert adapter.purge("staging token") == 2
    assert adapter.recall_texts("staging token", k=10) == []
    adapter.reset()
    assert adapter.inscribe("fresh") == 1


def test_forgeteval_rejects_invalid_inputs() -> None:
    adapter = ForgetEvalAdapter()
    try:
        adapter.inscribe("  ")
    except ValueError as error:
        assert str(error) == "text must be non-empty"
    else:
        raise AssertionError("blank memory was accepted")

    try:
        adapter.recall_texts("query", k=-1)
    except ValueError as error:
        assert str(error) == "k must be non-negative"
    else:
        raise AssertionError("negative k was accepted")
