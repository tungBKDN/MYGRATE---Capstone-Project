# Báo cáo Đánh giá và Phân tích Dịch chuyển Codebase: deepseek-v3.2_cloud

Báo cáo này tổng hợp chi tiết kết quả dịch chuyển Java 17 cho từng codebase, kèm theo lý do giải thích cụ thể cho từng trường hợp.

## ✅ Các Codebase Dịch chuyển Thành công (12)

### `Jasper-report-maven-plugin`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 50 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 10/10 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `balana`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 22 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 26/26 bài test gốc đều vượt qua và độ bao phủ code thậm chí còn tăng thêm 0.02%. Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `charts4j`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 41 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 384/384 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `druidry`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 29 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 950/950 bài test gốc đều vượt qua và độ bao phủ code thậm chí còn tăng thêm 3.06%. Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `geojson-jackson`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 50 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 152/152 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `hello-design-pattern`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 32 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 50/50 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `java-u2flib-server`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 40 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 230/230 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `log4j2-elasticsearch`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 46 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 2447/2447 bài test gốc đều vượt qua và độ bao phủ chỉ giảm nhẹ 0.91% (nằm trong ngưỡng cho phép). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `suffixtree`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 47 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 22/22 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `token-bucket`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 29 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 76/76 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `unidecode`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 48 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 76/76 bài test gốc đều vượt qua và độ bao phủ code được bảo toàn hoàn hảo (0.00% thay đổi). Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

### `velocity-spring-boot-project`

- **Kết quả**: THÀNH CÔNG (Pass cả 3 Gate)
- **Lý do (Enum)**: `SUCCESS`
- **Giải thích**: Dịch chuyển thành công hoàn toàn lên Java 17 sau 50 bước gọi LLM. Dự án biên dịch thông suốt, toàn bộ 24/24 bài test gốc đều vượt qua và độ bao phủ code thậm chí còn tăng thêm 0.14%. Mã nguồn sau khi migrate đảm bảo tính toàn vẹn và chạy ổn định.

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

## ❌ Các Codebase Dịch chuyển Thất Bại (31)

### `aggregate-persistence`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Không tìm thấy file log chạy của dự án này (có thể do thư mục workspace bị dọn dẹp hoặc tiến trình bị hủy đột ngột). Kết quả lưu vết cho thấy dự án không hoàn thành được pha biên dịch và kiểm thử cuối cùng.

### `apollo`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `artemis-odb`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `aws-apigateway-importer`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `biweekly`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 2310/2312 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `cloudhopper-smpp`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 386/392 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `ddd-cqrs-sample`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `docker-java-api`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 124/480 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `dropwizard-todo`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `firefly`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 1853/1862 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `friendly-id`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `hydra-java`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `jaydio`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại do không tương thích mã nguồn Java 17. Lỗi chính được ghi nhận: "error: Source option 6 is no longer supported. Use 7 or later. (và 119 lỗi biên dịch khác)". Agent chưa sửa đổi hết các API cũ hoặc thư viện bị loại bỏ trên JDK mới.

### `joauth`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `kafka-spout`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 56/102 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `mini-spring`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 52/68 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.

### `netty-zmtp`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `quilt`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `POM_CONFIG_SYNTAX_ERROR`
- **Giải thích**: Thất bại do gặp lỗi cú pháp cấu trúc XML trong file `pom.xml`. Trong quá trình tự động chèn plugin JaCoCo hoặc nâng cấp phiên bản, Agent đã đóng/mở sai thẻ `<plugins>` hoặc `<execution>`, dẫn đến Maven không thể parse được file cấu hình.

### `rhizobia_J`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `sonar-stash`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_RUNTIME_LOGIC_FAILED`
- **Giải thích**: Biên dịch thành công nhưng có một hoặc nhiều bài test gốc bị chạy lỗi (fail/error). Agent không tìm được cấu hình dependency tương thích hoàn toàn để làm xanh toàn bộ test suite.

### `spark-jobs-rest-client`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `spring-batch-rest`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `POM_CONFIG_SYNTAX_ERROR`
- **Giải thích**: Thất bại do gặp lỗi cú pháp cấu trúc XML trong file `pom.xml`. Trong quá trình tự động chèn plugin JaCoCo hoặc nâng cấp phiên bản, Agent đã đóng/mở sai thẻ `<plugins>` hoặc `<execution>`, dẫn đến Maven không thể parse được file cấu hình.

### `spring-boot-rest-example`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `spring-cloud-aws`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_DEPENDENCY_RESOLVE_FAILED`
- **Giải thích**: Biên dịch thất bại do không thể phân giải được các dependency hoặc plugin Maven. Hệ thống gặp lỗi kết nối đến repository hoặc bị chặn quyền truy cập (unauthorized) khi tải các thư viện cần thiết.

### `spring-context-support`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `spring-rest-exception-handler`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `sql-to-mongo-db-query-converter`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

### `staxon`

- **Kết quả**: THẤT BẠI
- **Cổng lỗi**: Compile: FAIL | Tests: FAIL | Coverage: FAIL
- **Lý do (Enum)**: `COMPILATION_SOURCE_INCOMPATIBLE`
- **Giải thích**: Biên dịch thất bại trong quá trình chạy pha đánh giá kiểm thử cuối cùng (mvn verify). Dù code có thể build thành công ở các bước trung gian, cấu hình POM hoặc mã nguồn cuối cùng vẫn chứa lỗi cú pháp/thiếu dependency khiến Maven không thể hoàn tất build.

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
- **Cổng lỗi**: Compile: PASS | Tests: FAIL | Coverage: PASS
- **Lý do (Enum)**: `TEST_COUNT_MISMATCH_SKIPPED`
- **Giải thích**: Thất bại ở Gate 2 do phát hiện việc bỏ qua kiểm thử (Test Skipping). Dù biên dịch thành công, dự án chỉ thực thi được 754/760 bài test gốc. Agent đã cấu hình skip các test suite để đối phó với lỗi runtime hoặc biên dịch test.
