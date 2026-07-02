# Migration Inspection Report: qwen3.5_cloud

This report lists the migration outcome for each codebase, categorized by success, skipped, and failure reasons.

## ✅ Successful Migrations (15)

| Codebase | Compile | Tests | Coverage (Baseline -> Final) | Steps |
| --- | --- | --- | --- | --- |
| `Jasper-report-maven-plugin` | PASS | PASS (10/10) | 65.87% -> 65.87% | 4 |
| `balana` | PASS | PASS (26/26) | 57.61% -> 57.64% | 27 |
| `charts4j` | PASS | PASS (384/384) | 84.09% -> 84.09% | 9 |
| `dropwizard-todo` | PASS | PASS (26/26) | 65.13% -> 65.13% | 20 |
| `druidry` | PASS | PASS (950/950) | 88.12% -> 88.12% | 9 |
| `geojson-jackson` | PASS | PASS (152/152) | 71.47% -> 71.47% | 7 |
| `java-u2flib-server` | PASS | PASS (230/230) | 87.30% -> 87.30% | 13 |
| `kafka-spout` | PASS | PASS (102/102) | 94.81% -> 90.95% | 23 |
| `mini-spring` | PASS | PASS (68/68) | 88.79% -> 88.79% | 15 |
| `netty-zmtp` | PASS | PASS (48/48) | 72.01% -> 72.01% | 7 |
| `spring-boot-rest-example` | PASS | PASS (4/4) | 71.19% -> 66.34% | 44 |
| `suffixtree` | PASS | PASS (22/22) | 90.54% -> 90.54% | 2 |
| `token-bucket` | PASS | PASS (76/76) | 74.67% -> 74.67% | 12 |
| `unidecode` | PASS | PASS (76/76) | 94.00% -> 94.00% | 4 |
| `velocity-spring-boot-project` | PASS | PASS (24/24) | 68.24% -> 68.38% | 28 |

## ⏭️ Skipped Codebases (4)

These codebases were skipped due to incomplete baseline metrics (e.g. 0% coverage or 0 passed tests):

- `DaisyDiff`: Skipped (Baseline Total Tests = 0, Baseline Coverage = 0.00%)
- `jadb`: Skipped (Baseline Total Tests = 24, Baseline Coverage = 0.00%)
- `jersey-jwt`: Skipped (Baseline Total Tests = 0, Baseline Coverage = 0.00%)
- `servicecomb-saga-actuator`: Skipped (Baseline Total Tests = 0, Baseline Coverage = 0.00%)

## ❌ Failed Migrations (28)

### `aggregate-persistence`

- **Step count**: 19
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `apollo`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
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

- **Step count**: 48
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Test Count Mismatch: Only 22 tests executed compared to a baseline of 44. Some test classes were skipped or excluded.
```

### `biweekly`

- **Step count**: 16
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `cloudhopper-smpp`

- **Step count**: 6
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `ddd-cqrs-sample`

- **Step count**: 50
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `docker-java-api`

- **Step count**: 4
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 478 tests executed compared to a baseline of 480. Some test classes were skipped or excluded.
```

### `firefly`

- **Step count**: 20
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `friendly-id`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `hello-design-pattern`

- **Step count**: 21
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `hydra-java`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 38 tests executed compared to a baseline of 368. Some test classes were skipped or excluded.
```

### `jaydio`

- **Step count**: 8
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `joauth`

- **Step count**: 33
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Test Count Mismatch: Only 12 tests executed compared to a baseline of 616. Some test classes were skipped or excluded.
```

### `log4j2-elasticsearch`

- **Step count**: 47
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `quilt`

- **Step count**: 22
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `rhizobia_J`

- **Step count**: 48
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `sonar-stash`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
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
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Maven Build Errors:
  - RestTest.jobsCanBeStartedWithDifferentProperties:85
  - Errors:
  - RestTest.swagger:101 » IllegalState The port must be an integer: 63294v3
  - Tests run: 41, Failures: 2, Errors: 1, Skipped: 0
  - Tests run: 4, Failures: 2, Errors: 1, Skipped: 0, Time elapsed: 11.767 s <<< FAILURE! - in com.github.chrisgleissner.springbatchrest.api.quartz.RestTest
  - swagger  Time elapsed: 0.209 s  <<< ERROR!
```

### `spring-cloud-aws`

- **Step count**: 16
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Maven Build Errors:
  - Tests run: 148, Failures: 0, Errors: 8, Skipped: 0
  - There are test failures.
  - Tests run: 13, Failures: 0, Errors: 13, Skipped: 0, Time elapsed: 0.75 s <<< FAILURE! - in org.springframework.cloud.aws.autoconfigure.cache.ElastiCacheAutoConfigurationTest
  - elastiCacheIsDisabled  Time elapsed: 0.027 s  <<< ERROR!
  - cacheManager_configuredNoCachesWithNoStack_configuresNoCacheManager  Time elapsed: 0.003 s  <<< ERROR!
  - enableElasticache_configuredWithoutExplicitCluster_configuresImplicitlyConfiguredCaches  Time elapsed: 0.003 s  <<< ERROR!
```

### `spring-context-support`

- **Step count**: 50
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `spring-rest-exception-handler`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```

### `sql-to-mongo-db-query-converter`

- **Step count**: 36
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `staxon`

- **Step count**: 14
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `stream-lib`

- **Step count**: 9
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `unix4j`

- **Step count**: 29
- **Outcome gates**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Failure Reason**:
```text
Build failed. See logs for full output details.
```

### `yawp`

- **Step count**: 50
- **Outcome gates**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Failure Reason**:
```text
Final evaluation compilation failed: The project changes or POM modifications introduced build/compilation errors, preventing the test suite from compiling and executing.
```
