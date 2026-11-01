# Instacart Customer Shopping Mining

Dự án khai phá dữ liệu giỏ hàng Instacart (Bài tập lớn môn Data Mining). Dự án tập trung vào phân tích hành vi mua sắm của khách hàng, phân cụm khách hàng và khai phá các luật kết hợp sản phẩm.

## 1. Mục tiêu chính

- **Customer Clustering:** Phân nhóm khách hàng dựa trên hành vi mua sắm (tần suất mua, quy mô giỏ hàng, độ đa dạng sản phẩm).
- **Association Rules Mining:** Khai phá tập mục phổ biến và luật kết hợp giữa các sản phẩm (so sánh hiệu năng và kết quả giữa Apriori và FP-Growth).
- **EDA & Insights:** Khảo sát toàn diện đặc trưng hành vi và cấu trúc tập dữ liệu Instacart (~37,3 triệu bản ghi, 206.209 khách hàng).

## 2. Cấu trúc thư mục

```text
├── config/              # Cấu hình dự án (project.toml)
├── data/                # Dữ liệu CSV Instacart (orders, products, aisles, departments...)
├── docs/                # Tài liệu, phân công và báo cáo
│   ├── figures/         # Biểu đồ và hình ảnh trực quan hóa
│   ├── report.md        # Báo cáo số liệu thực nghiệm EDA
│   └── task-assign.md   # Bảng phân công nhiệm vụ thành viên
├── src/                 # Mã nguồn chính
│   ├── analysis.py      # Script chạy EDA tổng thể
│   ├── figures_paper.py # Script tái tạo biểu đồ học thuật
│   └── instacart_mining/# Package xử lý dữ liệu, feature, model và đánh giá
├── tests/               # Unit test với pytest
├── requirements.txt     # Thư viện phục vụ chạy ứng dụng
└── requirements-dev.txt # Thư viện cho test và lint
```

## 3. Cài đặt và Chạy

Yêu cầu môi trường **Python 3.11+**.

```bash
# 1. Khởi tạo và kích hoạt virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Cài đặt dependencies phát triển
pip install --upgrade pip
pip install -r requirements-dev.txt

# 3. Chạy phân tích EDA
python src/analysis.py

# 4. Kiểm tra code style và unit test
python -m pytest
python -m ruff check src tests
```

## 4. Tài liệu tham khảo

- Báo cáo số liệu chi tiết: [`docs/report.md`](docs/report.md)
- Kế hoạch phân công công việc: [`docs/task-assign.md`](docs/task-assign.md)
