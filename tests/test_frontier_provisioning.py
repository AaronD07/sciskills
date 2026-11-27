"""Cold Docker startup and ownership for participant admission and sidecars."""

import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from benchmarks.research_review import frontier


class ColdProvisioningTests(unittest.TestCase):
    context = "selected-local-engine"
    task = {"id": "inverse-lithography"}

    def test_probe_and_sidecar_remove_exact_named_container_on_start_timeout(self):
        for operation in ("probe", "sidecar"):
            with (
                self.subTest(operation=operation),
                patch.object(
                    frontier, "_participant_context", return_value=self.context
                ),
                patch.object(
                    frontier,
                    "_docker",
                    return_value=["docker", "--context", self.context],
                ),
                patch.object(
                    frontier,
                    "_read_control",
                    return_value={"environment_image": "env-image"},
                ),
                patch.object(
                    frontier,
                    "command",
                    side_effect=subprocess.TimeoutExpired("docker", 900),
                ) as run,
                patch.object(frontier, "stop") as stop,
            ):
                with self.assertRaises(subprocess.TimeoutExpired):
                    if operation == "probe":
                        frontier.available_memory_mib(self.task)
                    else:
                        frontier._start_sidecar(
                            self.task,
                            "main-id",
                            "fabricator",
                            "service-image",
                            context=self.context,
                        )
                args, options = run.call_args
                self.assertEqual(args[:4], ("docker", "--context", self.context, "run"))
                name = args[args.index("--name") + 1]
                self.assertRegex(name, r"^sciskills-[0-9a-f]{32}$")
                self.assertEqual(options["timeout"], 900)
                stop.assert_called_once_with(name, context=self.context)

    def test_successful_probe_exits_with_automatic_cleanup(self):
        with (
            patch.object(frontier, "_participant_context", return_value=self.context),
            patch.object(
                frontier, "_docker", return_value=["docker", "--context", self.context]
            ),
            patch.object(
                frontier,
                "_read_control",
                return_value={"environment_image": "env-image"},
            ),
            patch.object(
                frontier,
                "command",
                return_value=SimpleNamespace(stdout="MemAvailable: 4096 kB\n"),
            ) as run,
            patch.object(frontier, "stop") as stop,
        ):
            self.assertEqual(frontier.available_memory_mib(self.task), 4)
            self.assertIn("--rm", run.call_args.args)
            self.assertEqual(run.call_args.args[-2:], ("env-image", "/proc/meminfo"))
            stop.assert_not_called()

    def test_sidecar_health_check_targets_its_owner_engine(self):
        with (
            patch.object(frontier, "_auxiliary_container") as start,
            patch.object(
                frontier, "_root_exec", return_value=SimpleNamespace(returncode=0)
            ) as health,
        ):
            frontier._start_sidecar(
                self.task,
                "main-id",
                "fabricator",
                "service-image",
                context=self.context,
            )
            self.assertEqual(start.call_args.args[0], self.context)
            self.assertIn("container:main-id", start.call_args.args)
            self.assertIn("sciskills.sidecar-for=main-id", start.call_args.args)
            self.assertEqual(health.call_args.kwargs["context"], self.context)

    def test_temporary_container_pins_owner_for_exception_cleanup(self):
        with (
            patch.object(
                frontier, "_participant_context", return_value=self.context
            ) as current,
            patch.object(frontier, "start", return_value="temporary-id") as start,
            patch.object(frontier, "stop") as stop,
        ):
            with self.assertRaisesRegex(RuntimeError, "work interrupted"):
                with frontier.temporary_container(self.task):
                    current.return_value = "another-engine"
                    raise RuntimeError("work interrupted")
            current.assert_called_once_with()
            self.assertEqual(start.call_args.kwargs["context"], self.context)
            stop.assert_called_once_with("temporary-id", context=self.context)
