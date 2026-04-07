# AGENTS.md

## Purpose

This repository must stay easy to understand, test, and extend.  
When making changes, optimize for:

- modularity
- code reuse
- clear interfaces
- low coupling
- high cohesion
- testability
- minimal, safe diffs

Do not optimize only for speed of implementation.

---

## Core principles

### 1) Reuse before adding
Before writing new code:

- inspect relevant existing modules
- reuse or extend existing code where it is a natural fit
- avoid duplicating logic already present elsewhere
- do not introduce parallel implementations of the same behavior

When similar logic already exists, prefer refactoring to a shared helper or module.

### 2) Single responsibility
Each file, class, and function should have one clear purpose.

- functions should do one thing well
- classes should represent one concept or responsibility
- modules should group closely related behavior only

Avoid "god files", "god classes", and long functions that mix unrelated concerns.

### 3) Separate concerns
Keep these concerns separate whenever possible:

- CLI entry points / API routes
- request parsing and validation
- LLM orchestration and agent logic
- code analysis and planning logic
- validation and comparison logic
- external tool execution (build, run, file I/O)
- configuration
- logging / metrics

Business logic should not be tightly coupled to framework details or I/O.

### 4) Keep interfaces small
Prefer narrow, explicit interfaces.

- minimize public surface area
- pass only needed data
- return structured results (Pydantic models)
- avoid hidden side effects
- avoid overly generic abstractions unless justified

### 5) Make core logic testable
Core logic should be testable without requiring:

- network access
- LLM API calls
- filesystem access to real codebases
- running C/C++ compilers or MPI
- framework bootstrapping

Prefer dependency injection or thin adapters around external systems.

### 6) Prefer simple composition
Prefer:

- small functions
- clear data flow
- composition over deep inheritance
- explicit dependencies over implicit globals

Avoid unnecessary indirection.

---

## Change workflow

For every non-trivial change, follow this process.

### Step 1: Understand before editing
Before coding:

1. identify relevant files and modules
2. identify reusable code
3. identify likely duplication risks
4. identify architectural boundaries that must be preserved

### Step 2: Plan first
Before implementation, produce a short plan that includes:

- files to modify
- why each file needs changes
- reusable code that will be used
- any new module or abstraction to introduce
- why the new abstraction is necessary
- **corner cases and failure scenarios** identified for the change (see Corner case analysis below)

### Step 3: Implement minimal clean change
Implement the smallest change that:

- solves the problem
- preserves architecture
- avoids duplication
- keeps interfaces clean
- **handles all identified corner cases** from the plan

### Step 4: Review your own diff
After implementation, review for:

- duplicated logic
- mixed responsibilities
- unnecessary coupling
- oversized functions/files
- dead code
- unclear naming
- avoidable breaking changes
- **unhandled corner cases** — revisit the list from Step 2 and verify each is addressed

Then refine.

---

## Corner case analysis

**Every** plan, implementation, and fix must include explicit corner case analysis. This is not optional — skipping it leads to fragile code that breaks on real-world input.

### When to analyze

Corner case analysis is required at **three** stages:

1. **During planning (Step 2)**: list corner cases as part of the plan. If you cannot identify any, state why the change is trivially safe.
2. **During implementation (Step 3)**: handle each identified corner case in the code.
3. **During review (Step 4)**: verify every listed corner case is addressed. Look for ones you missed.

### What to consider

For every change, systematically ask:

#### Data corner cases
- **Empty/null/missing**: what happens with empty strings, empty lists, None values, missing keys, missing files?
- **Boundary values**: zero, negative numbers, maximum values, off-by-one, first/last element
- **Unexpected types or formats**: wrong type, malformed input, unexpected encoding, extra whitespace, special characters
- **Duplicates**: duplicate entries, duplicate keys, repeated calls to the same function

#### State corner cases
- **Race conditions**: concurrent access, interleaved operations, stale state
- **Ordering**: does the code assume a specific order that is not guaranteed?
- **Partial failure**: what if the operation succeeds halfway? Is the state left consistent?
- **Re-entrancy**: what if this function or endpoint is called again before the first call finishes?

#### Integration corner cases
- **Network/I/O failures**: LLM API timeouts, connection refused, partial responses, empty responses, rate limits
- **External tool failures**: compiler errors, missing build tools, MPI not installed, VeloC library not found
- **Process execution**: non-zero exit codes, hanging processes, output too large, stderr mixed with stdout
- **External data changes**: what if the target codebase changes between analysis and injection?
- **Missing dependencies**: what if a required file, library, or tool does not exist?

#### LLM/agent corner cases
- **Malformed LLM output**: response doesn't match expected schema, truncated response, refusal
- **Tool call errors**: agent calls a tool with invalid arguments, tool returns unexpected result
- **Streaming interruptions**: SSE connection drops mid-stream, client disconnects
- **Token limits**: input too large for context window, response truncated

#### Code analysis corner cases
- **Unsupported code patterns**: code that doesn't match regex patterns, preprocessor macros, templates
- **Multi-file programs**: includes, headers, conditional compilation
- **Non-standard build systems**: custom Makefiles, mixed CMake/Make, missing build configuration

### How to document

In the plan, add a **Corner cases** section listing each identified case and how it will be handled. Use this format:

```
### Corner cases
- empty source file → return empty analysis, do not error
- LLM returns malformed JSON → parse error with context, allow retry
- build command fails → capture stderr, report in validation result
- MPI not installed → detect early, warn user, skip MPI-specific analysis
```

If a corner case is intentionally not handled (e.g., out of scope), state that explicitly with the reason.

### Rules

- **Never assume inputs are well-formed** unless validated at the boundary
- **Never assume external calls succeed** — always handle the failure path
- **Never assume collections are non-empty** — check before accessing first/last elements
- **Never assume state is unchanged** between async operations
- **Test corner cases** — every identified corner case should have a corresponding test (or be covered by an existing one)

---

## Architecture rules

### Project structure

The project follows this high-level organization:

| Directory | Purpose |
|-----------|---------|
| `guard_agent/` | Core library: CLI, analysis, planning, validation, MCP server, schemas |
| `agents/veloc/` | LLM-powered VeloC deployment agent (tool-calling, streaming, web UI) |
| `orchestrator/` | FastAPI orchestrator service for code transformation |
| `shared/` | Shared Pydantic schemas across packages |
| `validation/veloc/` | Validation framework: build, run, compare, report |
| `docs/` | User-facing documentation |

### Layering
When relevant, organize code into layers such as:

- `cli.py` or `routes/` for external entry points
- agent logic and orchestration for workflows
- analysis, planning, and validation for core domain logic
- tool implementations for external system interaction (file I/O, process execution)
- `schemas.py` for data models
- `config.py` for configuration

Do not mix these layers unnecessarily.

### Dependency direction
Prefer this direction:

`cli/api -> agent/orchestration -> domain logic -> tool adapters`

Rules:

- domain code (analysis, planning) should not depend on CLI or API framework code
- tool adapters (file I/O, process execution) should be replaceable
- higher-level logic should depend on abstractions, not concrete low-level details, when that meaningfully improves design

### Utility discipline
Do not create a "utils" dumping ground.

A helper belongs in shared code only when at least one of these is true:

- it is reused across packages
- it is clearly generic
- it has a stable, focused responsibility

If it is specific to one module, keep it near that module.

---

## Modularity rules

### Functions
Prefer functions that are:

- short
- named by intent
- side-effect-aware
- easy to test independently

As a guideline:

- avoid functions longer than ~40 lines unless clearly justified
- extract nested logic that has a nameable purpose

### Files
As a guideline:

- avoid oversized files
- split files when they contain multiple distinct responsibilities
- keep related code together, but do not accumulate unrelated helpers

### Classes
Use classes when they provide real value, such as:

- managing meaningful state (e.g., agent session, validation runner)
- encapsulating a domain concept (e.g., checkpoint plan, code inspection)
- providing a clean interface over a subsystem

Do not create classes just to wrap a few functions.

### Abstractions
Create a new abstraction only when it improves one of these:

- reuse
- readability
- testability
- separation of concerns
- future extension with clear evidence

Do not build speculative frameworks for one use case.

---

## Code reuse rules

Before adding code, check whether similar logic already exists.

When you find similar logic:

- prefer extending the existing implementation
- or extract shared behavior into a focused helper/module
- update callers carefully
- remove obsolete duplicated code where safe

Do not copy and slightly edit blocks across files.

When extracting shared code:

- keep the abstraction concrete enough to stay readable
- avoid introducing broad, vague helper APIs

---

## Naming rules

Names should reveal intent.

Prefer:

- domain words over vague technical words
- `analyze_source_file()` over `handle_data()`
- `build_checkpoint_plan()` over `process_input()`
- `validate_injection()` over `run_check()`

Avoid vague names like:

- `utils`
- `helpers`
- `manager`
- `common`
- `misc`
- `doStuff`

unless the scope is very clearly justified.

---

## Pydantic schema rules

This project uses Pydantic v2 extensively for data validation and serialization.

- define all data contracts as Pydantic `BaseModel` subclasses in `schemas.py` files
- use `Field()` with descriptions for API-facing models
- prefer strict types and validators over permissive `Any` fields
- keep schema files focused — one per package or domain area
- do not scatter model definitions across business logic files
- use `model_validator` or `field_validator` for complex cross-field validation
- return Pydantic models from core functions, not raw dicts

---

## LLM agent rules

### Tool definitions
- keep tool functions small and focused — one tool, one action
- tool functions should validate inputs before executing
- always return structured results (not free-form strings) when possible
- handle tool execution errors gracefully — return error info, do not crash the agent loop
- document tool parameters clearly for the LLM

### Agent loop
- the agent's tool-calling loop must be resilient to malformed LLM responses
- implement proper stop conditions — do not allow infinite tool-calling loops
- log each tool call and result for observability and debugging
- keep agent orchestration logic separate from tool implementation
- support both streaming and non-streaming execution paths

### LLM client configuration
- centralize LLM client setup (model, API key, base URL) in config modules
- support multiple providers (OpenAI, Argo, generic) via configuration, not code branches
- never hardcode API keys or model names in business logic

---

## CLI rules

This project uses Click for its CLI interface.

- keep CLI command handlers thin — delegate to core logic immediately
- validate CLI arguments at the boundary, pass clean data to business logic
- use Click's built-in validation (types, choices, callbacks) rather than manual checks
- provide clear `--help` text for all commands and options
- handle errors at the CLI level with user-friendly messages — do not let raw tracebacks escape

---

## FastAPI rules

For the orchestrator and web UI services:

- define request/response models as Pydantic schemas
- keep route handlers thin — delegate to service or domain functions
- use dependency injection for shared resources (LLM clients, config)
- handle errors with appropriate HTTP status codes and structured error responses
- for SSE/streaming endpoints, handle client disconnection gracefully

---

## Error handling

- handle errors close to the right boundary
- do not swallow exceptions silently
- return useful errors with enough context
- separate business-rule failures from infrastructure failures (LLM errors, build failures, I/O errors)
- keep error-handling paths readable

For external systems (LLM APIs, subprocess execution, file I/O), wrap low-level errors where useful so calling code sees domain-relevant failures.

---

## Configuration and constants

- avoid hardcoding environment-specific values in business logic
- keep config centralized (`.env` files, `config.py`, `.guard-agent.yaml`)
- prefer explicit config over scattered constants
- keep defaults safe and discoverable
- use `pydantic-settings` for environment variable loading where applicable

---

## Logging and observability

- log at boundaries and important state transitions (tool calls, LLM requests, build/run steps)
- avoid noisy logs inside tight inner loops unless needed
- include useful identifiers and context (session ID, file being analyzed, step name)
- do not leak secrets or sensitive data (API keys, tokens)
- use structured logging where feasible for agent session tracing

---

## Testing expectations

Every meaningful change **must** include tests. Tests **must** pass before any git commit.

### Mandatory workflow

1. Write or update tests for every new feature, bug fix, or behavior change
2. Run the full test suite: `python -m pytest tests/ -x`
3. All tests must pass before committing
4. If a test fails, fix the code or the test — never skip or delete passing tests

### Test tiers

- **Tier 1 — Unit tests**: Pure functions with no I/O (regex parsing, plan generation, schema validation, output comparison). No mocking needed.
- **Tier 2 — Tool/adapter tests**: File I/O, subprocess execution, config loading — use temporary directories and mock subprocesses.
- **Tier 3 — Integration tests**: FastAPI endpoints using test client, MCP tool invocations, CLI commands via Click test runner.
- **Tier 4 — Agent workflow tests**: Multi-step agent scenarios with mocked LLM responses.

Prefer:

- unit tests for core logic (analysis, planning, comparison)
- integration tests for API and CLI boundaries
- end-to-end tests only for critical flows

Test design rules:

- test behavior, not implementation trivia
- cover success cases, edge cases, and failure paths
- keep tests readable
- mock LLM responses — do not call real LLM APIs in tests
- avoid brittle timing-based tests when possible

When adding new logic:

- add tests for the new behavior
- update existing tests where behavior changes
- refactor code that is unnecessarily hard to test

### Running tests

```bash
# Run all tests (must pass before commit)
python -m pytest tests/ -x

# Run with verbose output
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/test_analyzer.py -v

# Run with coverage report
python -m pytest tests/ --cov=guard_agent --cov-report=term-missing
```

---

## Backward compatibility

Unless explicitly asked to break compatibility:

- preserve public interfaces (CLI commands, MCP tools, API endpoints)
- preserve configuration file formats (`.guard-agent.yaml`, `veloc.cfg`)
- preserve Pydantic schema contracts
- preserve existing behavior where reasonable
- make breaking changes explicit in the plan

When changing an interface, explain:

- what changed
- why it changed
- impact on callers
- migration path if needed

---

## Performance and simplification

Do not overcomplicate code in the name of performance without evidence.

Prefer:

1. clear code first
2. measure bottlenecks
3. optimize targeted hotspots
4. keep optimized code isolated and documented

A simpler design is usually better than a clever one.

---

## Documentation expectations

For non-trivial changes, update relevant documentation:

- docstrings for public functions/classes
- README or usage docs if behavior changes
- inline comments only where the reasoning is not obvious from code

Comment the "why", not the obvious "what".

---

## Forbidden patterns

Avoid these unless explicitly justified:

- copy-paste reuse
- giant multi-purpose classes
- long functions with mixed responsibilities
- hidden global state
- tightly coupling core logic to frameworks or I/O
- introducing abstractions for hypothetical future needs
- broad "utils" modules full of unrelated code
- silent exception handling
- magic constants scattered across files
- hardcoded API keys, model names, or endpoint URLs in business logic
- calling real LLM APIs in tests

---

## Required output format for coding tasks

For substantial tasks, respond in this structure:

### 1. Design plan
- relevant files
- intended changes
- reusable code found
- any new abstractions and why
- **corner cases** identified and how each will be handled

### 2. Implementation
- make the minimal clean change
- preserve architecture
- avoid duplication

### 3. Self-review
Explicitly check for:

- duplicated logic
- mixed concerns
- unclear interfaces
- **unhandled corner cases** — verify every case from the plan is addressed
- unnecessary new files
- oversized functions/classes
- test gaps

Revise before finalizing.

---

## Refactoring guidance

When touching messy code, do not rewrite everything without reason.

Prefer:

- incremental refactoring
- local cleanup around the changed area
- extraction of well-defined helpers
- preserving behavior while improving structure

Refactor enough to improve maintainability, but keep the diff controlled.

---

## Decision rules

When unsure, prefer the option that is:

1. simpler
2. more modular
3. easier to test
4. easier to extend
5. less duplicated
6. less coupled to infrastructure

---

## Example expectations

Good change:
- reuses an existing analysis module
- extracts validation into a small helper
- keeps CLI/API handlers thin
- adds unit tests for the core logic

Bad change:
- adds a second code parser in another file
- mixes CLI parsing, file I/O, LLM calls, and validation logic
- duplicates checkpoint template generation code
- adds no tests

---

## Issue tracking

All issues, feature requests, and improvements are tracked in `ISSUES.md` at the repository root.

### What gets tracked

`ISSUES.md` tracks **all** of the following:

- **Bug reports** — something is broken or behaves unexpectedly
- **Feature requests** — new functionality the user asks for
- **Improvements** — enhancements to existing behavior (analysis accuracy, performance, streaming, etc.)

Every non-trivial change must have a corresponding entry in `ISSUES.md` — not just bugs.

### Mandatory workflow

1. **When the user reports an issue or requests a feature**: before adding a new entry, **read `ISSUES.md` first** and check whether the same issue already exists:
   - If **Open**: do not duplicate — work on the existing entry.
   - If **Solved**: the previous fix may not have worked. Re-read the resolution, verify the current code, and investigate why it failed. Update the existing entry (revert to **Open** with a note) rather than creating a new one.
   - If **Closed**: the fix was confirmed but the problem has regressed. Reopen the existing entry (set back to **Open**) and note the regression.
   - If no matching issue exists: add a new entry with status **Open**, a clear explanation, and a proposed resolution approach.
2. **When planning a new feature or improvement**: add an entry with status **Open** before implementation begins. This ensures the proposed plan is visible and trackable. Include the scope and expected behavior in the explanation.
3. **When you implement a fix or feature**: update the issue status to **Solved** and note the resolution approach taken.
4. **When the user confirms the fix works**: update the issue status to **Closed**.

Never skip updating `ISSUES.md` — it is the single source of truth for known problems and planned work. Check it at the start of each session to see if there are open issues that need attention.

---

## Final instruction

Do not just make the code work.  
Make it easy to understand, easy to test, easy to reuse, and easy to extend.
