from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


SKILL_ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = SKILL_ROOT / "affiliate"
INVENTORY = SKILL_ROOT / "config" / "command-authority.json"
REGISTRY = SKILL_ROOT / "config" / "command-registry.json"
REGISTRY_SCHEMA = SKILL_ROOT / "config" / "schemas" / "command-registry-v1.json"
AUTHORITY_CLASSES = {
    "READ_ONLY",
    "WRITE_LOCAL",
    "SECRET_LOCAL",
    "MODEL_EXTERNAL",
    "WRITE_EXTERNAL",
    "MONEY_RECONCILE",
    "REPORT",
}


def command_choices(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    matches = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "command"
        ):
            continue
        for keyword in node.keywords:
            if keyword.arg == "choices":
                matches.append(tuple(ast.literal_eval(keyword.value)))
    if len(matches) != 1:
        raise AssertionError(f"expected one command choices tuple in {path}")
    return matches[0]


def dispatched_commands() -> dict[str, str]:
    source = DISPATCHER.read_text(encoding="utf-8")
    scripts = dict(re.findall(r"^  ([a-z]+)\) script=([a-z_]+\.py) ;;$", source, re.M))
    scripts.pop("x", None)
    discovered = {
        f"{group} {command}": f"scripts/{script}"
        for group, script in scripts.items()
        for command in command_choices(SKILL_ROOT / "scripts" / script)
    }
    for prefix, script in (("x", "x_profile_cli.py"), ("x post", "x_post_cli.py")):
        for command in command_choices(SKILL_ROOT / "scripts" / script):
            discovered[f"{prefix} {command}"] = f"scripts/{script}"
    return discovered


class CommandAuthorityInventoryTests(unittest.TestCase):
    def test_inventory_classifies_every_dispatched_command(self) -> None:
        self.assertTrue(INVENTORY.is_file(), f"missing command inventory: {INVENTORY}")
        value = json.loads(INVENTORY.read_text(encoding="utf-8"))
        self.assertEqual(value["schema_version"], 1)
        self.assertEqual(set(value["authority_classes"]), AUTHORITY_CLASSES)

        rows = value["commands"]
        by_command = {row["command"]: row for row in rows}
        self.assertEqual(len(by_command), len(rows), "duplicate inventory command")
        discovered = dispatched_commands()
        self.assertEqual(set(by_command), set(discovered))
        for command, entrypoint in discovered.items():
            with self.subTest(command=command):
                row = by_command[command]
                self.assertEqual(row["entrypoint"], entrypoint)
                self.assertIn(row["authority"], AUTHORITY_CLASSES)
                self.assertIs(type(row["external_effect"]), bool)

    def test_typed_registry_covers_inventory_with_valid_schemas(self) -> None:
        self.assertTrue(REGISTRY_SCHEMA.is_file(), f"missing registry schema: {REGISTRY_SCHEMA}")
        self.assertTrue(REGISTRY.is_file(), f"missing typed registry: {REGISTRY}")
        inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
        schema = json.loads(REGISTRY_SCHEMA.read_text(encoding="utf-8"))
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(registry)

        inventory_rows = {row["command"]: row for row in inventory["commands"]}
        registry_rows = {row["command"]: row for row in registry["commands"]}
        self.assertEqual(set(registry_rows), set(inventory_rows))
        for command, expected in inventory_rows.items():
            with self.subTest(command=command):
                row = registry_rows[command]
                self.assertEqual(row["entrypoint"], expected["entrypoint"])
                self.assertEqual(row["effect_class"], expected["authority"])
                expected_refs = {
                    "input_schema": "command-registry-v1.json#/$defs/input",
                    "output_schema": "command-registry-v1.json#/$defs/output",
                    "effect_schema": "command-registry-v1.json#/$defs/effect",
                    "precondition_schema": (
                        f"command-registry-v1.json#/$defs/precondition_{expected['authority'].lower()}"
                    ),
                    "semantic_postcondition_schema": (
                        f"command-registry-v1.json#/$defs/postcondition_{expected['authority'].lower()}"
                    ),
                }
                for field, reference in expected_refs.items():
                    self.assertEqual(row[field], {"$ref": reference})
                    Draft202012Validator.check_schema(row[field])


if __name__ == "__main__":
    unittest.main()
