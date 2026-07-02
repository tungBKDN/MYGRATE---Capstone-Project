# Dependency Migration Review: javax.ws.rs:jsr311-api

## Current Codebase
- **Project**: staxon (Java)
- **Target Java Version**: 17
- **Current Dependency**: javax.ws.rs:jsr311-api version 1.1.1 (provided scope)
- **Context**: Legacy JAX-RS 1.1 API used alongside Jersey 1.10 and older Jackson/Gson versions.

## Candidate Solutions
Three version variants were analyzed and smoke-tested:
1. **1.1**: Older stable release. Smoke Test: **PASS**. Compatibility: Warning.
2. **1.1.1**: Current stable release. Smoke Test: **PASS**. Compatibility: Warning.
3. **1.1-ea**: Early access build. Smoke Test: **PASS**. Compatibility: Warning.

## Selected Recommendation
**Version: 1.1.1**

## Why This Choice
- **Empirical Evidence**: All candidates passed the JVM class loading smoke test.
- **Stability**: 1.1.1 is the most recent stable version among the options. 1.1 is a downgrade, and 1.1-ea introduces early-access risk.
- **Minimal Change**: The project already uses 1.1.1. Validating that the current version works on Java 17 is sufficient for this migration step without introducing unnecessary version churn.

## Remaining Risks
- **Legacy Technology**: JSR 311 (JAX-RS 1.1) is deprecated in favor of JAX-RS 2.x/3.x. Static analysis flags warnings across all versions.
- **Scope**: The dependency is marked as `provided`, implying runtime environment dependency which must also be compatible.
- **Smoke Test Limitation**: Passing class loading does not guarantee full functional compatibility in complex request/response cycles.

## Next Steps
1. **Integration Testing**: Execute full test suite to verify HTTP handling.
2. **Monitoring**: Watch for runtime exceptions related to javax.ws.rs packages.
3. **Future Roadmap**: Schedule upgrade to Jakarta WS RS (JAX-RS 3.x) to eliminate legacy warnings and ensure long-term Java compatibility.