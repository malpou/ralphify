from ralphify._output import collect_output


class TestCollectOutput:
    def test_both_strings(self):
        assert collect_output("out\n", "err\n") == "out\nerr\n"

    def test_stdout_only(self):
        assert collect_output("out\n", "") == "out\n"

    def test_stderr_only(self):
        assert collect_output("", "err\n") == "err\n"

    def test_both_none(self):
        assert collect_output(None, None) == ""

    def test_stdout_none(self):
        assert collect_output(None, "err\n") == "err\n"

    def test_stderr_none(self):
        assert collect_output("out\n", None) == "out\n"

    def test_both_empty(self):
        assert collect_output("", "") == ""

    def test_bytes_stdout(self):
        assert collect_output(b"out\n", None) == "out\n"

    def test_bytes_stderr(self):
        assert collect_output(None, b"err\n") == "err\n"

    def test_bytes_both(self):
        assert collect_output(b"out\n", b"err\n") == "out\nerr\n"

    def test_mixed_str_and_bytes(self):
        assert collect_output("out\n", b"err\n") == "out\nerr\n"

    def test_bytes_with_replacement(self):
        result = collect_output(b"hello\xff\n", None)
        assert "hello" in result
        assert "\ufffd" in result  # replacement character
