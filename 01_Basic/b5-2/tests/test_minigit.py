"""미션의 사용자 동작을 확인한다. 실행: python -m unittest discover -s tests"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from minigit.__main__ import MiniGitCLI
from minigit.diff import DiffLimitError, compute_diff, compute_lcs_table, diff_files
from minigit.graph import find_ancestors, find_shortest_path, topological_sort
from minigit.models import Commit
from minigit.sorting import benchmark_sorts, merge_sort, quick_sort


class MiniGitTests(unittest.TestCase):
    def setUp(self):
        self.cli = MiniGitCLI()

    def command(self, line):
        return self.cli.execute(self.cli.parse_input(line))

    def test_init_branch_switch_commit_and_merge(self):
        self.command("INIT Alice")
        first = self.command('COMMIT "start here"')
        root = self.cli.repo.get_head_commit_hash()
        self.assertIn(root, first)
        self.command("BRANCH feature")
        self.command("SWITCH feature")
        self.command('USER "Bob Smith"')
        self.command('COMMIT "login feature"')
        feature = self.cli.repo.get_head_commit_hash()
        self.command("SWITCH main")
        self.command('COMMIT "main work"')
        main = self.cli.repo.get_head_commit_hash()
        self.assertEqual(self.cli.repo.commits[feature].parents, [root])
        self.assertEqual(self.cli.repo.commits[main].parents, [root])
        self.assertEqual(self.cli.repo.commits[feature].author, "Bob Smith")

        response = self.command("MERGE feature")
        merge_hash = self.cli.repo.get_head_commit_hash()
        self.assertIn(merge_hash, response)
        self.assertEqual(self.cli.repo.commits[merge_hash].parents, [main, feature])
        self.assertEqual(self.cli.repo.inverted_index.search_author("bob smith"),
                         {feature, main, merge_hash})
        order = [commit.hash for commit in topological_sort(self.cli.repo.commits)]
        self.assertLess(order.index(root), order.index(feature))
        self.assertLess(order.index(main), order.index(merge_hash))
        self.assertLess(order.index(feature), order.index(merge_hash))

    def test_identifier_remains_unique_after_init(self):
        with patch("minigit.models.time.time", return_value=123.0):
            self.command("INIT Alice")
            self.command("COMMIT same")
            first = self.cli.repo.get_head_commit_hash()
            self.command("INIT Alice")
            self.command("COMMIT same")
            second = self.cli.repo.get_head_commit_hash()
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith("-1"))
        self.assertTrue(second.endswith("-2"))

    def test_path_tie_no_path_and_ancestors(self):
        commits = {
            "r": Commit("r", "root", "A", 1, []),
            "b": Commit("b", "left", "A", 2, ["r"]),
            "a": Commit("a", "right", "A", 3, ["r"]),
            "z": Commit("z", "merge", "A", 4, ["b", "a"]),
            "x": Commit("x", "other root", "A", 5, []),
        }
        self.assertEqual(find_shortest_path(commits, "r", "z"), ["r", "a", "z"])
        self.assertEqual(find_shortest_path(commits, "b", "a"), ["b", "r", "a"])
        self.assertEqual(find_shortest_path(commits, "r", "x"), None)
        self.assertEqual(find_shortest_path(commits, "z", "z"), ["z"])
        self.assertEqual(set(find_ancestors(commits, "z")), {"r", "a", "b"})
        self.assertEqual(find_ancestors(commits, "r"), [])

    def test_cli_no_path_between_two_roots(self):
        self.command("INIT Alice")
        self.command("BRANCH spare")
        self.command("COMMIT first")
        first = self.cli.repo.get_head_commit_hash()
        self.command("SWITCH spare")
        self.command("COMMIT second")
        second = self.cli.repo.get_head_commit_hash()
        self.assertEqual(self.command(f"PATH {first} {second}"), "No path")

    def test_search_exact_word_phrase_author_and_order(self):
        with patch("minigit.models.time.time", side_effect=[10, 20, 30, 40]):
            self.command('INIT "Alice Lee"')
            self.command('COMMIT "Add login feature"')
            first = self.cli.repo.get_head_commit_hash()
            self.command('COMMIT "login new feature"')
            self.command('COMMIT "login feature, later"')
            self.command('USER "Bob Smith"')
            self.command('COMMIT "login feature"')
            last = self.cli.repo.get_head_commit_hash()

        phrase = self.command('SEARCH "login feature"')
        self.assertIn(first, phrase)
        self.assertIn(last, phrase)
        self.assertLess(phrase.index(first), phrase.index(last))
        self.assertNotIn("login new feature", phrase)
        self.assertNotIn("feature, later", phrase)
        self.assertIn("Found 4 commit(s)", self.command("SEARCH login"))
        author = self.command('SEARCH --author="Alice Lee"')
        self.assertIn("Found 3 commit(s)", author)
        self.assertIn("Found 1 commit(s)", self.command('SEARCH --author="Bob Smith"'))
        self.assertIn("No commits found", self.command("SEARCH missing"))

    def test_log_orders_and_sort_stability(self):
        with patch("minigit.models.time.time", side_effect=[30, 10, 20]):
            self.command("INIT Zoe")
            self.command("COMMIT one")
            one = self.cli.repo.get_head_commit_hash()
            self.command("USER Amy")
            self.command("COMMIT two")
            two = self.cli.repo.get_head_commit_hash()
            self.command("COMMIT three")
            three = self.cli.repo.get_head_commit_hash()
        basic = self.command("LOG")
        by_date = self.command("LOG --sort-by=date")
        by_author = self.command("LOG --sort-by=author")
        self.assertLess(basic.index(one), basic.index(two))
        self.assertLess(basic.index(two), basic.index(three))
        self.assertLess(by_date.index(two), by_date.index(three))
        self.assertLess(by_date.index(three), by_date.index(one))
        self.assertLess(by_author.index(two), by_author.index(three))
        self.assertLess(by_author.index(three), by_author.index(one))

        items = [("first", 1), ("second", 1), ("third", 0)]
        expected = [("third", 0), ("first", 1), ("second", 1)]
        self.assertEqual(merge_sort(items, lambda item: item[1]), expected)
        self.assertEqual(quick_sort(items, lambda item: item[1]), expected)
        self.assertEqual(items[0], ("first", 1))

    def test_strict_input_and_windows_paths(self):
        with self.assertRaises(ValueError):
            self.cli.parse_input('COMMIT "unfinished')
        self.assertEqual(
            self.cli.parse_input(r'DIFF C:\tmp\one.txt C:\tmp\two.txt'),
            ["DIFF", r"C:\tmp\one.txt", r"C:\tmp\two.txt"],
        )
        self.assertEqual(
            self.cli.parse_input(r'DIFF "C:\my files\one.txt" "C:\my files\two.txt"'),
            ["DIFF", r"C:\my files\one.txt", r"C:\my files\two.txt"],
        )
        self.assertIn("Invalid args", self.command("INIT Alice ignored"))
        self.command("INIT Alice")
        self.command("COMMIT one")
        for line in (
            "BRANCH feature extra", "SWITCH main extra", "COMMIT two words",
            "USER Bob Smith",
            "LOG --bad", "LOG --sort-by=date extra", "PATH only",
            "ANCESTORS a b", "SEARCH --author=", "SEARCH hello world",
            "MERGE main extra", "DIFF one", "BENCHMARK extra", "STATUS extra",
            "HELP extra",
        ):
            with self.subTest(line=line):
                self.assertIn("Invalid", self.command(line))

        output = io.StringIO()
        with patch("builtins.input", side_effect=["QUIT extra", 'COMMIT "unfinished', "quit"]):
            with contextlib.redirect_stdout(output):
                self.cli.run()
        self.assertEqual(output.getvalue().count("Error: Invalid args"), 2)
        self.assertIn("Goodbye!", output.getvalue())

    def test_diff_and_file_errors(self):
        self.assertEqual(
            compute_diff(["same", "old"], ["same", "new"])[0], (" ", "same")
        )
        with tempfile.TemporaryDirectory() as folder:
            old = Path(folder) / "old.txt"
            new = Path(folder) / "new.txt"
            invalid = Path(folder) / "invalid.txt"
            old.write_text("same\nold\n", encoding="utf-8")
            new.write_text("same\nnew\n", encoding="utf-8")
            invalid.write_bytes(b"\xff")
            result = diff_files(str(old), str(new))
            self.assertIn("- old", result)
            self.assertIn("+ new", result)
            self.assertIn("1 unchanged line(s)", result)
            self.assertIn("2 unchanged line(s)", diff_files(str(old), str(old)))
            self.assertIn("File not found", diff_files(str(old), str(old) + ".missing"))
            self.assertIn("Error reading", diff_files(str(invalid), str(new)))

    def test_benchmark_small_input(self):
        result = benchmark_sorts([3, 10])
        self.assertIn("merge", result)
        self.assertIn("quick", result)
        self.assertIn("       3 |", result)
        self.assertIn("      10 |", result)

    def test_empty_execute_and_repository_args_preserve_state(self):
        self.assertIn("Invalid args", self.cli.execute([]))
        self.command("INIT Alice")
        self.command("COMMIT start")
        first = self.cli.repo.get_head_commit_hash()
        for command in ("INIT", "COMMIT", "USER", "BRANCH", "SWITCH", "MERGE"):
            for args in ([], ["one", "two"]):
                with self.subTest(command=command, args=args):
                    self.assertIn("Invalid args", self.cli.execute([command] + args))
                    self.assertEqual(self.cli.repo.get_head_commit_hash(), first)
                    self.assertEqual(self.cli.repo.branches, {"main": first})
                    self.assertEqual(self.cli.repo.current_user, "Alice")
                    self.assertEqual(len(self.cli.repo.commits), 1)

    def test_repl_recovers_from_nul_path_and_escapes_output(self):
        message = "\x1b[2J\x9b31mhidden"
        inputs = ['DIFF "bad\0path" other.txt', "INIT Alice", f'COMMIT "{message}"', "LOG", "quit"]
        output = io.StringIO()
        with patch("builtins.input", side_effect=inputs):
            with contextlib.redirect_stdout(output):
                self.cli.run()
        displayed = output.getvalue()
        self.assertIn("Error reading", displayed)
        self.assertIn("Goodbye!", displayed)
        self.assertNotIn("\x1b", displayed)
        self.assertNotIn("\x9b", displayed)
        self.assertIn("\\x1b[2J\\x9b31mhidden", displayed)
        commit = self.cli.repo.commits[self.cli.repo.get_head_commit_hash()]
        self.assertEqual(commit.message, message)

    def test_diff_repl_escapes_file_controls(self):
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "old.txt"
            second = Path(folder) / "new.txt"
            first.write_text("same\n", encoding="utf-8")
            second.write_text("same\n\x1b[2Jhidden\n", encoding="utf-8")
            output = io.StringIO()
            with patch("builtins.input", side_effect=[f'DIFF "{first}" "{second}"', "quit"]):
                with contextlib.redirect_stdout(output):
                    self.cli.run()
            self.assertIn("+ \\x1b[2Jhidden", output.getvalue())
            self.assertNotIn("\x1b", output.getvalue())

    def test_diff_file_and_lcs_limits(self):
        with patch("minigit.constants.ConfigConstants.MAX_DIFF_CELLS", 12):
            table = compute_lcs_table(["a", "b"], ["a", "b", "c"])
            self.assertEqual(table[-1][-1], 2)
            with self.assertRaises(DiffLimitError):
                compute_lcs_table(["a", "b", "c"], ["a", "b", "c"])
            with tempfile.TemporaryDirectory() as folder:
                first = Path(folder) / "first.txt"
                second = Path(folder) / "second.txt"
                first.write_text("a\nb\nc\n", encoding="utf-8")
                second.write_text("a\nb\nc\n", encoding="utf-8")
                self.assertIn("LCS table needs 16 cells", diff_files(str(first), str(second)))
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "first.txt"
            second = Path(folder) / "second.txt"
            first.write_bytes(b"abcdefgh")
            second.write_bytes(b"abcdefgh")
            with patch("minigit.constants.ConfigConstants.MAX_DIFF_FILE_BYTES", 8):
                self.assertIn("1 unchanged line", diff_files(str(first), str(second)))
                second.write_bytes(b"abcdefghi")
                self.assertIn("8-byte file limit", diff_files(str(first), str(second)))

    def test_path_string_order_against_all_shortest_paths(self):
        # 모든 4노드 DAG에서 독립적으로 단순 경로를 열거해 결과를 대조한다.
        names = ["s", "a", "a!", "t"]
        edges = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
        for mask in range(1 << len(edges)):
            commits = {}
            adjacency = {name: [] for name in names}
            for index, name in enumerate(names):
                commits[name] = Commit(name, name, "Alice", index, [])
            for bit, (parent, child) in enumerate(edges):
                if mask & (1 << bit):
                    commits[names[child]].parents.append(names[parent])
                    adjacency[names[parent]].append(names[child])
                    adjacency[names[child]].append(names[parent])
            for start in names:
                for target in names:
                    paths = []
                    pending = [[start]]
                    while pending:
                        path = pending.pop()
                        if path[-1] == target:
                            paths.append(path)
                            continue
                        for neighbor in adjacency[path[-1]]:
                            if neighbor not in path:
                                pending.append(path + [neighbor])
                    expected = min(paths, key=lambda path: (len(path), "->".join(path)), default=None)
                    with self.subTest(mask=mask, start=start, target=target):
                        self.assertEqual(find_shortest_path(commits, start, target), expected)

    def test_path_reserved_separator(self):
        commits = {"s": Commit("s", "root", "A", 1, []),
                   "a->b": Commit("a->b", "child", "A", 2, ["s"])}
        with self.assertRaisesRegex(ValueError, "path separator"):
            find_shortest_path(commits, "s", "a->b")


if __name__ == "__main__":
    unittest.main()
