import pytest
import os
from src.infrastructure.file_converter import FileConverter


@pytest.fixture
def converter():
    return FileConverter()


def test_read_text_file(converter, tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello World", encoding="utf-8")
    content = converter.read_text(str(f))
    assert content == "Hello World"


def test_read_non_existent_file(converter):
    with pytest.raises(FileNotFoundError):
        converter.read_text("non_existent_file.xyz")
