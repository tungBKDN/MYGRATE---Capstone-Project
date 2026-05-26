Dưới đây là báo cáo chi tiết cho pipeline ở mục 10: “tìm các version của một thư viện tương thích với JDK đích, và nếu nhiều thư viện thì tìm các tổ hợp version cùng thỏa mãn”. Trục chính của pipeline này là: lấy candidate versions từ repository metadata, lọc nhanh, kiểm tra tương thích tĩnh, mô hình hóa ràng buộc dependency, rồi giải bằng solver để trả ra một hoặc nhiều bộ thỏa mãn. [github](https://github.com/basepom/dependency-versions-check-maven-plugin/releases)

## Mục tiêu
Mục tiêu không chỉ là hỏi “version nào compile được”, mà là “version nào thật sự an toàn trong môi trường JDK mục tiêu và không làm vỡ dependency graph”. Cách này khớp với thực tế mà các tool nghiên cứu và cộng đồng đang làm: static checks để bắt lỗi API/runtime, và resolver/solver để xử lý tổ hợp version. [github](https://github.com/uber-research/java-dependency-validator)
Với một thư viện đơn lẻ, output là danh sách version pass. Với nhiều thư viện, output là danh sách các combination pass, có thể nhiều hơn một bộ. [github](https://github.com/uber-research/java-dependency-validator)

## Bước 1: Lấy tập candidate versions
Đầu vào ban đầu là artifact coordinates, ví dụ `groupId:artifactId`, và JDK mục tiêu. Từ Maven Central hoặc Maven Resolver/Aether, bạn lấy toàn bộ version khả dụng của artifact đó để làm candidate set. [github](https://github.com/basepom/dependency-versions-check-maven-plugin/releases)
Đây là bước thuần metadata, chưa xét tương thích. Nó chỉ trả lời “có những version nào tồn tại”.  
Điểm mạnh của bước này là rõ ràng và chuẩn hóa; điểm yếu là candidate set thường rất lớn nếu artifact sống lâu hoặc có nhiều nhánh release.

## Bước 2: Tiền lọc heuristic
Sau khi có danh sách version, bạn nên lọc nhanh bằng heuristic để giảm số phiên bản phải kiểm tra sâu. Heuristic có thể là ngày release, khoảng version, tag Java baseline, hoặc các tín hiệu từ release notes và metadata cộng đồng. [conf.researchr](https://conf.researchr.org/details/icsme-2025/icsme-2025-tool-demonstration/4/MaRCo-Compatible-Version-Ranges-in-Maven)
Mục đích của heuristic là loại các version “rất khó phù hợp” trước khi chạy check nặng như bytecode scan hay compile test.  
Đây không phải chứng thực cuối cùng, chỉ là bước giảm tải.

## Bước 3: Static check theo từng version
Đây là lõi của pipeline. Với mỗi version candidate, bạn giải nén jar và trích xuất API usage hoặc public signatures, rồi so với JDK đích để xem có dùng API bị thiếu hay không. [github](https://github.com/lvc/japi-compliance-checker)
Ở tầng này, tool như Java Dependency Validator của Uber cho thấy một hướng rất thực tế: không chỉ so sánh thô từng dependency, mà tìm các call/load operation thật sự reachable từ code first-party để tránh false positive. [github](https://github.com/uber-research/java-dependency-validator)
Nói ngắn gọn: version nào có reference đến class/method không tồn tại trong JDK đích, hoặc chỉ tồn tại ở JDK khác, thì bị loại.

## Bước 4: Compile-check bổ sung
Sau bytecode/API scan, bạn có thể xác nhận lại bằng compile-check. Ý tưởng là sinh stub hoặc harness tối thiểu rồi compile bằng `javac --release` trên JDK đích để bắt lỗi source-level, API-level, và một phần module-related issues. [baeldung](https://www.baeldung.com/java-source-target-options)
Bước này hữu ích khi artifact có nguồn hoặc bạn có thể sinh stub từ bytecode. Nó không thay thế bytecode check, mà bổ sung cho nó.  
Trong thực tế, compile-check thường bắt các lỗi mà scan tĩnh không thấy hết do source compatibility và mức `--release`. [baeldung](https://www.baeldung.com/java-source-target-options)

## Bước 5: Model ràng buộc transitive
Nếu chỉ một thư viện thì bạn chỉ cần list version pass/fail. Nhưng nếu có nhiều thư viện thì phải xét thêm dependency kéo theo. Lúc này, mỗi version candidate của một library không còn độc lập nữa, vì nó có thể kéo một phiên bản transitives xung đột với library khác. [github](https://github.com/basepom/dependency-versions-check-maven-plugin/releases)
Cách xử lý là mô hình hóa thành các ràng buộc: nếu chọn `A:v1` thì phải chọn `C:vx`; nếu chọn `B:v2` thì không được chọn `D:vy`; đồng thời mọi version phải pass compatibility với JDK đích. [conf.researchr](https://conf.researchr.org/details/icsme-2025/icsme-2025-tool-demonstration/4/MaRCo-Compatible-Version-Ranges-in-Maven)
Mô hình này biến bài toán từ “lọc version” thành “giải tổ hợp”.

## Bước 6: Giải bằng SAT/SMT solver
Khi đã có constraint graph, bạn nạp vào Z3 hoặc SAT solver để tìm tất cả tổ hợp thỏa mãn. Điểm mạnh của solver là nó có thể trả về nhiều nghiệm, không chỉ một nghiệm duy nhất. [conf.researchr](https://conf.researchr.org/details/icsme-2025/icsme-2025-tool-demonstration/4/MaRCo-Compatible-Version-Ranges-in-Maven)
Điều này rất hợp với yêu cầu của bạn: “có khả năng có nhiều hơn 1 bộ thỏa mãn trong 1 lượt”. Solver có thể output tất cả bộ hợp lệ, hoặc top-K bộ theo tiêu chí tối ưu.  
Nếu muốn, bạn cũng có thể thêm objective function như minimize số thay đổi version so với baseline, hoặc maximize confidence score.

## Bước 7: Xác thực runtime cho top-K
Sau khi solver trả ra một số bộ candidate, bạn chọn top-K và chạy smoke test trên JDK mục tiêu. Mục tiêu là bắt lỗi runtime thật như `NoSuchMethodError`, `ClassNotFoundException`, `IllegalAccessError`. [github](https://github.com/uber-research/java-dependency-validator)
Java Dependency Validator của Uber được thiết kế đúng tinh thần này: tìm missing classes/methods reachable từ first-party code trước khi runtime bug lộ ra trong production. [github](https://github.com/uber-research/java-dependency-validator)
Runtime test không cần chạy cho mọi combo, chỉ cần cho những combo tốt nhất sau static/solver filtering.

## Vì sao pipeline này đúng với bài toán của bạn
Bài toán của bạn có hai lớp khác nhau. Lớp một là “version nào của library này chạy được trên JDK X”. Lớp hai là “nếu có nhiều library, tổ hợp version nào cùng chạy được”.  
Lớp một giải bằng metadata + static compatibility check. Lớp hai giải bằng resolver + solver. [github](https://github.com/basepom/dependency-versions-check-maven-plugin/releases)
Đây là lý do pipeline trong mục 10 mới là cấu trúc đúng: nó tách rõ candidate generation, compatibility validation, và combinatorial resolution.

## Ưu điểm thực tế
- Dễ cache: kết quả static check per artifact×version×JDK có thể tái sử dụng. [github](https://github.com/lvc/japi-compliance-checker)
- Dễ mở rộng: thêm JDK mới chỉ cần chạy lại bước check cho JDK đó.  
- Dễ trả nhiều nghiệm: solver hỗ trợ nhiều combination hợp lệ. [conf.researchr](https://conf.researchr.org/details/icsme-2025/icsme-2025-tool-demonstration/4/MaRCo-Compatible-Version-Ranges-in-Maven)
- Dễ giải thích: mỗi version bị loại đều có lý do rõ ràng, như missing class/method hoặc xung đột transitive. [github](https://github.com/uber-research/java-dependency-validator)

## Hạn chế cần chấp nhận
- Metadata không đủ để kết luận tương thích thật sự.  
- Bytecode/static check có thể bỏ sót behavioral incompatibility.  
- Runtime test đắt nên không thể chạy toàn bộ candidate space.  
- Solver chỉ giỏi xử lý logic ràng buộc, không tự biết “semantic compatibility”; nó cần dữ liệu từ static/runtime checks. [github](https://github.com/basepom/dependency-versions-check-maven-plugin/releases)

## Khuyến nghị triển khai cho Mygrate
Nếu bạn muốn làm đồ án chắc tay, tôi khuyên pipeline tối thiểu như sau:
1. Lấy versions từ Maven metadata/resolver. [github](https://github.com/basepom/dependency-versions-check-maven-plugin/releases)
2. Lọc heuristic để giảm số lượng candidate. [conf.researchr](https://conf.researchr.org/details/icsme-2025/icsme-2025-tool-demonstration/4/MaRCo-Compatible-Version-Ranges-in-Maven)
3. Chạy static API/bytecode check cho từng version trên JDK đích. [github](https://github.com/lvc/japi-compliance-checker)
4. Nếu nhiều thư viện, dùng solver để tìm mọi tổ hợp thỏa mãn. [conf.researchr](https://conf.researchr.org/details/icsme-2025/icsme-2025-tool-demonstration/4/MaRCo-Compatible-Version-Ranges-in-Maven)
5. Chỉ chạy runtime smoke test cho top-K combo. [github](https://github.com/uber-research/java-dependency-validator)

Nếu bạn muốn, bước tiếp theo tôi có thể viết luôn cho bạn một spec kỹ thuật rất cụ thể cho module này: input/output schema, data model, và pseudo-code cho từng stage.