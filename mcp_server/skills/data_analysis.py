"""Data analysis skill definition and prompts."""

from typing import Dict, Any

DATA_ANALYSIS_SKILL_METADATA = {
    "name": "data_analysis_skill",
    "description": "Expert data analyst workflow for statistical summaries, trend analysis, anomaly detection, and Python-driven computation.",
    "version": "1.0.0",
    "recommended_tools": ["execute_python", "workspace_file_ops", "calculate"]
}

def render_data_analysis_skill(dataset_summary: str, objective: str) -> str:
    """
    Renders structured instructions guiding the agent through rigorous data analysis.
    """
    return f"""# Skill: Expert Data Analyst

## Objective
{objective}

## Dataset Context
{dataset_summary}

## Instructions & Standard Operating Procedure
1. **Understand & Inspect**: Examine data types, distributions, missing values, and outliers.
2. **Execute Calculations**: Use the `execute_python` tool to compute accurate statistics (mean, median, variance, correlations, quartiles). DO NOT guess math calculations.
3. **Synthesize Insights**: Identify key trends, patterns, anomalies, and practical business or engineering takeaways.
4. **Structured Output**:
   - Executive Summary
   - Statistical Findings (with exact values verified via tools)
   - Anomalies / Edge Cases
   - Actionable Recommendations

Begin analysis systematically using available tools.
"""
