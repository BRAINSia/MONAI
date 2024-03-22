# Copyright (c) MONAI Consortium
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import argparse
import inspect
import os
import re
import sys
import time
import unittest
from pathlib import Path

from monai.utils import PerfContext
import html

results: dict = {}
failed_tests: dict = {}
passed_tests: list = []

monai_src_root: Path = Path(__file__).parent.parent


def check_python_version() -> (bool, str):
    required_python = ["3.8", "3.9", "3.10"]
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if current_version not in required_python:
        return False, (
            f"Warning: Your Python version {current_version} is not supported.\n"
            f"Supported versions: {required_python}"
        )
    return True, ""


def colorize_traceback(formatted_tb):

    # Start the HTML content
    html_content = (
        '<div style="font-family: monospace; background-color: #f9f9f9; padding: 10px; border: 1px solid #ccc;">'
    )

    # Add each line of the traceback with color coding
    for line in formatted_tb.split("\n"):
        line = html.escape(line)
        if "File" in line and "line" in line:
            html_content += f'<span style="color: blue;">{line}</span><br>'
        elif "Error" in line or "Exception" in line:
            html_content += f'<span style="color: red; font-weight: bold;">{line}</span><br>'
        else:
            html_content += f"<span>{line}</span><br>"

    # Close the HTML content
    html_content += "</div>"

    return html_content


class TimeLoggingTestResult(unittest.TextTestResult):
    """Overload the default results so that we can store the results."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timed_tests = {}

    def startTest(self, test):  # noqa: N802
        """Start timer, print test name, do normal test."""
        self.start_time = time.time()
        name = self.getDescription(test)
        self.stream.write(f"Starting test: {name}...\n")
        super().startTest(test)

    def stopTest(self, test):  # noqa: N802
        """On test end, get time, print, store and do normal behaviour."""
        elapsed = time.time() - self.start_time
        super().stopTest(test)
        name = self.getDescription(test)
        if name in results:
            raise AssertionError(f"expected all keys to be unique: {name} already in use")
        results[name] = elapsed
        self.stream.write(f"Finished test: {name} ({elapsed:.03}s)\n")
        if len(self.failures) > 0 or len(self.errors) > 0:
            all_failure_modes = self.failures + self.errors
            traceback_index = 1
            failed_tests[name] = [f[traceback_index] for f in all_failure_modes]
        else:
            passed_tests.append(name)


def print_results(results, discovery_time, thresh, status):
    # only keep results >= threshold
    filtered_results = dict(filter(lambda x: x[1] > thresh, results.items()))
    if len(filtered_results) > 0:
        print(f"\n\n{status}, printing completed times >{thresh}s in ascending order...\n")
        timings = dict(sorted(filtered_results.items(), key=lambda item: item[1]))

        for r in timings:
            if timings[r] >= thresh:
                print(f"{r} ({timings[r]:.03}s)")
        print(f"test discovery time: {discovery_time:.03}s")
        print(f"total testing time: {sum(filtered_results.values()):.03}s")
        print("Remember to check above times for any errors!")

    num_failed: int = len(failed_tests)
    num_passed: int = len(passed_tests)

    ignored_git_dir: Path = Path(__file__).parent.parent / ".coverage"
    print(f"XXXXXXXXXXXXXXXX ---- {ignored_git_dir}")
    ignored_git_dir.mkdir(exist_ok=True)
    current_date: str = time.strftime("%Y-%m-%d_%H-%M-%S")
    with open(ignored_git_dir / f"testing_outputs_{current_date}.html", "w") as f:
        f.write("<html><head><title>Failed Tests</title></head><body>")
        if num_failed > 0:
            f.write("<h1>Failed Tests</h1>")
            f.write(f"<p>Number of failed tests: {num_failed}</p>")
            for test_name, errors_found in failed_tests.items():
                f.write(f"<h2>{test_name}</h2>")
                f.write(f"<pre>python3.10 -m tests.{test_name}</pre>")
                for e in errors_found:
                    html_content: str = colorize_traceback(e)
                    f.write(f"{html_content}")
        else:
            f.write("<h1>All tests passed!</h1>")
        f.write(f"<p>Number of passed tests: {num_passed}\nNumber of failed tests: {num_failed}</p>")
        f.write("</body></html>")

        # print("*" * 80)
        # print(f"Failed cases: {num_failed}")
        # for test_name, errors_found in failed_tests.items():
        #     print(f"tests.{test_name}")
        #     for e in errors_found:
        #         print("- " * 40)
        #         print(f"{e}")
        #         print("- " * 40)
    print(f"{num_failed} test cases failed, {num_passed} test cases passed, out of {num_failed+num_passed}")


def parse_args():
    parser = argparse.ArgumentParser(description="Runner for MONAI unittests with timing.")
    parser.add_argument(
        "-s", action="store", dest="path", default=".", help="Directory to start discovery (default: '%(default)s')"
    )
    parser.add_argument(
        "-p",
        action="store",
        dest="pattern",
        default="test_*.py",
        help="Pattern to match tests (default: '%(default)s')",
    )
    parser.add_argument(
        "-t",
        "--thresh",
        dest="thresh",
        default=10.0,
        type=float,
        help="Display tests longer than given threshold (default: %(default)d)",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        action="store",
        dest="verbosity",
        type=int,
        default=1,
        help="Verbosity level (default: %(default)d)",
    )
    parser.add_argument("-q", "--quick", action="store_true", dest="quick", default=False, help="Only do quick tests")
    parser.add_argument(
        "-f", "--failfast", action="store_true", dest="failfast", default=False, help="Stop testing on first failure"
    )
    args = parser.parse_args()
    print(f"Running tests in folder: '{args.path}'")
    if args.pattern:
        print(f"With file pattern: '{args.pattern}'")

    return args


def get_default_pattern(loader):
    signature = inspect.signature(loader.discover)
    params = {k: v.default for k, v in signature.parameters.items() if v.default is not inspect.Parameter.empty}
    return params["pattern"]


if __name__ == "__main__":
    # Parse input arguments
    args = parse_args()

    # If quick is desired, set environment variable
    if args.quick:
        os.environ["QUICKTEST"] = "True"

    is_valid_python_version, version_check_msg = check_python_version()
    if not is_valid_python_version:
        print(version_check_msg)
        print("Exiting..., please run the tests with a supported Python version.")
        sys.exit(1)

    # Get all test names (optionally from some path with some pattern)
    with PerfContext() as pc:
        # the files are searched from `tests/` folder, starting with `test_`
        tests_path = Path(__file__).parent / args.path
        files = {
            file.relative_to(tests_path).as_posix()
            for file in tests_path.rglob("test_*py")
            if re.search(args.pattern, file.name[:-3])
        }
        print(files)
        cases = []
        for test_module in tests_path.rglob("test_*py"):
            test_file = str(test_module.relative_to(tests_path).as_posix())
            case_str = test_file.replace("/", ".")[:-3]
            case_str = f"tests.{case_str}"
            if test_file in files:
                cases.append(case_str)
            else:
                print(f"monai test runner: excluding {test_module.name}")
        print(cases)
        tests = unittest.TestLoader().loadTestsFromNames(cases)
    discovery_time = pc.total_time
    print(f"time to discover tests: {discovery_time}s, total cases: {tests.countTestCases()}.")

    test_runner = unittest.runner.TextTestRunner(
        resultclass=TimeLoggingTestResult, verbosity=args.verbosity, failfast=args.failfast
    )
    # Use try catches to print the current results if encountering exception or keyboard interruption
    try:
        test_result = test_runner.run(tests)
        print_results(results, discovery_time, args.thresh, "tests finished")
        sys.exit(not test_result.wasSuccessful())
    except KeyboardInterrupt:
        print_results(results, discovery_time, args.thresh, "tests cancelled")
        sys.exit(1)
    except Exception:
        print_results(results, discovery_time, args.thresh, "exception reached")
        raise
