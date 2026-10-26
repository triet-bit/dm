# Học EDA bằng cách tự tái tạo

Quy tắc: **bạn viết code và nhận xét trước, AI chỉ review.** Không mở `src/eda_*.py`
hay `docs/report.md` trước khi có kết quả của riêng bạn.

## Vòng lặp cho mỗi task (30–60 phút)

1. Copy `worksheet_template.md` thành `scratch/taskNN.md`, điền phần A (trước khi code).
2. Viết code đơn giản trong `scratch/taskNN.py` (hoặc notebook). Dùng `nrows=` hoặc một
   `usecols` nhỏ trước, đừng load cả `order_products__prior.csv` nếu chưa cần.
3. Chạy `python learning/check.py <khoá> <giá trị của bạn>` để biết khớp hay lệch.
   Lệch thì tự debug 15 phút trước khi hỏi AI.
4. Viết nhận xét của bạn (phần C), rồi mới nhờ AI phản biện.
5. Cuối cùng so sánh code của bạn với `src/` và ghi lại khác biệt (phần D).

## Nhờ AI review bằng prompt nào

- "Đây là code và nhận xét của tôi cho Task N. Chỉ ra: (1) đếm sai cấp dữ liệu,
  (2) leakage, (3) câu nào trong nhận xét vượt quá số liệu, (4) biểu đồ có đo đúng
  metric không. Không viết lại code giúp tôi."
- Khi bị lỗi: "Gợi ý cách kiểm tra, đừng đưa đáp án."

## Thứ tự gợi ý (dễ → khó, mỗi nhóm có một bẫy riêng)

| Nhóm | Task | Bẫy cần tự phát hiện |
|---|---|---|
| Khởi động | 9, 5, 6, 3 | Đơn vị phân tích là đơn hay dòng? Dùng bảng `orders` hay `orders_prior`? |
| Cấp dữ liệu | 11, 13, 14, 17 | Đếm số dòng hay số đơn chứa? Cùng một sản phẩm có xuất hiện hai lần trong một đơn không? |
| Mẫu số | 23, 24, 25, 20 | Đơn đầu tiên có `reordered = 0` hoàn toàn — nên đưa vào mẫu số không? Tỉ lệ gộp hay trung bình tỉ lệ? |
| Thiếu và chặn | 8, 26 | `NaN` và giá trị 30 của `days_since_prior_order` nghĩa là gì? |
| Leakage | 27 | Tập nào là lịch sử, tập nào là nhãn? Đơn `train` nằm ở đâu so với `prior`? |
| Cặp và lift | 28, 29, 30 | Support/lift tính trên đơn hay trên dòng? Vì sao lift cao với support thấp có thể là nhiễu? |

Task 22 (nhóm hành vi) để cuối cùng, khi bạn đã tự tính được 4 đặc trưng ở cấp khách.
