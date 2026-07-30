import json
import importlib.util
import os
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
GIG_ROOT = ROOT / "skills" / "earn" / "gig"
RUNNER = ROOT / "runtime" / "agent-runner" / "agent_runner.py"
CONFIG = ROOT / "runtime" / "agent-runner" / "config.json"
GIG_PASS = GIG_ROOT / "gig_pass.sh"


class AgentRunnerContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.prompt = self.root / "prompt.txt"
        self.prompt.write_text("Return contract JSON only.\n", encoding="utf-8")
        self.schema = self.root / "schema.json"
        self.schema.write_text(json.dumps({
            "type": "object",
            "required": ["status", "evidence"],
            "properties": {
                "status": {"const": "ok"},
                "evidence": {"type": "array", "minItems": 1},
            },
        }), encoding="utf-8")

    def write_executable(self, name, body):
        path = self.bin / name
        path.write_text("#!/usr/bin/env bash\nset -u\n" + body, encoding="utf-8")
        path.chmod(0o755)
        return path

    def test_local_validator_accepts_strict_nullable_types(self):
        sys.path.insert(0, str(RUNNER.parent))
        self.addCleanup(lambda: sys.path.remove(str(RUNNER.parent)))
        spec = importlib.util.spec_from_file_location("agent_runner_nullable", RUNNER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        schema = {
            "type": "object",
            "required": ["eligible_count", "applications"],
            "properties": {
                "eligible_count": {"type": ["integer", "null"]},
                "applications": {
                    "type": ["array", "null"],
                    "items": {"type": "object"},
                },
            },
        }
        self.assertEqual(
            runner.validate_schema(
                {"eligible_count": 0, "applications": None},
                schema,
            ),
            [],
        )

    def write_config(self, candidates, timeout=2):
        path = self.root / "config.json"
        path.write_text(json.dumps({
            "version": 1,
            "task_classes": {
                "deterministic": {"candidates": []},
                "composition-agent": {"candidates": candidates},
                "repeatable-agent": {"candidates": candidates},
                "tool-agent": {"candidates": candidates},
                "high-value-agent": {"candidates": candidates},
            },
            "providers": {
                "claude": {"executable": "claude"},
                "codex": {"executable": "codex"},
                "openclaw": {"executable": "openclaw", "agent": "anicca"},
            },
            "timeout_seconds": timeout,
        }), encoding="utf-8")
        return path

    def run_runner(self, config, task_class="repeatable-agent", extra_env=None, extra_args=None,
                   workdir=None):
        evidence = self.root / "evidence"
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env['PATH']}"
        env["AGENT_RUNNER_CONFIG"] = str(config)
        env["ANICCA_USAGE_LEDGER"] = str(self.root / "agent-usage.jsonl")
        env.update(extra_env or {})
        command = [
            "python3", str(RUNNER), "--task-class", task_class,
            "--prompt-file", str(self.prompt), "--schema", str(self.schema),
            "--evidence-dir", str(evidence), "--task-label", "fixture",
            "--loop", "fixture-loop",
            "--workdir", str(workdir or self.root),
        ]
        command.extend(extra_args or [])
        proc = subprocess.run(command, env=env, text=True, capture_output=True)
        return proc, evidence

    def test_business_script_passes_task_class_only_and_models_stay_in_runner_config(self):
        gig = GIG_PASS.read_text(encoding="utf-8")
        config = CONFIG.read_text(encoding="utf-8")
        self.assertIn("agent_runner.py", gig)
        self.assertNotRegex(gig, r"gpt-5\.|sonnet|--model|-m[ =]")
        for task_class in ("deterministic", "composition-agent", "repeatable-agent", "tool-agent", "high-value-agent"):
            self.assertIn(task_class, config)
        for model in ("gpt-5.6-luna", "gpt-5.6-terra"):
            self.assertIn(model, config)
        self.assertIn("gpt-5.6-sol", config)
        production_config = json.loads(config)
        self.assertEqual(
            production_config["providers"]["claude"]["executable_fallbacks"],
            ["~/.local/bin/claude"],
        )
        self.assertEqual(
            production_config["providers"]["claude"]["base_url"],
            "http://127.0.0.1:8317",
        )
        self.assertEqual(
            production_config["providers"]["claude"]["auth_token_file"],
            "~/.cli-proxy-api-key",
        )
        self.assertEqual(
            production_config["providers"]["codex"]["automation_home"],
            "~/.local/state/life-manager/codex-runner",
        )
        self.assertEqual(
            production_config["providers"]["codex"]["auth_file"],
            "~/.codex/auth.json",
        )
        self.assertEqual(
            production_config["providers"]["codex"]["ssl_cert_file"],
            "/etc/ssl/cert.pem",
        )
        self.assertEqual(
            production_config["providers"]["codex"]["project_doc_max_bytes"], 0,
        )
        self.assertEqual(
            production_config["providers"]["codex"]["disabled_skills"],
            ["imagegen", "openai-docs", "plugin-creator", "skill-creator", "skill-installer"],
        )
        self.assertEqual(
            production_config["providers"]["codex"]["disabled_features"],
            [
                "apps", "auth_elicitation", "browser_use", "browser_use_external",
                "browser_use_full_cdp_access", "computer_use", "goals", "hooks",
                "image_generation", "in_app_browser", "multi_agent", "plugins",
                "remote_plugin", "tool_call_mcp_elicitation", "tool_suggest",
                "workspace_dependencies",
            ],
        )
        production = "\n".join((GIG_ROOT / name).read_text(encoding="utf-8") for name in (
            "gig_pass.sh", "gig-cli.sh", "gig_reality_verify.sh", "auditor.sh",
        ))
        self.assertNotRegex(production, r"command -v claude|\$CLAUDE|claude\s+-p|--model\s+sonnet")

        step_schema = json.loads((GIG_ROOT / "schemas" / "gig_step_result.schema.json").read_text())
        self.assertEqual(step_schema["properties"]["status"]["type"], "string")
        self.assertEqual(step_schema["properties"]["status"]["const"], "ok")
        verdict_schema = json.loads((GIG_ROOT / "schemas" / "gig_reality_verdict.schema.json").read_text())
        self.assertEqual(set(verdict_schema["required"]), set(verdict_schema["properties"]))

    def test_every_shared_runner_call_has_explicit_loop_attribution(self):
        expected = {
            GIG_ROOT / "gig_pass.sh": "gig",
            GIG_ROOT / "gig_reality_verify.sh": "gig",
            GIG_ROOT / "scripts" / "reply_composer.py": "gig",
            ROOT / "skills" / "life-manager" / "life-manager-daily.sh": "life-manager",
        }
        for script, loop in expected.items():
            with self.subTest(script=script):
                text = script.read_text(encoding="utf-8")
                self.assertGreater(text.count("--task-label"), 0)
                self.assertEqual(text.count("--loop"), text.count("--task-label"))
                self.assertIn(loop, text)

    def test_production_config_is_gpt_first_for_every_agent_class(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        expected_models = {
            "composition-agent": "gpt-5.6-terra",
            "repeatable-agent": "gpt-5.6-luna",
            "tool-agent": "gpt-5.6-terra",
            "diagnostic-agent": "gpt-5.6-luna",
            "marketing-agent": "gpt-5.6-luna",
            "high-value-agent": "gpt-5.6-luna",
            "escalation-agent": "gpt-5.6-sol",
        }
        expected_reservations = {
            "composition-agent": 16384,
            "tool-agent": 24576,
            "repeatable-agent": 32768,
            "diagnostic-agent": 32768,
            "marketing-agent": 49152,
            "high-value-agent": 65536,
            "escalation-agent": 65536,
        }
        for task_class, expected_model in expected_models.items():
            with self.subTest(task_class=task_class):
                candidates = config["task_classes"][task_class]["candidates"]
                self.assertEqual(candidates[0]["provider"], "codex")
                self.assertEqual(candidates[0]["model"], expected_model)
                self.assertEqual(
                    config["task_classes"][task_class]["token_reservation"],
                    expected_reservations[task_class],
                )
                if task_class == "composition-agent":
                    self.assertEqual(
                        [(row["provider"], row["model"]) for row in candidates],
                        [
                            ("codex", "gpt-5.6-terra"),
                            ("claude-direct", "sonnet"),
                        ],
                    )
                elif task_class == "repeatable-agent":
                    self.assertEqual(
                        [(row["provider"], row["model"]) for row in candidates],
                        [
                            ("codex", "gpt-5.6-luna"),
                            ("claude-direct", "sonnet"),
                        ],
                    )
                    self.assertEqual(
                        config["task_classes"]["repeatable-agent"]["timeout_seconds"],
                        90,
                    )
                elif task_class == "tool-agent":
                    self.assertEqual(
                        [(row["provider"], row["model"]) for row in candidates],
                        [
                            ("codex", "gpt-5.6-terra"),
                            ("claude-direct", "sonnet"),
                        ],
                    )
                    self.assertEqual(
                        config["task_classes"]["tool-agent"]["timeout_seconds"],
                        180,
                    )
        high_value = config["task_classes"]["high-value-agent"]["candidates"]
        self.assertEqual(
            [(row["provider"], row["model"]) for row in high_value],
            [
                ("codex", "gpt-5.6-luna"),
                ("claude-direct", "sonnet"),
            ],
        )
        self.assertEqual(high_value[0]["effort"], "medium")
        self.assertEqual(config["task_classes"]["high-value-agent"]["timeout_seconds"], 900)
        for task_class, route in config["task_classes"].items():
            for candidate in route["candidates"]:
                restricted = (
                    candidate.get("effort") == "high"
                    or "sol" in str(candidate.get("model") or "").lower()
                )
                if restricted:
                    self.assertEqual(task_class, "escalation-agent")
                    self.assertTrue(route["requires_explicit_escalation"])
        self.assertTrue(
            config["providers"]["openclaw"]["model_capabilities"]
            ["openai/gpt-5.4"]["tool_write"]
        )
        self.assertNotIn(
            "google/gemini-3.1-pro-preview",
            config["providers"]["openclaw"]["model_capabilities"],
        )
        profile = config["candidate_profiles"]["gig-paid-builder"]
        self.assertEqual(profile["task_class"], "high-value-agent")
        self.assertEqual(profile["openclaw"]["agent"], "gig-paid-builder")
        self.assertEqual(profile["openclaw"]["sandbox"], {
            "mode": "all",
            "workspaceAccess": "rw",
            "workspace": "~/gig/projects",
            "containerWorkspace": "/workspace",
            "sessionIsSandboxed": True,
            "elevated": False,
            "execHost": "sandbox",
        })

    def test_application_lane_gets_an_hour_while_other_browser_lanes_stay_bounded(self):
        """The two jobs that shared tool-agent want opposite bounds.

        Measured 2026-07-27: the apply lane's attempt ran 174s against Coconala and was
        killed as transient_timeout with 289KB of progress already on stdout. Delivery,
        at 900s, completed; applications, at 180s, ran five times in a week.

        Measured 2026-07-29: after the search contract expanded to newest + 27
        categories + keyword/pagination, the lane had only traversed the first category
        after three minutes. A shared 900-second browser timeout cannot honestly promise
        exhaustive search. B2 therefore owns a longer route while B0/B1/profile retain
        the existing bound and the auditor stays short.
        """
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.assertGreaterEqual(
            config["task_classes"]["browser-lane-agent"]["timeout_seconds"], 900
        )
        self.assertGreaterEqual(
            config["task_classes"]["application-lane-agent"]["timeout_seconds"], 3600
        )
        self.assertLessEqual(config["task_classes"]["tool-agent"]["timeout_seconds"], 180)

        pass_source = GIG_PASS.read_text(encoding="utf-8")
        for label in ("B0", "PROFILE", "B1"):
            self.assertIn(f'step "{label}" "browser-lane-agent"', pass_source)
        self.assertIn('lane_step "B2" "application-lane-agent"', pass_source)
        self.assertIn(
            "--task-class tool-agent",
            (GIG_ROOT / "gig_reality_verify.sh").read_text(encoding="utf-8"),
        )

    def test_reality_auditor_uses_bounded_route_without_openclaw(self):
        source = (GIG_ROOT / "gig_reality_verify.sh").read_text(encoding="utf-8")
        self.assertIn("--task-class tool-agent", source)
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        route = config["task_classes"]["tool-agent"]
        self.assertLessEqual(route["timeout_seconds"], 180)
        self.assertNotIn("openclaw", {row["provider"] for row in route["candidates"]})
        self.assertIn('--candidate-profile "gig-paid-builder"', GIG_PASS.read_text())

    def test_paid_openclaw_profile_fails_closed_when_dedicated_agent_is_missing(self):
        invoked = self.root / "paid-openclaw-invoked"
        agents = {"list": []}
        self.write_executable(
            "openclaw",
            "if [ \"${1:-}\" = config ]; then\n"
            f"  printf '%s\\n' {shlex.quote(json.dumps(agents))}\n"
            "  exit 0\n"
            "fi\n"
            f"touch {shlex.quote(str(invoked))}\nexit 99\n",
        )
        config = self.write_config([{
            "provider": "openclaw",
            "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        value["candidate_profiles"] = {
            "gig-paid-builder": {
                "task_class": "high-value-agent",
                "openclaw": {
                    "agent": "gig-paid-builder",
                    "sandbox": {
                        "mode": "all", "workspaceAccess": "rw", "workspace": str(self.root),
                        "containerWorkspace": "/workspace", "sessionIsSandboxed": True,
                        "elevated": False, "execHost": "sandbox",
                    },
                },
            },
        }
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(
            config,
            task_class="high-value-agent",
            extra_args=["--candidate-profile", "gig-paid-builder"],
        )

        self.assertNotEqual(proc.returncode, 0)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertIn("openclaw paid sandbox preflight failed", attempt["adapter_error"])
        self.assertFalse(attempt["sandbox_preflight"]["verified"])
        self.assertFalse(invoked.exists())

    def test_paid_openclaw_profile_fails_closed_on_workspace_mismatch(self):
        invoked = self.root / "workspace-mismatch-invoked"
        agents = {"list": [{
            "id": "gig-paid-builder",
            "workspace": str(self.root / "wrong-workspace"),
            "sandbox": {"mode": "all", "workspaceAccess": "rw"},
            "tools": {"elevated": {"enabled": False}, "exec": {"host": "sandbox"}},
        }]}
        self.write_executable(
            "openclaw",
            "if [ \"${1:-}\" = config ]; then\n"
            f"  printf '%s\\n' {shlex.quote(json.dumps(agents))}\n"
            "  exit 0\n"
            "fi\n"
            f"touch {shlex.quote(str(invoked))}\nexit 99\n",
        )
        config = self.write_config([{
            "provider": "openclaw", "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        value["candidate_profiles"] = {
            "gig-paid-builder": {
                "task_class": "high-value-agent",
                "openclaw": {
                    "agent": "gig-paid-builder",
                    "sandbox": {
                        "mode": "all", "workspaceAccess": "rw", "workspace": str(self.root),
                        "containerWorkspace": "/workspace", "sessionIsSandboxed": True,
                        "elevated": False, "execHost": "sandbox",
                    },
                },
            },
        }
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(
            config, task_class="high-value-agent",
            extra_args=["--candidate-profile", "gig-paid-builder"],
        )

        self.assertNotEqual(proc.returncode, 0)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertIn("workspace mismatch", attempt["adapter_error"])
        self.assertFalse(attempt["sandbox_preflight"]["verified"])
        self.assertFalse(invoked.exists())

    def test_paid_openclaw_profile_fails_closed_when_effective_mode_is_off(self):
        invoked = self.root / "mode-off-invoked"
        agents = {"list": [{
            "id": "gig-paid-builder", "workspace": str(self.root),
            "sandbox": {"mode": "all", "workspaceAccess": "rw"},
            "tools": {"elevated": {"enabled": False}, "exec": {"host": "sandbox"}},
        }]}
        explain = {
            "agentId": "gig-paid-builder",
            "sandbox": {"mode": "off", "workspaceAccess": "rw", "sessionIsSandboxed": False},
            # A global feature switch may remain on; this dedicated agent is
            # safe only because its row explicitly disables elevated and the
            # effective allow decisions are both false.
            "elevated": {"enabled": True, "allowedByConfig": False,
                         "alwaysAllowedByConfig": False},
        }
        self.write_executable(
            "openclaw",
            "if [ \"${1:-}\" = config ]; then\n"
            f"  printf '%s\\n' {shlex.quote(json.dumps(agents))}\n  exit 0\n"
            "fi\n"
            "if [ \"${1:-}\" = sandbox ] && [ \"${2:-}\" = explain ]; then\n"
            f"  printf '%s\\n' {shlex.quote(json.dumps(explain))}\n  exit 0\n"
            "fi\n"
            f"touch {shlex.quote(str(invoked))}\nexit 99\n",
        )
        config = self.write_config([{
            "provider": "openclaw", "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        value["candidate_profiles"] = {
            "gig-paid-builder": {"task_class": "high-value-agent", "openclaw": {
                "agent": "gig-paid-builder", "sandbox": {
                    "mode": "all", "workspaceAccess": "rw", "workspace": str(self.root),
                    "containerWorkspace": "/workspace", "sessionIsSandboxed": True,
                    "elevated": False, "execHost": "sandbox",
                },
            }},
        }
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(
            config, task_class="high-value-agent",
            extra_args=["--candidate-profile", "gig-paid-builder"],
        )

        self.assertNotEqual(proc.returncode, 0)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertIn("sandbox mode mismatch", attempt["adapter_error"])
        self.assertFalse(attempt["sandbox_preflight"]["verified"])
        self.assertFalse(invoked.exists())

    def test_paid_openclaw_profile_rejects_elevated_or_host_exec_escape(self):
        for unsafe_tools, expected_error in (
            ({"elevated": {"enabled": True}, "exec": {"host": "sandbox"}}, "elevated"),
            ({"elevated": {"enabled": False}, "exec": {"host": "gateway"}}, "exec host"),
        ):
            with self.subTest(unsafe_tools=unsafe_tools):
                invoked = self.root / (expected_error.replace(" ", "-") + "-invoked")
                agents = {"list": [{
                    "id": "gig-paid-builder", "workspace": str(self.root),
                    "sandbox": {"mode": "all", "workspaceAccess": "rw"},
                    "tools": unsafe_tools,
                }]}
                self.write_executable(
                    "openclaw",
                    "if [ \"${1:-}\" = config ]; then\n"
                    f"  printf '%s\\n' {shlex.quote(json.dumps(agents))}\n  exit 0\n"
                    "fi\n"
                    f"touch {shlex.quote(str(invoked))}\nexit 99\n",
                )
                config = self.write_config([{
                    "provider": "openclaw", "model": "google/gemini-3.1-pro-preview",
                    "required_capabilities": ["tool_write"],
                }])
                value = json.loads(config.read_text())
                value["providers"]["openclaw"]["model_capabilities"] = {
                    "google/gemini-3.1-pro-preview": {"tool_write": True},
                }
                value["candidate_profiles"] = {
                    "gig-paid-builder": {"task_class": "high-value-agent", "openclaw": {
                        "agent": "gig-paid-builder", "sandbox": {
                            "mode": "all", "workspaceAccess": "rw", "workspace": str(self.root),
                            "containerWorkspace": "/workspace", "sessionIsSandboxed": True,
                            "elevated": False, "execHost": "sandbox",
                        },
                    }},
                }
                config.write_text(json.dumps(value))

                proc, evidence = self.run_runner(
                    config, task_class="high-value-agent",
                    extra_args=["--candidate-profile", "gig-paid-builder"],
                )

                self.assertNotEqual(proc.returncode, 0)
                attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
                self.assertIn(expected_error, attempt["adapter_error"])
                self.assertFalse(attempt["sandbox_preflight"]["verified"])
                self.assertFalse(invoked.exists())

    def test_paid_openclaw_profile_selects_dedicated_verified_sandbox_agent(self):
        selected_agent = self.root / "selected-agent"
        selected_message = self.root / "selected-message"
        workspace = self.root / "projects"
        project_root = workspace / "5167108"
        project_root.mkdir(parents=True)
        self.prompt.write_text(
            f"Work only inside PROJECT_ROOT={project_root}. Stable project root: {project_root}.\n",
            encoding="utf-8",
        )
        agents = {"list": [{
            "id": "gig-paid-builder",
            "workspace": str(workspace),
            "sandbox": {"mode": "all", "workspaceAccess": "rw"},
            "tools": {"elevated": {"enabled": False}, "exec": {"host": "sandbox"}},
        }]}
        explain = {
            "agentId": "gig-paid-builder",
            "sandbox": {"mode": "all", "workspaceAccess": "rw", "sessionIsSandboxed": True},
            "elevated": {"enabled": True, "allowedByConfig": False,
                         "alwaysAllowedByConfig": False},
        }
        wrapper = {
            "result": {
                "payloads": [{"text": '{"status":"ok","evidence":["sandboxed"]}'}],
                "meta": {"toolSummary": {"calls": 1, "tools": ["write"], "failures": 0}},
            },
        }
        self.write_executable(
            "openclaw",
            "if [ \"${1:-}\" = config ]; then\n"
            f"  printf '%s\\n' {shlex.quote(json.dumps(agents))}\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"${1:-}\" = sandbox ] && [ \"${2:-}\" = explain ]; then\n"
            f"  printf '%s\\n' {shlex.quote(json.dumps(explain))}\n"
            "  exit 0\n"
            "fi\n"
            "while [ $# -gt 0 ]; do\n"
            f"  if [ \"$1\" = --agent ]; then shift; printf '%s' \"$1\" > {shlex.quote(str(selected_agent))}; fi\n"
            f"  if [ \"$1\" = --message ]; then shift; printf '%s' \"$1\" > {shlex.quote(str(selected_message))}; fi\n"
            "  shift || true\n"
            "done\n"
            f"printf '%s\\n' {shlex.quote(json.dumps(wrapper))}\n",
        )
        config = self.write_config([{
            "provider": "openclaw",
            "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        value["candidate_profiles"] = {
            "gig-paid-builder": {
                "task_class": "high-value-agent",
                "openclaw": {
                    "agent": "gig-paid-builder",
                    "sandbox": {
                        "mode": "all", "workspaceAccess": "rw", "workspace": str(workspace),
                        "containerWorkspace": "/workspace", "sessionIsSandboxed": True,
                        "elevated": False, "execHost": "sandbox",
                    },
                },
            },
        }
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(
            config,
            task_class="high-value-agent",
            extra_args=["--candidate-profile", "gig-paid-builder"],
            workdir=project_root,
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertTrue(attempt["sandbox_preflight"]["verified"])
        self.assertEqual(attempt["sandbox_preflight"]["sandbox_project_root"], "/workspace/5167108")
        self.assertEqual(selected_agent.read_text(), "gig-paid-builder")
        message = selected_message.read_text()
        self.assertIn(f"PROJECT_ROOT={project_root}", message)
        self.assertIn("Workdir: /workspace/5167108", message)
        self.assertIn("Sandbox tool project root: /workspace/5167108", message)
        self.assertIn(f"Host-canonical project root: {project_root.resolve()}", message)
        self.assertIn("every path field MUST use the host-canonical project root, never /workspace", message)

    def test_missing_model_tool_write_capability_fails_closed_before_provider_launch(self):
        openclaw_marker = self.root / "unproven-openclaw-invoked"
        self.write_executable(
            "openclaw",
            f"touch '{openclaw_marker}'\n"
            "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"fictional-path\\\"]}\"}]}}'\n",
        )
        config = self.write_config([{
            "provider": "openclaw",
            "model": "blockrun/free",
            "required_capabilities": ["tool_write"],
        }])
        proc, evidence = self.run_runner(config, task_class="high-value-agent")
        self.assertNotEqual(proc.returncode, 0)
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["provider"], "openclaw")
        self.assertEqual(attempts[0]["error_class"], "validation_or_task_failure")
        self.assertIn("missing required model capabilities: tool_write", attempts[0]["adapter_error"])
        self.assertFalse(attempts[0]["result_present"])
        self.assertFalse(openclaw_marker.exists())

    def test_static_tool_write_capability_without_runtime_tool_summary_fails_closed(self):
        openclaw_marker = self.root / "static-only-openclaw-invoked"
        self.write_executable(
            "openclaw",
            f"touch '{openclaw_marker}'\n"
            "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"real-domain-validator-next\\\"]}\"}]}}'\n",
        )
        config = self.write_config([{
            "provider": "openclaw",
            "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        config.write_text(json.dumps(value))
        proc, evidence = self.run_runner(config, task_class="high-value-agent")
        self.assertNotEqual(proc.returncode, 0)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertFalse(attempt["schema_valid"])
        self.assertFalse(attempt["result_present"])
        self.assertIn("missing result.meta.toolSummary", attempt["adapter_error"])
        self.assertTrue(openclaw_marker.exists())

    def test_static_and_runtime_tool_write_proof_allows_payload_validation(self):
        self.write_executable(
            "openclaw",
            "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"domain-validator-next\\\"]}\"}],\"meta\":{\"toolSummary\":{\"calls\":2,\"tools\":[\"write\",\"read\"],\"failures\":0}}}}'\n",
        )
        config = self.write_config([{
            "provider": "openclaw",
            "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        config.write_text(json.dumps(value))
        proc, evidence = self.run_runner(config, task_class="high-value-agent")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertTrue(attempt["schema_valid"])
        self.assertEqual(attempt["runtime_capabilities"]["tool_write"], True)
        self.assertEqual(attempt["runtime_capabilities"]["write_tools"], ["write"])
        self.assertEqual(attempt["runtime_capabilities"]["tool_summary"]["calls"], 2)

    def test_runtime_tool_write_summary_is_strict_and_fail_closed(self):
        summaries = {
            "missing": None,
            "zero-calls": {"calls": 0, "tools": ["write"], "failures": 0},
            "failure": {"calls": 2, "tools": ["write", "read"], "failures": 1},
            "read-only": {"calls": 1, "tools": ["read"], "failures": 0},
            "malformed-tools": {"calls": 1, "tools": "write", "failures": 0},
        }
        for name, summary in summaries.items():
            with self.subTest(name=name):
                wrapper = {
                    "result": {
                        "payloads": [{"text": '{"status":"ok","evidence":["fictional"]}'}],
                        "meta": {},
                    },
                }
                if summary is not None:
                    wrapper["result"]["meta"]["toolSummary"] = summary
                self.write_executable("openclaw", f"printf '%s\\n' {shlex.quote(json.dumps(wrapper))}\n")
                config = self.write_config([{
                    "provider": "openclaw",
                    "model": "google/gemini-3.1-pro-preview",
                    "required_capabilities": ["tool_write"],
                }])
                value = json.loads(config.read_text())
                value["providers"]["openclaw"]["model_capabilities"] = {
                    "google/gemini-3.1-pro-preview": {"tool_write": True},
                }
                config.write_text(json.dumps(value))
                proc, evidence = self.run_runner(config, task_class="high-value-agent")
                self.assertNotEqual(proc.returncode, 0)
                attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
                self.assertFalse(attempt["result_present"])
                self.assertFalse(attempt["schema_valid"])
                self.assertTrue(attempt["adapter_error"])

    def test_runtime_tool_proof_accepts_exec_and_records_exact_tool(self):
        wrapper = {
            "result": {
                "payloads": [{"text": '{"status":"ok","evidence":["domain-validator-next"]}'}],
                "meta": {"toolSummary": {"calls": 1, "tools": ["exec"], "failures": 0}},
            },
        }
        self.write_executable("openclaw", f"printf '%s\\n' {shlex.quote(json.dumps(wrapper))}\n")
        config = self.write_config([{
            "provider": "openclaw",
            "model": "google/gemini-3.1-pro-preview",
            "required_capabilities": ["tool_write"],
        }])
        value = json.loads(config.read_text())
        value["providers"]["openclaw"]["model_capabilities"] = {
            "google/gemini-3.1-pro-preview": {"tool_write": True},
        }
        config.write_text(json.dumps(value))
        proc, evidence = self.run_runner(config, task_class="high-value-agent")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertEqual(attempt["runtime_capabilities"]["write_tools"], ["exec"])

    def test_openclaw_thinking_is_configurable_and_invalid_value_fails_before_launch(self):
        marker = self.root / "thinking"
        self.write_executable(
            "openclaw",
            f"while [ $# -gt 0 ]; do [ \"$1\" = '--thinking' ] && {{ shift; printf '%s' \"$1\" > {shlex.quote(str(marker))}; }}; shift || true; done\n"
            "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"proof\\\"]}\"}]}}'\n",
        )
        config = self.write_config([{"provider": "openclaw", "model": "blockrun/free", "thinking": "high"}])
        proc, _ = self.run_runner(config)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(marker.read_text(), "high")

        marker.unlink()
        config = self.write_config([{"provider": "openclaw", "model": "blockrun/free", "thinking": "impossible"}])
        proc, evidence = self.run_runner(config)
        self.assertNotEqual(proc.returncode, 0)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertIn("invalid openclaw thinking", attempt["adapter_error"])
        self.assertFalse(marker.exists())

    def test_runtime_tool_proof_accepts_one_whole_string_json_fence(self):
        payloads = (
            '```json\n{"status":"ok","evidence":["lf"]}\n```',
            '```json\r\n{"status":"ok","evidence":["crlf"]}\r\n```',
        )
        for payload in payloads:
            with self.subTest(payload=payload):
                wrapper = {
                    "result": {
                        "payloads": [{"text": payload}],
                        "meta": {"toolSummary": {"calls": 2, "tools": ["write", "read"], "failures": 0}},
                    },
                }
                self.write_executable("openclaw", f"printf '%s\\n' {shlex.quote(json.dumps(wrapper))}\n")
                config = self.write_config([{
                    "provider": "openclaw",
                    "model": "google/gemini-3.1-pro-preview",
                    "required_capabilities": ["tool_write"],
                }])
                value = json.loads(config.read_text())
                value["providers"]["openclaw"]["model_capabilities"] = {
                    "google/gemini-3.1-pro-preview": {"tool_write": True},
                }
                config.write_text(json.dumps(value))
                proc, evidence = self.run_runner(config, task_class="high-value-agent")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
                self.assertTrue(attempt["result_present"])
                self.assertTrue(attempt["schema_valid"])
                result = json.loads(Path(attempt["result_path"]).read_text())
                self.assertEqual(result["status"], "ok")

    def test_json_fence_normalization_rejects_nonexact_or_unsafe_forms(self):
        payloads = {
            "unknown-language": '```javascript\n{"status":"ok","evidence":["x"]}\n```',
            "uppercase-language": '```JSON\n{"status":"ok","evidence":["x"]}\n```',
            "unclosed": '```json\n{"status":"ok","evidence":["x"]}',
            "prefix-prose": 'result follows\n```json\n{"status":"ok","evidence":["x"]}\n```',
            "suffix-prose": '```json\n{"status":"ok","evidence":["x"]}\n```\ndone',
            "wallet-warning": '> wallet empty\n\n```json\n{"status":"ok","evidence":["x"]}\n```',
            "second-fence": '```json\n{"status":"ok","evidence":["x"]}\n```\n```json\n{}\n```',
            "nested-fence": '```json\n{"status":"ok","evidence":["```"]}\n```',
            "trailing-newline": '```json\n{"status":"ok","evidence":["x"]}\n```\n',
            "malformed-json": '```json\n{"status":\n```',
        }
        for name, payload in payloads.items():
            with self.subTest(name=name):
                wrapper = {
                    "result": {
                        "payloads": [{"text": payload}],
                        "meta": {"toolSummary": {"calls": 2, "tools": ["write", "read"], "failures": 0}},
                    },
                }
                self.write_executable("openclaw", f"printf '%s\\n' {shlex.quote(json.dumps(wrapper))}\n")
                config = self.write_config([{
                    "provider": "openclaw",
                    "model": "google/gemini-3.1-pro-preview",
                    "required_capabilities": ["tool_write"],
                }])
                value = json.loads(config.read_text())
                value["providers"]["openclaw"]["model_capabilities"] = {
                    "google/gemini-3.1-pro-preview": {"tool_write": True},
                }
                config.write_text(json.dumps(value))
                proc, evidence = self.run_runner(config, task_class="high-value-agent")
                self.assertNotEqual(proc.returncode, 0)
                attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
                self.assertFalse(attempt["schema_valid"])
                self.assertIn("result parse failed", attempt["schema_errors"][0])

    def test_json_fence_is_not_normalized_without_required_runtime_capability_proof(self):
        wrapper = {
            "result": {
                "payloads": [{"text": '```json\n{"status":"ok","evidence":["no-proof"]}\n```'}],
                "meta": {"toolSummary": {"calls": 2, "tools": ["write", "read"], "failures": 0}},
            },
        }
        self.write_executable("openclaw", f"printf '%s\\n' {shlex.quote(json.dumps(wrapper))}\n")
        config = self.write_config([{
            "provider": "openclaw",
            "model": "blockrun/free",
        }])
        proc, evidence = self.run_runner(config, task_class="tool-agent")
        self.assertNotEqual(proc.returncode, 0)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertEqual(attempt["runtime_capabilities"], {})
        self.assertFalse(attempt["schema_valid"])
        self.assertIn("result parse failed", attempt["schema_errors"][0])

    def test_provider_executable_resolves_user_relative_fallback_outside_path(self):
        fallback = self.root / ".local" / "bin" / "claude"
        fallback.parent.mkdir(parents=True)
        fallback.write_text(
            "#!/usr/bin/env bash\nprintf '%s\\n' "
            "'{\"status\":\"ok\",\"evidence\":[\"user-relative-claude\"]}'\n",
            encoding="utf-8",
        )
        fallback.chmod(0o755)
        config = self.write_config([{"provider": "claude", "model": "sonnet"}])
        value = json.loads(config.read_text())
        value["providers"]["claude"] = {
            "executable": "claude-not-on-launchd-path",
            "executable_fallbacks": ["~/.local/bin/claude"],
        }
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(config, extra_env={"HOME": str(self.root)})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertEqual(attempt["provider"], "claude")
        self.assertEqual(attempt["executable"], str(fallback))
        self.assertTrue(attempt["schema_valid"])

    def test_claude_child_uses_headless_gateway_auth_without_leaking_secret(self):
        secret = "fixture-cli-proxy-secret-never-log"
        (self.root / ".cli-proxy-api-key").write_text(secret + "\n", encoding="utf-8")
        self.write_executable(
            "claude",
            "[ \"${ANTHROPIC_BASE_URL:-}\" = 'http://127.0.0.1:8317' ] || exit 91\n"
            f"[ \"${{ANTHROPIC_AUTH_TOKEN:-}}\" = {shlex.quote(secret)} ] || exit 92\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"headless-gateway-auth\"]}'\n",
        )
        config = self.write_config([{"provider": "claude", "model": "sonnet"}])

        proc, evidence = self.run_runner(
            config,
            extra_env={
                "HOME": str(self.root),
                "ANTHROPIC_BASE_URL": "",
                "ANTHROPIC_AUTH_TOKEN": "",
                "ANTHROPIC_API_KEY": "",
                "CLAUDE_CODE_OAUTH_TOKEN": "",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertTrue(attempt["schema_valid"])
        evidence_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in evidence.rglob("*") if path.is_file()
        )
        self.assertNotIn(secret, evidence_text)

    def test_claude_direct_uses_oauth_without_proxy_env_and_records_identity(self):
        self.write_executable("codex", "exit 99\n")
        self.write_executable(
            "claude",
            "[ -z \"${ANTHROPIC_BASE_URL:-}\" ] || exit 91\n"
            "[ -z \"${ANTHROPIC_AUTH_TOKEN:-}\" ] || exit 92\n"
            "[ -z \"${ANTHROPIC_API_KEY:-}\" ] || exit 93\n"
            "[ -z \"${CLAUDE_CODE_OAUTH_TOKEN:-}\" ] || exit 94\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"direct-oauth\"]}'\n",
        )
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-terra"},
            {"provider": "claude-direct", "model": "sonnet"},
        ])
        value = json.loads(config.read_text())
        value["providers"]["claude-direct"] = {
            "executable": "claude",
            "account": "operator@example.com",
        }
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(
            config,
            extra_env={
                "ANTHROPIC_BASE_URL": "http://127.0.0.1:8317",
                "ANTHROPIC_AUTH_TOKEN": "proxy-token",
                "ANTHROPIC_API_KEY": "api-key",
                "CLAUDE_CODE_OAUTH_TOKEN": "oauth-env-token",
                "AGENT_RUNNER_PROVIDER": "claude-direct",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertEqual(attempt["provider"], "claude-direct")
        self.assertEqual(attempt["model"], "sonnet")
        self.assertEqual(attempt["account"], "operator@example.com")
        self.assertTrue(attempt["schema_valid"])

    def test_non_claude_child_does_not_receive_cli_proxy_secret(self):
        (self.root / ".cli-proxy-api-key").write_text("fixture-secret\n", encoding="utf-8")
        self.write_executable(
            "codex",
            "[ -z \"${ANTHROPIC_BASE_URL:-}\" ] || exit 93\n"
            "[ -z \"${ANTHROPIC_AUTH_TOKEN:-}\" ] || exit 94\n"
            "result_path=''\n"
            "while [ $# -gt 0 ]; do\n"
            "  if [ \"$1\" = '-o' ]; then shift; result_path=\"$1\"; fi\n"
            "  shift || true\n"
            "done\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{}}'\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"provider-isolated\"]}' > \"$result_path\"\n",
        )
        config = self.write_config([{
            "provider": "codex", "model": "gpt-5.6-terra", "effort": "medium",
        }])

        proc, evidence = self.run_runner(
            config,
            extra_env={
                "HOME": str(self.root),
                "ANTHROPIC_BASE_URL": "",
                "ANTHROPIC_AUTH_TOKEN": "",
            },
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertTrue(attempt["schema_valid"])

    def test_claude_without_headless_credentials_fails_before_keychain_launch(self):
        invoked = self.root / "claude-invoked"
        self.write_executable(
            "claude",
            f"touch {shlex.quote(str(invoked))}\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"should-not-run\"]}'\n",
        )
        config = self.write_config([{"provider": "claude", "model": "sonnet"}])

        proc, evidence = self.run_runner(
            config,
            extra_env={
                "HOME": str(self.root),
                "ANTHROPIC_BASE_URL": "",
                "ANTHROPIC_AUTH_TOKEN": "",
                "ANTHROPIC_API_KEY": "",
                "CLAUDE_CODE_OAUTH_TOKEN": "",
            },
        )

        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(invoked.exists())
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertIn("claude headless auth unavailable", attempt["adapter_error"])

    def test_codex_child_uses_isolated_home_with_linked_auth(self):
        source_home = self.root / "interactive-codex"
        source_home.mkdir()
        source_auth = source_home / "auth.json"
        secret = "fixture-codex-auth-never-log"
        source_auth.write_text(secret + "\n", encoding="utf-8")
        automation_home = self.root / "automation-codex"
        self.write_executable(
            "codex",
            f"[ \"${{CODEX_HOME:-}}\" = {shlex.quote(str(automation_home))} ] || exit 95\n"
            f"[ \"${{HOME:-}}\" = {shlex.quote(str(automation_home / 'user-home'))} ] || exit 100\n"
            "[ -L \"$CODEX_HOME/auth.json\" ] || exit 96\n"
            f"[ \"$(cat \"$CODEX_HOME/auth.json\")\" = {shlex.quote(secret)} ] || exit 97\n"
            f"[ \"${{SSL_CERT_FILE:-}}\" = {shlex.quote(str(self.root / 'cert.pem'))} ] || exit 99\n"
            "printf '%s\\n' \"$@\" | grep -Fqx 'project_doc_max_bytes=0' || exit 101\n"
            "printf '%s\\n' \"$@\" | grep -Fq 'skills.config=[' || exit 102\n"
            f"printf '%s\\n' \"$@\" | grep -Fq {shlex.quote('shell_environment_policy.set.HOME=' + json.dumps(str(self.root)))} || exit 103\n"
            "printf '%s\\n' \"$@\" | grep -Fqx 'multi_agent' || exit 104\n"
            "printf '%s\\n' \"$@\" | grep -Fqx 'plugins' || exit 105\n"
            "result_path=''\n"
            "ignore_user_config=0\n"
            "while [ $# -gt 0 ]; do\n"
            "  if [ \"$1\" = '-o' ]; then shift; result_path=\"$1\"; fi\n"
            "  if [ \"$1\" = '--ignore-user-config' ]; then ignore_user_config=1; fi\n"
            "  shift || true\n"
            "done\n"
            "[ \"$ignore_user_config\" = 1 ] || exit 98\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{}}'\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"isolated-codex-home\"]}' > \"$result_path\"\n",
        )
        config = self.write_config([{
            "provider": "codex", "model": "gpt-5.6-terra", "effort": "medium",
        }])
        value = json.loads(config.read_text())
        value["providers"]["codex"].update({
            "automation_home": str(automation_home),
            "auth_file": str(source_auth),
            "ssl_cert_file": str(self.root / "cert.pem"),
            "project_doc_max_bytes": 0,
            "disabled_skills": [
                "imagegen", "openai-docs", "plugin-creator", "skill-creator", "skill-installer",
            ],
            "disabled_features": ["multi_agent", "plugins"],
        })
        (self.root / "cert.pem").write_text("fixture certificate bundle\n", encoding="utf-8")
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(
            config,
            extra_env={"CODEX_HOME": str(source_home), "HOME": str(self.root)},
        )

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((automation_home / "auth.json").is_symlink())
        self.assertFalse((automation_home / "plugins").exists())
        evidence_text = "\n".join(
            target.read_text(encoding="utf-8", errors="replace")
            for target in evidence.rglob("*") if target.is_file()
        )
        self.assertNotIn(secret, evidence_text)

    def test_codex_isolated_home_without_auth_fails_before_launch(self):
        invoked = self.root / "codex-invoked"
        self.write_executable("codex", f"touch {shlex.quote(str(invoked))}\nexit 0\n")
        config = self.write_config([{
            "provider": "codex", "model": "gpt-5.6-terra", "effort": "medium",
        }])
        value = json.loads(config.read_text())
        value["providers"]["codex"].update({
            "automation_home": str(self.root / "automation-codex"),
            "auth_file": str(self.root / "missing-auth.json"),
        })
        config.write_text(json.dumps(value))

        proc, evidence = self.run_runner(config, extra_env={"OPENAI_API_KEY": ""})

        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(invoked.exists())
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertIn("codex automation auth unavailable", attempt["adapter_error"])

    def test_codex_and_sonnet_quota_fall_back_to_openclaw_and_extract_fresh_payload(self):
        sessions = self.root / "openclaw-sessions"
        delivered_prompt = self.root / "openclaw-prompt"
        agent_value = self.root / "openclaw-agent"
        model_value = self.root / "openclaw-model"
        thinking_value = self.root / "openclaw-thinking"
        timeout_value = self.root / "openclaw-timeout"
        claude_marker = self.root / "claude-invoked"
        self.write_executable(
            "codex",
            "echo \"You've hit your usage limit; try again on Jul 29\" >&2\nexit 1\n",
        )
        self.write_executable(
            "claude",
            f"touch '{claude_marker}'\necho 'weekly limit resets Jul 24' >&2\nexit 42\n",
        )
        self.write_executable(
            "openclaw",
            "[ \"$1\" = 'agent' ]\n"
            "while [ $# -gt 0 ]; do\n"
            f"  case \"$1\" in --session-id) printf '%s\\n' \"$2\" >> '{sessions}' ;;\n"
            f"    --message) printf '%s' \"$2\" > '{delivered_prompt}' ;;\n"
            f"    --agent) printf '%s' \"$2\" > '{agent_value}' ;;\n"
            f"    --model) printf '%s' \"$2\" > '{model_value}' ;;\n"
            f"    --thinking) printf '%s' \"$2\" > '{thinking_value}' ;;\n"
            f"    --timeout) printf '%s' \"$2\" > '{timeout_value}' ;; esac\n"
            "  shift\n"
            "done\n"
            "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"blockrun-free\\\"]}\"}]}}'\n",
        )
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
            {"provider": "claude", "model": "sonnet"},
            {"provider": "openclaw", "model": "blockrun/free"},
        ])

        first, evidence = self.run_runner(config)
        second, evidence = self.run_runner(config)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["selected_provider"], "openclaw")
        self.assertEqual(summary["selected_model"], "blockrun/free")
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual([row["provider"] for row in attempts], ["codex", "claude", "openclaw"])
        self.assertEqual(attempts[0]["error_class"], "transient_quota")
        self.assertEqual(attempts[1]["error_class"], "transient_quota")
        self.assertEqual(attempts[2]["attempt"], 3)
        self.assertTrue(attempts[2]["schema_valid"])
        self.assertEqual(
            json.loads(Path(attempts[2]["result_path"]).read_text()),
            {"status": "ok", "evidence": ["blockrun-free"]},
        )
        session_ids = sessions.read_text().splitlines()
        self.assertEqual(len(session_ids), 2)
        self.assertEqual(len(set(session_ids)), 2)
        self.assertTrue(all(session_ids))
        self.assertEqual(agent_value.read_text(), "anicca")
        self.assertEqual(model_value.read_text(), "blockrun/free")
        self.assertEqual(thinking_value.read_text(), "off")
        self.assertEqual(timeout_value.read_text(), "2")
        prompt = delivered_prompt.read_text()
        self.assertTrue(prompt.startswith("Return contract JSON only."))
        self.assertIn("STRICT OUTPUT CONTRACT", prompt)
        self.assertIn(str(self.root.resolve()), prompt)
        self.assertIn('"required":["status","evidence"]', prompt)
        self.assertIn('"evidence":{"type":"array"', prompt)
        self.assertIn("result.payloads[0].text", prompt)
        self.assertTrue(claude_marker.exists())

    def test_openclaw_malformed_missing_nonzero_and_no_output_fail_closed(self):
        cases = {
            "malformed-wrapper": "printf '%s\\n' '{'\n",
            "missing-payload": "printf '%s\\n' '{\"result\":{\"payloads\":[]}}'\n",
            "nonzero": "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"bad\\\"]}\"}]}}'\nexit 9\n",
            "no-output": ":\n",
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                claude_marker = self.root / f"claude-invoked-{name}"
                self.write_executable("codex", "echo quota >&2\nexit 1\n")
                self.write_executable("openclaw", body)
                self.write_executable("claude", f"touch '{claude_marker}'\necho 'weekly limit' >&2\nexit 42\n")
                config = self.write_config([
                    {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
                    {"provider": "claude", "model": "sonnet"},
                    {"provider": "openclaw", "model": "blockrun/free"},
                ], timeout=1)
                proc, evidence = self.run_runner(config)
                self.assertNotEqual(proc.returncode, 0)
                attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
                self.assertEqual([row["provider"] for row in attempts], ["codex", "claude", "openclaw"])
                self.assertFalse(attempts[-1]["schema_valid"])
                self.assertTrue(claude_marker.exists())

    def test_openclaw_timeout_is_failed_last_resort_attempt(self):
        self.write_executable("codex", "echo 'resets Jul 29' >&2\nexit 1\n")
        self.write_executable("openclaw", "sleep 5\n")
        self.write_executable(
            "claude",
            "echo 'weekly limit resets Jul 24' >&2\nexit 42\n",
        )
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
            {"provider": "claude", "model": "sonnet"},
            {"provider": "openclaw", "model": "blockrun/free"},
        ], timeout=1)
        proc, evidence = self.run_runner(config)
        self.assertNotEqual(proc.returncode, 0)
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual([row["provider"] for row in attempts], ["codex", "claude", "openclaw"])
        self.assertEqual(attempts[0]["error_class"], "transient_quota")
        self.assertEqual(attempts[1]["error_class"], "transient_quota")
        self.assertTrue(attempts[2]["timed_out"])
        self.assertEqual(attempts[2]["error_class"], "transient_timeout")

    def test_fresh_valid_result_survives_provider_exit_timeout_without_retry(self):
        """A completed side effect must not be repeated because the CLI failed to exit.

        Production LEARN pass 1785304094-88563 wrote three durable lessons and a
        schema-valid result before Codex remained alive until the 90-second timeout.
        Treating the process exit as the authority discarded that completed contract
        and invoked Claude against the same append-only work a second time.
        """
        fallback_marker = self.root / "fallback-invoked"
        self.write_executable(
            "codex",
            "result=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  if [ \"$1\" = '-o' ]; then result=\"$2\"; shift 2; continue; fi\n"
            "  shift\n"
            "done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"durable-effect\"]}' > \"$result\"\n"
            "sleep 5\n",
        )
        self.write_executable(
            "claude",
            f"touch '{fallback_marker}'\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"duplicate\"]}'\n",
        )
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
            {"provider": "claude", "model": "sonnet"},
        ], timeout=1)

        proc, evidence = self.run_runner(config)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["selected_provider"], "codex")
        attempts = [
            json.loads(line)
            for line in (evidence / "attempts.jsonl").read_text().splitlines()
        ]
        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0]["timed_out"])
        self.assertTrue(attempts[0]["schema_valid"])
        self.assertFalse(fallback_marker.exists())

    def test_explicit_timeout_bounds_the_entire_fallback_chain(self):
        self.write_executable("codex", "sleep 5\n")
        self.write_executable("claude", "sleep 5\n")
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
            {"provider": "claude", "model": "sonnet"},
        ], timeout=5)
        started = time.monotonic()
        proc, evidence = self.run_runner(
            config,
            extra_args=["--timeout-seconds", "1"],
        )
        elapsed = time.monotonic() - started
        self.assertNotEqual(proc.returncode, 0)
        self.assertLess(elapsed, 2.5)
        attempts = [
            json.loads(line)
            for line in (evidence / "attempts.jsonl").read_text().splitlines()
        ]
        self.assertEqual(len(attempts), 1)
        self.assertTrue(attempts[0]["timed_out"])

    def test_timeout_terminates_the_provider_process_tree(self):
        child_pid_path = self.root / "provider-child.pid"
        self.write_executable(
            "codex",
            "sleep 30 &\n"
            "child=$!\n"
            f"printf '%s' \"$child\" > '{child_pid_path}'\n"
            "wait \"$child\"\n",
        )
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
        ], timeout=1)

        proc, evidence = self.run_runner(config)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(child_pid_path.exists())
        child_pid = int(child_pid_path.read_text())
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            child_alive = False
        else:
            child_alive = True
        finally:
            if child_alive:
                os.kill(child_pid, 9)

        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertTrue(attempt["timed_out"])
        self.assertFalse(child_alive, f"provider child process {child_pid} survived timeout")

    def test_composition_prompt_uses_stdin_and_disables_user_tools(self):
        argv_path = self.root / "codex-argv"
        stdin_path = self.root / "codex-stdin"
        self.write_executable(
            "codex",
            f"printf '%s\\n' \"$*\" > '{argv_path}'\n"
            f"cat > '{stdin_path}'\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"composed\"]}' > \"$out\"\n",
        )
        secret_prompt = "private buyer question must stay off argv"
        evidence = self.root / "composition-evidence"
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env['PATH']}"
        env["ANICCA_USAGE_LEDGER"] = str(self.root / "composition-usage.jsonl")
        proc = subprocess.run([
            "python3", str(RUNNER), "--task-class", "composition-agent",
            "--prompt-stdin", "--schema", str(self.schema),
            "--evidence-dir", str(evidence), "--task-label", "compose-fixture",
            "--loop", "fixture-loop",
        ], env=env, input=secret_prompt, text=True, capture_output=True)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        argv = argv_path.read_text(encoding="utf-8")
        self.assertNotIn(secret_prompt, argv)
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--sandbox read-only", argv)
        self.assertEqual(stdin_path.read_text(encoding="utf-8"), secret_prompt)

    def test_healthy_gpt_is_attempt_one_and_never_invokes_sonnet(self):
        claude_marker = self.root / "claude-invoked"
        self.write_executable("claude", f"touch '{claude_marker}'\nexit 99\n")
        self.write_executable(
            "codex",
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"healthy-gpt\"]}' > \"$out\"\n",
        )
        for task_class, expected_model in (
            ("repeatable-agent", "gpt-5.6-luna"),
            ("tool-agent", "gpt-5.6-terra"),
            ("high-value-agent", "gpt-5.6-luna"),
        ):
            with self.subTest(task_class=task_class):
                proc, evidence = self.run_runner(CONFIG, task_class=task_class)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                summary = json.loads((evidence / "summary.json").read_text())
                self.assertEqual(summary["selected_provider"], "codex")
                self.assertEqual(summary["selected_model"], expected_model)
                self.assertEqual(summary["attempt_count"], 1)
                self.assertFalse(claude_marker.exists())

    def test_provider_reported_usage_is_appended_with_loop_attribution(self):
        self.write_executable(
            "codex",
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"measured\"]}' > \"$out\"\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":24763,\"cached_input_tokens\":24448,\"output_tokens\":122,\"reasoning_output_tokens\":7}}'\n",
        )
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
        ])

        proc, evidence = self.run_runner(config)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        self.assertEqual(attempt["usage"]["measurement"], "provider_reported")
        self.assertEqual(attempt["usage"]["total_tokens"], 24885)
        ledger = [
            json.loads(line)
            for line in (self.root / "agent-usage.jsonl").read_text().splitlines()
        ]
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["loop"], "fixture-loop")
        self.assertEqual(ledger[0]["provider"], "codex")
        self.assertEqual(ledger[0]["model"], "gpt-5.6-luna")
        self.assertEqual(ledger[0]["effort"], "low")
        self.assertEqual(ledger[0]["tokens"]["total"], 24885)
        self.assertEqual(ledger[0]["route"], "repeatable-agent:configured")
        self.assertFalse(ledger[0]["escalated"])
        self.assertIsNone(ledger[0]["escalation_reason"])

    def test_high_or_sol_route_requires_reason_and_records_it_everywhere(self):
        marker = self.root / "codex-invoked"
        self.write_executable(
            "codex",
            f"touch {shlex.quote(str(marker))}\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"escalated\"]}' > \"$out\"\n",
        )
        config = json.loads(self.write_config([]).read_text(encoding="utf-8"))
        config["task_classes"]["escalation-agent"] = {
            "route": "explicit-escalation",
            "requires_explicit_escalation": True,
            "candidates": [
                {"provider": "codex", "model": "gpt-5.6-sol", "effort": "medium"},
            ],
        }
        config_path = self.root / "escalation-config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        rejected, _ = self.run_runner(config_path, task_class="escalation-agent")
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("explicit escalation reason", rejected.stderr)
        self.assertFalse(marker.exists())

        accepted, evidence = self.run_runner(
            config_path,
            task_class="escalation-agent",
            extra_args=["--escalation-reason", "buyer-evidence-conflict"],
        )
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        usage = json.loads((self.root / "agent-usage.jsonl").read_text().splitlines()[0])
        for row in (summary, attempt, usage):
            self.assertEqual(row["route"], "explicit-escalation")
            self.assertTrue(row["escalated"])
            self.assertEqual(row["escalation_reason"], "buyer-evidence-conflict")

    def test_pass_and_daily_token_breakers_stop_before_another_provider_call(self):
        calls = self.root / "provider-calls"
        self.write_executable(
            "codex",
            f"printf '%s\\n' call >> {shlex.quote(str(calls))}\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"budgeted\"]}' > \"$out\"\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":70,\"output_tokens\":10}}'\n",
        )
        config_path = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
        ])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["task_classes"]["repeatable-agent"].update({
            "route": "luna-medium-decision",
            "token_reservation": 30,
        })
        config_path.write_text(json.dumps(config), encoding="utf-8")
        budget_env = {
            "ANICCA_BUDGET_SCOPE_ID": "pass-1",
            "ANICCA_PASS_TOKEN_BUDGET": "100",
            "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "100",
            "ANICCA_TOKEN_BUDGET_LEDGER": str(self.root / "token-budget.jsonl"),
        }

        first, _ = self.run_runner(config_path, extra_env=budget_env)
        self.assertEqual(first.returncode, 0, first.stderr)

        same_pass, evidence = self.run_runner(config_path, extra_env=budget_env)
        self.assertEqual(same_pass.returncode, 75, same_pass.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["status"], "budget_blocked")
        self.assertEqual(summary["budget"]["reason"], "pass_token_budget_exceeded")

        next_pass_env = dict(budget_env, ANICCA_BUDGET_SCOPE_ID="pass-2")
        next_pass, evidence = self.run_runner(config_path, extra_env=next_pass_env)
        self.assertEqual(next_pass.returncode, 75, next_pass.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["budget"]["reason"], "loop_daily_token_budget_exceeded")
        self.assertEqual(calls.read_text().splitlines(), ["call"])

    def test_budget_required_turns_a_missing_budget_into_a_hard_failure(self):
        """X20: 47 gig model calls ran with budget_not_configured and were never
        charged, because the reply-detector LaunchAgent never exported the budget
        env. Silence is the failure mode; an owner that declares itself budgeted
        must refuse to run unbudgeted rather than degrade to no breaker at all."""
        calls = self.root / "provider-calls"
        self.write_executable(
            "codex",
            f"printf '%s\\n' call >> {shlex.quote(str(calls))}\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"budgeted\"]}' > \"$out\"\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":70,\"output_tokens\":10}}'\n",
        )
        config_path = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
        ])
        refused, _ = self.run_runner(
            config_path, extra_env={"ANICCA_BUDGET_REQUIRED": "1"},
        )
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertIn("token budget is required", refused.stderr)
        self.assertFalse(calls.exists())

    def test_daily_scope_defaults_to_the_loop_and_is_recorded(self):
        """Callers that do not name an owner keep the pre-X20 behaviour."""
        self.write_executable(
            "codex",
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"budgeted\"]}' > \"$out\"\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":70,\"output_tokens\":10}}'\n",
        )
        config_path = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
        ])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["task_classes"]["repeatable-agent"]["token_reservation"] = 30
        config_path.write_text(json.dumps(config), encoding="utf-8")
        ledger = self.root / "token-budget.jsonl"

        ran, _ = self.run_runner(config_path, extra_env={
            "ANICCA_BUDGET_SCOPE_ID": "pass-default",
            "ANICCA_PASS_TOKEN_BUDGET": "1000",
            "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "1000",
            "ANICCA_TOKEN_BUDGET_LEDGER": str(ledger),
        })
        self.assertEqual(ran.returncode, 0, ran.stderr)
        row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["daily_scope"], "fixture-loop")

        named, _ = self.run_runner(config_path, extra_env={
            "ANICCA_BUDGET_SCOPE_ID": "pass-named",
            "ANICCA_BUDGET_DAILY_SCOPE": "gig-auditor",
            "ANICCA_PASS_TOKEN_BUDGET": "1000",
            "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "1000",
            "ANICCA_TOKEN_BUDGET_LEDGER": str(ledger),
        })
        self.assertEqual(named.returncode, 0, named.stderr)
        owners = {
            json.loads(line)["daily_scope"]
            for line in ledger.read_text(encoding="utf-8").splitlines()
            if json.loads(line)["type"] == "reservation"
        }
        self.assertEqual(owners, {"fixture-loop", "gig-auditor"})

    def test_cached_codex_input_is_telemetry_but_not_charged_again_to_budget(self):
        calls = self.root / "provider-calls"
        self.write_executable(
            "codex",
            f"printf '%s\\n' call >> {shlex.quote(str(calls))}\n"
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"budgeted\"]}' > \"$out\"\n"
            "printf '%s\\n' '{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":70,\"cached_input_tokens\":60,\"output_tokens\":10}}'\n",
        )
        config_path = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
        ])
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["task_classes"]["repeatable-agent"].update({
            "route": "luna-medium-decision",
            "token_reservation": 30,
        })
        config_path.write_text(json.dumps(config), encoding="utf-8")
        budget_env = {
            "ANICCA_BUDGET_SCOPE_ID": "pass-cached",
            "ANICCA_PASS_TOKEN_BUDGET": "100",
            "ANICCA_LOOP_DAILY_TOKEN_BUDGET": "100",
            "ANICCA_TOKEN_BUDGET_LEDGER": str(self.root / "token-budget.jsonl"),
        }

        first, evidence = self.run_runner(config_path, extra_env=budget_env)
        first_summary = json.loads((evidence / "summary.json").read_text())
        first_attempt = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        second, evidence = self.run_runner(config_path, extra_env=budget_env)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first_attempt["usage"]["total_tokens"], 80)
        self.assertEqual(first_attempt["usage"]["cached_input_tokens"], 60)
        self.assertEqual(first_summary["budget"]["charged_tokens"], 20)
        self.assertEqual(first_summary["budget"]["pass_consumed_after_tokens"], 20)

        # Life Manager's shared runner reserves the full pass ceiling at
        # admission. Only 80 daily tokens remain after the first measured
        # 20-token charge, so a second 100-token pass is rejected before the
        # provider launches even though cached input was not charged twice.
        self.assertEqual(second.returncode, 75, second.stderr)
        second_summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(second_summary["status"], "budget_blocked")
        self.assertEqual(second_summary["budget"]["reservation_tokens"], 100)
        self.assertEqual(second_summary["budget"]["daily_consumed_tokens"], 20)
        self.assertEqual(calls.read_text().splitlines(), ["call"])

    def test_healthy_sonnet_after_codex_quota_never_invokes_openclaw(self):
        openclaw_marker = self.root / "openclaw-invoked"
        self.write_executable("codex", "echo 'usage limit resets Jul 29' >&2\nexit 1\n")
        self.write_executable(
            "claude",
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"healthy-sonnet\"]}'\n",
        )
        self.write_executable("openclaw", f"touch '{openclaw_marker}'\nexit 99\n")
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
            {"provider": "claude", "model": "sonnet"},
            {"provider": "openclaw", "model": "blockrun/free"},
        ])
        proc, evidence = self.run_runner(config)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["selected_provider"], "claude")
        self.assertEqual(summary["selected_model"], "sonnet")
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual([row["provider"] for row in attempts], ["codex", "claude"])
        self.assertFalse(openclaw_marker.exists())

    def test_expired_provider_auth_falls_through_to_openclaw(self):
        messages = (
            "Failed to authenticate: OAuth session expired and could not be refreshed",
            "Authentication token expired",
            "Access token has expired",
            "OAuth token refresh failed",
        )
        for message in messages:
            with self.subTest(message=message):
                self.write_executable("codex", "echo 'usage limit resets Jul 29' >&2\nexit 1\n")
                self.write_executable("claude", f"printf '%s\\n' {json.dumps(message)}\nexit 1\n")
                self.write_executable(
                    "openclaw",
                    "printf '%s\\n' '{\"result\":{\"payloads\":[{\"text\":\"{\\\"status\\\":\\\"ok\\\",\\\"evidence\\\":[\\\"auth-fallback\\\"]}\"}]}}'\n",
                )
                config = self.write_config([
                    {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
                    {"provider": "claude", "model": "sonnet"},
                    {"provider": "openclaw", "model": "blockrun/free"},
                ])
                proc, evidence = self.run_runner(config)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                summary = json.loads((evidence / "summary.json").read_text())
                self.assertEqual(summary["selected_provider"], "openclaw")
                attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
                self.assertEqual([row["provider"] for row in attempts], ["codex", "claude", "openclaw"])
                self.assertEqual(attempts[0]["error_class"], "transient_quota")
                self.assertEqual(attempts[1]["error_class"], "transient_auth")
                self.assertTrue(attempts[2]["schema_valid"])

    def test_invalid_credentials_and_permissions_do_not_fallback(self):
        messages = (
            "Failed to authenticate: invalid credentials",
            "Permission denied: insufficient permissions",
            "Invalid API key",
        )
        for message in messages:
            with self.subTest(message=message):
                openclaw_marker = self.root / "openclaw-auth-denied-invoked"
                openclaw_marker.unlink(missing_ok=True)
                self.write_executable("codex", "echo quota >&2\nexit 1\n")
                self.write_executable("claude", f"printf '%s\\n' {json.dumps(message)}\nexit 1\n")
                self.write_executable("openclaw", f"touch '{openclaw_marker}'\nexit 0\n")
                config = self.write_config([
                    {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
                    {"provider": "claude", "model": "sonnet"},
                    {"provider": "openclaw", "model": "blockrun/free"},
                ])
                proc, evidence = self.run_runner(config)
                self.assertNotEqual(proc.returncode, 0)
                attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
                self.assertEqual([row["provider"] for row in attempts], ["codex", "claude"])
                self.assertEqual(attempts[1]["error_class"], "validation_or_task_failure")
                self.assertFalse(openclaw_marker.exists())

    def test_sonnet_429_does_not_block_luna_candidate(self):
        self.write_executable("claude", "echo '429 All credentials for claude-sonnet are cooling down' >&2\nexit 42\n")
        self.write_executable("codex", "out=''\nwhile [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\nprintf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"luna\"]}' > \"$out\"\necho luna-stdout\n")
        config = self.write_config([
            {"provider": "claude", "model": "sonnet", "effort": "low"},
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
        ])
        proc, evidence = self.run_runner(config)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["selected_model"], "gpt-5.6-luna")
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual([row["rc"] for row in attempts], [42, 0])
        self.assertIn("429", Path(attempts[0]["stderr_path"]).read_text())

    def test_all_candidates_fail_is_nonzero_with_durable_attempt_evidence(self):
        self.write_executable("codex", "echo provider-down >&2\nexit 9\n")
        config = self.write_config([{"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"}])
        proc, evidence = self.run_runner(config)
        self.assertNotEqual(proc.returncode, 0)
        summary = json.loads((evidence / "summary.json").read_text())
        self.assertEqual(summary["status"], "failed")
        row = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[0])
        for field in (
            "attempt", "provider", "model", "executable", "rc", "timed_out",
            "task_class", "stdout_path", "stderr_path", "schema_valid",
        ):
            self.assertIn(field, row)

    def test_nontransient_codex_task_failure_does_not_fallback(self):
        openclaw_marker = self.root / "openclaw-invoked"
        self.write_executable("codex", "echo task-failed >&2\nexit 9\n")
        self.write_executable("openclaw", f"touch '{openclaw_marker}'\nexit 0\n")
        config = self.write_config([
            {"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"},
            {"provider": "openclaw", "model": "blockrun/free"},
        ])
        proc, evidence = self.run_runner(config)
        self.assertNotEqual(proc.returncode, 0)
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual([row["provider"] for row in attempts], ["codex"])
        self.assertEqual(attempts[0]["error_class"], "validation_or_task_failure")
        self.assertFalse(openclaw_marker.exists())

    def test_reused_evidence_dir_cannot_accept_a_stale_result_file(self):
        codex = self.write_executable(
            "codex",
            "out=''\nwhile [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"fresh-first-run\"]}' > \"$out\"\n",
        )
        config = self.write_config([{"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"}])
        first, evidence = self.run_runner(config)
        self.assertEqual(first.returncode, 0, first.stderr)

        codex.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        codex.chmod(0o755)
        second, evidence = self.run_runner(config)
        self.assertNotEqual(second.returncode, 0, "rc0/no-result reused the first run's result")
        attempts = [json.loads(line) for line in (evidence / "attempts.jsonl").read_text().splitlines()]
        self.assertEqual(len(attempts), 1, "attempt ledger from a prior run leaked into this run")
        self.assertFalse(attempts[0]["result_present"])
        self.assertFalse(attempts[0]["schema_valid"])

    def test_timeout_invalid_schema_and_missing_evidence_each_fail(self):
        cases = {
            "timeout": "sleep 5\n",
            "invalid-schema": "out=''\nwhile [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\nprintf '%s\\n' 'not-json' > \"$out\"\n",
            "missing-evidence": "out=''\nwhile [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\nprintf '%s\\n' '{\"status\":\"ok\",\"evidence\":[]}' > \"$out\"\n",
        }
        for name, body in cases.items():
            with self.subTest(name=name):
                self.write_executable("codex", body)
                config = self.write_config([{"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"}], timeout=1)
                proc, evidence = self.run_runner(config)
                self.assertNotEqual(proc.returncode, 0)
                row = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[-1])
                if name == "timeout":
                    self.assertTrue(row["timed_out"])
                else:
                    self.assertFalse(row["schema_valid"])

    def test_prose_wrapped_and_fenced_result_is_still_accepted(self):
        # Measured 2026-07-27, gig-pass-1785123005 agent-LEARN: codex timed out, the
        # claude-direct fallback then did the work correctly and wrote a valid contract
        # object -- but prefixed with a sentence and wrapped in a ```json fence, so
        # json.loads(whole file) died on "Expecting value: line 1 column 1" and the whole
        # step was recorded as a failure. Self-improvement had been stalled since 07-21
        # on exactly this, and capafy's listing lane fails the same way. The work is not
        # missing; only the reader is too strict.
        body = (
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "{\n"
            "  printf '%s\\n\\n' 'Schema seen. Dedup check done, evidence gathered.'\n"
            "  printf '%s\\n' '```json'\n"
            "  printf '%s\\n' '{\"status\":\"ok\",\"evidence\":[\"fenced-result\"]}'\n"
            "  printf '%s\\n' '```'\n"
            "} > \"$out\"\n"
        )
        self.write_executable("codex", body)
        config = self.write_config(
            [{"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"}])
        proc, evidence = self.run_runner(config)
        row = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[-1])
        self.assertTrue(row["schema_valid"], row.get("schema_errors"))
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_prose_without_any_json_object_still_fails(self):
        # The salvage must not become a licence to accept an acknowledgement. A reply
        # with no object at all is still a failed attempt.
        self.write_executable("codex", (
            "out=''\n"
            "while [ $# -gt 0 ]; do [ \"$1\" = '-o' ] && { shift; out=$1; }; shift || true; done\n"
            "printf '%s\\n' 'I have completed the task successfully.' > \"$out\"\n"
        ))
        config = self.write_config(
            [{"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"}])
        proc, evidence = self.run_runner(config)
        row = json.loads((evidence / "attempts.jsonl").read_text().splitlines()[-1])
        self.assertFalse(row["schema_valid"])
        self.assertNotEqual(proc.returncode, 0)

    def test_sigterm_to_runner_terminates_detached_provider_child(self):
        # 2026-07-27 incident: launch_gig_worker's shutdown() TERMs the WORKER
        # process group, but the provider runs in its own session
        # (start_new_session) so the signal never reaches it — the codex child
        # survived as an orphan and held the gig browser lock for 12 minutes
        # (next pass: deferred_cdp_busy, exit 75). The runner must forward its
        # own termination to the live provider's process group before dying.
        pid_file = self.root / "provider.pid"
        self.write_executable("codex", f'echo $$ > "{pid_file}"\nsleep 60\n')
        config = self.write_config(
            [{"provider": "codex", "model": "gpt-5.6-luna", "effort": "low"}],
            timeout=55)
        evidence = self.root / "evidence"
        env = os.environ.copy()
        env["PATH"] = f"{self.bin}:{env['PATH']}"
        env["AGENT_RUNNER_CONFIG"] = str(config)
        env["ANICCA_USAGE_LEDGER"] = str(self.root / "agent-usage.jsonl")
        runner = subprocess.Popen(
            ["python3", str(RUNNER), "--task-class", "tool-agent",
             "--prompt-file", str(self.prompt), "--schema", str(self.schema),
             "--evidence-dir", str(evidence), "--task-label", "fixture",
             "--loop", "fixture-loop", "--workdir", str(self.root)],
            env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        provider_pid = None
        try:
            deadline = time.time() + 10
            while time.time() < deadline and not pid_file.exists():
                time.sleep(0.1)
            self.assertTrue(pid_file.exists(), "provider fake never started")
            provider_pid = int(pid_file.read_text().strip())
            runner.send_signal(signal.SIGTERM)
            runner.communicate(timeout=10)
            deadline = time.time() + 3
            provider_alive = True
            while time.time() < deadline:
                try:
                    os.kill(provider_pid, 0)
                except ProcessLookupError:
                    provider_alive = False
                    break
                time.sleep(0.1)
            self.assertFalse(
                provider_alive,
                f"provider {provider_pid} outlived the runner's SIGTERM as an orphan")
        finally:
            if provider_pid:
                try:
                    os.killpg(provider_pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            if runner.poll() is None:
                runner.kill()
                runner.communicate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
