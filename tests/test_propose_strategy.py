"""Tests for the propose_strategy tool and the strategy gate in _dispatch_tool."""

import json

import pytest

from agents.veloc.agent import (
    _GATED_TOOLS,
    _dispatch_tool,
    propose_strategy,
)
import agents.veloc.agent as agent_module


# ---------------------------------------------------------------------------
# Helpers — valid input fixtures
# ---------------------------------------------------------------------------

def _valid_critical_variables():
    return [
        {
            "name": "recon",
            "type": "float*",
            "file": "art.c",
            "line": 45,
            "evidence": "allocated with malloc at line 45, used as MPI_Allreduce buffer at line 72",
            "rationale": "holds iteratively refined reconstruction; losing it means restarting from scratch",
        },
    ]


def _valid_checkpoint_placement():
    return [
        {
            "file": "art.c",
            "line": 40,
            "loop_variable": "iter",
            "evidence": "main loop at lines 40-80, iterates over iter, contains MPI_Allreduce at line 72",
            "rationale": "checkpoint at end of loop body; loop iterator provides monotonic version",
        },
    ]


def _valid_strategy_kwargs():
    return {
        "critical_variables": _valid_critical_variables(),
        "checkpoint_placement": _valid_checkpoint_placement(),
        "veloc_mode": "memory_based",
        "veloc_mode_rationale": "all critical state is contiguous heap arrays",
    }


# ---------------------------------------------------------------------------
# Tests: propose_strategy validation
# ---------------------------------------------------------------------------

class TestProposeStrategyValidation:
    """Test propose_strategy input validation."""

    def test_valid_input_accepted(self):
        result = json.loads(propose_strategy(**_valid_strategy_kwargs()))
        assert result["accepted"] is True
        assert "1 critical variable" in result["summary"]
        assert "1 checkpoint placement" in result["summary"]
        assert "memory_based" in result["summary"]

    def test_empty_critical_variables_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"] = []
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "critical_variables must not be empty" in result["error"]

    def test_empty_checkpoint_placement_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["checkpoint_placement"] = []
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "checkpoint_placement must not be empty" in result["error"]

    def test_missing_variable_name_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"][0].pop("name")
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "critical_variables[0].name" in result["error"]

    def test_missing_variable_evidence_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"][0]["evidence"] = ""
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "critical_variables[0].evidence" in result["error"]

    def test_missing_variable_line_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"][0]["line"] = 0
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "critical_variables[0].line" in result["error"]

    def test_invalid_line_type_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"][0]["line"] = "not_a_number"
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "critical_variables[0].line" in result["error"]

    def test_missing_placement_evidence_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["checkpoint_placement"][0]["evidence"] = "   "
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "checkpoint_placement[0].evidence" in result["error"]

    def test_missing_placement_loop_variable_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["checkpoint_placement"][0].pop("loop_variable")
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "checkpoint_placement[0].loop_variable" in result["error"]

    def test_invalid_veloc_mode_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["veloc_mode"] = "hybrid"
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "veloc_mode" in result["error"]

    def test_empty_veloc_mode_rationale_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["veloc_mode_rationale"] = ""
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "veloc_mode_rationale" in result["error"]

    def test_file_based_mode_accepted(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["veloc_mode"] = "file_based"
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is True
        assert "file_based" in result["summary"]

    def test_multiple_variables_accepted(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"].append({
            "name": "theta",
            "type": "double*",
            "file": "art.c",
            "line": 50,
            "evidence": "allocated at line 50, modified in loop body at line 60",
            "rationale": "angle array modified every iteration",
        })
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is True
        assert "2 critical variable" in result["summary"]

    def test_risks_optional(self):
        kwargs = _valid_strategy_kwargs()
        # No risks provided — should be accepted
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is True

    def test_risks_included(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["risks"] = ["large array may slow checkpoint"]
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is True

    def test_non_dict_variable_rejected(self):
        kwargs = _valid_strategy_kwargs()
        kwargs["critical_variables"] = ["not_a_dict"]
        result = json.loads(propose_strategy(**kwargs))
        assert result["accepted"] is False
        assert "must be an object" in result["error"]


# ---------------------------------------------------------------------------
# Tests: gate logic in _dispatch_tool
# ---------------------------------------------------------------------------

class TestStrategyGate:
    """Test that gated tools are blocked until propose_strategy succeeds."""

    def setup_method(self):
        """Reset the gate before each test."""
        agent_module._strategy_proposed = False

    def test_gated_tools_blocked_before_strategy(self):
        for tool_name in _GATED_TOOLS:
            result = json.loads(_dispatch_tool(tool_name, "{}"))
            assert "error" in result
            assert "propose_strategy" in result["error"]

    def test_ungated_tools_work_before_strategy(self):
        # list_directory, read_file, remove_file should not be gated
        # (they may fail for other reasons, but NOT with a gate error)
        for tool_name in ("list_directory", "read_file", "remove_file"):
            result = json.loads(_dispatch_tool(tool_name, json.dumps({"dir_path": "/nonexistent", "file_path": "/nonexistent"})))
            if "error" in result:
                assert "propose_strategy" not in result["error"]

    def test_gate_unlocks_after_valid_strategy(self):
        # Call propose_strategy with valid args
        args = json.dumps(_valid_strategy_kwargs())
        result_str = _dispatch_tool("propose_strategy", args)
        result = json.loads(result_str)
        assert result["accepted"] is True

        # Gate should now be unlocked
        assert agent_module._strategy_proposed is True

    def test_gate_stays_locked_after_rejected_strategy(self):
        # Call propose_strategy with invalid args (empty variables)
        args = json.dumps({
            "critical_variables": [],
            "checkpoint_placement": _valid_checkpoint_placement(),
            "veloc_mode": "memory_based",
            "veloc_mode_rationale": "test",
        })
        result = json.loads(_dispatch_tool("propose_strategy", args))
        assert result["accepted"] is False

        # Gate should still be locked
        assert agent_module._strategy_proposed is False

        # Gated tools should still be blocked
        result = json.loads(_dispatch_tool("write_file", json.dumps({"file_path": "test.c", "contents": "//"})))
        assert "error" in result
        assert "propose_strategy" in result["error"]

    def test_propose_strategy_itself_not_gated(self):
        # propose_strategy should always be callable
        args = json.dumps(_valid_strategy_kwargs())
        result = json.loads(_dispatch_tool("propose_strategy", args))
        assert result["accepted"] is True
