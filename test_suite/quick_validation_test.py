"""Quick validation test that doesn't require LLM API calls."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_suite.validators.syntax_validator import validate_python_syntax
from test_suite.validators.structure_validator import validate_file_structure
from test_suite.validators.import_validator import validate_imports

# Test with reference agent files
reference_agent_path = Path(__file__).parent.parent / "my_agent"

print("=" * 80)
print("QUICK VALIDATION TEST")
print("=" * 80)
print()

# Load reference agent files
reference_files = {}
files_to_check = [
    "agent.py",
    "config/agent_config.py",
    "tools/__init__.py",
    "tools/pipedream_tools.py",
    "tools/pipedream_client.py"
]

print("Loading reference agent files...")
for file_path in files_to_check:
    full_path = reference_agent_path / file_path
    if full_path.exists():
        reference_files[file_path] = full_path.read_text(encoding='utf-8')
        print(f"  ✓ Loaded {file_path}")
    else:
        print(f"  ✗ Missing {file_path}")

print()
print("=" * 80)
print("VALIDATION RESULTS")
print("=" * 80)
print()

# Test syntax validation
print("1. Syntax Validation:")
syntax_errors = 0
for file_path, content in reference_files.items():
    result = validate_python_syntax(file_path, content)
    if result["valid"]:
        print(f"   ✓ {file_path} - Valid syntax")
    else:
        syntax_errors += len(result["errors"])
        print(f"   ✗ {file_path} - {len(result['errors'])} syntax errors")
        for error in result["errors"]:
            print(f"      - {error.get('message', 'Unknown error')}")

print()

# Test structure validation
print("2. Structure Validation:")
structure_result = validate_file_structure(reference_files)
if structure_result["valid"]:
    print("   ✓ File structure valid")
else:
    print(f"   ✗ {len(structure_result['errors'])} structure errors")
    for error in structure_result["errors"]:
        print(f"      - {error.get('message', 'Unknown error')}")

print()

# Test import validation
print("3. Import Validation:")
import_errors = 0
import_warnings = 0
for file_path, content in reference_files.items():
    result = validate_imports(file_path, content, reference_agent_path)
    if result["valid"]:
        if result.get("warnings"):
            import_warnings += len(result["warnings"])
            print(f"   ⚠ {file_path} - {len(result['warnings'])} warnings")
        else:
            print(f"   ✓ {file_path} - Valid imports")
    else:
        import_errors += len(result.get("errors", []))
        print(f"   ✗ {file_path} - {len(result.get('errors', []))} errors")

print()
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Syntax errors: {syntax_errors}")
print(f"Structure errors: {len(structure_result.get('errors', []))}")
print(f"Import errors: {import_errors}")
print(f"Import warnings: {import_warnings}")
print()

if syntax_errors == 0 and len(structure_result.get('errors', [])) == 0 and import_errors == 0:
    print("✅ All validations passed!")
    sys.exit(0)
else:
    print("❌ Some validations failed")
    sys.exit(1)
