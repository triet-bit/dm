# Instacart Customer Shopping Mining

Phân tích dữ liệu Instacart Market Basket để khám phá phân khúc khách hàng,
luật kết hợp sản phẩm và dự đoán khả năng mua lại. Code mới được tổ chức thành
Python package có thể kiểm thử; các script EDA hiện có được giữ để tái tạo báo cáo.

## Mục tiêu và phạm vi

- Ba đầu ra chính: customer clustering, association rules và reorder prediction.
- Dùng dữ liệu cục bộ trong `data/`; không tải lại hoặc thay đổi dữ liệu gốc khi
  chưa được yêu cầu rõ ràng.
- Dùng tập `prior` làm lịch sử; tôn trọng tách `prior` / `train` / `test` để tránh
  rò rỉ dữ liệu theo thời gian hoặc theo khách hàng.

## Cấu trúc dự án

```text
config/                         # cấu hình dùng chung, không chứa secret
  project.toml                  # đường dẫn dữ liệu và tham số baseline
data/                           # CSV Instacart đầu vào (đã có sẵn)
docs/                           # đề bài, báo cáo, kết quả và hình xuất bản
  figures/                      # PNG/PDF được sinh từ script, không sửa thủ công
  report.md                     # chỉ số liệu, bảng/hình và mô tả factual
  execution-log.md              # nhật ký chi tiết các bước tạo/cập nhật report
src/
  analysis.py                   # EDA và tạo các thống kê/biểu đồ ban đầu
  figures_paper.py              # tái tạo figure theo phong cách báo cáo
  instacart_mining/             # package cho code phát triển mới
    data/                       # đọc, kiểm tra schema, tạo dataset phân tích
    features/                   # customer/order/customer-product features
    models/                     # clustering, association, reorder models
    evaluation/                 # metrics, validation và so sánh baseline
    visualization/              # biểu đồ tái sử dụng
tests/                          # pytest; tên file là test_*.py
requirements.txt                # dependencies chạy ứng dụng/analysis
requirements-dev.txt            # dependencies cho test và lint
pyproject.toml                  # cấu hình pytest, Ruff và packaging
```

## Cài đặt và lệnh

Dùng Python 3.11+ và virtual environment `.venv` tại root.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python src/analysis.py
python src/figures_paper.py
python -m pytest
python -m ruff check src tests
python -m compileall src
```

`compileall` là kiểm tra build hiện tại; dự án chưa có artifact deploy riêng.

## Quy ước code

- Dùng Python 3.11+, 4 spaces indent, UTF-8 và line length tối đa 100 ký tự.
- Dùng `snake_case` cho module, hàm, biến; `PascalCase` cho class;
  `UPPER_SNAKE_CASE` cho hằng số.
- Thêm type hints cho hàm public và docstring ngắn cho module/hàm public.
- Dùng `pathlib.Path` cho đường dẫn. Tính root từ `Path(__file__)`; không phụ
  thuộc current working directory.
- Hàm xử lý dữ liệu nhận input và trả output rõ ràng; chỉ CLI/script mới đọc file,
  ghi file hoặc in ra stdout.
- Đặt seed tường minh cho mọi thao tác ngẫu nhiên. Ghi feature list, split và
  metrics vào artifact kết quả để có thể tái lập.
- Đọc CSV lớn với `usecols`, `dtype` hoặc `chunksize` khi phù hợp; không load các
  bảng order-product đầy đủ nếu bài toán chỉ cần một phần cột/dòng.
- Dùng `ruff check src tests` trước khi hoàn tất thay đổi Python. Viết hoặc cập
  nhật test cho logic mới; không sửa artifact dưới `docs/figures/` thủ công.
- Không hard-code đường dẫn máy cá nhân, secret, ID cloud, hoặc kết quả đo lường
  chưa chạy. Không sửa CSV trong `data/` trừ khi yêu cầu nêu rõ file đích.

## Report và nhật ký thực thi

- Ghi mọi kết quả đã chạy vào `docs/report.md`. Report chỉ chứa số liệu, đơn vị,
  bảng/hình tham chiếu, cấu hình đo, và mô tả factual có thể kiểm chứng từ output.
- Dùng câu mô tả quan sát được, ví dụ `Median orders per customer: 10`; không ghi
  lập luận, diễn giải nguyên nhân, kết luận, khuyến nghị hoặc business implication.
  Phần diễn giải/kết luận do chủ dự án tự viết.
- Mỗi lần thêm hoặc thay đổi số liệu, bảng, hình trong `docs/report.md`, thêm một
  entry tương ứng vào `docs/execution-log.md` trong cùng thay đổi.
- Mỗi entry log dùng tiêu đề `## YYYY-MM-DD HH:MM GMT+07:00 — <step>` và nêu rõ:
  mục report đã cập nhật, lệnh/script đã chạy, input/source path, tham số/seed,
  output path, và tóm tắt số liệu được ghi. Ghi `not applicable` cho trường không
  áp dụng; không bịa giá trị chưa chạy.
- Giữ log theo thứ tự thời gian tăng dần. Log được phép ghi chi tiết kỹ thuật nhưng
  không thay thế report; report vẫn là nơi duy nhất trình bày kết quả chính.

## Quy ước figure học thuật bắt buộc

Áp dụng visual language của Academic Figure Skill cho mọi chart, plot và figure
kỹ thuật.

- Bắt đầu từ một câu hỏi khoa học và một thông điệp chính cho mỗi figure. Chọn
  chart dựa trên dữ liệu; không dùng template để thay cho lý do phân tích.
- Dùng Matplotlib/Seaborn hoặc R từ script tái lập được trong `src/`. Lưu script,
  đường dẫn dữ liệu nguồn, tham số và seed cùng artifact; không tạo figure số liệu
  bằng image generator.
- Tạo figure ở đúng kích thước xuất bản: 89 mm cho một cột hoặc 183 mm cho hai
  cột. Dùng nền trắng, font `Arial` hoặc `Helvetica` (fallback `DejaVu Sans`),
  cỡ chữ cuối cùng từ 5 pt trở lên, và panel label `A`, `B`, `C` in đậm khi có
  nhiều panel.
- Dùng palette thống nhất, thân thiện mù màu: primary `#3C78B5`, secondary
  `#E07A5F`, tertiary `#4D9A85`, neutral `#6C757D`, accent `#D6A430`.
  Dùng 2--4 màu semantic và tối đa một accent trong một figure; gán cùng một ý
  nghĩa dữ liệu cho cùng một màu xuyên suốt báo cáo.
- Dùng đường trục mảnh, chỉ giữ left/bottom spines, không dùng gridlines mặc định,
  viền bốn cạnh, colormap `jet`, legend che dữ liệu, hay title lặp lại caption.
  Đặt legend ngoài vùng dữ liệu khi cần; caption chỉ định nghĩa dữ liệu, đơn vị và
  phép đo, không nêu diễn giải hay kết luận.
- Hiển thị raw points cùng summary khi biểu đồ cột biểu diễn nhóm mẫu. Ghi rõ `n`,
  statistic trung tâm, độ phân tán, phép kiểm định và hiệu chỉnh multiple testing
  trong caption hoặc file thống kê khi áp dụng.
- Xuất master vector `PDF` (hoặc `SVG`) cho line, bar, scatter và text; kèm preview
  `PNG` tối thiểu 300 dpi. Dùng raster >=300 dpi chỉ cho nội dung raster thực sự.
- Đặt file là `docs/figures/fig_<topic>.pdf` và `.png`; figure nhiều panel dùng
  một basename. Không chỉnh sửa PNG/PDF thủ công sau khi script sinh ra.
- Trước khi hoàn tất, kiểm tra data range, nhãn/đơn vị, legend, font, palette,
  kích thước, PDF/PNG khác rỗng và khả năng đọc ở kích thước đặt trong báo cáo.

## Hỏi lại trước khi thực hiện

- Hỏi khi lựa chọn mục tiêu chính, metric đánh giá, mức lấy mẫu dữ liệu hoặc đơn
  vị split chưa được xác định.
- Hỏi trước khi đổi schema/ghi đè file trong `data/`, tải dữ liệu ngoài, thêm dịch
  vụ trả phí, hoặc chạy tác vụ dự kiến cần hơn 30 phút hay GPU.
- Hỏi trước khi chọn cách xử lý missing values, định nghĩa positive label cho
  reorder, hoặc threshold để diễn giải association rule nếu đề bài không chỉ rõ.
