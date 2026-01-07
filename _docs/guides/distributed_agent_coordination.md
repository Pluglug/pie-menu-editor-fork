# Distributed Agent Coordination Guide

> **Status**: Experimental (2026-01-08)
> **Context**: PME2 Phase 9-D investigation
> **Purpose**: Document and evaluate multi-agent coordination patterns

---

## Background

### The Problem

Large refactoring projects often involve multiple interconnected tasks:
- Each task requires deep context to solve properly
- Tasks have dependencies but also some independence
- A single agent session may hit context limits
- "Reading everything again" is expensive (tokens, time, coherence)

### The Experiment

PME2 Phase 9-D encountered blocking issues. We created 4 investigation branches:
- `investigate/9d1-property-crash` - PROPERTY mode crash analysis
- `investigate/9d2-hpg-mystery` - HPANEL prefix investigation
- `investigate/9d3-extend-target` - extend_target design review
- `investigate/9d4-editor-io` - Editor I/O architecture study

Each branch maintained its own context (diagnosis reports, code understanding).
The question: **Can we preserve and leverage these specialized contexts?**

---

## Coordination Model

### Roles

| Role | Responsibility |
|------|---------------|
| **Composer** (human or designated agent) | Orchestration, final decisions, conflict resolution |
| **Specialist Agents** (9d1, 9d2, etc.) | Deep investigation, implementation within scope |
| **GitHub Issue** | Meeting point, contract storage, async communication |

### Workflow

```
1. Composer creates/updates Issue with current contract
2. Specialist reads Issue body (contract) + recent comments
3. Specialist works on their branch
4. Specialist comments with findings/proposals
5. Other specialists respond (if needed)
6. Composer updates Issue body when consensus reached
7. Specialist implements agreed changes
8. Merge to main branch
9. Next specialist takes over (relay)
```

### Issue as Contract

The Issue body serves as the "source of truth":

```markdown
## Confirmed Decisions
- uid: PMItem direct field (all modes)
- extend_target: pm.data via schema (PANEL/DIALOG/RMENU only)

## Open Questions
- HPANEL prefix: hp or hpg?

## Next Actions
- Waiting for [9d3-agent]: Confirm alignment
- After consensus: Implementation begins
```

---

## Communication Rules

### 1. Identify Yourself

```markdown
**[9d2-agent]**

Your comment content here...
```

All GitHub comments appear as the same user. Agent identification prevents confusion.

### 2. Reference, Don't Embed

```markdown
# Good
See commit `ae94515` lines 141-152 for the implementation.
Ref: editors/property.py:369 - prop_by_type()

# Bad
Here's the code:
```python
def prop_by_type(prop_type, is_vector=False):
    name = "VectorProperty" if is_vector else "Property"
    ...
`` `
```

Code embedding explodes context. References keep it manageable.

### 3. Three-Comment Convergence

If a topic doesn't converge in 3 comments:
- The scope is too large
- Split into a new Issue
- Or escalate to Composer for decision

### 4. Explicit Handoff

End comments with clear next steps:

```markdown
**Waiting for [9d3-agent]**: Please confirm uid implementation approach.

**Ready for implementation**: No blockers, proceeding with uid field addition.

**Blocked**: Need Composer decision on prefix naming convention.
```

### 5. Update Issue Body

After consensus, Composer updates the Issue body:
- Move items from "Open Questions" to "Confirmed Decisions"
- Update "Next Actions"
- Keep Issue body as the canonical reference

---

## Comparison with Alternatives

### Single Agent Pair Programming

| Aspect | Single Agent | Distributed Relay |
|--------|-------------|-------------------|
| Coordination cost | Zero | High |
| Context consistency | High (one session) | Low (Issue-mediated) |
| Specialization depth | Limited | Deep |
| Failure blast radius | Entire project | Local to branch |
| Scalability | Difficult | Possible |
| Long-term projects | Context limits | Context preserved |

**When to use single agent**: Small tasks, tight deadlines, simple dependencies.

**When to use distributed**: Multiple independent concerns, long-term projects, need for deep specialization.

### Auto Claude / Fully Automated

```
Manual ←──────────────────────────────────────→ Fully Automated

   Single Agent    Our Approach         Auto Claude
   Pair Prog      (Human Composer)     (Auto Orchestration)
       │               │                    │
   Safe, Limited   Experimental        Ambitious, Risky
```

Our approach keeps human as the orchestrator. This is more conservative but safer for production codebases.

---

## Advantages

### 1. Specialized Context Preservation

Each agent maintains deep understanding of their domain:
- 9d1 knows PROPERTY mode internals
- 9d2 understands prefix conventions
- 9d3 has thought through uid/extend_target design

This context would be expensive to rebuild in a new session.

### 2. Failure Localization

If 9d2 goes in the wrong direction:
- 9d3's work is unaffected
- Easy to discard 9d2's branch and retry
- Single agent mistakes propagate everywhere

### 3. Reviewability

Human can review each branch independently:
- Smaller, focused changes
- Clear responsibility ("9d2 did this")
- Easier to catch mistakes

### 4. Parallelization Potential

If tasks are truly independent:
- Multiple agents can work simultaneously
- Clock time reduction
- (Not yet tested in this experiment)

---

## Disadvantages

### 1. Coordination Overhead

Time spent on:
- Branch synchronization
- Issue management
- "Which agent goes next?" decisions
- Resolving communication ambiguities

This time is zero in single-agent mode.

### 2. Information Asymmetry

Each agent only sees:
- Their own branch's code
- Issue body and comments
- Referenced commits (if they fetch them)

They don't see:
- Other branches' uncommitted work
- The "why" behind others' decisions (only the "what")
- Real-time state of other work

### 3. Cognitive Load Transfer

Coordination burden shifts to the Composer (usually human):
- Must understand all domains
- Must detect conflicts early
- Must keep Issue body updated

If Composer loses track, the system fails.

### 4. Merge Risk

If multiple branches modify the same files:
- Merge conflicts
- Semantic conflicts (harder to detect)
- Integration testing burden

Mitigation: Strict file boundaries or relay (sequential) execution.

---

## When This Approach Works

### Good Fit

1. **Investigation/diagnosis phase**: Deep, independent analysis
2. **Loosely coupled features**: Different files, clear interfaces
3. **Long-term projects**: Context needs to survive across sessions
4. **Multiple expertise domains**: Each agent specializes

### Poor Fit

1. **Tightly coupled changes**: Same files, interleaved logic
2. **Short tasks**: Coordination overhead exceeds benefit
3. **Unclear requirements**: Need rapid iteration with human
4. **Single domain**: No specialization benefit

### PME2 Evaluation

| Phase | Distributed Value |
|-------|------------------|
| Investigation (9d1-4 diagnosis) | **High** - Deep analysis achieved |
| Implementation (Phase 9-X) | **Medium** - Dependencies exist, relay needed |
| Testing/Polish | **Low** - Single agent sufficient |

---

## Refinement Directions

### 1. Contract-Driven Development

Stronger contracts before implementation:

```yaml
# _docs/contracts/phase9x.yaml
confirmed:
  uid:
    location: PMItem
    type: StringProperty
    generator: generate_uid(mode)
  extend_target:
    location: pm.data
    types: [pg, pd, rm]

interfaces:
  - name: generate_uid
    signature: (mode: str) -> str
    owner: 9d3-agent
```

### 2. Event Markers

File-based signals instead of Issue comments:

```
_docs/events/
  9d3_uid_complete.md      # Existence = milestone reached
  9d2_awaiting_9d3.md      # Blocked state
```

Machine-readable, git-tracked, less ambiguous.

### 3. Structured Reports

Standardized output format:

```yaml
agent: 9d3
branch: investigate/9d3-extend-target
status: complete
changes:
  - file: pme_types.py
    action: add_field
    name: uid
commits: [abc123, def456]
next: 9d2
```

### 4. Automated Sync

Script to update all worktrees:

```bash
#!/bin/bash
for wt in A B C D; do
  cd "$WORKTREE_$wt"
  git fetch origin
  git merge origin/pme2-dev
done
```

Reduces manual coordination.

---

## Experiment Results: Issue #89 Coordination (2026-01-08)

### Overview

| Metric | Result |
|--------|--------|
| Participating agents | 5 (composer, 9d1, 9d2, 9d3, 9d4) |
| Total comments | 4 (after duplicate removal) |
| Time to consensus | ~2 hours |
| Outcome | Success - 7 decisions confirmed |

### Comment Flow

```
1. [pme2-dev-composer] - Review & coordination rules proposal
2. [9d3-agent] - Agreement + Option C (Incremental) proposal
3. [9d2-agent] - HPANEL exception clarification
4. [9d4-agent] - Self-retraction, pm.data sufficient
```

### Confirmed Decisions

| Item | Decision | Agreed By |
|------|----------|-----------|
| `uid` | PMItem direct field | All |
| `extend_target` | pm.data via schema (pg, pd, rm) | All |
| `extend_position` | pm.data via schema | 9d3, composer |
| `prop_type` | pm.data via schema (prop) | 9d1, composer |
| HPANEL | No extend_target, settings `{}` | 9d2, composer |
| HPANEL prefix | `hpg` (fix converter.py) | 9d2, composer |
| Editor I/O methods | NOT needed | 9d4 (retracted) |

### What Worked

1. **Convergence**: 4 comments reached consensus on 7 decisions
2. **Knowledge integration**: Each specialist contributed unique insights
   - 9d1: pm.data as carrier concept
   - 9d2: HPANEL exception discovery
   - 9d3: EXTENDED_PANELS key problem
   - 9d4: Self-correction (over-engineering recognition)
3. **Explicit handoff**: "Waiting for [agent]" pattern helped flow
4. **Reference-based**: Commit IDs and file paths avoided code bloat

### Issues Encountered

1. **Agent ID inconsistency**: 9d3, 9d2 initially forgot `**[agent-id]**` prefix
   - **Fix**: Composer edited comments post-hoc via gh api
2. **Duplicate comment**: 9d2 posted twice (correction attempt)
   - **Fix**: Composer deleted duplicate via gh api
3. **Scope creep**: 9d3's C-4, C-5 phases exceeded #89 scope
   - **Status**: Marked "Under Review" in Issue body for human decision

### Lessons Learned

1. **Issue body as contract works**: "Confirmed Decisions" section provided clarity
2. **Self-correction is valuable**: 9d4 retracting own diagnosis shows agents can peer-review
3. **Human intervention still needed**: C-4/C-5 scope decision requires human judgment
4. **gh api is powerful**: Comment editing, deletion enabled Issue cleanup

### Process Adjustments Made

| Adjustment | Reason |
|------------|--------|
| Added `**[agent-id]**` to all comments | Prevent confusion |
| Removed duplicate 9d2 comment | Clean Issue history |
| Added "Confirmed Decisions" to Issue body | Single source of truth |
| Added "Under Review" section | Flag items needing human decision |

### Context Usage Analysis

| Agent | Context Used | Status | Notes |
|-------|-------------|--------|-------|
| pme2-dev (composer) | 70% | OK | Coordination overhead |
| 9d1 | 74% | OK | PROPERTY mode deep dive |
| 9d2 | 80% | Near limit | HPANEL investigation |
| 9d3 | 90% | Critical | Most complex analysis (extend_target + uid) |
| 9d4 | 60% | OK | Lighter scope (retracted early) |

**Key Observations**:

1. **Distributed context is real**: 5 agents × ~75% avg = ~375% of single-agent capacity
2. **Specialization has cost**: 9d3's deep analysis consumed 90% - near the limit
3. **Manual compact timing matters**: Auto-compact disabled; human decides when to compact

**Compact Strategy (Human Composer)**:

```
Timing considerations:
- Before major implementation phase
- After consensus reached (diagnosis context less critical)
- Preserve: confirmed decisions, file locations, function signatures
- Discard: exploration dead-ends, rejected approaches, verbose logs
```

**Trade-off**:

| Approach | Context Cost | Quality | Human Burden |
|----------|-------------|---------|--------------|
| Single agent | 100% | Limited depth | Low |
| Distributed (5 agents) | ~375% | Deep specialization | High (compact timing) |

The distributed approach trades **context tokens** for **specialization depth**. Human must manage compact timing to prevent context exhaustion before task completion.

### Distributed Compact as Advantage

Paradoxically, context management is also a **benefit** of distributed relay:

| Aspect | Single Agent | Distributed Relay |
|--------|-------------|-------------------|
| Compact granularity | All or nothing | Per-agent selective |
| Compact timing | Forced at 100% | Human-controlled per agent |
| Information loss risk | High (entire context) | Low (other agents retain) |
| External backup | None | Issue body preserves decisions |
| Natural checkpoints | None | Phase transitions (investigation → implementation) |

**Why this matters**:

1. **Selective compact**: 9d3 at 90% can be compacted while 9d4 at 60% retains full context
2. **Safe compact**: Confirmed decisions live in Issue #89, not just in agent memory
3. **Phase-aligned**: "Investigation complete" is a natural compact point - discard exploration, keep conclusions
4. **Parallel preservation**: While one agent compacts, others maintain continuity

**Example**:
```
Before 9d3 compact:
  - 90% used on extend_target exploration
  - Dead ends: direct PMItem field approach (rejected)
  - Keep: pm.data decision, schema registration plan

After 9d3 compact:
  - Freed context for uid implementation
  - Lost: why PMItem direct was rejected (but Issue #89 has summary)
  - Retained: what to implement, where, how
```

This is a form of **distributed memory** - the system's knowledge is spread across agents + Issue, making individual agent compact less catastrophic.

### Evaluation Against Criteria

| Criterion | Result |
|-----------|--------|
| 3-comment convergence | ✅ (4 comments, acceptable) |
| Agent ID compliance | △ (required post-hoc fix) |
| Reference-based communication | ✅ |
| Explicit handoff | ✅ |
| Knowledge integration | ✅ |
| Human could follow | ✅ |
| Context management | △ (9d3 at 90%, requires careful compact) |

**Overall**: First experiment **successful with minor issues**. The coordination model is viable for investigation-to-implementation handoff. Context management is a hidden cost requiring human attention.

---

## Evaluation Criteria

At experiment end, evaluate:

### Quantitative

| Metric | Measurement |
|--------|-------------|
| Total time | Start to merge completion |
| Coordination time | Issue management, sync, decisions |
| Rework | Discarded commits, reverted changes |
| Merge conflicts | Count and resolution time |

### Qualitative

| Criterion | Questions |
|-----------|-----------|
| Context value | Did specialization produce better solutions? |
| Communication clarity | Were Issue comments sufficient? |
| Human burden | Was Composer role sustainable? |
| Failure handling | How well did we recover from mistakes? |

### Success Indicators

- [ ] All tasks completed without major rework
- [ ] Issue comments converged in ≤3 rounds
- [ ] No semantic merge conflicts
- [ ] Human could follow and intervene when needed
- [ ] Specialists maintained useful context

### Failure Indicators

- [ ] Excessive coordination time (>30% of total)
- [ ] Repeated miscommunication
- [ ] Merge conflicts requiring significant resolution
- [ ] Human lost track of overall state
- [ ] Context didn't provide value (could have just re-read)

---

## References

- [Auto Claude](https://github.com/AndyMik90/Auto-Claude) - Parallel agent orchestration
- GitHub Issues as coordination: This experiment
- PME2 Phase 9-D: #88, #89

---

## Appendix: PME2 Experiment Setup

### Worktrees

```
E:/0339_Blender version archive/blender-5.0.1-A/.../pie_menu_editor  → 9d1
E:/0339_Blender version archive/blender-5.0.1-B/.../pie_menu_editor  → 9d2
E:/0339_Blender version archive/blender-5.0.1-C/.../pie_menu_editor  → 9d3
E:/0339_Blender version archive/blender-5.0.1-D/.../pie_menu_editor  → 9d4
E:/0187_Pie-Menu-Editor/MyScriptDir/addons/pie_menu_editor           → pme2-dev (composer)
```

### Coordination Issue

- #89: Phase 9-X Internal Implementation Strategy

### Agent Responsibilities

| Agent | Domain | Key Insight |
|-------|--------|-------------|
| 9d1 | PROPERTY mode | poll_cmd dual-use problem |
| 9d2 | HPANEL prefix | hpg vs hp confusion |
| 9d3 | extend_target design | settings placement, uid need |
| 9d4 | Editor I/O | pm.data approach eliminates need |
| composer | Orchestration | Relay coordination, Issue management |

---

*This document will be updated with experiment results and lessons learned.*
