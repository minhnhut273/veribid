# Hướng dẫn nhanh VeriBid

Ứng dụng: <https://main.d2jw7e2fbiu6od.amplifyapp.com/app>

VeriBid giúp đối chiếu yêu cầu mua sắm với hồ sơ nhà cung cấp. Kết quả là gợi ý có dẫn chứng; người dùng phải tự review trước khi export. Ứng dụng không tự chọn nhà cung cấp thắng thầu.

## Chạy một evaluation

1. Mở **Open workspace**, đăng nhập và tạo evaluation với tên dễ nhận biết, ví dụ `Cloud platform procurement`.
2. Trong **Add the evaluation files**, chọn role `BUYER_RFP`, tải RFP; sau đó chọn `BUYER_RUBRIC` và tải rubric. File được tải ngay khi chọn.
3. Chọn **Extract requirements**. Chờ số requirement xuất hiện trong checkpoint **Requirements**.
4. Với mỗi vendor, chọn `VENDOR_PROPOSAL`, nhập **Vendor ID** và **Proposal ID**, rồi tải proposal. Chọn `VENDOR_PRICING`, dùng lại đúng cặp ID đó và tải bảng giá.
5. Chọn **Run evaluation**. Trong lúc chạy, xem trạng thái và tiến độ ở đầu trang.
6. Khi hiện **Evaluation complete**, chọn **View results**. Nút đưa thẳng đến **Evidence matrix**.
7. Chọn một ô trong ma trận để xem kết quả, bằng chứng, source pointer và xung đột liên quan. Chọn `ACCEPT system suggestion` nếu đồng ý rồi bấm **Record review**; chỉ chọn `OVERRIDE with rationale` khi có căn cứ và điền lý do.
8. Khi mọi kết quả đã được review, dùng **Export PDF** hoặc **Export Markdown**.

## Đọc ma trận

- Mỗi hàng là một requirement; mỗi cột là một vendor scope.
- Trạng thái trong ô là gợi ý của hệ thống hoặc trạng thái cuối sau review. Mở ô để phân biệt hai phần.
- **CONFLICTING EVIDENCE**: các nguồn có thông tin mâu thuẫn; kiểm tra cả hai phía.
- **INSUFFICIENT EVIDENCE**: hồ sơ thiếu hoặc chưa đủ căn cứ; không tự suy ra là đạt.
- **Needs human review**: chưa có quyết định của người dùng.

## Bộ dữ liệu thực hành

Giải nén một ZIP trong `fixtures/datasets/` rồi mở `README_upload_vi.md` bên trong bộ đó. Mỗi bộ gồm RFP, rubric, ba proposal và ba pricing workbook; cần tạo evaluation riêng cho từng bộ.

| Bộ | Vendor ID / Proposal ID |
|---|---|
| Cloud platform | `VEN_CLOUD_A` / `PROP_CLOUD_A`; `VEN_CLOUD_B` / `PROP_CLOUD_B`; `VEN_CLOUD_C` / `PROP_CLOUD_C` |
| E-signature SaaS | `VEN_ESIGN_A` / `PROP_ESIGN_A`; `VEN_ESIGN_B` / `PROP_ESIGN_B`; `VEN_ESIGN_C` / `PROP_ESIGN_C` |
| Invoice OCR | `VEN_OCR_A` / `PROP_OCR_A`; `VEN_OCR_B` / `PROP_OCR_B`; `VEN_OCR_C` / `PROP_OCR_C` |

Các proposal, tên nhà cung cấp và giá trong ba bộ là dữ liệu mô phỏng. Chỉ CSV trong `public_reference/` là bản ghi hợp đồng công khai để tham khảo; không upload CSV đó như bằng chứng của vendor. Không upload `sources.md` hoặc `expected_signals.md` vào evaluation.

## Nếu bị kẹt

- Nút chọn file của vendor bị khóa: nhập cả Vendor ID và Proposal ID trước.
- Vừa chọn file mà chưa thấy tài liệu: chờ dòng xác nhận upload và kiểm tra **Document ledger**.
- Run hoàn tất nhưng chưa thấy bảng: chọn **View results** ở thông báo hoàn tất.
- Không export được: kiểm tra số **need human review**; mọi kết quả cần được người dùng xác nhận hoặc override trước.
- Nếu có lỗi đỏ trong **Pipeline checkpoints**, xử lý lỗi đó rồi thử lại; đừng đổi vendor/proposal ID giữa proposal và pricing.
