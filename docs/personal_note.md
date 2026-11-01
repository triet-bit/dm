- các ngày từ 0->6 không có ý nghĩa là từ CN->T7, vì trong datacard bài toán gốc không có xác nhận điều này 
- hệ số tương quan thuận 
- Tỷ lệ mua lại gộp (63,01%) > Trung vị (53,85%) vì tỷ lệ gộp là trung bình có trọng số theo lượt mua: nhóm sản phẩm bán chạy nhất (high volume như chuối, sữa tươi) đều có tỷ lệ mua lại áp đảo (80%–90%), tạo trọng số lớn kéo tỷ lệ gộp vượt lên trên trung vị của toàn bộ sản phẩm.
- Ý tưởng Modeling & Feature Engineering từ EDA Reorder:
  + Feature Engineering cho Reorder Prediction: Tỷ lệ mua lại theo sản phẩm, aisle, department là các đặc trưng baseline priors quan trọng nhất (ví dụ: nhóm dairy eggs và aisle milk có xác suất tiên nghiệm cao hơn gấp đôi so với nhóm personal care).
  + Xử lý mẫu nhỏ (Cold-start / Low-support items): Với những sản phẩm ít lượt mua (< 100 dòng), tỷ lệ mua lại cấp sản phẩm không đáng tin cậy. Khi đó, có thể dùng kỹ thuật làm mịn (Bayesian shrinkage / additive smoothing) dựa trên tỷ lệ của aisle hoặc department trực thuộc.
- Trong tập `train` (và `test`), mỗi khách chỉ có đúng 1 đơn hàng cuối cùng (131.209 đơn = 131.209 khách). Do đó, "trung bình sản phẩm mua lại trên mỗi đơn train" đồng nhất với "trung bình sản phẩm mua lại trên mỗi khách" (đều bằng 828.824 / 131.209 ≈ 6,32 món), khác hoàn toàn với tập `prior` (một khách có nhiều đơn).
- Ý tưởng Modeling từ Tần suất mua (Frequency in Prior):
  + Đặc trưng `user_product_total_orders` (số lần user đã mua item): Tần suất mua tỉ lệ thuận mạnh mẽ với xác suất mua lại (từ 4,71% khi mua 1 lần lên 48,43% khi mua >= 20 lần — tăng hơn 10 lần). Đây sẽ là feature có độ quan trọng (feature importance) hàng đầu cho mô hình (LightGBM/XGBoost).
  + Đánh đổi Số lượng vs Chất lượng: Nhóm mua >= 20 lần có tỷ lệ trúng rất cao (48,43%) nhưng số lượng cặp rất ít (0,85%). Ngược lại, nhóm mua 1 lần có tỷ lệ trúng thấp (4,71%) nhưng lượng ứng viên khổng lồ (gần 60%), vẫn đóng góp tới gần 30% tổng số lượt mua lại thực tế trong `train` (~239k / 828k món). Do đó không thể loại bỏ nhóm mua 1 lần mà cần kết hợp thêm recency (độ mới) và danh mục để sàng lọc.
- Phân biệt hai khái niệm Recency:
  + Recency ở Mục 14 (Chủ thể: Cặp Khách hàng – Sản phẩm): Đo số đơn hàng trôi qua mà món đồ đó vắng mặt trong giỏ ("Đã bao nhiêu lần đi chợ khách chưa mua lại món Y?"). Phục vụ dự đoán Reorder.
  + Recency theo Khách hàng (Customer Recency trong mô hình RFM): Đo số ngày từ lần cuối khách đặt đơn ("Đã bao lâu khách chưa mở app mua hàng?"). Phục vụ bài toán Churn Prediction hoặc Phân khúc khách hàng.
- Bản chất và Đơn vị trong Khai phá Luật kết hợp (Association Rules):
  + Không gian khảo sát: Giới hạn top 300 sản phẩm tạo ra C(300, 2) = 44.850 cặp nhằm tránh bùng nổ tổ hợp C(50k, 2) ≈ 1,23 tỷ cặp gây tràn bộ nhớ và nhiễu dữ liệu.
  + Support (đơn vị %): Tỷ lệ đơn chứa cả A và B trên tổng số đơn. Đo lường độ phổ biến toàn cục của cặp.
  + Confidence A→B (đơn vị %): Xác suất có điều kiện P(B|A) — nếu đã nhặt A thì bao nhiêu % nhặt thêm B. Mang tính định hướng bất đối xứng (Conf A→B ≠ Conf B→A).
  + Lift (hệ số tỉ lệ / số lần, không có đơn vị): Mức độ gắn kết thực sự sau khi triệt tiêu độ phổ biến tự nhiên. Lift = 1 (độc lập), Lift > 1 (tương hỗ mạnh), Lift < 1 (thay thế/triệt tiêu).
  + Đánh đổi Top Support vs Top Lift: Cặp top Support (Chuối + Bơ) xuất hiện cùng nhau chủ yếu do bản thân mỗi món ai cũng mua (Lift thấp ~1,5–2,5); ngược lại, cặp top Lift (các vị sữa chua, nước có ga khác nhau) có Support thấp (<0,25%) nhưng Lift vọt lên hàng chục lần (~20–74 lần) phản ánh thói quen mua kèm nhiều biến thể cùng dòng.
- Mức độ tập trung (Hiệu ứng Pareto 80/20) theo từng Department:
  + Định nghĩa chỉ số "Dòng của 10% sản phẩm đầu (%)": Lấy top 10% sản phẩm bán chạy nhất trong ngành hàng, tính tỷ lệ số lượt mua của nhóm này so với tổng lượt mua của cả ngành hàng đó.
  + Phân hóa giữa các ngành hàng:
    * Tập trung cao nhất — `produce` (81,23%) và `dairy eggs` (72,82%): Hiệu ứng Pareto thể hiện rõ rệt, chỉ 10% sản phẩm đầu bảng (chuối, bơ, sữa tươi...) đã gánh hơn 70%–81% lượt mua của cả ngành. Khách hàng chủ yếu mua đi mua lại các nhu yếu phẩm quen thuộc.
    * Phân tán nhất — `pets` (48,57%): Thị trường rất ngách và dàn trải (mỗi giống thú cưng dùng một loại thức ăn/đồ dùng riêng), không có sản phẩm nào áp đảo tuyệt đối.
  + Ý nghĩa Modeling: Các ngành hàng tập trung cao sẽ có độ phân tách mạnh và dễ dự đoán Reorder hơn nhờ baseline prior; các ngành hàng phân tán đòi hỏi mô hình phải dựa nhiều hơn vào sở thích cá nhân hóa của từng user.
- Quy trình tiền xử lý và phương pháp luận phân khúc khách hàng & PCA (Mục 20):
  + Biến đổi `log1p(x) = ln(1 + x)`:
    * Áp dụng cho 3 biến có phân phối lệch phải mạnh / đuôi dài (`mean_gap`, `mean_basket`, `distinct_products`) nhằm nén các giá trị ngoại lai cực lớn, đưa phân phối về dạng gần đối xứng (chuông chuẩn).
    * Không áp dụng cho `reorder_rate` vì đây là tỷ lệ phần trăm bị chặn trong đoạn $[0, 1]$ (hoặc $0–100\%$) và phân phối tự nhiên đã đối xứng quanh mốc $50\%$.
  + Chuẩn hóa Z-score ($z = \frac{x - \mu}{\sigma}$):
    * Đưa cả 4 đặc trưng về cùng thang đo: trung bình $\mu = 0$, độ lệch chuẩn $\sigma = 1$.
    * Bắt buộc trước khi chạy PCA vì thuật toán tối đa hóa phương sai; nếu không chuẩn hóa, các biến có thang đo lớn (như `distinct_products` lên đến hàng trăm) sẽ có phương sai áp đảo, hoàn toàn làm lu mờ biến tỷ lệ nhỏ (`reorder_rate` chỉ từ $0$ đến $1$).
  + Phân nhóm theo Tertile của `mean_gap` thay vì Clustering:
    * Tertile (tam phân vị) chia 206.209 khách thành 3 nhóm bằng nhau về số lượng (mỗi nhóm $33,33\% \approx 68.700$ khách) theo chu kỳ đi chợ: Gap ngắn ($\le 11$ ngày), Gap vừa ($11–18$ ngày), Gap dài ($18–30$ ngày).
    * Lý do không dùng thuật toán phân cụm (K-Means/DBSCAN): Không gian hành vi khách hàng Instacart là một dải phân bố liên tục (continuum), không có cụm tự nhiên tách rời. Ép K-Means sẽ tạo ranh giới khiên cưỡng. Phân khúc theo luật kinh doanh (Rule-based / RFM) vừa khách quan, vừa dễ hiểu và ứng dụng thực tế hơn.
  + PCA tính bằng SVD trên toàn bộ 206.209 khách hàng:
    * Dùng SVD (Singular Value Decomposition) trên toàn bộ dữ liệu giúp tỷ lệ giải thích phương sai (PC1 $47,88\%$, PC2 $30,39\%$, giữ lại $78,27\%$ thông tin) và hệ số tải trọng phản ánh chuẩn xác $100\%$ toàn bộ cơ sở dữ liệu.
  + Lấy mẫu 6.000 khách vẽ scatter với `seed = 42`:
    * Giải quyết hiện tượng đè điểm (Overplotting): 206k điểm sẽ đặc quánh thành một mảng màu, không quan sát được mật độ. 6.000 điểm vừa đủ thấy rõ hình dạng đám mây elip.
    * Cố định `seed = 42` đảm bảo tính tái lập (Reproducibility) trong nghiên cứu khoa học.
- Phân biệt Tần suất đi chợ vs Kích thước giỏ vs Độ đa dạng (Mục 11, 19, 20):
  + Độ đa dạng (Số món tích lũy vs Tốc độ khám phá món mới):
    * Tổng số món khác nhau từng mua tích lũy (`distinct_products`) tăng thuận theo số đơn (từ median 28 món ở nhóm 4–5 đơn lên 175 món ở nhóm 61–100 đơn).
    * Cái "giảm" là tốc độ khám phá món mới trên mỗi đơn (`distinct / n_orders` giảm từ 6,00 xuống 2,41). Khách càng mua nhiều đơn thì càng lười thử món mới, giỏ hàng dần thu hẹp vào danh mục quen thuộc.
  + Nghịch lý kích thước giỏ hàng cố định (~9 món) giữa các nhóm tần suất:
    * Dù đi chợ hàng tuần (~7 ngày) hay hàng tháng (~23 ngày), kích thước giỏ trung bình (`mean_basket`) đều xấp xỉ quanh 9 món (tương quan $\rho(\text{mean\_gap}, \text{mean\_basket}) = -0,04$, hoàn toàn độc lập).
    * Khách mua thưa không hề "dồn toa" để mua giỏ lớn như siêu thị truyền thống mà là nhóm ít gắn bó (low-engagement / churned), chỉ đặt khi cần kíp vài món.
  + Kết luận cốt lõi: Tần suất đi chợ quyết định độ trung thành (`reorder_rate`: 61,54% ở nhóm đi hàng tuần vs 39,37% ở nhóm đi hàng tháng), chứ không quyết định độ to nhỏ của chiếc giỏ hàng mỗi lần mua.

