# Lab 25 Submission - GPU FinOps Optimization

## 1. Baseline vs Optimized

Trong phần core của Lab 25, hệ thống NimbusAI được phân tích theo hướng FinOps, tập trung vào chi phí GPU và chi phí inference tính theo `$/1M-token`.

Kết quả tổng hợp từ `outputs/report.md`:

| Metric | Value |
|---|---:|
| Baseline monthly spend | $27,133 |
| Optimized monthly spend | $14,626 |
| Monthly savings | $12,507 |
| Savings percentage | 46% |

Kết quả inference từ Mission 2:

| Metric | Baseline | Optimized |
|---|---:|---:|
| Daily inference cost | $48.87/day | $8.48/day |
| Unit cost | $6.488/1M-token | $1.126/1M-token |
| Inference savings | | 82.6% |

Điểm quan trọng là chi phí được đánh giá bằng `$/1M-token`, không chỉ bằng `$/GPU-hour`. `$/GPU-hour` cho biết giá thuê GPU, nhưng `$/1M-token` phản ánh tốt hơn hiệu quả thực tế: cùng một số tiền GPU có thể phục vụ được bao nhiêu token.

## 2. Savings by Lever

Các đòn bẩy tiết kiệm trong báo cáo:

| Lever | Monthly Savings |
|---|---:|
| Inference (cascade/cache/batch) | $1,212 |
| Purchasing (spot/reserved) | $10,040 |
| Right-size util-lies | $655 |
| Kill idle GPUs | $600 |

Đòn bẩy lớn nhất là purchasing optimization, tiết kiệm $10,040/tháng. Điều này cho thấy việc chọn đúng GPU purchasing tier có tác động rất lớn: workload có thể gián đoạn nên dùng spot, còn workload inference chạy ổn định nên dùng reserved.

Inference optimization cũng rất hiệu quả: cascade, prompt caching và batch API giảm chi phí inference từ $6.488/1M-token xuống $1.126/1M-token. Đây là mức giảm 82.6%, chứng minh rằng tối ưu routing và billing model có thể tạo tác động lớn mà không cần thay đổi hạ tầng GPU vật lý.

## 3. GPU-Util Lie

Mission 1 phát hiện các GPU có GPU utilization cao nhưng MFU thấp:

```text
GPU-Util LIES: ['gpu-h100-4', 'gpu-a10g-1']
```

Trường hợp nổi bật là `gpu-h100-4`:

| GPU | GPU-Util | MFU | MBU |
|---|---:|---:|---:|
| gpu-h100-4 | 98.2% | 0.194 | 0.207 |

GPU-Util gần 98% dễ tạo cảm giác GPU đang được dùng rất tốt. Tuy nhiên MFU chỉ khoảng 19.4%, nghĩa là workload chỉ khai thác được một phần nhỏ năng lực FLOPs của H100.

Nguyên nhân có thể là workload bị memory-bound, memory stall, I/O wait, kernel overhead hoặc batch size chưa phù hợp. Vì vậy, chỉ nhìn `nvidia-smi` hoặc GPU-Util là không đủ để ra quyết định FinOps. Cần theo dõi thêm MFU, MBU và chi phí trên mỗi token.

## 4. Inference Optimization

Mission 2 áp dụng ba chiến lược chính:

1. Cascade: route các request đơn giản sang model nhỏ.
2. Prompt caching: phần input đã cache được tính giá rẻ hơn.
3. Batch API: request không cần realtime được batch để giảm giá.

Kết quả:

```text
baseline  : $48.87/day   $6.488/1M-token
optimized : $8.48/day    $1.126/1M-token
savings   : 82.6%
```

Discount stack minh họa tác động nhân của các đòn bẩy:

```text
batch + 100% cache = 0.050 of naive
```

Điều này có nghĩa là khi request vừa dùng batch API vừa có 100% cached input, chi phí input-heavy có thể chỉ còn khoảng 5% so với naive baseline.

## 5. Purchasing Strategy

Mission 3 so sánh chi phí on-demand với chiến lược tối ưu gồm spot và reserved.

Kết quả:

```text
monthly: on-demand $25,667 -> optimized $15,627
savings: 39.1%
```

Các job được chọn spot:

- `job-train-llm`
- `job-train-embed`
- `job-finetune`
- `job-dev-sandbox`
- `job-batch-eval`

Các job này phù hợp với spot vì có thể gián đoạn hoặc checkpoint được.

Các job được chọn reserved:

- `job-infer-chat`
- `job-infer-rag`
- `job-infer-search`

Các job này phù hợp reserved vì chạy ổn định, duty cycle cao và vượt ngưỡng hòa vốn. Với reserved discount 45%, break-even utilization là khoảng 55%, tương đương 13.2 giờ/ngày.

## 6. Cost Allocation and Chargeback

Mission 4 phân bổ chi phí theo team:

| Team | Cost per day |
|---|---:|
| assistant | $2.59 |
| search | $2.49 |
| eval | $1.79 |
| rag | $1.60 |

Tag coverage:

```text
tag coverage: 92%
chargeback ready: True
```

Vì tag coverage đạt 92%, vượt ngưỡng 80%, NimbusAI có đủ độ tin cậy dữ liệu để chuyển từ showback sang chargeback. Nếu tag coverage thấp hơn 80%, chargeback sẽ rủi ro vì có thể tính sai chi phí cho các team.

File FOCUS export đã được tạo:

```text
outputs/focus_export.csv
```

FOCUS export quan trọng vì giúp chuẩn hóa dữ liệu chi phí, đặc biệt hữu ích khi tổ chức dùng nhiều cloud provider hoặc nhiều dịch vụ AI khác nhau.

## 7. Sustainability

Báo cáo tổng hợp ghi nhận:

| Metric | Value |
|---|---:|
| Energy per query | 0.24 Wh |
| Carbon per query | 0.091 gCO2e |
| Cheapest and cleanest region | europe-north1 |

Điều này cho thấy tối ưu FinOps không chỉ là tối ưu tiền, mà còn liên quan đến năng lượng và phát thải carbon. Với các workload có thể gián đoạn hoặc không yêu cầu latency thấp, có thể cân nhắc chuyển sang region sạch hơn như `europe-north1`.

## 8. Recommendations for NimbusAI

Ba hành động ưu tiên:

1. Tối ưu purchasing trước: dùng spot cho interruptible training/eval jobs và reserved cho inference workload ổn định.
2. Theo dõi `$/1M-token`, MFU và MBU thay vì chỉ nhìn `$/GPU-hour` hoặc GPU-Util.
3. Chuẩn hóa tagging để duy trì tag coverage trên 80%, từ đó triển khai chargeback công bằng cho từng team.

Các hành động tiếp theo:

1. Right-size các GPU có MFU thấp, đặc biệt các trường hợp GPU-Util cao nhưng hiệu quả thấp.
2. Tắt hoặc tự động scale down GPU idle để tránh lãng phí.
3. Áp dụng cascade, prompt caching và batch API cho inference traffic không yêu cầu realtime.
4. Bổ sung carbon-aware scheduling cho các job có thể gián đoạn.

## 9. Verification

Các kiểm tra core đã pass:

```text
python verify.py -> 11/11 checks passed
pytest -q        -> 15 passed
```

Các file output đã được tạo:

```text
outputs/report.md
outputs/savings.png
outputs/focus_export.csv
```

## 10. Your Turn Extensions

Đã triển khai 2 extension trong `missions/m6_extensions.py` và xuất báo cáo chi tiết ra:

```text
outputs/extensions.md
```

### Extension 1 - Reasoning Budget

Extension này tách riêng traffic `is_reasoning=1` để đo chi phí và năng lượng.

Kết quả:

| Metric | Value |
|---|---:|
| Total requests | 2,400 |
| Reasoning requests | 201 |
| Reasoning traffic share | 8.4% |
| Reasoning token share | 16.5% |
| Reasoning optimized cost share | 16.5% |
| Reasoning energy share | 94.0% |
| Estimated cost saved by capping reasoning to 5% traffic | $0.56/day |
| Estimated energy saved by cap | 12,004.0 Wh/day |

Insight: reasoning traffic chỉ chiếm 8.4% số request nhưng chiếm tới 94.0% năng lượng. Vì vậy, reasoning nên được quản trị bằng budget/routing rule riêng, ví dụ chỉ dùng khi task có độ phức tạp cao hoặc confidence của model thường thấp.

### Extension 2 - Carbon-aware Scheduling

Extension này ước tính lợi ích khi chuyển các job `interruptible=1` từ `us-east-1` sang `europe-north1`.

Kết quả:

| Metric | Value |
|---|---:|
| Source carbon at us-east-1 | 679.8 kgCO2e |
| Target carbon at europe-north1 | 53.7 kgCO2e |
| Carbon saved | 626.1 kgCO2e |
| Carbon reduction | 92.1% |
| Energy cost saved | $53.67 |

Các job được xét:

- `job-train-llm`
- `job-train-embed`
- `job-finetune`
- `job-dev-sandbox`
- `job-batch-eval`

Insight: các job interruptible là ứng viên tốt cho carbon-aware scheduling vì chúng ít nhạy cảm latency hơn inference realtime. Chuyển chúng sang region sạch hơn có thể giảm phát thải đáng kể mà không ảnh hưởng trực tiếp đến trải nghiệm người dùng.
