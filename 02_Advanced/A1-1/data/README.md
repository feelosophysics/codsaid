# 내 데이터로 실행하기

아래 형식으로 변환한 파일을 `data/external/`처럼 별도 폴더에 두고 경로를 지정하세요. 임의의 데이터를 자동으로 변환해 주는 도구는 아니에요.

```bash
uv run python -m src.run_analysis --data-dir data/external --output-dir results/external --reference-date 2026-10-10 --observation-end 2026-10-09
```

| 파일 | 필요한 내용 |
| --- | --- |
| `transactions.csv` | `line_id`, `order_id`, `customer_id`, `order_date`, `product_id`, `unit_price`, `quantity`, `amount`, `shipping_days`. `amount`는 그 행의 금액이어야 해요. 주문 전체 금액을 행마다 반복하면 안 돼요 |
| `products.csv` | `product_id`(중복 없음), `product_name`, `category`(빈칸 없음), `catalog_price`, `rating`, `image_index`(0부터 시작하는 위치) |
| `images.npy` | 크기와 픽셀 범위가 같은 숫자 배열. 모양은 `(N,H,W)` 또는 `(N,H,W,C)`이고, pickle 배열은 안 돼요 |
| `customers.csv` (코호트 보너스용) | `customer_id`, `signup_date`. 구매하지 않은 가입 고객도 넣어요. 다른 위치면 `--customers-path`로 지정하고, 가입일이 없으면 `--skip-bonus`로 필수 분석만 돌려요 |

## 주의할 점

- `--generate-sample`은 지정한 폴더의 샘플 파일을 덮어쓰니 실제 데이터 폴더에는 쓰지 마세요.
- 표를 잘못 연결했거나, `line_id`가 중복되거나, 한 주문에 고객이나 날짜가 여러 개이거나, `amount`가 `unit_price × quantity`와 다르면 분석이 오류로 멈춰요.
- 고객, 주문, 날짜가 유효하지 않거나 구매 금액이 양수가 아닌 행은 RFM에서 빠져요. 실행 후 실제 그룹 수와 뺀 행 수를 `audit.json`에서 확인하세요.
