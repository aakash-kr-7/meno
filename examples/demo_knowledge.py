"""
MENO Intelligence Platform — Interactive Demo
Shows: define context -> store typed knowledge -> relate objects ->
retrieve with expansion -> walk graph -> session promotion.
Run: python examples/demo_knowledge.py
Requires: docker compose up --build (API at localhost:8000)
No external LLM API key needed.
"""

import os
import sys
import time

# Ensure python SDK is in import search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sdk", "python")))

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


def print_title(text: str):
    if HAS_RICH:
        console.print(Panel(f"[bold cyan]{text}[/bold cyan]", border_style="cyan"))
    else:
        print(f"\n=== {text} ===")


def print_step(text: str):
    if HAS_RICH:
        console.print(f"[bold yellow]>> {text}[/bold yellow]")
    else:
        print(f"\n>> {text}")


def print_info(text: str):
    if HAS_RICH:
        console.print(f"[green]{text}[/green]")
    else:
        print(text)


def print_error(text: str):
    if HAS_RICH:
        console.print(f"[bold red]ERROR: {text}[/bold red]")
    else:
        print(f"ERROR: {text}")


# Main execution flow
def main():
    print_title("MENO Intelligence Platform — Interactive Demo")
    print_info("Starting client initialization...")

    from meno import Meno, MenoError, KnowledgeType, RelationshipType, ContextType

    try:
        sdk = Meno(base_url="http://localhost:8000")
    except Exception as e:
        print_error(f"Failed to initialize MENO client: {e}")
        return

    # Count tracking for final complete message
    total_objects_stored = 0
    total_relationships_created = 0

    # -------------------------------------------------------------------------
    # PHASE 1: define_context("project", "sol_demo")
    # -------------------------------------------------------------------------
    print_step("PHASE 1: Define context")
    try:
        ctx = sdk.define_context(
            context_type=ContextType.PROJECT.value,
            context_id="sol_demo",
            metadata={"name": "Sol Demo Project", "description": "Interactive demonstration context"}
        )
        print_info(f"Context defined: project:sol_demo (ID: {ctx.id})")
    except MenoError as me:
        print_error(f"Meno API error in Phase 1: {me.status_code} - {me}")
        return
    except Exception as e:
        print_error(f"Failed to define context: {e}")
        return

    # -------------------------------------------------------------------------
    # PHASE 2: store CODE_PATTERN + DECISION + BUG_REPORT, all with context_id
    # -------------------------------------------------------------------------
    print_step("PHASE 2: Store typed knowledge")
    try:
        # 1. Store CODE_PATTERN
        pattern_res = sdk.store(
            user_id="demo_user",
            content="Batch processing pattern for Postgres using executemany with chunks of 500.",
            type=KnowledgeType.CODE_PATTERN.value,
            title="Postgres Batch Execution Pattern",
            context_ids=[ctx.id]
        )
        total_objects_stored += 1
        print_info(f"Stored CODE_PATTERN: ID={pattern_res.id} type={pattern_res.type} content='{pattern_res.content}'")

        # 2. Store DECISION
        decision_res = sdk.store(
            user_id="demo_user",
            content="We decided to use chunks of 500 in Postgres batch queries to balance performance and memory usage.",
            type=KnowledgeType.DECISION.value,
            title="Postgres Batch Chunk Size Decision",
            context_ids=[ctx.id]
        )
        total_objects_stored += 1
        print_info(f"Stored DECISION: ID={decision_res.id} type={decision_res.type} content='{decision_res.content}'")

        # 3. Store BUG_REPORT
        bug_res = sdk.store(
            user_id="demo_user",
            content="Postgres connection pool exhausted during high concurrency batching operations.",
            type=KnowledgeType.BUG_REPORT.value,
            title="Database Connection Pool Exhaustion Bug",
            context_ids=[ctx.id]
        )
        total_objects_stored += 1
        print_info(f"Stored BUG_REPORT: ID={bug_res.id} type={bug_res.type} content='{bug_res.content}'")

    except MenoError as me:
        print_error(f"Meno API error in Phase 2: {me.status_code} - {me}")
        return
    except Exception as e:
        print_error(f"Failed to store knowledge objects: {e}")
        return

    # -------------------------------------------------------------------------
    # PHASE 3: relate DECISION->CODE_PATTERN with IMPLEMENTS
    # -------------------------------------------------------------------------
    print_step("PHASE 3: Relate objects")
    try:
        rel_res = sdk.relate(
            source_id=decision_res.id,
            target_id=pattern_res.id,
            relationship_type=RelationshipType.IMPLEMENTS.value,
            confidence=0.9,
            explanation="Postgres batch execution pattern implements the batch chunk size decision"
        )
        total_relationships_created += 1
        print_info(f"Linked: decision IMPLEMENTS code_pattern (Relationship ID: {rel_res.id})")
    except MenoError as me:
        print_error(f"Meno API error in Phase 3: {me.status_code} - {me}")
        return
    except Exception as e:
        print_error(f"Failed to link objects: {e}")
        return

    # -------------------------------------------------------------------------
    # PHASE 4: retrieve("how do we handle batching?", expand_relationships=True, context_id=...)
    # -------------------------------------------------------------------------
    print_step("PHASE 4: Retrieve with expansion")
    try:
        results = sdk.retrieve(
            user_id="demo_user",
            query="how do we handle batching?",
            context_id=ctx.id,
            expand_relationships=True
        )

        if results:
            top_result = results[0]
            print_info(f"Top result retrieved: Title: '{top_result.title}' | Score: {top_result.score:.4f} | Type: {top_result.type}")
            print_info(f"Content: {top_result.content}")
            print_info(f"Relationships: {top_result.relationships}")
        else:
            print_info("No retrieval results returned.")
    except MenoError as me:
        print_error(f"Meno API error in Phase 4: {me.status_code} - {me}")
        return
    except Exception as e:
        print_error(f"Failed to retrieve objects: {e}")
        return

    # -------------------------------------------------------------------------
    # PHASE 5: get_graph(code_pattern_id, max_depth=2)
    # -------------------------------------------------------------------------
    print_step("PHASE 5: Walk graph")
    try:
        graph = sdk.get_graph(object_id=pattern_res.id, max_depth=2)
        print_info(f"Graph root: {graph.root}")
        print_info("Nodes in Subgraph:")
        for idx, node in enumerate(graph.nodes):
            print_info(f"  [{idx}] ID={node.get('id')} | Type={node.get('type')} | Content='{node.get('content')}'")
        print_info("Edges in Subgraph:")
        for idx, edge in enumerate(graph.edges):
            print_info(f"  [{idx}] Source={edge.get('source')} --({edge.get('type')})--> Target={edge.get('target')}")
    except MenoError as me:
        print_error(f"Meno API error in Phase 5: {me.status_code} - {me}")
        return
    except Exception as e:
        print_error(f"Failed to walk graph: {e}")
        return

    # -------------------------------------------------------------------------
    # PHASE 6: create_session, append 3 messages, promote_session, get_extracted_from_session
    # -------------------------------------------------------------------------
    print_step("PHASE 6: Session promotion and extraction")
    try:
        session = sdk.create_session(user_id="demo_user")
        print_info(f"Session created: ID={session.id}")

        # Message 1
        sdk.append_message(
            session_id=session.id,
            role="user",
            content="Hello, let's review the database performance issues we observed."
        )
        # Message 2 (Matches BUG_REPORT due to keyword 'fails')
        sdk.append_message(
            session_id=session.id,
            role="assistant",
            content="Yes, our Postgres batch insertion fails under high load, causing connection pool exhaustions."
        )
        # Message 3 (Matches DECISION due to keyword 'decided')
        sdk.append_message(
            session_id=session.id,
            role="user",
            content="That's right, we decided to use Redis to queue the batch jobs and throttle concurrent connections."
        )
        print_info("Appended 3 messages to the session. Promoting session...")

        # Promote session triggers rule-based extraction pipeline
        promo_res = sdk.promote_session(session_id=session.id)
        print_info(f"Promote response: {promo_res}")

        # Give database / worker a brief moment (async worker in production, sync here)
        time.sleep(0.5)

        # Retrieve extracted items
        extracted = sdk.get_extracted_from_session(session_id=session.id)
        print_info(f"Extracted {len(extracted)} objects from session:")
        for item in extracted:
            total_objects_stored += 1
            print_info(f"  - [{item.type.upper()}] ID={item.id} | Content='{item.content}'")

    except MenoError as me:
        print_error(f"Meno API error in Phase 6: {me.status_code} - {me}")
        return
    except Exception as e:
        print_error(f"Failed session lifecycle: {e}")
        return

    # -------------------------------------------------------------------------
    # Final Result
    # -------------------------------------------------------------------------
    print_step("Demo complete")
    print_info(f"Demo complete. {total_objects_stored} objects stored, {total_relationships_created} relationships created.")


if __name__ == "__main__":
    main()
