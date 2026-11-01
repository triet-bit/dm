# Phân công công việc — BTL Data Mining (Instacart)


| Thành viên | Vai trò |
|---|---|
| TV1 — `<tên>` | Association Rules (frequent itemsets) |
| TV2 — `<tên>` | Association Rules (luật & đánh giá)|
| TV3 — Triết | Clustering |

> [!NOTE]
> **Hiện trạng dữ liệu (Tham chiếu chi tiết tại [`docs/report.md`](report.md)):**
> - **Chất lượng dữ liệu:** Không có dòng trùng lặp; toàn vẹn tham chiếu khóa ngoại 100% (mọi `order_id` và `product_id` trong các bảng giao dịch đều tồn tại ở bảng danh mục).
> - **Giá trị thiếu (Missing values):** Chỉ xuất hiện duy nhất ở cột `days_since_prior_order` với đúng 206.209 giá trị NaN (6,03%, ứng với đơn khởi đầu `order_number = 1` của 206.209 khách hàng). Đây là *structural missing* (thiếu mang tính cấu trúc logic), không phải lỗi thu thập.
> - **Định hướng tiền xử lý:** Dữ liệu thô không cần làm sạch cơ bản. Nhóm sẽ tập trung toàn bộ điểm Mục 2 vào: xử lý ngưỡng trần cực trị, chuẩn hóa phân phối đặc trưng (log1p, z-score), và biến đổi biểu diễn transaction dạng ma trận thưa cho mô hình (chi tiết tại [Mục 2](#2-tiền-xử-lý-mục-2--3-điểm)).

---

## 0. Mục chấm điểm và người phụ trách

| Mục trong đề | Điểm | Nội dung | Viết | Duyệt |
|---|---:|---|---|---|
| 1. Mô tả bài toán | 2 | Lĩnh vực, nguồn dữ liệu, mục tiêu khai phá | TV1 | TV3 |
| 2. Tiền xử lý | 3 | Xem mục 2 bên dưới | TV1 (TV3 cung cấp phần clustering) | TV3 |
| 3a. Clustering | 2,5 | K-Means + thuật toán so sánh | TV3 làm, TV1 viết lại vào Word | TV3 |
| 3b. Association Rules | 2,5 | Apriori vs FP-Growth, luật | TV1 + TV2 | TV3 |
| 4. Phân tích, thảo luận | 3 | Ý nghĩa, hạn chế, hướng phát triển | TV2 | TV3 |
| 5. Ràng buộc bổ sung (≥ 3) | 2 | Ràng buộc thực tế không có trong dữ liệu | TV2 | TV3 |
| Slides + thuyết trình | — | Mỗi người trình bày phần mình làm | TV2 ghép | TV3 |

## 1. Cần chốt

- [ ] Câu hỏi khai phá của mỗi kỹ thuật và mục tiêu chung (đề yêu cầu "nêu rõ mục tiêu khai phá").
- [ ] Phạm vi association: top-N sản phẩm và/hoặc cấp aisle/department; có lấy mẫu đơn không.
- [ ] Ngưỡng `min_support` / `min_confidence` / `lift`. `min_support = 0.01` trong
      `config/project.toml` quá cao cho cấp sản phẩm (cặp có support cao nhất chỉ 1,94%, `report.md` mục 15).
- [ ] Bộ feature cho clustering và cách xử lý feature phụ thuộc số đơn của khách.

## 2. Tiền xử lý (mục 2 - 3 điểm)

Không cần làm sạch, nhưng đề vẫn chấm phần "xử lý giá trị thiếu, loại bỏ nhiễu, chuẩn hóa, chọn
thuộc tính", nên báo cáo phải trình bày các quyết định sau, kèm bảng/hình trước–sau:

| Bước | Nội dung | Ai cung cấp |
|---|---|---|
| Giá trị thiếu | NaN `days_since_prior_order` là structural (đơn đầu); cách dùng khi tính `mean_gap` | TV3 |
| Nhiễu / cực trị | Trần 30 ngày, trần 100 đơn, giỏ 1 item / 145 item: giữ hay cắt | TV3 |
| Chuẩn hóa | `log1p` + z-score cho feature khách hàng | TV3 |
| Chọn thuộc tính | Feature clustering; top-N sản phẩm cho association | TV3 / TV2 |
| Biến đổi dữ liệu | Order → transaction (sparse one-hot), basket cấp aisle/department | TV1 |
| Thực thể đặc biệt | Department `missing` (1.258 sản phẩm), tên gần trùng (`Organic  Whole Milk`) | TV1 |

## 3. Công việc chi tiết

### TV3 — Clustering (`src/instacart_mining/features/customer.py`, `models/clustering.py`)

Dùng lại: `customer_table()`, `standardize()`, `pca()` trong `src/eda_customers.py`; `report.md` mục 19, 20.

- [ ] Bảng feature khách hàng (chỉ từ `prior`); chọn feature, xử lý skew, scaling.
- [ ] Kiểm tra correlation; xử lý phụ thuộc số đơn (`distinct_products` ρ = 0,67 với số đơn;
      `reorder_rate` tăng theo `order_number`, `report.md` mục 21).
- [ ] K-Means với nhiều k; chọn k bằng Elbow + Silhouette.
- [ ] Thuật toán so sánh: Agglomerative trên mẫu (hoặc MiniBatch K-Means).
- [ ] Silhouette, Davies–Bouldin, kích thước cluster, độ ổn định theo seed/mẫu.
- [ ] Profile từng cluster (bảng + figure); xuất `artifacts/cluster_assignments`.
- [ ] Ghi kết quả vào `docs/report.md` + `docs/execution-log.md`; bàn giao cho TV1 viết Word.

### TV1 — Frequent itemsets (`src/instacart_mining/features/transactions.py`, `models/association.py`)

Dùng lại: `count_products()`, `cooccurrence()` trong `src/eda_cooccurrence.py`;
`department_presence()` trong `src/eda_association.py`; `report.md` mục 10, 15, 22.

- [ ] Biểu diễn mỗi order thành transaction (sparse matrix); thống kê độ dài transaction.
- [ ] Chọn phạm vi theo long-tail (4.538 sản phẩm chiếm 80% số dòng, `report.md` mục 10).
- [ ] Tạo basket cấp aisle/department.
- [ ] Chạy **Apriori và FP-Growth** trên cùng dữ liệu, thử nhiều ngưỡng support.
- [ ] So sánh: thời gian chạy, bộ nhớ, số lượng và kích thước itemset theo ngưỡng.
- [ ] Bàn giao frequent itemsets cho TV2.

### TV2 — Luật kết hợp & đánh giá (`models/association.py`, `evaluation/rules.py`)

Dùng lại: `pair_table()`, `select_diverse()` trong `src/eda_cooccurrence.py`; `report.md` mục 15, 23.

- [ ] Sinh luật từ frequent itemsets; tính support, confidence, lift (+ leverage/conviction).
- [ ] Lọc luật trùng lặp và luật chỉ là biến thể cùng dòng sản phẩm (ví dụ sữa chua đổi vị).
- [ ] So sánh luật confidence cao vs lift cao; cấp sản phẩm vs cấp aisle/department.
- [ ] Kiểm tra độ ổn định luật trên hai nửa tập đơn (seed 42).
- [ ] Figure cho cặp/nhóm sản phẩm nổi bật.
- [ ] Ghi kết quả vào `docs/report.md` + `docs/execution-log.md`.

### Việc chung (nếu còn thời gian)

- [ ] **Luật theo cluster:** TV3 đưa `cluster_assignments`, TV2 mine luật riêng cho từng cluster để
      so sánh hai kỹ thuật với nhau.
- [ ] Reorder prediction (Classification): ngoài phạm vi; chỉ nêu ở "hướng phát triển".

## 4. Báo cáo và slides

### TV1 — Lead báo cáo Word
- [ ] Dựng khung Word theo đúng 5 mục của đề.
- [ ] Viết mục 1 (Mô tả bài toán) và mục 2 (Tiền xử lý), chọn 5–8 bảng/hình EDA phù hợp từ `report.md`.
- [ ] Viết mục 3a từ kết quả clustering của TV3, mục 3b phần frequent itemsets.
- [ ] Ghép phần của TV2; thống nhất định dạng, đánh số bảng/hình, tài liệu tham khảo.
- [ ] Danh sách thành viên; đóng gói `.zip` (Word + mã nguồn + hình).

### TV2 — Lead slides
- [ ] Viết mục 3b phần luật kết hợp, mục 4 (Thảo luận) và mục 5 (Ràng buộc bổ sung).
- [ ] Mục 5 — ít nhất 3 ràng buộc, mỗi ràng buộc nêu ảnh hưởng tới kết quả. Ứng viên: không có giá/doanh
      thu; không có ngày tháng thật (mùa vụ, khuyến mãi); không có tồn kho / hết hàng / thay thế; không có
      nhân khẩu học hoặc khu vực; phí và khung giờ giao hàng; dữ liệu là snapshot ẩn danh đã chọn lọc.
- [ ] Làm slides; phân công mỗi người trình bày phần mình làm.

### TV3 — Duyệt
- [ ] Duyệt số liệu trong Word khớp với `docs/report.md`.
- [ ] Duyệt mục 2, 3a, 4 về độ chính xác kỹ thuật; duyệt slides trước buổi thuyết trình.
- [ ] Kiểm tra chạy lại các kết quả chính từ mã nguồn.

## 5. Mốc thời gian (đếm ngược từ tuần 14)

```text
Mốc 1  : Họp chốt mục 1; TV1 viết mục 1, dựng khung Word
Mốc 2  : TV3 xong customer features | TV1 xong transactions
Mốc 3  : TV3 chạy clustering | TV1 chạy Apriori/FP-Growth ──► bàn giao itemsets cho TV2
Mốc 4  : TV2 sinh và đánh giá luật | TV3 bàn giao kết quả clustering cho TV1
Mốc 5  : (tùy chọn) luật theo cluster; TV2 viết mục 4, 5
Mốc 6  : TV1 ghép Word, TV2 làm slides, TV3 duyệt
Tuần 14: Nộp zip + bản cứng + thuyết trình
```

Trong lúc chờ TV1 bàn giao itemsets, TV2 viết code sinh luật trên một mẫu nhỏ và bắt đầu mục 5.

## 6. Quy tắc làm việc

- Code mới trong `src/instacart_mining/`, có test `tests/test_*.py`. Chạy `python -m ruff check src tests`
  và `python -m pytest` trước khi merge. Mỗi người một branch (`feat/clustering`, `feat/itemsets`,
  `feat/rules`).
- Seed lấy từ `config/project.toml` (`random_seed = 42`). Artifact ghi vào `artifacts/`.
- Số liệu vào `docs/report.md` phải có entry tương ứng trong `docs/execution-log.md`. `report.md` chỉ
  ghi số liệu factual; nhận xét và thảo luận viết trong file Word.
- Figure theo quy ước trong `AGENTS.md`. Không sửa `data/` và không sửa tay `docs/figures/`.
- Tránh đạo văn: tự viết, trích dẫn nguồn Kaggle và tài liệu tham khảo.
