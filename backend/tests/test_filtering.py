from pathlib import Path

from app.services.filtering import collect_text_files


def test_filtering_applies_gitignore_noise_size_and_binary_rules(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "ignored.py").write_text("print('ignored')", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "image.bin").write_bytes(b"\x00\x01")
    (tmp_path / "large.txt").write_text("x" * 20, encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.js").write_text("ignored", encoding="utf-8")

    result = collect_text_files(tmp_path, max_file_size_bytes=12)

    assert result == {"main.py": "print('ok')"}
