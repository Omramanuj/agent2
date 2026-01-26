"""Test runner for agent generation pipeline."""
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any
import subprocess

# Add parent directory to path (agent2_codegen directory)
test_suite_dir = Path(__file__).parent
agent2_codegen_dir = test_suite_dir.parent

# Add the parent of agent2_codegen (agentForge) to path so we can import agent2_codegen
parent_dir = agent2_codegen_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Now import from agent2_codegen
from agent2_codegen.io import load_input_json, write_generated_files
from agent2_codegen.graph import create_graph
from agent2_codegen.state import Agent2State

from .validators.syntax_validator import validate_all_files as validate_syntax
from .validators.import_validator import validate_all_imports
from .validators.structure_validator import validate_all_structures
from .validators.template_compliance_validator import validate_template_compliance

logger = logging.getLogger(__name__)


class TestRunner:
    """Test runner for generating and validating agents."""
    
    def __init__(self, config_path: Path, output_dir: Path, reference_path: Path):
        """
        Initialize test runner.
        
        Args:
            config_path: Path to test_agents_config.json
            output_dir: Directory for generated test agents
            reference_path: Path to reference agent (my_agent)
        """
        self.config_path = config_path
        self.output_dir = output_dir
        self.reference_path = reference_path
        self.config = self._load_config()
        self.results = []
    
    def _load_config(self) -> Dict[str, Any]:
        """Load test configuration."""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all test agent generations and validations.
        
        Returns:
            Dictionary with test results
        """
        logger.info("=" * 80)
        logger.info("AGENT GENERATION TEST SUITE")
        logger.info("=" * 80)
        logger.info(f"Test agents: {len(self.config['test_agents'])}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Reference agent: {self.reference_path}")
        logger.info("")
        
        all_results = {
            "total_tests": len(self.config['test_agents']),
            "passed": 0,
            "failed": 0,
            "test_results": []
        }
        
        for test_config in self.config['test_agents']:
            logger.info("")
            logger.info("-" * 80)
            logger.info(f"Testing: {test_config['name']}")
            logger.info(f"Description: {test_config['description']}")
            logger.info("-" * 80)
            
            result = self.run_single_test(test_config)
            all_results["test_results"].append(result)
            
            if result["overall_success"]:
                all_results["passed"] += 1
                logger.info(f"✅ {test_config['name']} PASSED")
            else:
                all_results["failed"] += 1
                logger.error(f"❌ {test_config['name']} FAILED")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("TEST SUITE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total tests: {all_results['total_tests']}")
        logger.info(f"Passed: {all_results['passed']}")
        logger.info(f"Failed: {all_results['failed']}")
        logger.info("=" * 80)
        
        return all_results
    
    def run_single_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test agent generation and validation.
        
        Args:
            test_config: Test agent configuration
            
        Returns:
            Test result dictionary
        """
        result = {
            "name": test_config["name"],
            "description": test_config["description"],
            "generation_success": False,
            "validation_results": {},
            "overall_success": False,
            "errors": [],
            "warnings": []
        }
        
        # Step 1: Generate agent
        logger.info(f"Step 1: Generating agent from {test_config['input_file']}")
        try:
            input_path = Path(__file__).parent / test_config['input_file']
            if not input_path.exists():
                result["errors"].append(f"Input file not found: {input_path}")
                return result
            
            input_data = load_input_json(str(input_path))
            
            # Create state
            state = Agent2State(
                pipeline_id=f"test-{test_config['name']}",
                agent_spec_version=input_data.get("agent_spec_version", "v1"),
                user_query=input_data.get("user_query", ""),
                agent_spec=input_data.get("agent_spec", {}),
                tool_registry=input_data.get("tool_registry", []),
                integrations=input_data.get("integrations", {})
            )
            
            # Run pipeline
            graph = create_graph()
            final_state_dict = graph.invoke(state)
            final_state = Agent2State(**final_state_dict) if isinstance(final_state_dict, dict) else final_state_dict
            
            # Check for critical missing files even if status is "success"
            required_files = [
                "agent.py",
                "config/agent_config.py",
                "tools/__init__.py",
                "tools/pipedream_client.py",
                "tools/pipedream_tools.py"
            ]
            missing_files = [f for f in required_files if f not in final_state.generated_files]
            
            if final_state.status != "success" or missing_files:
                if final_state.errors:
                    result["errors"].extend([e.get("message", str(e)) for e in final_state.errors])
                if missing_files:
                    result["errors"].append({
                        "type": "missing_critical_files",
                        "message": f"Critical files missing: {', '.join(missing_files)}",
                        "missing_files": missing_files
                    })
                if final_state.status != "success" or missing_files:
                    return result
            
            # Write files
            agent_output_dir = self.output_dir / final_state.pipeline_id
            write_generated_files(
                final_state.generated_files,
                str(self.output_dir),
                final_state.pipeline_id
            )
            
            result["generation_success"] = True
            result["generated_files"] = list(final_state.generated_files.keys())
            logger.info(f"✅ Agent generated successfully ({len(final_state.generated_files)} files)")
            
            # Step 2: Validate generated agent
            logger.info("Step 2: Validating generated agent")
            try:
                validation_results = self.validate_agent(
                    final_state.generated_files,
                    agent_output_dir
                )
                result["validation_results"] = validation_results
                
                # Determine overall success
                result["overall_success"] = (
                    result["generation_success"] and
                    validation_results.get("syntax", {}).get("valid", False) and
                    validation_results.get("structure", {}).get("valid", False) and
                    validation_results.get("imports", {}).get("valid", True)  # Imports may have warnings
                )
                
                if not result["overall_success"]:
                    # Collect errors
                    for validator_name, validator_result in validation_results.items():
                        if isinstance(validator_result, dict):
                            if not validator_result.get("valid", True):
                                result["errors"].extend(validator_result.get("errors", []))
                            result["warnings"].extend(validator_result.get("warnings", []))
                
                logger.info(f"✅ Validation complete")
                
            except Exception as e:
                result["errors"].append(f"Validation failed: {str(e)}")
                logger.error(f"❌ Validation failed: {e}")
                import traceback
                traceback.print_exc()
            
        except Exception as e:
            result["errors"].append(f"Generation failed: {str(e)}")
            logger.error(f"❌ Generation failed: {e}")
            import traceback
            traceback.print_exc()
        
        return result
    
    def validate_agent(
        self,
        generated_files: Dict[str, str],
        agent_dir: Path
    ) -> Dict[str, Any]:
        """
        Run all validators on generated agent.
        
        Args:
            generated_files: Dictionary of generated files
            agent_dir: Directory where agent is located
            
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        # Syntax validation
        logger.info("  → Validating Python syntax...")
        syntax_result = validate_syntax(generated_files)
        results["syntax"] = syntax_result
        if syntax_result["valid"]:
            logger.info(f"    ✅ Syntax valid ({syntax_result['valid_files']}/{syntax_result['total_files']} files)")
        else:
            logger.error(f"    ❌ Syntax errors found: {len(syntax_result['errors'])}")
        
        # Structure validation
        logger.info("  → Validating file structure...")
        structure_result = validate_all_structures(generated_files)
        results["structure"] = structure_result
        if structure_result["valid"]:
            logger.info("    ✅ Structure valid")
        else:
            logger.error(f"    ❌ Structure errors: {len(structure_result['errors'])}")
        
        # Import validation
        logger.info("  → Validating imports...")
        import_result = validate_all_imports(generated_files, agent_dir)
        results["imports"] = import_result
        if import_result["valid"]:
            logger.info("    ✅ Imports valid")
        else:
            logger.warning(f"    ⚠️  Import warnings: {len(import_result['warnings'])}")
        
        # Template compliance validation
        logger.info("  → Validating template compliance...")
        if self.reference_path.exists():
            compliance_result = validate_template_compliance(
                generated_files,
                self.reference_path
            )
            results["template_compliance"] = compliance_result
            if compliance_result["valid"]:
                logger.info("    ✅ Template compliance valid")
            else:
                logger.warning(f"    ⚠️  Template compliance issues: {len(compliance_result['warnings'])}")
        else:
            logger.warning(f"    ⚠️  Reference path not found: {self.reference_path}")
            results["template_compliance"] = {"valid": True, "warnings": ["Reference path not found"]}
        
        return results


def main():
    """Main entry point for test runner."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get paths - ensure we're using the correct base directory
    test_suite_dir = Path(__file__).parent
    agent2_codegen_dir = test_suite_dir.parent
    
    # If running from agent2_codegen directory, we need to go up one more level
    if agent2_codegen_dir.name == "agent2_codegen":
        base_dir = agent2_codegen_dir.parent
    else:
        base_dir = agent2_codegen_dir
    
    config_path = test_suite_dir / "test_agents_config.json"
    output_dir = agent2_codegen_dir / "test_generated_agents"
    reference_path = agent2_codegen_dir / "my_agent"
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    # Run tests
    runner = TestRunner(config_path, output_dir, reference_path)
    results = runner.run_all_tests()
    
    # Save results
    results_file = output_dir / "test_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Test results saved to: {results_file}")
    
    # Exit with error code if any tests failed
    if results["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
