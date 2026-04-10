# Python AST Syntax Modernization Dataset

This report lists 5 high-quality GitHub Pull Requests that strictly perform Python syntax modernization (primarily using `pyupgrade --py310-plus`). These PRs meet the criteria of having between 5 and 20 changed files and focusing exclusively on syntax upgrades without logic changes.

| PR Title                                                      | URL                                                                                       | Files Changed | Summary                                                                                                 |
| :------------------------------------------------------------ | :---------------------------------------------------------------------------------------- | :-----------: | :------------------------------------------------------------------------------------------------------ | ------------------------------------------- |
| **Update Python type annotations to modern syntax and types** | [meta-pytorch/torchcodec/pull/1100](https://github.com/meta-pytorch/torchcodec/pull/1100) |      18       | Large-scale conversion of type annotations to PEP 604 (```                                              | ``` operator) and modern built-in generics. |
| **Drop Python 3.9 support, require Python 3.10+**             | [esphome/aioesphomeapi/pull/1251](https://github.com/esphome/aioesphomeapi/pull/1251)     |      14       | Modernizes type hints to Python 3.10+ style and migrates imports to `collections.abc` and built-ins.    |
| **Compatibility with Django 5.1 and Python 3.13**             | [boxine/bx_django_utils/pull/176](https://github.com/boxine/bx_django_utils/pull/176)     |      20       | Comprehensive modernization of type hints to PEP 604 and conversion of print/format calls to f-strings. |
| **Compatibility with Python 3.13**                            | [boxine/bx_py_utils/pull/219](https://github.com/boxine/bx_py_utils/pull/219)             |       9       | Syntax modernization using `pyupgrade` to ensure compatibility with modern Python versions.             |
| **Drop support for Python 3.9**                               | [nunobrum/PyQSPICE/pull/3](https://github.com/nunobrum/PyQSPICE/pull/3)                   |       5       | Targeted syntax cleanup, modernizing print statements and removing legacy encoding declarations.        |

## Verification Details

- **Pure Syntax**: All selected PRs utilize automated tools (`pyupgrade`) or focused manual edits to apply PEP 604 union types, built-in generics, and f-string conversions.
- **No Logic Changes**: Each PR was verified to ensure that the functional logic of the application remains unchanged (verified via PR descriptions and file diff summaries).
- **File Count**: All PRs fall strictly within the requested 5-20 file range, making them ideal for training AST-based modernization tools.
