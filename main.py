"""Main entry point for Agent 2 codegen."""
import argparse
import json
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
# This allows running from agent2_codegen directory: python main.py
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from agent2_codegen.graph import create_graph
from agent2_codegen.state import Agent2State
from agent2_codegen.io import load_input_json, write_generated_files

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def main():
    """Run Agent 2 codegen pipeline."""
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Agent 2: Dynamic Agent Code Generator")
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input JSON file"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./generated_agents/",
        help="Output directory for generated agents"
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Don't write files to disk, only return JSON"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Set logging level from argument
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info("=" * 60)
    logger.info("AGENT 2 CODE GENERATOR")
    logger.info("=" * 60)
    logger.info(f"Input file: {args.input}")
    logger.info(f"Output directory: {args.out}")
    logger.info(f"Log level: {args.log_level}")
    logger.info("")
    
    # Load input
    logger.info("Loading input JSON file...")
    try:
        input_data = load_input_json(args.input)
        logger.info(f"✓ Input file loaded successfully")
    except FileNotFoundError:
        logger.error(f"❌ Input file not found: {args.input}")
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in input file: {e}")
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create initial state
    logger.info("Creating initial state...")
    state = Agent2State(
        pipeline_id=input_data.get("pipeline_id", "unknown"),
        agent_spec_version=input_data.get("agent_spec_version", "v1"),
        user_query=input_data.get("user_query", ""),
        agent_spec=input_data.get("agent_spec", {}),
        tool_registry=input_data.get("tool_registry", []),
        integrations=input_data.get("integrations", {})
    )
    logger.info(f"✓ State created (pipeline_id: {state.pipeline_id})")
    logger.info("")
    
    # Run graph
    logger.info("Initializing code generation graph...")
    graph = create_graph()
    logger.info("✓ Graph initialized")
    logger.info("")
    
    try:
        logger.info("Starting code generation pipeline...")
        final_state_dict = graph.invoke(state)
        # LangGraph returns a dict, convert back to state object for easier access
        final_state = Agent2State(**final_state_dict) if isinstance(final_state_dict, dict) else final_state_dict
        logger.info("✓ Code generation pipeline completed")
    except Exception as e:
        logger.error(f"❌ Error during codegen: {e}")
        import traceback
        traceback.print_exc()
        print(f"Error during codegen: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Write files if requested
    if not args.no_write:
        logger.info("")
        logger.info("Writing generated files to disk...")
        try:
            write_generated_files(
                final_state.generated_files,
                args.out,
                final_state.pipeline_id
            )
            logger.info(f"✓ Files written to {args.out}/{final_state.pipeline_id}/")
            print(f"✓ Files written to {args.out}/{final_state.pipeline_id}/")
        except Exception as e:
            logger.error(f"❌ Failed to write files: {e}")
            print(f"Warning: Failed to write files: {e}", file=sys.stderr)
    else:
        logger.info("Skipping file write (--no-write flag set)")
    
    # Output JSON result
    logger.info("")
    logger.info("=" * 60)
    logger.info("FINAL STATUS")
    logger.info("=" * 60)
    logger.info(f"Pipeline ID: {final_state.pipeline_id}")
    logger.info(f"Status: {final_state.status}")
    logger.info(f"Files generated: {len(final_state.generated_files)}")
    logger.info(f"Progress events: {len(final_state.progress_events)}")
    if final_state.errors:
        logger.warning(f"Errors: {len(final_state.errors)}")
    logger.info("")
    
    output = {
        "pipeline_id": final_state.pipeline_id,
        "status": final_state.status,
        "manifest": final_state.manifest,
        "generated_files": final_state.generated_files,
        "progress_events": final_state.progress_events
    }
    
    if final_state.errors:
        output["errors"] = final_state.errors
    
    print(json.dumps(output, indent=2))
    
    # Exit with error code if failed
    if final_state.status != "success":
        logger.error("Pipeline completed with errors")
        sys.exit(1)
    else:
        logger.info("✓ Pipeline completed successfully")


if __name__ == "__main__":
    main()
