# JIRA_Checker

A tool for validating JIRA tickets

---

## Features

1. Deployment Note Validation
    - Extracts and validates remote links from JIRA issues
    - Fetches and checks Confluence page content
    - Ensures release notes are present and correctly linked

2. Linked Dependency Validation
    - Checks for proper linking between dependent tickets
    - Validates sprint assignments for linked issues
    - Supports whitelisting with `SuppressScanning` label
    - Provides detailed warnings for dependency issues

## Requirements

- Python 3.8+
- `requests` library

## Installation

```bash
pip install -r requirements.txt
```
