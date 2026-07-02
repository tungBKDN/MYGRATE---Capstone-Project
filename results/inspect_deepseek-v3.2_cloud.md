# Migration Inspection Report: deepseek-v3.2_cloud

This report lists the migration outcome for each codebase, categorized by success, skipped, and failure reasons.

## ✅ Successful Migrations (12)

| Codebase | Compile | Tests | Coverage (Baseline -> Final) | Steps |
| --- | --- | --- | --- | --- |
| `Jasper-report-maven-plugin` | PASS | PASS (10/10) | 65.87% -> 65.87% | 50 |
| `balana` | PASS | PASS (26/26) | 57.61% -> 57.64% | 22 |
| `charts4j` | PASS | PASS (384/384) | 84.09% -> 84.09% | 41 |
| `druidry` | PASS | PASS (950/950) | 88.12% -> 91.18% | 29 |
| `geojson-jackson` | PASS | PASS (152/152) | 71.47% -> 71.47% | 50 |
| `hello-design-pattern` | PASS | PASS (50/50) | 98.57% -> 98.57% | 32 |
| `java-u2flib-server` | PASS | PASS (230/230) | 87.30% -> 87.30% | 40 |
| `log4j2-elasticsearch` | PASS | PASS (2447/2447) | 100.00% -> 99.09% | 46 |
| `suffixtree` | PASS | PASS (22/22) | 90.54% -> 90.54% | 47 |
| `token-bucket` | PASS | PASS (76/76) | 74.67% -> 74.67% | 29 |
| `unidecode` | PASS | PASS (76/76) | 94.00% -> 94.00% | 48 |
| `velocity-spring-boot-project` | PASS | PASS (24/24) | 68.24% -> 68.38% | 50 |

## ⏭️ Skipped Codebases (4)

These codebases were skipped due to incomplete baseline metrics (e.g. 0% coverage or 0 passed tests):

- `DaisyDiff`: Skipped (Baseline Total Tests = 0, Baseline Coverage = 0.00%)
- `jadb`: Skipped (Baseline Total Tests = 24, Baseline Coverage = 0.00%)
- `jersey-jwt`: Skipped (Baseline Total Tests = 0, Baseline Coverage = 0.00%)
- `servicecomb-saga-actuator`: Skipped (Baseline Total Tests = 0, Baseline Coverage = 0.00%)

## ❌ Failed Migrations (31)

### `aggregate-persistence`

- **Step count**: 52
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Log file not found (the workspace folder may have been cleaned/recreated).
```

### `apollo`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Test Count Mismatch: Only 50 tests executed compared to a baseline of 462. Some test classes were skipped or excluded.
```

### `artemis-odb`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 504 tests executed compared to a baseline of 884. Some test classes were skipped or excluded.
```

### `aws-apigateway-importer`

- **Step count**: 27
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 2 tests executed compared to a baseline of 44. Some test classes were skipped or excluded.
```

### `biweekly`

- **Step count**: 50
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `cloudhopper-smpp`

- **Step count**: 4
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `ddd-cqrs-sample`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `docker-java-api`

- **Step count**: 12
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 478 tests executed compared to a baseline of 480. Some test classes were skipped or excluded.
```

### `dropwizard-todo`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `firefly`

- **Step count**: 32
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `friendly-id`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `hydra-java`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Test Count Mismatch: Only 38 tests executed compared to a baseline of 368. Some test classes were skipped or excluded.
```

### `jaydio`

- **Step count**: 41
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 10 tests executed compared to a baseline of 105. Some test classes were skipped or excluded.
```

### `joauth`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `kafka-spout`

- **Step count**: 50
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `mini-spring`

- **Step count**: 10
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `netty-zmtp`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `quilt`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Failed to prepare POM for JaCoCo: Opening and ending tag mismatch: plugins line 602 and execution, line 656, column 23 (file:/D:/capstone_project/MYGRATE---Capstone-Project/working/deepseek-v3.2_cloud/quilt/pom.xml, line 656)
```

### `rhizobia_J`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `sonar-stash`

- **Step count**: 50
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Maven Build Errors:
  - Tests run: 1, Failures: 0, Errors: 1, Skipped: 0
  - There are test failures.
  - Tests run: 1, Failures: 0, Errors: 1, Skipped: 0, Time elapsed: 0.065 s <<< FAILURE! - in org.sonar.plugins.stash.CompleteITCase
  - org.sonar.plugins.stash.CompleteITCase  Time elapsed: 0.063 s  <<< ERROR!
  - Tests run: 1, Failures: 0, Errors: 1, Skipped: 0, Time elapsed: 0.061 s <<< FAILURE! - in org.sonar.plugins.stash.CompleteITCase
  - org.sonar.plugins.stash.CompleteITCase  Time elapsed: 0.06 s  <<< ERROR!
```

### `spark-jobs-rest-client`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `spring-batch-rest`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Failed to prepare POM for JaCoCo: Opening and ending tag mismatch: project line 2 and build, line 103, column 11 (file:/D:/capstone_project/MYGRATE---Capstone-Project/working/deepseek-v3.2_cloud/spring-batch-rest/pom.xml, line 103)
```

### `spring-boot-rest-example`

- **Step count**: 51
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `spring-cloud-aws`

- **Step count**: 51
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 102 tests executed compared to a baseline of 751. Some test classes were skipped or excluded.
```

### `spring-context-support`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `spring-rest-exception-handler`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `sql-to-mongo-db-query-converter`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `staxon`

- **Step count**: 51
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `stream-lib`

- **Step count**: 40
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `unix4j`

- **Step count**: 14
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `yawp`

- **Step count**: 50
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```
