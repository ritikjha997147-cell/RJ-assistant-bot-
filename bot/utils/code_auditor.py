import ast
import os
import pathlib

# Blacklisted dangerous terms for Threat Detection System
DANGEROUS_KEYWORDS = [
    "os.system", "subprocess", "eval(", "exec(", "shutil.rmtree", 
    "rm -rf", "exposed_token", "bot8640584928"
]

def analyze_submitted_code(code_text, target_filename=None):
    report = {
        "syntax_errors": [],
        "duplicate_functions": [],
        "security_issues": [],
        "architecture_issues": [],
        "recommended_fixes": [],
        "score": 100,
        "status": "PASS",
        "expected_output": "N/A (Static Syntax & Logic Check Validated)",
        "runtime_risks": []
    }
    
    if not code_text.strip():
        report["syntax_errors"].append("Empty code submitted.")
        report["score"] = 0
        report["status"] = "FAIL"
        return report

    # 1. Threat Detection & Security Check
    for keyword in DANGEROUS_KEYWORDS:
        if keyword in code_text:
            report["security_issues"].append(f"CRITICAL: Dangerous keyword/action detected: '{keyword}'")
            report["runtime_risks"].append("High Risk: Arbitrary Code Execution / System Abuse Threat")
            report["recommended_fixes"].append(f"Remove any usage of '{keyword}' immediately.")
            report["score"] -= 40

    # 2. Syntax Analysis using AST
    try:
        parsed_ast = ast.parse(code_text)
        
        # 3. Structural & Duplicate Detection
        defined_functions = []
        for node in ast.walk(parsed_ast):
            if isinstance(node, ast.FunctionDef):
                if node.name in defined_functions:
                    report["duplicate_functions"].append(f"Duplicate function definition found: '{node.name}'")
                    report["score"] -= 10
                else:
                    defined_functions.append(node.name)
                    
            # Check for bad imports
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in ["os", "subprocess", "sys"] and "security_issues" not in report:
                        report["architecture_issues"].append(f"Unsafe module import architecture: '{alias.name}'")
                        report["score"] -= 5

    except SyntaxError as e:
        report["syntax_errors"].append(f"Line {e.lineno}: {e.msg} (Check missing colons/brackets/indentation)")
        report["status"] = "FAIL"
        report["score"] -= 50
        report["recommended_fixes"].append("Fix the structural python syntax before requesting a merge.")

    # Architectural File-Size Checks
    if len(code_text.splitlines()) > 300:
        report["architecture_issues"].append("Oversized file structure: Script is over 300 lines (Mixed Responsibilities).")
        report["score"] -= 10

    # Final Adjustment
    report["score"] = max(0, report["score"])
    if report["score"] < 70 or report["syntax_errors"]:
        report["status"] = "FAIL"

    return report