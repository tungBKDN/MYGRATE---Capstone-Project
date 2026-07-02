# Báo cáo Đánh giá và Phân tích Dịch chuyển Codebase: qwen3.5_cloud

Báo cáo này tổng hợp chi tiết kết quả dịch chuyển Java 17 cho từng codebase, kèm theo lý do giải thích cụ thể cho từng trường hợp.

## ✅ Các Codebase Dịch chuyển Thành công (15)

### `Jasper-report-maven-plugin`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 4 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 10/10 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `balana`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 27 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 26/26 bài test gốc đều vượt qua và độ bao phủ code thậm chí còn tăng thêm 0.02%. Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `charts4j`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 9 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 384/384 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `dropwizard-todo`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 20 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 26/26 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `druidry`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 9 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 950/950 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `geojson-jackson`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 7 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 152/152 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `java-u2flib-server`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 13 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 230/230 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `kafka-spout`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 23 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 102/102 bài test gốc đều vượt qua và độ bao phủ chỉ giảm nhẹ 3.86% (nằm trong ngưỡng cho phép). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `mini-spring`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 15 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 68/68 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `netty-zmtp`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 7 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 48/48 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `spring-boot-rest-example`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 44 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 4/4 bài test gốc đều vượt qua và độ bao phủ chỉ giảm nhẹ 4.85% (nằm trong ngưỡng cho phép). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `suffixtree`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 2 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 22/22 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `token-bucket`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 12 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 76/76 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `unidecode`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 4 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 76/76 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `velocity-spring-boot-project`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 28 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 24/24 bài test gốc đều vượt qua và độ bao phủ code thậm chí còn tăng thêm 0.14%. Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

## ⏭️ Các Codebase Bị Bỏ Qua / Skip (4)

### `DaisyDiff`

- **Kết quả**: SKIPPED
- **Lý do (Enum)**: `BASELINE_INVALID`
- **Giải thích**: Dự án được bỏ qua do số liệu baseline không hợp lệ (không có bài test nào hoặc độ bao phủ bằng 0.0%). Hệ thống đã tự động skip theo cấu hình để tránh gây sai lệch kết quả đánh giá chung của toàn bộ batch.

### `jadb`

- **Kết quả**: SKIPPED
- **Lý do (Enum)**: `BASELINE_INVALID`
- **Giải thích**: Dự án được bỏ qua do số liệu baseline không hợp lệ (không có bài test nào hoặc độ bao phủ bằng 0.0%). Hệ thống đã tự động skip theo cấu hình để tránh gây sai lệch kết quả đánh giá chung của toàn bộ batch.

### `jersey-jwt`

- **Kết quả**: SKIPPED
- **Lý do (Enum)**: `BASELINE_INVALID`
- **Giải thích**: Dự án được bỏ qua do số liệu baseline không hợp lệ (không có bài test nào hoặc độ bao phủ bằng 0.0%). Hệ thống đã tự động skip theo cấu hình để tránh gây sai lệch kết quả đánh giá chung của toàn bộ batch.

### `servicecomb-saga-actuator`

- **Kết quả**: SKIPPED
- **Lý do (Enum)**: `BASELINE_INVALID`
- **Giải thích**: Dự án được bỏ qua do số liệu baseline không hợp lệ (không có bài test nào hoặc độ bao phủ bằng 0.0%). Hệ thống đã tự động skip theo cấu hình để tránh gây sai lệch kết quả đánh giá chung của toàn bộ batch.

## ❌ Các Codebase Dịch chuyển Thất Bại (28)

### `aggregate-persistence`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `apollo`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `artemis-odb`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `aws-apigateway-importer`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 20/44 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `biweekly`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `cloudhopper-smpp`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 386/392 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `ddd-cqrs-sample`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 40/48 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `docker-java-api`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 124/480 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `firefly`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `friendly-id`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `hello-design-pattern`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `hydra-java`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `jaydio`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 44/105 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `joauth`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 12/616 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `log4j2-elasticsearch`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 2445/2447 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `quilt`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `rhizobia_J`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `sonar-stash`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `spark-jobs-rest-client`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `spring-batch-rest`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 53/63 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `spring-cloud-aws`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `spring-context-support`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 94/98 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `spring-rest-exception-handler`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `sql-to-mongo-db-query-converter`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_RUNTIME_LOGIC_FAILED`
- **Giải thích**: Biên dịch thành công nhưng có một hoặc nhiều bài test gốc bị chạy lỗi (fail/error). Agent không tìm được cấu hình dependency tương thích hoàn toàn để làm xanh toàn bộ test suite.

### `staxon`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 760/764 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `stream-lib`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 140/152 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `unix4j`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 912/920 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `yawp`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.
