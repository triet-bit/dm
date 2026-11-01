# Execution Log

Nhật ký này liên kết từng lần chạy với số liệu, bảng hoặc figure được ghi trong
`docs/report.md`. Dùng timezone `GMT+07:00` và thêm entry theo thứ tự thời gian tăng dần.

## Entry template

```markdown
## YYYY-MM-DD HH:MM GMT+07:00 — <step name>

- Report updated: `<section or table/figure reference>`
- Command/script: `<exact command or script path>`
- Input/source: `<data and source paths>`
- Parameters/seed: `<parameters and random seed>`
- Output: `<generated file paths>`
- Recorded values: `<only the values copied into report.md>`
```

## 2026-10-20 21:47 GMT+07:00 — Visualize customer behavior EDA

- Report updated: `docs/report.md` mục 3–8 và Figure 3–7 (thêm mục 4 ngày/giờ đặt hàng, mục 5 khoảng cách giữa các đơn, mục 6 kích thước giỏ, mục 7 biến động kích thước giỏ; cập nhật bảng file sinh ra)
- Command/script: `.venv/bin/python src/eda_behavior.py`; `.venv/bin/python src/figures_paper.py`
- Input/source: `data/orders.csv`, `data/orders_prior.csv`, `data/order_products__prior.csv`
- Parameters/seed: seed 42 (không lấy mẫu ngẫu nhiên, dùng toàn bộ dữ liệu); đọc `order_products__prior.csv` theo chunk 5.000.000 dòng; loại 206.209 đơn đầu tiên (NaN) khỏi phân phối khoảng cách; biến động giỏ tính trên các cặp đơn liên tiếp trong `prior`
- Output: `docs/figures/fig_orders_per_customer.pdf`/`.png`, `fig_order_timing.pdf`/`.png`, `fig_days_since_prior.pdf`/`.png`, `fig_basket_size.pdf`/`.png`, `fig_basket_variation.pdf`/`.png`, `docs/behavior_summary.json`
- Recorded values: 206.209 khách, 3.421.083 đơn, median 10 đơn/khách, Q3 20; thời điểm đặt hàng n = 3.214.874, ngày mã 0 cao nhất 17.35%, giờ 10 cao nhất 8.46%, khung 9–16 giờ 64.96%; khoảng cách n = 3.008.665, median 7 ngày, 0 ngày 64.436 (2.14%), 30 ngày 10.18%; giỏ hàng n = 3.214.874, mean 10.09 item, median 8, Q3 14, max 145; biến động n = 3.008.665 cặp, median |Δ| = 3, không đổi 10.68%, r lag-1 = 0.5783
- Note: Figure 1–2 được vẽ lại theo cùng palette/font sans-serif; số liệu không đổi.

## 2026-10-20 22:26 GMT+07:00 — Visualize product popularity, diversity and reorder behavior

- Report updated: `docs/report.md` thêm mục 8–12 và Figure 8–13; đổi mục "File sinh ra" thành mục 13
- Command/script: `.venv/bin/python src/eda_products.py`
- Input/source: `data/order_products__prior.csv`, `data/orders_prior.csv`, `data/products.csv`, `data/aisles.csv`, `data/departments.csv`
- Parameters/seed: seed 42 (không lấy mẫu ngẫu nhiên); đọc theo chunk 4.000.000 dòng; loại 2.078.068 dòng thuộc đơn đầu tiên khi tính reorder; ngưỡng hiển thị: sản phẩm ≥ 100 dòng hợp lệ cho phân phối, ≥ 5.000 cho top tỉ lệ, aisle ≥ 10.000
- Output: `docs/figures/fig_top_products.pdf`/`.png`, `fig_top_groups.pdf`/`.png`, `fig_popularity_longtail.pdf`/`.png`, `fig_customer_diversity.pdf`/`.png`, `fig_reorder_products.pdf`/`.png`, `fig_reorder_groups.pdf`/`.png`, `docs/product_summary.json`
- Recorded values: 49.677 sản phẩm, 32.434.489 dòng; Banana 472.565 dòng (1.46%); produce 29.23%, dairy eggs 16.69%; Gini 0.8738, top 1% = 42.80%, top 10% = 81.43%, 4.538 sản phẩm cho 80%; diversity median 48 (Q1 25, Q3 86, max 726), median 4.77 sản phẩm/đơn; reorder 63.01% trên 30.356.421 dòng hợp lệ, median sản phẩm 53.85%, dairy eggs 71.39%, milk aisle 82.82%
- Tests: `tests/test_eda_products.py` (3 test cho Gini/long-tail, tổng hợp nhóm và tỉ lệ sản phẩm); `python -m pytest` 7 passed
- Note: `reordered` của đơn đầu tiên bằng 0 cho toàn bộ 2.078.068 dòng, nên các đơn này được loại khỏi mẫu số tỉ lệ mua lại.

## 2026-10-20 22:28 GMT+07:00 — Correct diversity order groups and section numbering

- Report updated: `docs/report.md` mục 11 (bảng độ đa dạng theo nhóm số đơn), đánh số lại mục 8–13; `docs/product_summary.json` cập nhật `diversity.by_order_group`
- Command/script: `.venv/bin/python src/eda_products.py`; `.venv/bin/python -m pytest`
- Input/source: `data/order_products__prior.csv`, `data/orders_prior.csv`, `data/products.csv`
- Parameters/seed: seed 42; nhóm theo tổng số đơn = số đơn `prior` + 1; bins (3, 10], (10, 25], (25, 50], (50, 100]
- Output: `docs/product_summary.json`; các figure 8–13 được tái tạo cùng lần chạy
- Recorded values: sửa tỉ lệ mua lại của Organic Blueberries từ 67.73% thành 67.69%; nhóm 4–10 đơn: 104.513 khách, median 30 sản phẩm, 6.00 sản phẩm/đơn prior; 11–25: 63.671, 67, 4.54; 26–50: 27.115, 112, 3.35; 51–100: 10.910, 162, 2.41; tổng 206.209 khách
- Tests: `tests/test_eda_products.py` thêm 3 test; `python -m pytest` 7 passed
- Note: bảng trước đó dùng trực tiếp số đơn `prior` với bin bắt đầu tại 3 nên bỏ sót 23.986 khách có 3 đơn `prior` (4 đơn tổng); đã sửa bằng cách dùng tổng số đơn.

## 2026-10-20 23:02 GMT+07:00 — Visualize purchase frequency, recency and product co-occurrence

- Report updated: `docs/report.md` thêm mục 13–15 và Figure 14–16; đổi mục "File sinh ra" thành mục 16
- Command/script: `.venv/bin/python src/eda_repeat.py`; `.venv/bin/python src/eda_cooccurrence.py`
- Input/source: `data/orders_prior.csv`, `data/orders_train.csv`, `data/order_products__prior.csv`, `data/order_products__train.csv`, `data/products.csv`
- Parameters/seed: seed 42 (không lấy mẫu ngẫu nhiên); holdout là đơn `train` ngay sau `prior`; 131.209 khách train; recency tính bằng số đơn, không dùng ngày vì `days_since_prior_order` cap 30; co-occurrence giới hạn 300 sản phẩm phổ biến nhất, support ≥ 0,05% cho bảng lift, mỗi sản phẩm tối đa 1 cặp và mỗi aisle tối đa 3 cặp khi chọn top lift
- Output: `docs/figures/fig_purchase_frequency_repurchase.pdf`/`.png`, `fig_recency_repurchase.pdf`/`.png`, `fig_product_pairs.pdf`/`.png`, `docs/repeat_summary.json`, `docs/cooccurrence_summary.json`
- Recorded values: 8.474.661 cặp; 20.641.991 dòng prior; 828.824/1.384.617 dòng train là mua lại (59,86%), 6,32 sản phẩm mua lại/đơn; xác suất mua lại theo cặp 9,78%; tần suất 1 lần 59,98%, ≥2 lần 40,02%; mua lại theo tần suất 4,71% → 48,43%; recency median 4 đơn, 16,04% recency 0; mua lại theo recency 27,92% → 1,05%; 3.214.874 đơn, 44.850 cặp trong 300 sản phẩm, 4.677 cặp support ≥ 0,05%; cặp cùng đơn nhiều nhất 62.341 đơn (1,94%), lift cao nhất 73,64
- Tests: `tests/test_eda_repeat.py` (2 test) và `tests/test_eda_cooccurrence.py` (2 test); `python -m pytest` 11 passed
- Dependency: thêm `scipy` vào `requirements.txt` cho ma trận thưa co-occurrence
- Note: mẫu mua lại chỉ gồm khách có đơn `train`; xác suất 9,78% là trên cặp (khách, sản phẩm), không phải tỉ lệ dòng trong đơn.

## 2026-10-21 08:08 GMT+07:00 — Redesign Figures 1–3

- Report updated: `docs/report.md` mục 1–3 (caption Figure 1–3)
- Command/script: `.venv/bin/python src/figures_paper.py`; `.venv/bin/python -` (gọi `eda_behavior.fig_orders_per_customer` với `docs/behavior_summary.json`); `.venv/bin/python -m ruff check src tests`; `.venv/bin/python -m pytest -q`
- Input/source: `docs/summary.json`, `docs/behavior_summary.json`, `data/orders.csv`
- Parameters/seed: seed 42 (không lấy mẫu ngẫu nhiên); Figure 1–2 đọc lại số liệu từ `docs/summary.json`; Figure 3 đếm `user_id` trên `data/orders.csv`; không thay đổi dữ liệu nguồn
- Output: `docs/figures/fig_eval_split.pdf`/`.png`, `fig_missing.pdf`/`.png`, `fig_orders_per_customer.pdf`/`.png` (PNG 300 dpi, PDF vector)
- Recorded values: 3.421.083 đơn = prior 3.214.874 (93,97%) + train 131.209 (3,84%) + test 75.000 (2,19%); 23 cột trên 6 file, 1 cột có missing 6,03% (206.209 dòng); 206.209 khách, median 10 đơn, Q3 20 đơn, 1.374 khách ở mốc 100
- Tests: `python -m pytest` 11 passed; `ruff check src tests` passed
- Note: Figure 1 chuyển sang 2 panel (A: thanh 100% tỉ lệ, B: số đơn thang log) thay cho thanh log bị cắt trục; Figure 2 chuyển từ barh 23 dòng sang dot plot có nhóm theo file; Figure 3 bỏ histogram bin rộng 1 đứt quãng, tô riêng cột mốc 100 và vẽ ECDF dạng step.

## 2026-10-22 22:23 GMT+07:00 — Visualize table sizes, department popularity and first-in-cart products

- Report updated: `docs/report.md` mục 16–18 và Figure 17–19; thêm script/file vào mục 25 "File sinh ra"
- Command/script: `.venv/bin/python src/eda_catalog.py`
- Input/source: `data/orders.csv`, `data/order_products__prior.csv`, `data/order_products__train.csv`, `data/products.csv`, `data/aisles.csv`, `data/departments.csv`
- Parameters/seed: seed 42 (chỉ dùng để lấy 250 điểm thô mỗi department cho strip plot); đọc theo chunk 4.000.000 dòng; ngưỡng tỉ lệ vào giỏ đầu: sản phẩm ≥ 5.000 dòng; top 10% = làm tròn lên số sản phẩm của department
- Output: `docs/figures/fig_dataset_overview.pdf`/`.png`, `fig_department_popularity.pdf`/`.png`, `fig_first_in_cart.pdf`/`.png`, `docs/catalog_summary.json`
- Recorded values: orders.csv 3.421.083 dòng, order_products__prior 32.434.489, order_products__train 1.384.617, products 49.688, aisles 134, departments 21; 49.677 sản phẩm có dòng prior; produce median 329 dòng/sản phẩm, missing median 12; top 10% sản phẩm chiếm 81,23% dòng produce và 48,57% dòng pets; 3.214.874 dòng ở vị trí giỏ đầu; Banana 110.916 lần ở vị trí 1 (23,47%); Organic Low Fat Milk tỉ lệ cao nhất 40,51%
- Tests: `tests/test_eda_extra.py` (`top_share`); `python -m pytest` 16 passed
- Note: các giá trị trên lấy từ `docs/catalog_summary.json`; không sửa file trong `data/`.

## 2026-10-22 22:23 GMT+07:00 — Visualize basket size by time, customer profile, behavior groups and reorder rate

- Report updated: `docs/report.md` mục 19–22 và Figure 20–23; thêm script/file vào mục 25
- Command/script: `.venv/bin/python src/eda_customers.py`
- Input/source: `data/orders_prior.csv`, `data/order_products__prior.csv`
- Parameters/seed: seed 42 (chọn 6.000 khách cho scatter PCA); chunk 4.000.000 dòng; 4 đặc trưng PCA = mean_gap, mean_basket, distinct_products, reorder_rate; `log1p` cho mean_gap, mean_basket, distinct_products rồi z-score; nhóm = tertile của mean_gap (không clustering); PCA bằng SVD numpy trên toàn bộ 206.209 khách; reorder rate của khách tính trên dòng của đơn `order_number ≥ 2`; không có đơn thiếu item và không có khách thiếu giá trị
- Output: `docs/figures/fig_basket_by_time.pdf`/`.png`, `fig_customer_profile.pdf`/`.png`, `fig_customer_segments.pdf`/`.png`, `fig_reorder_rate.pdf`/`.png`, `docs/customer_summary.json`
- Recorded values: giỏ median 9 (mã 0 và 6, mean 11,13 và 10,74) và 8 các ngày còn lại; median số đơn prior 9, sản phẩm khác nhau 48, giỏ trung bình 8,93, tỉ lệ mua lại 50,00%; Spearman số đơn–đa dạng 0,6736; ba nhóm mean_gap có 68.746 / 68.874 / 68.589 khách; PC1 47,88%, PC2 30,39% phương sai; reorder 58,97% trên mọi dòng prior, 63,01% trên đơn `order_number ≥ 2`; tỉ lệ gộp theo order_number 27,24% (2) → 84,26% (99); theo ngày 73,88% (0), 61,76% (1), 45,56% (30)
- Tests: `tests/test_eda_extra.py` (`reorder_by`, `standardize`, `pca`, `frequency_groups`); `python -m pytest` 16 passed
- Note: số đơn prior mỗi khách trong mục 20 (min 3, max 99) khác Figure 3 (đếm cả đơn train/test, min 4, max 100). Mã `order_dow` 0 và 6 được ghi nguyên như trong dữ liệu.

## 2026-10-22 22:23 GMT+07:00 — Visualize department co-occurrence and support vs lift

- Report updated: `docs/report.md` mục 23–24 và Figure 24–25; thêm script/file vào mục 25
- Command/script: `.venv/bin/python src/eda_association.py`
- Input/source: `data/orders_prior.csv`, `data/order_products__prior.csv`, `data/products.csv`, `data/departments.csv`
- Parameters/seed: seed 42 (không lấy mẫu ngẫu nhiên); chunk 4.000.000 dòng; department hiện diện theo đơn (mỗi đơn tính một lần mỗi department); cặp sản phẩm giới hạn 300 sản phẩm phổ biến nhất, support ≥ 0,05%, top 50 theo số đơn chứa cả hai; Spearman không hiệu chỉnh multiple testing
- Output: `docs/figures/fig_department_pairs.pdf`/`.png`, `fig_support_vs_lift.pdf`/`.png`, `docs/association_summary.json`
- Recorded values: 210 cặp department, lift 0,11 – 3,10, 185 cặp lift > 1; produce + dairy eggs support 55,05% (1.769.735 đơn), lift 1,08; alcohol + other lift cao nhất 3,10; Spearman support–lift 0,5607 (44.850 cặp) và 0,0286 (4.677 cặp support ≥ 0,05%, p = 0,050); 15 cặp có số đơn cao nhất lift 1,44 – 3,00; 49/50 cặp top số đơn có lift > 1
- Tests: `tests/test_eda_extra.py` (`department_cooccurrence`, `support_lift`); `python -m pytest` 16 passed
- Note: ma trận đồng xuất hiện department dùng mảng bool theo đơn để tránh đếm đúp khi một đơn nằm ở hai chunk.

## 2026-10-26 09:17 GMT+07:00 — Verify commentary figures and remove bold from report text

- Report updated: `docs/report.md` mục 5, 6, 20 (số liệu trong phần Nhận xét); bỏ in đậm ở phần text và nhận xét mục 1–22 (giữ in đậm ở tiêu đề bảng và hàng tổng trong bảng)
- Command/script: inline `.venv/bin/python` (pandas) — not saved as script
- Input/source: `data/orders.csv`, `data/order_products__prior.csv`
- Parameters/seed: not applicable; kích thước giỏ = số dòng order–product mỗi đơn `prior`; tỉ lệ mua lại của khách tính trên dòng của đơn `order_number ≥ 2`
- Output: `docs/report.md`
- Recorded values: mode kích thước giỏ 5 item (228.330 đơn, 7,10%), 6 item (227.675 đơn, 7,08%); đơn ≥ 40 item 0,50%; đơn ≤ 8 item 51,39%, ≤ 14 item 77,82%; `days_since_prior_order` 7 ngày 10,18%, 14 ngày 3,09%, 21 ngày 1,37%, 28 ngày 0,79%, 30 ngày 10,18%; 11 sản phẩm trong catalog không xuất hiện trong `prior`; khách có tỉ lệ mua lại 0% là 1,48%, 100% là 0,47%; khách có giỏ trung bình 5–13 item là 56,15%
- Tests: not applicable
- Note: `.venv` được tạo mới và cài `requirements.txt`.

## 2026-10-26 09:40 GMT+07:00 — Add dataset overview section

- Report updated: `docs/report.md` mục 0 (Tổng quan về dataset) và danh sách mục ở đầu report
- Command/script: inline `.venv/bin/python` (pandas) kiểm tra schema, khoá và miền giá trị; `ls -la data/` cho dung lượng file — not saved as script
- Input/source: `data/orders.csv`, `data/order_products__prior.csv`, `data/order_products__train.csv`, `data/products.csv`, `data/aisles.csv`, `data/departments.csv`
- Parameters/seed: not applicable
- Output: `docs/report.md`, `docs/schema.dbml`
- Recorded values: số dòng 6 file (3.421.083 / 32.434.489 / 1.384.617 / 49.688 / 134 / 21); miền giá trị `order_number` 1–100, `order_dow` 0–6, `order_hour_of_day` 0–23, `days_since_prior_order` 0–30, `add_to_cart_order` 1–145 (prior) và 1–80 (train); 0 cặp `(order_id, product_id)` trùng trong `order_products__prior`; 0 cặp `(user_id, order_number)` trùng; mọi `order_id`/`product_id` trong `order_products__*` tồn tại trong `orders`/`products`; 206.209 khách, mỗi khách đúng 1 đơn `train` hoặc `test` (131.209 / 75.000)
- Tests: not applicable
- Note: thông tin nguồn (Kaggle 2017) và việc dữ liệu đã ẩn danh là mô tả chung về bộ dữ liệu, không đo từ file.

## 2026-10-26 09:55 GMT+07:00 — Extend section 4 commentary

- Report updated: `docs/report.md` mục 4 (Nhận xét)
- Command/script: inline `.venv/bin/python` (pandas crosstab `order_dow` × `order_hour_of_day`, chuẩn hoá theo ngày) — not saved as script
- Input/source: `data/orders_prior.csv`
- Parameters/seed: not applicable
- Output: `docs/report.md`
- Recorded values: ngày 0 + 1 chiếm 34,67% số đơn; giờ cao điểm theo ngày: ngày 0 và 6 lúc 14 giờ (9,05% và 8,62% đơn của ngày), ngày 1–5 lúc 10 giờ (8,24% – 9,52%); tỉ lệ giờ 10 / giờ 3 ≈ 53,1 lần
- Tests: not applicable
- Note: not applicable

## 2026-11-01 09:52 GMT+07:00 — Clarify section 13 sample metrics

- Report updated: `docs/report.md` mục 13 (chuẩn hoá bảng định nghĩa và công thức tính các chỉ số mẫu)
- Command/script: not applicable
- Input/source: `docs/repeat_summary.json`
- Parameters/seed: not applicable
- Output: `docs/report.md`
- Recorded values: 131.209 khách train; 20.641.991 dòng prior của mẫu; 8.474.661 cặp duy nhất (khách, sản phẩm); 1.384.617 dòng train, 828.824 dòng mua lại (59,86%); mean 6,32 sản phẩm mua lại/đơn; xác suất mua lại theo cặp 9,78%
- Tests: not applicable
- Note: chuyển danh sách số liệu rời rạc thành bảng có mô tả cách tính và công thức đối chiếu, không thay đổi số liệu gốc.

## 2026-11-01 11:12 GMT+07:00 — Merge section 16 into section 0 and renumber sections

- Report updated: `docs/report.md` mục 0 (thêm mục 0.1 Quy mô bảng và số thực thể từ mục 16 cũ), xóa mục 16 cũ và đánh số lại mục 16–24
- Command/script: not applicable
- Input/source: `docs/report.md`
- Parameters/seed: not applicable
- Output: `docs/report.md`
- Recorded values: 49.688 sản phẩm catalog, 49.677 sản phẩm prior, 134 aisle, 21 department; phân phối sản phẩm theo 21 department; Figure 17 overview
- Tests: not applicable
- Note: ghép nội dung quy mô bảng và số thực thể lên mục 0 để nhóm toàn bộ thông tin tổng quan dataset vào đầu tài liệu; sửa số thứ tự các mục 17–25 thành 16–24.

## 2026-11-01 15:09 GMT+07:00 — Complete section 20 introductory framing

- Report updated: `docs/report.md` mục 20 (Nhóm hành vi khách hàng)
- Command/script: not applicable
- Input/source: `docs/customer_summary.json`
- Parameters/seed: not applicable
- Output: `docs/report.md`
- Recorded values: 4 đặc trưng phân tích (`mean_gap`, `mean_basket`, `distinct_products`, `reorder_rate`); biến đổi `log1p` và z-score; n = 206.209 khách
- Tests: not applicable
- Note: bổ sung hoàn chỉnh đoạn văn mở đầu và 4 câu hỏi định hình 4 đặc trưng hành vi khách hàng ở mục 20.


